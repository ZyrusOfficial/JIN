"""Desktop control port — launch apps, windows, files, system controls."""

from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass
class AppAction:
    action: str  # launch | close | minimize | maximize | focus
    target: str  # app name or window title
    args: list[str] | None = None


@runtime_checkable
class DesktopControl(Protocol):
    @abstractmethod
    def launch_app(
        self, app_name: str, args: list[str] | None = None, confirm: bool = False
    ) -> bool:
        """Launch an app (T2 if it modifies system state)."""

    @abstractmethod
    def close_app(self, app_name: str, confirm: bool = False) -> bool:
        """Close an app."""

    @abstractmethod
    def list_windows(self) -> list[str]:
        """List open window titles."""

    @abstractmethod
    def health(self) -> str:
        """Return health status."""
