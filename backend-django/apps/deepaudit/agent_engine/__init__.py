"""
DeepAudit Agent engine package.

Keep package-level imports intentionally minimal so submodule imports do not
fail on partially migrated optional components.
"""

from importlib import import_module

__all__ = [
    "AgentEventData",
    "AgentEventEmitter",
    "EventManager",
]


def __getattr__(name: str):
    if name in __all__:
        module = import_module(".event_manager", __name__)
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
