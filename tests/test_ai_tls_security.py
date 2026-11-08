"""Regression guard: GigaChat HTTP requests must never disable TLS checks.

The test loads the module with stubbed configuration/decorator imports and
performs no network requests. No credentials are needed.
"""

import ast
import runpy
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import patch

import pytest


SOURCE = Path(__file__).resolve().parents[1] / "app" / "ai_analyzer.py"


def _load_with_ssl_setting(setting=None):
    fake_decouple = ModuleType("decouple")

    def config(name, default=None, cast=None):
        if name == "GIGACHAT_VERIFY_SSL" and setting is not None:
            return setting
        return default

    fake_decouple.config = config
    fake_tenacity = ModuleType("tenacity")
    fake_tenacity.retry = lambda *args, **kwargs: (lambda fn: fn)
    fake_tenacity.stop_after_attempt = lambda *args, **kwargs: None
    fake_tenacity.wait_exponential = lambda *args, **kwargs: None
    fake_tenacity.retry_if_exception_type = lambda *args, **kwargs: None

    with patch.dict(sys.modules, {"decouple": fake_decouple, "tenacity": fake_tenacity}):
        return runpy.run_path(str(SOURCE), run_name="tls_security_test")


def test_gigachat_tls_verification_enabled_by_default():
    module = _load_with_ssl_setting()
    assert module["VERIFY_SSL"] is True


def test_gigachat_tls_cannot_be_explicitly_disabled():
    with pytest.raises(RuntimeError, match="TLS verification"):
        _load_with_ssl_setting(False)


def test_all_gigachat_http_clients_use_verified_tls():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    clients = [
        n for n in ast.walk(tree)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Attribute)
        and isinstance(n.func.value, ast.Name)
        and n.func.value.id == "httpx"
        and n.func.attr == "AsyncClient"
    ]
    assert len(clients) == 2, "Unexpected HTTP client call site; audit new call sites"
    for client in clients:
        kwargs = {kw.arg: kw.value for kw in client.keywords}
        assert isinstance(kwargs.get("verify"), ast.Name)
        assert kwargs["verify"].id == "VERIFY_SSL"
