from __future__ import annotations

from typing import Any, Dict, Literal

from langgraph.types import Command
from langgraph.runtime import Runtime
from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain.chat_models import init_chat_model

from aita.state import AitaState, Context
from aita.configuration import Configuration
from aita.prompts import PROMPTS
from aita.state import (
    ContextGateOutput,
    EvaluatorOutput,
    PlannerOutput,
)
from aita.utils import with_error_escalation


@with_error_escalation("context_gate")
async def context_gate(
    state: AitaState, config: RunnableConfig, runtime: Runtime[Context]
) -> Command[Literal["retriever", "evaluator"]]:
    configurable = Configuration.from_runnable_config(config)
    model = (
        init_chat_model(
            configurable_fields=("model", "reasoning_effort", "verbosity", "api_key")
        )
        .with_structured_output(ContextGateOutput, method="function_calling")
        .with_retry(stop_after_attempt=configurable.max_structured_output_retries)
        .with_config(
            {
                "model": "openai:gpt-5.1",
                "reasoning_effort": "low",
                "verbosity": "low",
                "api_key": config.get("api_key"),
                "tags": ["langsmith:nostream"],
            }
        )
    )

    project_display = (
        runtime.context.project_id if runtime.context.project_id else "unspecified"
    )
    context_header = f"**Session Context:**\n- Course: {runtime.context.course_code}\n- Project: {project_display}\n\n"
    plan = state.get("plan")

    prompt_content = context_header + PROMPTS[
        "context_gate_system_prompt"
    ].content.format(plan="\n\n".join(plan) if plan else "No plan")

    messages = state.get("messages", [])

    response: ContextGateOutput = await model.ainvoke(
        [SystemMessage(content=prompt_content), *messages]
    )

    if response.need_retrieval:
        return Command(goto="retriever")
    else:
        return Command(goto="evaluator")


@with_error_escalation("evaluator")
async def evaluator(
    state: AitaState, config: RunnableConfig, runtime: Runtime[Context]
) -> Command[Literal["planner", "dialogue_generator"]]:
    configurable = Configuration.from_runnable_config(config)
    model = (
        init_chat_model(
            configurable_fields=("model", "reasoning_effort", "verbosity", "api_key")
        )
        .with_structured_output(EvaluatorOutput, method="function_calling")
        .with_retry(stop_after_attempt=configurable.max_structured_output_retries)
        .with_config(
            {
                "model": "openai:gpt-5.1",
                "reasoning_effort": "medium",
                "verbosity": "low",
                "api_key": config.get("api_key"),
                "tags": ["langsmith:nostream"],
            }
        )
    )

    plan = state.get("plan")

    gaurdrails = (
        PROMPTS["tutoring_gaurdrails"].content.strip()
        if "tutoring_gaurdrails" in PROMPTS
        else ""
    )
    tutoring_philosophy = (
        PROMPTS["tutoring_philosophy"].content.strip()
        if "tutoring_philosophy" in PROMPTS
        else ""
    )
    prompt_content = PROMPTS["evaluator_system_prompt"].content.format(
        gaurdrails=gaurdrails,
        tutoring_philosophy=tutoring_philosophy,
        plan="\n\n".join(plan) if plan else "No plan",
    )

    messages = state.get("messages", [])

    response: EvaluatorOutput = await model.ainvoke(
        [SystemMessage(content=prompt_content), *messages]
    )

    update: Dict[str, Any] = {}
    new_messages: list[Any] = []

    # Track evaluator control flags in state for downstream nodes
    update["escalate"] = {
        "type": "override",
        "value": response.escalate,
    }
    update["should_respond"] = {
        "type": "override",
        "value": response.should_respond,
    }

    # Handle completed subgoals by trimming the plan queue
    if response.completed_subgoals and plan and isinstance(plan, list):
        completed_sorted = sorted(response.completed_subgoals, reverse=True)
        updated_plan = list(plan)
        for idx in completed_sorted:
            if 0 <= idx < len(updated_plan):
                subgoal_text = updated_plan[idx]
                updated_plan.pop(idx)
                new_messages.append(
                    SystemMessage(
                        content=f"[Evaluator] Subgoal {subgoal_text} marked as completed"
                    )
                )
        update["plan"] = {"type": "override", "value": updated_plan}

    # Log evaluator's internal decision message, if provided
    if response.message:
        new_messages.append(SystemMessage(content=f"[Evaluator] {response.message}"))

    if new_messages:
        update["messages"] = new_messages

    if response.need_plan:
        return Command(goto="planner", update=update)
    else:
        return Command(goto="dialogue_generator", update=update)


@with_error_escalation("planner")
async def planner(
    state: AitaState, config: RunnableConfig, runtime: Runtime[Context]
) -> Dict[str, Any]:
    """
    Planner - Creates or revises the tutoring plan using conversation history and current plan.
    """
    # Configure model
    configurable = Configuration.from_runnable_config(config)
    model = (
        init_chat_model(
            configurable_fields=("model", "reasoning_effort", "verbosity", "api_key")
        )
        .with_structured_output(PlannerOutput, method="function_calling")
        .with_retry(stop_after_attempt=configurable.max_structured_output_retries)
        .with_config(
            {
                "model": "openai:gpt-5.1",
                "reasoning_effort": "low",
                "verbosity": "medium",
                "api_key": config.get("api_key"),
                "tags": ["langsmith:nostream"],
            }
        )
    )

    plan = state.get("plan")

    gaurdrails = (
        PROMPTS["tutoring_gaurdrails"].content.strip()
        if "tutoring_gaurdrails" in PROMPTS
        else ""
    )
    tutoring_philosophy = (
        PROMPTS["tutoring_philosophy"].content.strip()
        if "tutoring_philosophy" in PROMPTS
        else ""
    )
    prompt_content = PROMPTS["planner_system_prompt"].content.format(
        gaurdrails=gaurdrails,
        tutoring_philosophy=tutoring_philosophy,
        plan="\n\n".join(plan) if plan else "No plan",
    )

    messages = state.get("messages", [])

    response: PlannerOutput = await model.ainvoke(
        [SystemMessage(content=prompt_content), *messages]
    )

    if not response.plan:
        return {}

    new_messages = []

    new_messages.append(SystemMessage(content=f"[Planner] New plan created"))

    return {
        "plan": {"type": "override", "value": response.plan},
        "messages": new_messages,
    }


@with_error_escalation("dialogue_generator")
async def dialogue_generator(
    state: AitaState, config: RunnableConfig, runtime: Runtime[Context]
) -> Command[Literal["summarize_messages", "__end__"]]:
    """
    Dialogue Generator - Generates the final response to the student.
    """
    configurable = Configuration.from_runnable_config(config)
    model = init_chat_model(
        configurable_fields=("model", "max_completion_tokens", "temperature", "api_key")
    ).with_config(
        {
            "model": "openai:gpt-5.1-chat-latest",
            "max_completion_tokens": "1024",
            "temperature": 1,
            "api_key": config.get("api_key"),
            "tags": ["langsmith:nostream"],
        }
    )

    plan = state.get("plan")

    project_display = (
        runtime.context.project_id if runtime.context.project_id else "unspecified"
    )

    student_env_summary = (
        PROMPTS["student_environment_context"].content.strip()
        if "student_environment_context" in PROMPTS
        else ""
    )

    context_header = f"**Session Context:**\n- Course: {runtime.context.course_code}\n- Project: {project_display}"
    if student_env_summary:
        context_header += f"\n- Environment: {student_env_summary}"
    context_header += "\n\n"

    gaurdrails = (
        PROMPTS["tutoring_gaurdrails"].content.strip()
        if "tutoring_gaurdrails" in PROMPTS
        else ""
    )
    tutoring_philosophy = (
        PROMPTS["tutoring_philosophy"].content.strip()
        if "tutoring_philosophy" in PROMPTS
        else ""
    )
    system_prompt = PROMPTS["dialogue_generator"].content
    prompt_content = context_header + system_prompt.format(
        gaurdrails=gaurdrails,
        tutoring_philosophy=tutoring_philosophy,
        plan="\n\n".join(plan) if plan else "No plan",
    )

    messages = state.get("messages", [])
    should_respond = state.get("should_respond", True)

    threshold = configurable.message_summarization_threshold
    next_node = "summarize_messages" if len(messages) >= threshold else "__end__"

    # If evaluator indicates no response is needed, skip generation and just continue flow
    if not should_respond:
        return Command(goto=next_node, update={})

    response = await model.ainvoke([SystemMessage(content=prompt_content), *messages])

    return Command(
        goto=next_node,
        update={
            "messages": [response],
        },
    )


@with_error_escalation("summarize_messages")
async def summarize_messages(
    state: AitaState, config: RunnableConfig, runtime: Runtime[Context]
) -> Dict[str, Any]:
    trace_list = state.get("trace", []) or []

    # Configure model (use small model for summarization)
    configurable = Configuration.from_runnable_config(config)
    threshold = configurable.message_summarization_threshold

    if len(trace_list) < threshold:
        return {}

    model = init_chat_model(
        configurable_fields=("model", "reasoning_effort", "verbosity", "api_key")
    ).with_config(
        {
            "model": "openai:gpt-5.1",
            "reasoning_effort": "low",
            "verbosity": "low",
            "api_key": config.get("api_key"),
            "tags": ["langsmith:nostream"],
        }
    )

    plan = state.get("plan")

    prompt_content = PROMPTS["message_summarizer_system_prompt"].content.format(
        plan="\n\n".join(plan) if plan else "No plan"
    )

    messages = state.get("messages", [])

    response = await model.ainvoke([SystemMessage(content=prompt_content), *messages])

    summary_text = response.content if hasattr(response, "content") else str(response)

    return {
        "messages": {"type": "override", "value": [SystemMessage(content=summary_text)]}
    }
