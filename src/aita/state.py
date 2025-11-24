import operator
from dataclasses import dataclass
from enum import Enum
from typing import Annotated, Any, Dict, List, Literal, Optional
from typing_extensions import TypedDict

from langgraph.graph import MessagesState
from langgraph.graph.message import AnyMessage
from pydantic import BaseModel, Field, field_validator


@dataclass
class Context:
    course_code: str
    project_id: Optional[str] = None
    segment_id: Optional[str] = None
    user_id: Optional[str] = None
    thread_id: Optional[str] = None


def override_reducer(current_value, new_value):
    """Reducer function that allows overriding values in state."""
    if isinstance(new_value, dict) and new_value.get("type") == "override":
        return new_value.get("value", new_value)
    else:
        return operator.add(current_value, new_value)


class PlannerOutput(BaseModel):
    plan: Optional[List[str]] = Field(
        default=None,
        description="The list of sub-goals to be completed to resolve the diagnosis",
    )


class ContextGateOutput(BaseModel):
    need_retrieval: bool = Field(
        description="Whether retrieval should be called to get more context. Output true if retrieval is required, false otherwise."
    )


class EvaluatorOutput(BaseModel):
    need_plan: bool = Field(
        description="Whether a tutoring plan is needed (initial planning or replanning)"
    )
    completed_subgoals: List[int] = Field(
        default_factory=list,
        description="Indexes of subgoals that are now complete (empty list if none completed)",
    )
    escalate: bool = Field(
        default=False,
        description="Whether the situation should be escalated to human support (TAs/instructors).",
    )
    message: str = Field(
        default="",
        description=(
            "A short, internal system message summarizing the evaluator's decision, "
            "next suggested move, or escalation note. This is logged and may be surfaced "
            "to other nodes, but is not shown verbatim to the student."
        ),
    )
    should_respond: bool = Field(
        default=True,
        description=(
            "Whether the tutor should generate a reply in this turn. "
            "False when silence or no direct response is appropriate (e.g., "
            "waiting for student work, off-target chatter, or multi-party side talk)."
        ),
    )


class ProbePlannerOutput(BaseModel):
    probe_task: str = Field(
        description="The task to be completed to resolve the uncertainty"
    )


class AitaState(MessagesState):
    cli_trace: Annotated[list[AnyMessage], override_reducer] = []
    plan: Optional[List[str]] = None
    probe_task: Optional[str] = None
    escalate: Annotated[Optional[bool], override_reducer] = None
    should_respond: Annotated[Optional[bool], override_reducer] = None
