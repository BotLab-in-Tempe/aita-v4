from __future__ import annotations

import os
import subprocess
from dataclasses import asdict, dataclass, field
from typing import Any

from aita.logger import get_logger

logger = get_logger()


@dataclass
class DockerEnvironmentConfig:
    image: str
    cwd: str = "/workspace"
    env: dict[str, str] = field(default_factory=dict)
    forward_env: list[str] = field(default_factory=list)
    timeout: int = 30
    executable: str = os.getenv("DOCKER_EXECUTABLE", "docker")
    run_args: list[str] = field(default_factory=lambda: ["--rm"])
    container_timeout: str = "30m"
    pull_timeout: int = 120


class DockerEnvironment:
    def __init__(
        self,
        *,
        user_id: str,
        config_class: type = DockerEnvironmentConfig,
        **kwargs: Any,
    ):
        self.container_id: str | None = None
        self.user_id = user_id
        self.config = config_class(**kwargs)
        self._start_container()

    def get_template_vars(self) -> dict[str, Any]:
        return asdict(self.config)

    def _start_container(self) -> None:
        safe_user_id = "".join(
            c if c.isalnum() or c == "-" else "-" for c in self.user_id
        )
        container_name = f"aita-sandbox-user-{safe_user_id}"

        check_cmd = [
            self.config.executable,
            "ps",
            "--filter",
            f"name={container_name}",
            "--filter",
            "status=running",
            "--format",
            "{{.ID}}",
        ]
        check_result = subprocess.run(
            check_cmd,
            capture_output=True,
            text=True,
            timeout=10,
        )
        existing_id = check_result.stdout.strip()

        if existing_id:
            self.container_id = existing_id
            logger.info(
                f"Docker container reused - user_id={self.user_id}, "
                f"container_id={existing_id[:12]}, name={container_name}"
            )
            self._reset_idle_timer()
            return

        check_any_cmd = [
            self.config.executable,
            "ps",
            "-a",
            "--filter",
            f"name={container_name}",
            "--format",
            "{{.ID}}",
        ]
        check_any_result = subprocess.run(
            check_any_cmd,
            capture_output=True,
            text=True,
            timeout=10,
        )
        existing_any_id = check_any_result.stdout.strip()

        if existing_any_id:
            logger.info(
                f"Docker container restarting - user_id={self.user_id}, "
                f"container_id={existing_any_id[:12]}, name={container_name}"
            )
            start_cmd = [
                self.config.executable,
                "start",
                existing_any_id,
            ]
            try:
                start_result = subprocess.run(
                    start_cmd,
                    capture_output=True,
                    text=True,
                    timeout=self.config.pull_timeout,
                    check=True,
                )
                self.container_id = start_result.stdout.strip() or existing_any_id
                logger.info(
                    f"Docker container restarted - user_id={self.user_id}, "
                    f"container_id={self.container_id[:12]}"
                )
                self._reset_idle_timer()
                return
            except subprocess.CalledProcessError as e:
                logger.error(
                    f"Docker container restart failed - user_id={self.user_id}, "
                    f"container_id={existing_any_id[:12]}, returncode={e.returncode}"
                )
                raise

        run_args = [arg for arg in self.config.run_args if arg != "--rm"]

        watchdog_script = (
            "touch /tmp/last_active && "
            "while true; do "
            "sleep 60; "
            "if [ $(find /tmp/last_active -mmin +30 2>/dev/null | wc -l) -gt 0 ]; then "
            "echo 'Idle timeout reached, exiting'; "
            "exit 0; "
            "fi; "
            "done"
        )

        cmd = [
            self.config.executable,
            "run",
            "-d",
            "--name",
            container_name,
            "-w",
            self.config.cwd,
            *run_args,
            self.config.image,
            "bash",
            "-c",
            watchdog_script,
        ]

        logger.info(
            f"Docker container creating - user_id={self.user_id}, "
            f"name={container_name}, image={self.config.image}"
        )
        logger.error(f"DEBUG DOCKER CMD: {' '.join(cmd)}")
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.pull_timeout,
                check=True,
            )
            self.container_id = result.stdout.strip()
            logger.info(
                f"Docker container created - user_id={self.user_id}, "
                f"container_id={self.container_id[:12]}, image={self.config.image}"
            )
        except subprocess.CalledProcessError as e:
            logger.error(
                f"Docker container creation failed - user_id={self.user_id}, "
                f"image={self.config.image}, returncode={e.returncode}, "
                f"stderr={e.stderr[:200] if e.stderr else 'N/A'}"
            )
            raise

    def _reset_idle_timer(self) -> None:
        if not self.container_id:
            return

        try:
            cmd = [
                self.config.executable,
                "exec",
                self.container_id,
                "touch",
                "/tmp/last_active",
            ]
            subprocess.run(cmd, capture_output=True, timeout=5, check=False)
        except Exception:
            pass

    def execute(
        self, command: str, cwd: str | None = None, *, timeout: int | None = None
    ) -> dict[str, Any]:
        assert self.container_id, "Container not started"

        self._reset_idle_timer()

        workdir = cwd or self.config.cwd
        cmd = [self.config.executable, "exec", "-w", workdir]

        for key in self.config.forward_env:
            value = os.getenv(key)
            if value is not None:
                cmd.extend(["-e", f"{key}={value}"])

        for key, value in self.config.env.items():
            cmd.extend(["-e", f"{key}={value}"])

        cmd.extend([self.container_id, "bash", "-lc", command])

        result = subprocess.run(
            cmd,
            text=True,
            timeout=timeout or self.config.timeout,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        return {"output": result.stdout, "returncode": result.returncode}

    def cleanup(self) -> None:
        if getattr(self, "container_id", None) is not None:
            logger.info(
                f"Docker container cleanup initiated - user_id={self.user_id}, "
                f"container_id={self.container_id[:12]}"
            )
            cmd = (
                f"(timeout 60 {self.config.executable} stop {self.container_id} "
                f"|| {self.config.executable} rm -f {self.container_id}) "
                "> /dev/null 2>&1 &"
            )
            subprocess.Popen(cmd, shell=True)

    def __del__(self) -> None:
        self.cleanup()
