from __future__ import annotations

from typing import Literal

from langchain.messages import SystemMessage
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command
from langgraph.runtime import Runtime

from aita.state import (
    AitaState,
    Context,
    ProbePlannerOutput,
)
from aita.prompts import PROMPTS
from aita.configuration import Configuration
from langchain.chat_models import init_chat_model
from aita.utils import build_docker_env_for_user, with_error_escalation
from aita.tools import make_execute_bash_tool
from langchain.agents import create_agent


@with_error_escalation("probe_planner")
async def probe_planner(
    state: AitaState, config: RunnableConfig, runtime: Runtime[Context]
) -> Command[Literal["cli_agent"]]:
    """
    Probe Planner - Plans probe tasks to gather diagnostic information from the student's environment.
    """

    configurable = Configuration.from_runnable_config(config)
    model = (
        init_chat_model(
            configurable_fields=("model", "reasoning_effort", "verbosity", "api_key")
        )
        .with_structured_output(ProbePlannerOutput, method="function_calling")
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

    sandbox_environment_context = (
        PROMPTS["sandbox_environment_context"].content
        if "sandbox_environment_context" in PROMPTS
        and PROMPTS["sandbox_environment_context"].content.strip()
        else "No previous environment context."
    )

    plan = state.get("plan")

    project_display = (
        runtime.context.project_id if runtime.context.project_id else "unspecified"
    )
    context_header = f"**Session Context:**\n- Course: {runtime.context.course_code}\n- Project: {project_display}\n\n"

    prompt_content = context_header + PROMPTS[
        "probe_planner_system_prompt"
    ].content.format(
        sandbox_environment_context=sandbox_environment_context,
        plan="\n\n".join(plan) if plan else "No plan",
    )

    messages = state.get("messages", [])

    response: ProbePlannerOutput = await model.ainvoke(
        [SystemMessage(content=prompt_content), *messages]
    )

    return Command(
        goto="cli_agent",
        update={
            "probe_task": response.probe_task,
        },
    )


@with_error_escalation("cli_agent")
async def cli_agent(
    state: AitaState, config: RunnableConfig, runtime: Runtime[Context]
) -> Command[Literal["__end__"]]:
    """
    CLI Agent - Executes bash commands in the student's Docker environment to gather diagnostic information.
    """

    configurable = Configuration.from_runnable_config(config)

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

    docker_env = await build_docker_env_for_user(runtime.context.user_id)
    execute_bash_tool = make_execute_bash_tool(docker_env)

    probe_task = state.get("probe_task") or "No probe task"
    sandbox_environment_context = (
        PROMPTS["sandbox_environment_context"].content
        if "sandbox_environment_context" in PROMPTS
        and PROMPTS["sandbox_environment_context"].content.strip()
        else "No previous environment context."
    )

    project_display = (
        runtime.context.project_id if runtime.context.project_id else "unspecified"
    )
    context_header = f"**Session Context:**\n- Course: {runtime.context.course_code}\n- Project: {project_display}\n\n"

    formatted_prompt = context_header + PROMPTS[
        "cli_agent_system_prompt"
    ].content.format(
        probe_task=probe_task, sandbox_environment_context=sandbox_environment_context
    )

    agent = create_agent(
        model=model, tools=[execute_bash_tool], system_prompt=formatted_prompt
    )

    result = await agent.ainvoke({"messages": state.get("cli_trace", [])})

    return Command(
        goto="diagnoser",
        update={
            "cli_trace": result.get("messages", []),
        },
    )


@with_error_escalation("diagnoser")
async def diagnoser(
    state: AitaState, config: RunnableConfig, runtime: Runtime[Context]
) -> Command[Literal["__end__"]]:
    """
    Diagnoser - Analyzes CLI trace output and generates diagnostic insights about the student's issue.
    """
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

    cli_trace = state.get("cli_trace", []) or []

    plan = state.get("plan")

    project_display = (
        runtime.context.project_id if runtime.context.project_id else "unspecified"
    )
    context_header = f"**Session Context:**\n- Course: {runtime.context.course_code}\n- Project: {project_display}\n\n"

    prompt_content = context_header + PROMPTS["diagnoser_system_prompt"].content.format(
        plan="\n\n".join(plan) if plan else "No plan",
    )
    messages = state.get("messages", [])

    response = await model.ainvoke(
        [SystemMessage(content=prompt_content), *messages, *cli_trace]
    )

    diagnosis_text = response.content if isinstance(response, AIMessage) else ""

    return Command(
        goto="__end__",
        update={
            "messages": [SystemMessage(content=f"[Diagnoser] {diagnosis_text}")],
            "cli_trace": {"type": "override", "value": []},
        },
    )
