"""Fake secrets broker — records injections for test assertions."""

from jarvis.ports.secrets_broker import SecretsBroker


class FakeSecretsBroker(SecretsBroker):
    def __init__(self) -> None:
        self.injections: list[tuple[str, str]] = []
        self.secrets: dict[tuple[str, str], str] = {}
        self.revoked: list[str] = []

    def inject(self, capability_id: str, secret_key: str) -> str:
        self.injections.append((capability_id, secret_key))
        return self.secrets.get(
            (capability_id, secret_key), f"fake-secret-{capability_id}-{secret_key}"
        )

    def rotate(self, capability_id: str, secret_key: str, new_value: str) -> None:
        self.secrets[(capability_id, secret_key)] = new_value

    def revoke(self, capability_id: str) -> None:
        self.revoked.append(capability_id)
