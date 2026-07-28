from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SUPERVISOR_PATH = Path(__file__).parents[3] / "deploy" / "aio" / "supervisor.py"


def load_supervisor():
    spec = importlib.util.spec_from_file_location("teamnav_aio_supervisor", SUPERVISOR_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("SECRET_KEY", ""),
        ("SECRET_KEY", "too-short"),
        ("SECRET_KEY", "replace-with-at-least-32-random-characters"),
        ("ADMIN_TOKEN", ""),
        ("ADMIN_TOKEN", "too-short"),
        ("ADMIN_TOKEN", "replace-with-a-long-random-admin-token"),
    ],
)
def test_validate_environment_rejects_unsafe_secrets(name: str, value: str) -> None:
    supervisor = load_supervisor()
    environment = {"SECRET_KEY": "s" * 32, "ADMIN_TOKEN": "a" * 32, name: value}

    with pytest.raises(supervisor.ConfigurationError, match=name):
        supervisor.validate_environment(environment)


def test_validate_environment_accepts_production_secrets() -> None:
    supervisor = load_supervisor()

    supervisor.validate_environment({"SECRET_KEY": "s" * 32, "ADMIN_TOKEN": "a" * 32})


def test_process_specs_bind_internal_services_to_loopback() -> None:
    supervisor = load_supervisor()

    specs = {spec.name: spec for spec in supervisor.process_specs()}

    assert set(specs) == {"api", "web", "gateway"}
    assert specs["api"].command[-4:] == ("--host", "127.0.0.1", "--port", "8000")
    assert specs["web"].environment == {"HOSTNAME": "127.0.0.1", "PORT": "3000"}
    assert specs["gateway"].command == (
        "nginx",
        "-c",
        "/etc/nginx/teamnav-aio.conf",
        "-g",
        "daemon off;",
    )
