"""Couche d'abstraction IA."""

from app.services.ai.base import AICompletionRequest, AICompletionResponse, AIProvider
from app.services.ai.service import AIService, build_provider, word_count

__all__ = [
    "AIProvider",
    "AICompletionRequest",
    "AICompletionResponse",
    "AIService",
    "build_provider",
    "word_count",
]
