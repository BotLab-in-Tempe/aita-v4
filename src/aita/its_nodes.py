from __future__ import annotations

from typing import Any, Dict, Literal, Optional

from langgraph.types import Command
from langgraph.runtime import Runtime
from langchain_core.messages import SystemMessage, HumanMessage
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
from aita.utils import format_plan_md, with_error_escalation


@with_error_escalation("context_gate")
async def context_gate(
    state: AitaState, config: RunnableConfig, runtime: Runtime[Context]
) -> Command[Literal["retriever", "evaluator"]]:
    configurable = Configuration.from_runnable_config(config)
    model = (
        init_chat_model(configurable_fields=("model", "reasoning_effort", "verbosity", "api_key"))
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

    trace_list = state.get("trace", []) or []

    plan = state.get("plan")
    plan_cursor = state.get("plan_cursor", 0)
    formatted_plan = (
        format_plan_md(plan, title="Current Plan", plan_cursor=plan_cursor)
        if plan and plan.subgoals
        else "No plan"
    )

    project_display = (
        runtime.context.project_id if runtime.context.project_id else "unspecified"
    )
    context_header = f"**Session Context:**\n- Course: {runtime.context.course_code}\n- Project: {project_display}\n\n"
    prompt_content = context_header + PROMPTS[
        "context_gate_system_prompt"
    ].content.format(
        plan=formatted_plan,
        trace="\n\n".join(trace_list) if trace_list else "No previous evaluations",
    )
    messages = state.get("messages", [])[-6:]

    response: ContextGateOutput = await model.ainvoke(
        [SystemMessage(content=prompt_content), *messages]
    )

    if response.need_retrieval:
        return Command(
            goto="retriever"
        )
    else:
        return Command(
            goto="evaluator"
        )


@with_error_escalation("evaluator")
async def evaluator(
    state: AitaState, config: RunnableConfig, runtime: Runtime[Context]
) -> Command[Literal["planner", "dialogue_manager"]]:
    configurable = Configuration.from_runnable_config(config)
    model = (
        init_chat_model(configurable_fields=("model", "reasoning_effort", "verbosity", "api_key"))
        .with_structured_output(EvaluatorOutput, method="function_calling")
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

    plan = state.get("plan")
    plan_cursor = state.get("plan_cursor", 0)
    formatted_plan = (
        format_plan_md(plan, title="Current Plan", plan_cursor=plan_cursor)
        if plan and plan.subgoals
        else "No plan"
    )
    trace_list = state.get("trace", []) or []

    prompt_content = PROMPTS["evaluator_system_prompt"].content.format(
        trace="\n\n".join(trace_list) if trace_list else "No previous evaluations",
        current_plan=formatted_plan,
    )

    messages = state.get("messages", [])[-6:]

    response: EvaluatorOutput = await model.ainvoke(
        [SystemMessage(content=prompt_content), *messages]
    )

    trace_entry = f"[Evaluator] {response.reasoning}\nNeed plan: {response.need_plan}"

    if response.completed_subgoals:
        max_completed_index = max(response.completed_subgoals)
        new_cursor = max_completed_index + 1
        completed_indices = ", ".join(
            str(i) for i in sorted(response.completed_subgoals)
        )
        trace_entry += f"\nCompleted subgoals: {completed_indices}"

    update = {"trace": [trace_entry]}

    if response.completed_subgoals:
        max_completed_index = max(response.completed_subgoals)
        new_cursor = max_completed_index + 1
        update["plan_cursor"] = new_cursor

    if response.need_plan:
        return Command(goto="planner", update=update)
    else:
        return Command(goto="dialogue_manager", update=update)


@with_error_escalation("planner")
async def planner(
    state: AitaState, config: RunnableConfig, runtime: Runtime[Context]
) -> Dict[str, Any]:
    """
    Planner - Creates or revises the tutoring plan using the existing trace context.
    """
    # Configure model
    configurable = Configuration.from_runnable_config(config)
    model = (
        init_chat_model(configurable_fields=("model", "reasoning_effort", "verbosity", "api_key"))
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

    # Extract state
    trace_list = state.get("trace", []) or []
    existing_plan = state.get("plan")
    plan_cursor = state.get("plan_cursor", 0) or 0

    # Build unified planning/replanning prompt
    formatted_plan = (
        format_plan_md(existing_plan, title="Current Plan", plan_cursor=plan_cursor)
        if existing_plan and existing_plan.subgoals
        else "No plan"
    )
    prompt_content = PROMPTS["planner_system_prompt"].content.format(
        trace="\n\n".join(trace_list) if trace_list else "No previous trace",
        current_plan=formatted_plan,
    )

    messages = state.get("messages", [])[-6:]

    # Invoke model
    response: PlannerOutput = await model.ainvoke(
        [SystemMessage(content=prompt_content), *messages]
    )

    # Return plan update
    if not response.plan or not response.plan.subgoals:
        return {}

    from aita.state import Plan

    new_subgoals = response.plan.subgoals

    # Always return a full Plan (replaces entire plan when replanning)
    return {"plan": Plan(subgoals=new_subgoals), "plan_cursor": 0}


@with_error_escalation("dialogue_manager")
async def dialogue_manager(
    state: AitaState, config: RunnableConfig, runtime: Runtime[Context]
) -> Command[Literal["summarize_trace", "__end__"]]:
    """
    Dialogue Manager - Generates the final response to the student.
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

    trace_list = state.get("trace", []) or []
    plan = state.get("plan")
    plan_cursor = state.get("plan_cursor", 0)
    formatted_plan = (
        format_plan_md(plan, title="Current Plan", plan_cursor=plan_cursor)
        if plan and plan.subgoals
        else "No plan"
    )

    project_display = (
        runtime.context.project_id if runtime.context.project_id else "unspecified"
    )
    
    student_env_summary = (
        "Students work in isolated VS Code containers on pwn.college. Template files and model binaries (modelgood/modelbad) are pre-loaded. Testing uses system_tests and user_tests."
        if "student_environment_context" in PROMPTS
        and PROMPTS["student_environment_context"].content.strip()
        else ""
    )
    
    context_header = f"**Session Context:**\n- Course: {runtime.context.course_code}\n- Project: {project_display}"
    if student_env_summary:
        context_header += f"\n- Environment: {student_env_summary}"
    context_header += "\n\n"

    system_prompt = PROMPTS["dialogue"].content
    prompt_content = context_header + system_prompt.format(
        trace="\n\n".join(trace_list) if trace_list else "No previous trace",
        plan=formatted_plan,
    )

    messages = state.get("messages", [])[-6:]  # Last 3 turns

    response = await model.ainvoke([SystemMessage(content=prompt_content), *messages])

    threshold = configurable.trace_summarization_threshold
    next_node = "summarize_trace" if len(trace_list) >= threshold else "__end__"

    return Command(
        goto=next_node,
        update={
            "messages": [response],
        },
    )


@with_error_escalation("summarize_trace")
async def summarize_trace(
    state: AitaState, config: RunnableConfig, runtime: Runtime[Context]
) -> Dict[str, Any]:
    trace_list = state.get("trace", []) or []

    # Configure model (use small model for summarization)
    configurable = Configuration.from_runnable_config(config)
    threshold = configurable.trace_summarization_threshold

    if len(trace_list) < threshold:
        return {}

    model = init_chat_model(
        configurable_fields=("model", "reasoning_effort", "verbosity", "api_key")
    ).with_config(
        {
            "model": "openai:gpt-5.1",
            "reasoning_effort": "low",
            "verbosity": "medium",
            "api_key": config.get("api_key"),
            "tags": ["langsmith:nostream"],
        }
    )

    # Summarize all entries into one comprehensive summary
    trace_entries_text = "\n\n".join(f"- {entry}" for entry in trace_list)

    # Get the current plan for context
    plan = state.get("plan")
    plan_cursor = state.get("plan_cursor", 0)
    formatted_plan = (
        format_plan_md(plan, title="Current Plan", plan_cursor=plan_cursor)
        if plan and plan.subgoals
        else "No plan"
    )

    prompt_content = PROMPTS["trace_summarizer_system_prompt"].content.format(
        trace_entries=trace_entries_text, current_plan=formatted_plan
    )

    response = await model.ainvoke([SystemMessage(content=prompt_content)])

    summary_text = response.content if hasattr(response, "content") else str(response)

    return {"trace": {"type": "override", "value": [summary_text]}}
