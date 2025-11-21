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


class SubGoal(BaseModel):
    subgoal: str = Field(description="The sub-goal to be completed")
    success_predicate: str = Field(
        description="The predicate that defines whether the sub-goal is successful/satisfied"
    )


class Plan(BaseModel):
    subgoals: List[SubGoal] = Field(
        default_factory=list,
        description="The list of sub-goals to be completed to resolve the diagnosis",
    )


class PlanPatch(BaseModel):
    """Value you write to state['plan'] to replace from an index onward."""

    from_index: int = 0
    subgoals: List[SubGoal] = Field(default_factory=list)


def plan_splice(prev: Optional[Plan], patch: Plan | PlanPatch | dict | None) -> Plan:
    prev_list: List[SubGoal] = [] if prev is None else list(prev.subgoals)
    if not patch:
        return Plan(subgoals=prev_list)
    # If a full Plan is passed, replace entirely
    if isinstance(patch, Plan):
        return patch
    if isinstance(patch, dict):
        patch = PlanPatch(**patch)
    idx = max(0, min(patch.from_index, len(prev_list)))
    return Plan(subgoals=prev_list[:idx] + list(patch.subgoals))


class PlannerOutput(BaseModel):
    plan: Optional[Plan] = Field(
        default=None, description="The plan to resolve the diagnosis"
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


class ProbePlannerOutput(BaseModel):
    probe_task: str = Field(
        description="The task to be completed to resolve the uncertainty"
    )


class AitaState(MessagesState):
    trace: Annotated[list[str], override_reducer] = []
    cli_trace: Annotated[list[AnyMessage], override_reducer] = []
    plan: Annotated[Optional[Plan], plan_splice] = None
    plan_cursor: int = 0
    probe_task: Optional[str] = None
