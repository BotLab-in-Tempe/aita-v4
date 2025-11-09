from __future__ import annotations
import os

from langgraph.graph import StateGraph, START, END
from langgraph.types import Command
from langgraph.runtime import Runtime
from langchain_core.runnables import RunnableConfig

from aita.state import (
    AitaState,
    Context,
)
from aita.configuration import Configuration
from aita.retriever_nodes import (
    probe_planner,
    cli_agent,
    response_generator,
)
from aita.its_nodes import (
    context_gate,
    evaluator,
    planner,
    dialogue_manager,
    summarize_trace,
)
from urllib.parse import quote_plus
from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from aita.logger import get_logger

logger = get_logger()
# Store-related imports commented out
# from langgraph.store.postgres.aio import AsyncPostgresStore
# from langgraph.store.base import BaseStore
# from langchain.embeddings import init_embeddings


def _dsn() -> str:
    return (
        "postgresql://"
        f"{quote_plus(os.getenv('PGUSER'))}:{quote_plus(os.getenv('PGPASSWORD'))}"
        f"@{os.getenv('PGHOST')}:{os.getenv('PGPORT')}/{os.getenv('PGDATABASE')}"
    )


async def init_checkpointer(
    max_size: int = 10,
) -> tuple[AsyncConnectionPool, AsyncPostgresSaver]:
    pg_host = os.getenv("PGHOST", "unknown")
    pg_port = os.getenv("PGPORT", "unknown")
    pg_db = os.getenv("PGDATABASE", "unknown")

    logger.info(
        f"Initializing PostgreSQL connection pool - "
        f"host={pg_host}, port={pg_port}, database={pg_db}, max_size={max_size}"
    )

    try:
        pool = AsyncConnectionPool(
            _dsn(),
            open=False,
            max_size=max_size,
            kwargs={
                "autocommit": True,
                "connect_timeout": 5,
                "prepare_threshold": None,
            },
        )
        await pool.open()
        logger.info("PostgreSQL connection pool opened successfully")

        saver = AsyncPostgresSaver(pool)
        await saver.setup()
        logger.info("AsyncPostgresSaver setup complete")

        return pool, saver
    except Exception as e:
        logger.error(
            f"Failed to initialize PostgreSQL checkpointer - "
            f"host={pg_host}, port={pg_port}, database={pg_db}, "
            f"error={type(e).__name__}: {str(e)}"
        )
        raise


def create_retriever_subgraph():
    builder = StateGraph(
        AitaState,
        input=AitaState,
        config_schema=Configuration,
        context_schema=Context,
    )
    builder.add_node("probe_planner", probe_planner)
    builder.add_node("cli_agent", cli_agent)
    builder.add_node("response_generator", response_generator)

    builder.add_edge(START, "probe_planner")
    builder.add_edge("probe_planner", "cli_agent")
    builder.add_edge("cli_agent", "response_generator")
    builder.add_edge("response_generator", END)

    return builder.compile()


retriever_subgraph = create_retriever_subgraph()


def create_aita_graph(checkpointer=None):  # Removed store parameter
    builder = StateGraph(AitaState, config_schema=Configuration, context_schema=Context)
    builder.add_node("retriever", retriever_subgraph)
    builder.add_node("context_gate", context_gate)
    builder.add_node("evaluator", evaluator)
    builder.add_node("planner", planner)
    builder.add_node("dialogue_manager", dialogue_manager)
    builder.add_node("summarize_trace", summarize_trace)

    builder.add_edge(START, "context_gate")
    builder.add_edge("retriever", "evaluator")
    builder.add_edge("planner", "dialogue_manager")
    builder.add_edge("summarize_trace", END)

    return builder.compile(
        name="aita", checkpointer=checkpointer
    )  # Removed store parameter


async def make_graph():
    pool, saver = await init_checkpointer(max_size=20)
    # Store setup commented out
    # embeddings = init_embeddings("openai:text-embedding-3-small")
    # store_cm = AsyncPostgresStore.from_conn_string(
    #     _dsn(),
    #     index={
    #         "embed": embeddings,
    #         "dims": 1536,
    #         # Pick a safe default. If you plan to *always* pass `index=` at write time,
    #         # you can set fields to an empty list (or a harmless field you never use).
    #         "fields": [],  # nothing is embedded by default
    #     },
    # )
    # store = await store_cm.__aenter__()
    # await store.setup()

    graph = create_aita_graph(checkpointer=saver)  # Removed store parameter
    return graph, pool


graph = create_aita_graph()
