# command_safety.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass
class CommandSafetyResult:
    is_safe: bool
    reason: str


ALLOWED_BINARIES: set[str] = {
    "ls",
    "cat",
    "grep",
    "find",
    "head",
    "tail",
    "wc",
    "stat",
}


FORBIDDEN_TOKENS: tuple[str, ...] = (
    " rm ",
    " rm-",
    "sudo",
    "apt-get",
    "systemctl",
    "shutdown",
    "reboot",
    "mkfs",
    ":(){",  # fork bomb
    ">/dev/sd",
    "dd ",
)


def _contains_any(text: str, tokens: Iterable[str]) -> str | None:
    for tok in tokens:
        if tok in text:
            return tok
    return None


def validate_command_safety(command: str) -> CommandSafetyResult:
    """
    Very simple sandbox validation:
    - require a single-line command
    - first word must be in ALLOWED_BINARIES
    - forbid obviously dangerous substrings
    """
    stripped = command.strip()

    if not stripped:
        return CommandSafetyResult(False, "Empty command.")

    if "\n" in stripped:
        return CommandSafetyResult(False, "Multi-line commands are not allowed.")

    first_word = stripped.split()[0]
    if first_word not in ALLOWED_BINARIES:
        return CommandSafetyResult(
            False,
            f"Command must start with one of {sorted(ALLOWED_BINARIES)}, got {first_word!r}.",
        )

    bad_tok = _contains_any(f" {stripped} ", FORBIDDEN_TOKENS)
    if bad_tok is not None:
        return CommandSafetyResult(
            False,
            f"Command contains forbidden token {bad_tok!r}.",
        )

    return CommandSafetyResult(True, "Command appears safe for this sandbox.")
