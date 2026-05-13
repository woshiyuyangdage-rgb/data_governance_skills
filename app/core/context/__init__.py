"""Context resolution interfaces."""

from app.core.context.context_loader import load_context_resolution_config
from app.core.context.context_resolver import ContextResolver

__all__ = [
    "load_context_resolution_config",
    "ContextResolver",
]
