from __future__ import annotations

import uvicorn
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from contextlib import asynccontextmanager

from aita.graph import make_graph, create_aita_graph
from aita.logger import get_logger
from langfuse.langchain import CallbackHandler
from langfuse import get_client, propagate_attributes
from dotenv import load_dotenv

load_dotenv(override=True)

logger = get_logger()
langfuse = get_client()
langfuse_handler = CallbackHandler()


class ChatRequest(BaseModel):
    session_id: str
    course_code: str
    project_id: Optional[str] = None
    user_id: Optional[str] = None
    tutoring_mode: Optional[bool] = None
    messages: List[Dict[str, Any]]


def preprocess_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for m in messages:
        mc = dict(m)
        content = mc.get("content", mc.get("text"))
        if isinstance(content, str):
            content = [{"type": "text", "text": content}]
        if isinstance(content, list):
            blocks = []
            for b in content:
                if isinstance(b, dict) and b.get("type") == "image":
                    if "base64" not in b or "mime_type" not in b:
                        raise HTTPException(
                            status_code=400,
                            detail="image block must include base64 and mime_type",
                        )
                    blocks.append(
                        {
                            "type": "image",
                            "base64": b["base64"],
                            "mime_type": b["mime_type"],
                        }
                    )
                elif isinstance(b, dict) and b.get("type") == "text":
                    blocks.append({"type": "text", "text": b.get("text", "")})
                else:
                    blocks.append(b)
            mc["content"] = blocks
        out.append(mc)
    return out


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("API server starting")
    try:
        graph, pool = await make_graph()
        logger.info("Database connection pool initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database connection pool: {e}")
        graph, pool = create_aita_graph(), None
        logger.warning("Running without persistent checkpointer")
    app.state.graph = graph
    app.state.pool = pool
    logger.info("API server startup complete")
    yield
    logger.info("API server shutting down")
    if app.state.pool:
        try:
            await app.state.pool.close()
            logger.info("Database connection pool closed")
        except Exception as e:
            logger.error(f"Error closing database connection pool: {e}")


app = FastAPI(lifespan=lifespan)


@app.post("/chat")
async def chat(body: ChatRequest):
    # Log request audit trail
    logger.info(
        f"Chat request received - session_id={body.session_id}, "
        f"user_id={body.user_id or 'unknown'}, course_code={body.course_code}"
    )
    try:
        # Build context object
        ctx = {"course_code": body.course_code}
        if body.user_id is not None:
            ctx["user_id"] = body.user_id
        if body.project_id is not None:
            ctx["project_id"] = body.project_id
        cfg = {"configurable": {"thread_id": body.session_id}, "recursion_limit": 25, "callbacks": [langfuse_handler]}
        preprocessed = preprocess_messages(body.messages)
        with langfuse.start_as_current_span(name="aita"):
            with propagate_attributes(user_id=body.user_id):
                result = await app.state.graph.ainvoke(
                    {"messages": preprocessed}, cfg, context=ctx
                )
        logger.info(f"Chat request completed - session_id={body.session_id}")
        return result
    except Exception as e:
        import traceback

        logger.error(
            f"Chat request failed - session_id={body.session_id}, "
            f"error={type(e).__name__}: {str(e)}"
        )
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail={"error": str(e), "traceback": traceback.format_exc()},
        )
