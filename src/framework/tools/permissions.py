"""Tool principal and permission checks."""

from dataclasses import dataclass


class ToolPermissionDeniedError(PermissionError):
    """Raised when a principal lacks one or more required tool permissions."""


@dataclass(frozen=True)
class ToolPrincipal:
    """Identity and explicit grants presented to the tool executor."""

    principal_id: str
    grants: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        if not self.principal_id.strip():
            raise ValueError("principal_id must not be blank")
        if not isinstance(self.grants, (set, frozenset)):
            raise TypeError("grants must be a set of permission names")
        if any(not isinstance(grant, str) or not grant.strip() for grant in self.grants):
            raise ValueError("permission grants must not be blank")
        object.__setattr__(self, "grants", frozenset(self.grants))


class PermissionPolicy:
    """Deny by default when any tool-required permission is absent."""

    @staticmethod
    def authorize(tool_name: str, required: frozenset[str], principal: ToolPrincipal) -> None:
        """Raise an explicit error listing missing permission names."""
        missing = required - principal.grants
        if missing:
            names = ", ".join(sorted(missing))
            raise ToolPermissionDeniedError(
                f"Principal {principal.principal_id!r} cannot execute tool {tool_name!r}; missing permissions: {names}"
            )
