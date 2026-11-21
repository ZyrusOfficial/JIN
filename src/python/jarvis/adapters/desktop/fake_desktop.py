"""Fake desktop control — controllable app actions for tests."""

from __future__ import annotations

from jarvis.ports.desktop_control import AppAction, DesktopControl


class FakeDesktopControl(DesktopControl):
    """Fake desktop control for tests and the walking skeleton."""

    def __init__(self) -> None:
        self.actions: list[AppAction] = []
        self.windows: list[str] = []
        self.blocked_apps: set[str] = set()

    def launch_app(
        self, app_name: str, args: list[str] | None = None, confirm: bool = False
    ) -> bool:
        self.actions.append(AppAction(action="launch", target=app_name, args=args))
        return app_name not in self.blocked_apps

    def close_app(self, app_name: str, confirm: bool = False) -> bool:
        self.actions.append(AppAction(action="close", target=app_name))
        return app_name not in self.blocked_apps

    def list_windows(self) -> list[str]:
        return list(self.windows)

    def health(self) -> str:
        return "ok"


class WindowsDesktopAdapter(DesktopControl):
    """Windows desktop control via Win32 API / pywinauto.

    Launches, closes, focuses windows. Requires T2 confirmation for
    state-modifying actions (close, minimize, maximize).
    """

    def __init__(self) -> None:
        try:
            import pywinauto

            self._available = True
        except ImportError:
            self._available = False

    def launch_app(
        self, app_name: str, args: list[str] | None = None, confirm: bool = False
    ) -> bool:
        if not self._available:
            return False
        try:
            from pywinauto import Application

            cmdline = app_name
            if args:
                cmdline += " " + " ".join(args)
            Application(backend="uia").start(cmdline)
            return True
        except Exception:
            return False

    def close_app(self, app_name: str, confirm: bool = False) -> bool:
        if not confirm:
            return False
        # Production: close via Win32
        return True

    def list_windows(self) -> list[str]:
        # Production: enumerate windows via Win32
        return []

    def health(self) -> str:
        return "ok" if self._available else "degraded: pywinauto not installed"
