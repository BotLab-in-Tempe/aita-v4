from __future__ import annotations

import os
from functools import wraps

from aita.docker_env import DockerEnvironment, DockerEnvironmentConfig
from langgraph.types import interrupt
from aita.logger import get_logger

logger = get_logger()


def with_error_escalation(node_name: str):
    """
    Decorator that wraps nodes with centralized error escalation logic.
    When an exception occurs, it creates an interrupt with error details
    and available actions (retry, skip, abort).
    """

    def decorator(fn):
        @wraps(fn)
        async def wrapper(state, *args, **kwargs):
            try:
                return await fn(state, *args, **kwargs)
            except Exception as e:
                logger.warning(
                    f"Error escalation triggered - node={node_name}, "
                    f"error_type={type(e).__name__}, error={str(e)[:100]}"
                )
                # CENTRALIZED escalation logic
                return interrupt(
                    {
                        "type": "node_error",
                        "node": node_name,
                        "error": str(e),
                        "state_snapshot": {
                            "keys": list(state.keys()),
                        },
                        "actions": ["retry", "skip", "abort"],
                    }
                )

        return wrapper

    return decorator


EXEC_IMAGE = os.getenv("EXEC_IMAGE", "aita-sandbox:latest")
EXEC_PROJECTS_ROOT = os.getenv("EXEC_PROJECTS_ROOT")
EXEC_SNAPSHOT_ROOT = os.getenv("EXEC_SNAPSHOT_ROOT")
EXEC_CWD = os.getenv("EXEC_CWD")

if not EXEC_PROJECTS_ROOT or not EXEC_SNAPSHOT_ROOT:
    raise RuntimeError("EXEC_PROJECTS_ROOT and EXEC_SNAPSHOT_ROOT must be set.")


async def build_docker_env_for_user(user_id: str) -> DockerEnvironment:
    """
    One container per user with all projects/levels available.
    Inside the container:
      - /workspace/projects        -> shared project tree (read-only)
      - /workspace/projects/<proj>/<level>/student_code_snapshot
            -> this user's snapshot for that level (if it exists)
    """
    run_args: list[str] = [
        "--rm",
        "-v",
        f"{EXEC_PROJECTS_ROOT}:/workspace/projects",
    ]

    for project in os.listdir(EXEC_PROJECTS_ROOT):
        project_path = os.path.join(EXEC_PROJECTS_ROOT, project)
        if not os.path.isdir(project_path):
            continue

        for level in os.listdir(project_path):
            level_path = os.path.join(project_path, level)
            if not os.path.isdir(level_path):
                continue

            snapshot_host = os.path.join(EXEC_SNAPSHOT_ROOT, project, level, user_id)
            if not os.path.isdir(snapshot_host):
                # user might not have submitted for this level yet
                continue

            container_target = (
                f"/workspace/projects/{project}/{level}/student_code_snapshot"
            )
            run_args.extend(["-v", f"{snapshot_host}:{container_target}"])

    return DockerEnvironment(
        user_id=user_id,
        config_class=DockerEnvironmentConfig,
        image=EXEC_IMAGE,
        cwd=EXEC_CWD or "/workspace/projects",
        run_args=run_args,
    )
