"""Fake desktop control — controllable app/window actions for tests."""

from jarvis.ports.desktop_control import AppAction, DesktopControl


class FakeDesktopControl(DesktopControl):
    def __init__(self) -> None:
        self.actions: list[AppAction] = []
        self.windows: list[str] = ["Fake Window 1", "Fake Window 2"]

    def launch_app(
        self,
        app_name: str,
        args: list[str] | None = None,
        confirm: bool = False,
    ) -> bool:
        self.actions.append(AppAction(action="launch", target=app_name, args=args or []))
        return True

    def close_app(self, app_name: str, confirm: bool = False) -> bool:
        self.actions.append(AppAction(action="close", target=app_name))
        return True

    def list_windows(self) -> list[str]:
        return list(self.windows)

    def health(self) -> str:
        return "ok"
