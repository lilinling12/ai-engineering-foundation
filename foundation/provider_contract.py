"""Provider-neutral execution request validation; no model connection is enabled."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

class ProviderCapability(str, Enum):
    READ_AUTHORITY = "read-authority"
    PROPOSE_PATCH = "propose-patch"
    REQUEST_CHECK = "request-check"

class ProviderRequestError(ValueError):
    pass

@dataclass(frozen=True)
class ProviderRequest:
    task_id: str
    authority_digest: str
    provider_id: str
    allowed_capabilities: frozenset[ProviderCapability]
    max_steps: int = 12

    def validate(self) -> None:
        if self.provider_id not in {"codex", "claude-code"}:
            raise ProviderRequestError("Unsupported provider")
        if not self.task_id or len(self.task_id) > 100:
            raise ProviderRequestError("Invalid task id")
        if len(self.authority_digest) != 64 or any(ch not in "0123456789abcdef" for ch in self.authority_digest):
            raise ProviderRequestError("Authority revision digest required")
        if not (1 <= self.max_steps <= 25):
            raise ProviderRequestError("Step budget exceeded")
        if not self.allowed_capabilities.issubset(set(ProviderCapability)):
            raise ProviderRequestError("Unknown capability")

def planned_provider_flow(request: ProviderRequest) -> tuple[str, ...]:
    """Descriptive protocol only. Cannot launch an actual CLI."""
    request.validate()
    return ("restore-authority", "request-human-approval",
            "propose-patch", "validate-allowed-paths", "offline-isolated-evaluation",
            "record-evidence", "handoff")
