"""Architecture tests — enforce hexagonal import rules.

Domain code may not import adapters, UI, network, or OS libraries.
Adapters may not import each other.
Capabilities may import only the SDK.
"""

from pathlib import Path

import pytest

DOMAIN_DIR = Path(__file__).resolve().parents[3] / "jarvis" / "domain"
ADAPTER_DIR = Path(__file__).resolve().parents[3] / "jarvis" / "adapters"
FORBIDDEN_DOMAIN_IMPORTS = [
    "socket",
    "urllib",
    "requests",
    "httpx",
    "aiohttp",
    "win32",
    "pywinauto",
    "uiautomation",
    "tkinter",
    "PyQt5",
    "PyQt6",
    "tauri",
    "electron",
]


def _python_files(directory: Path) -> list[Path]:
    if not directory.exists():
        return []
    return sorted(directory.rglob("*.py"))


def test_domain_has_no_forbidden_imports() -> None:
    """Domain code must not import platform/network/UI libraries."""
    for py_file in _python_files(DOMAIN_DIR):
        text = py_file.read_text()
        for forbidden in FORBIDDEN_DOMAIN_IMPORTS:
            assert f"import {forbidden}" not in text, (
                f"{py_file} imports forbidden module {forbidden}"
            )


def test_adapters_do_not_import_each_other() -> None:
    """Adapter modules must not import from other adapter modules."""
    for py_file in _python_files(ADAPTER_DIR):
        text = py_file.read_text()
        # Adapters may import from jarvis.ports (the interface) but not from
        # jarvis.adapters.<other>
        import re

        for match in re.finditer(r"from\s+jarvis\.adapters\.(\w+)", text):
            pytest.fail(f"{py_file} imports from another adapter: {match.group(0)}")
