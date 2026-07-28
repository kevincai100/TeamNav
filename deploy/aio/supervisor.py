from __future__ import annotations

import os
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Mapping
from typing import NamedTuple

API_DIR = "/workspace/apps/api"
WEB_DIR = "/workspace/apps/web"
SHUTDOWN_TIMEOUT_SECONDS = 15


class ConfigurationError(RuntimeError):
    pass


class ProcessSpec(NamedTuple):
    name: str
    command: tuple[str, ...]
    cwd: str
    environment: dict[str, str] | None = None


def validate_environment(environment: Mapping[str, str]) -> None:
    for name in ("SECRET_KEY", "ADMIN_TOKEN"):
        value = environment.get(name, "").strip()
        if len(value) < 32 or value.startswith("replace-with-"):
            raise ConfigurationError(f"{name} must contain at least 32 non-placeholder characters")


def process_specs() -> tuple[ProcessSpec, ...]:
    return (
        ProcessSpec(
            "api",
            (
                "python",
                "-m",
                "uvicorn",
                "app.main:app",
                "--proxy-headers",
                "--host",
                "127.0.0.1",
                "--port",
                "8000",
            ),
            API_DIR,
        ),
        ProcessSpec(
            "web",
            ("node", "server.js"),
            WEB_DIR,
            {"HOSTNAME": "127.0.0.1", "PORT": "3000"},
        ),
        ProcessSpec(
            "gateway",
            ("nginx", "-c", "/etc/nginx/teamnav-aio.conf", "-g", "daemon off;"),
            "/workspace",
        ),
    )


def child_environment(overrides: Mapping[str, str] | None) -> dict[str, str]:
    environment = os.environ.copy()
    if overrides:
        environment.update(overrides)
    return environment


def terminate_processes(processes: Mapping[str, subprocess.Popen[bytes]]) -> None:
    running = [process for process in processes.values() if process.poll() is None]
    for process in running:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass

    deadline = time.monotonic() + SHUTDOWN_TIMEOUT_SECONDS
    while running and time.monotonic() < deadline:
        running = [process for process in running if process.poll() is None]
        if running:
            time.sleep(0.1)

    for process in running:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass

    for process in processes.values():
        try:
            process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            pass


def run() -> int:
    validate_environment(os.environ)
    print("[teamnav-aio] applying database migrations", flush=True)
    subprocess.run(
        ("python", "-m", "alembic", "upgrade", "head"),
        cwd=API_DIR,
        check=True,
    )

    shutdown = threading.Event()

    def request_shutdown(signum: int, _frame: object) -> None:
        print(f"[teamnav-aio] received signal {signum}; stopping", flush=True)
        shutdown.set()

    signal.signal(signal.SIGINT, request_shutdown)
    signal.signal(signal.SIGTERM, request_shutdown)

    processes: dict[str, subprocess.Popen[bytes]] = {}
    try:
        for spec in process_specs():
            processes[spec.name] = subprocess.Popen(
                spec.command,
                cwd=spec.cwd,
                env=child_environment(spec.environment),
                start_new_session=True,
            )
            print(f"[teamnav-aio] started {spec.name} (pid {processes[spec.name].pid})", flush=True)

        while not shutdown.wait(0.25):
            for name, process in processes.items():
                exit_code = process.poll()
                if exit_code is not None:
                    print(
                        f"[teamnav-aio] {name} exited with status {exit_code}; stopping container",
                        file=sys.stderr,
                        flush=True,
                    )
                    return exit_code if exit_code != 0 else 1
        return 0
    finally:
        terminate_processes(processes)


def main() -> int:
    try:
        return run()
    except ConfigurationError as exc:
        print(f"[teamnav-aio] configuration error: {exc}", file=sys.stderr, flush=True)
        return 64
    except subprocess.CalledProcessError as exc:
        print(
            f"[teamnav-aio] database migration failed with status {exc.returncode}",
            file=sys.stderr,
            flush=True,
        )
        return exc.returncode or 1


if __name__ == "__main__":
    raise SystemExit(main())
