"""
Core package for the DeepAudit agent engine.

Avoid eager re-export of every optional component here. Several advanced
modules are still being migrated, and package-level side effects would break
imports for otherwise healthy submodules.
"""

__all__: list[str] = []
