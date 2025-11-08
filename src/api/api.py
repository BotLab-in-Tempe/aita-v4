from __future__ import annotations

import uvicorn
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from contextlib import asynccontextmanager

from aita.graph import make_graph, create_aita_graph

from dotenv import load_dotenv
load_dotenv(override=True)


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
                        raise HTTPException(status_code=400, detail="image block must include base64 and mime_type")
                    blocks.append({"type": "image", "base64": b["base64"], "mime_type": b["mime_type"]})
                elif isinstance(b, dict) and b.get("type") == "text":
                    blocks.append({"type": "text", "text": b.get("text", "")})
                else:
                    blocks.append(b)
            mc["content"] = blocks
        out.append(mc)
    return out


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        graph, pool = await make_graph()
    except Exception:
        graph, pool = create_aita_graph(), None
    app.state.graph = graph
    app.state.pool = pool
    yield
    if app.state.pool:
        await app.state.pool.close()


app = FastAPI(lifespan=lifespan)

@app.post("/chat")
async def chat(body: ChatRequest):
    try:
        # Build context object
        ctx = {"course_code": body.course_code}
        if body.user_id is not None:
            ctx["user_id"] = body.user_id
        if body.project_id is not None:
            ctx["project_id"] = body.project_id
        cfg = {"configurable": {"thread_id": body.session_id}, "recursion_limit": 25}
        preprocessed = preprocess_messages(body.messages)
        result = await app.state.graph.ainvoke({"messages": preprocessed}, cfg, context=ctx)
        return result
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail={"error": str(e), "traceback": traceback.format_exc()})
