from __future__ import annotations

import subprocess
import sys
from types import SimpleNamespace
from typing import List, Sequence, Tuple

import pytest

from plexity_sdk.graphrag import ensure_microsoft_graphrag_runtime


def capture_commands(monkeypatch: pytest.MonkeyPatch) -> List[Tuple[Tuple[str, ...], bool, str | None]]:
    commands: List[Tuple[Tuple[str, ...], bool, str | None]] = []

    def fake_run(cmd: Sequence[str], check: bool = False, cwd: str | None = None, **_: object) -> SimpleNamespace:
        commands.append((tuple(str(part) for part in cmd), check, cwd))
        if "show" in cmd:
            return SimpleNamespace(returncode=0)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    return commands


def test_ensure_runtime_skips_reinstall_when_present(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    commands = capture_commands(monkeypatch)

    ensure_microsoft_graphrag_runtime(
        virtual_env=str(tmp_path / "env"),
        workspace=str(tmp_path / "workspace"),
        python_executable=sys.executable,
        skip_if_installed=True,
        verbose=False,
    )

    install_commands = [cmd for cmd, _check, _cwd in commands if "install" in cmd]
    assert not install_commands
    assert any("graphrag" in cmd for cmd, *_ in commands)


def test_ensure_runtime_raises_runtime_error_on_failure(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    def failing_run(cmd: Sequence[str], check: bool = False, cwd: str | None = None, **_: object) -> SimpleNamespace:
        if "install" in cmd:
            raise subprocess.CalledProcessError(returncode=1, cmd=list(cmd))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(subprocess, "run", failing_run)

    with pytest.raises(RuntimeError):
        ensure_microsoft_graphrag_runtime(
            virtual_env=str(tmp_path / "env"),
            workspace=str(tmp_path / "workspace"),
            python_executable=sys.executable,
            skip_if_installed=False,
            verbose=False,
        )
