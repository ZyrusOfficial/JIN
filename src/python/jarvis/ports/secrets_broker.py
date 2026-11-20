"""Secrets broker port — injects credentials at call time, never into prompts/logs.

Non-negotiable (section 3.3, invariant 5): secrets never reach prompts, logs,
or the model. The broker injects credentials into a capability at call time only.
"""

from __future__ import annotations

from abc import abstractmethod
from typing import Protocol, runtime_checkable


@runtime_checkable
class SecretsBroker(Protocol):
    @abstractmethod
    def inject(self, capability_id: str, secret_key: str) -> str:
        """Return the secret value for a capability at call time."""

    @abstractmethod
    def rotate(self, capability_id: str, secret_key: str, new_value: str) -> None:
        """Rotate a secret."""

    @abstractmethod
    def revoke(self, capability_id: str) -> None:
        """Revoke all secrets for a capability."""
