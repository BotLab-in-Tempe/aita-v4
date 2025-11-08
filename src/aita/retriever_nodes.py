from __future__ import annotations

from typing import Dict, Any, Literal

from langchain.messages import SystemMessage
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command
from langgraph.runtime import Runtime

from aita.state import (
    AitaState,
    Context,
    ProbePlannerOutput,
    ResponseGeneratorOutput,
)
from aita.prompts import PROMPTS
from aita.configuration import Configuration
from langchain.chat_models import init_chat_model
from aita.utils import build_docker_env_for_user
from aita.tools import make_execute_bash_tool
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI


async def probe_planner(
    state: AitaState, config: RunnableConfig, runtime: Runtime[Context]
) -> Command[Literal["cli_agent"]]:

    configurable = Configuration.from_runnable_config(config)
    model = (
        init_chat_model(configurable_fields=("model", "max_tokens", "api_key"))
        .with_structured_output(ProbePlannerOutput, method="function_calling")
        .with_retry(stop_after_attempt=configurable.max_structured_output_retries)
        .with_config(
            {
                "model": configurable.main_model,
                "max_tokens": configurable.small_tokens,
                "api_key": config.get("api_key"),
                "tags": ["langsmith:nostream"],
            }
        )
    )

    # Get the AITA trace
    trace = state.get("trace", [])
    trace_text = "\n".join(trace) if trace else "No trace yet"
    
    student_environment_context = (
        PROMPTS["student_environment_context"].content
        if "student_environment_context" in PROMPTS
        and PROMPTS["student_environment_context"].content.strip()
        else "No previous environment context."
    )

    prompt_content = PROMPTS["probe_planner_system_prompt"].content.format(
        aita_trace=trace_text,
        student_environment_context=student_environment_context,
    )

    messages = state.get("messages", [])[-6:]  # Last 3 turns
    cli_trace = state.get("cli_trace", []) or []

    response: ProbePlannerOutput = await model.ainvoke(
        [SystemMessage(content=prompt_content), *messages, *cli_trace]
    )

    return Command(
        goto="cli_agent",
        update={
            "probe_task": response.probe_task,
        },
    )


async def cli_agent(
    state: AitaState, config: RunnableConfig, runtime: Runtime[Context]
) -> Command[Literal["__end__"]]:

    configurable = Configuration.from_runnable_config(config)

    model = ChatOpenAI(
        api_key=config.get("api_key"),
        model="gpt-4o",
        temperature=0,
    )

    docker_env = await build_docker_env_for_user(runtime.context.user_id)
    execute_bash_tool = make_execute_bash_tool(docker_env)

    # Get probe_task from probe_planner
    probe_task = state.get("probe_task") or "No probe task"
    student_environment_context = (
        PROMPTS["student_environment_context"].content
        if "student_environment_context" in PROMPTS
        and PROMPTS["student_environment_context"].content.strip()
        else "No previous environment context."
    )

    formatted_prompt = PROMPTS["cli_agent_system_prompt"].content.format(
        probe_task=probe_task,
        student_environment_context=student_environment_context
    )

    agent = create_agent(
        model=model, tools=[execute_bash_tool], system_prompt=formatted_prompt
    )

    result = await agent.ainvoke({"messages": state.get("cli_trace", [])})

    return Command(
        goto="response_generator",
        update={
            "cli_trace": result.get("messages", []),
        },
    )


async def response_generator(
    state: AitaState, config: RunnableConfig, runtime: Runtime[Context]
) -> Command[Literal["__end__"]]:

    configurable = Configuration.from_runnable_config(config)

    model = (
        init_chat_model(configurable_fields=("model", "max_tokens", "api_key"))
        .with_structured_output(ResponseGeneratorOutput, method="function_calling")
        .with_config(
            {
                "model": configurable.main_model,
                "max_tokens": 4096,  # Enough for focused summaries with necessary content
                "api_key": config.get("api_key"),
                "tags": ["langsmith:nostream"],
            }
        )
    )

    cli_trace = state.get("cli_trace", []) or []
    
    # Get the AITA trace
    trace = state.get("trace", [])
    trace_text = "\n".join(trace) if trace else "No trace yet"
    
    probe_task = state.get("probe_task") or "No probe task"

    prompt_content = PROMPTS["response_generator_system_prompt"].content.format(
        probe_task=probe_task,
        aita_trace=trace_text
    )

    response: ResponseGeneratorOutput = await model.ainvoke(
        [SystemMessage(content=prompt_content)] + cli_trace
    )

    # Commented out cli_trace_summarizer for now - going directly to END
    return Command(
        goto="__end__",
        update={
            "trace": [f"[Retriever] {response.response}"],
        },
    )


async def cli_trace_summarizer(
    state: AitaState, config: RunnableConfig, runtime: Runtime[Context]
) -> Dict[str, Any]:
    cli_trace = state.get("cli_trace", []) or []

    if not cli_trace:
        return {}

    # Configure model (use small model for summarization)
    configurable = Configuration.from_runnable_config(config)
    model = init_chat_model(
        configurable_fields=("model", "max_tokens", "api_key")
    ).with_config(
        {
            "model": configurable.small_model,
            "max_tokens": configurable.medium_tokens,
            "api_key": config.get("api_key"),
            "tags": ["langsmith:nostream"],
        }
    )

    student_environment_context = (
        PROMPTS["student_environment_context"].content
        if "student_environment_context" in PROMPTS
        and PROMPTS["student_environment_context"].content.strip()
        else "No previous environment context."
    )

    prompt_content = PROMPTS["cli_trace_summarizer_system_prompt"].content.format(
        environment_context=student_environment_context
    )

    cli_trace = state.get("cli_trace", []) or []

    response = await model.ainvoke([SystemMessage(content=prompt_content)] + cli_trace)

    summary_text = response.content if hasattr(response, "content") else str(response)

    return {"cli_trace": {"type": "override", "value": [SystemMessage(content=summary_text)]}}
