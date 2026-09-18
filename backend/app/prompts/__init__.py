"""Registre des prompts versionnes.

L'import de ce module suffit a peupler `PROMPT_REGISTRY` : chaque module de
prompt s'enregistre lui-meme via `register()`.
"""

from app.prompts import (  # noqa: F401  (imports a effet de bord : enregistrement)
    bible,
    characters,
    intention,
    logline,
    pitch,
    realization,
    screenplay,
    synopsis,
    treatment,
)
from app.prompts.base import (
    PROMPT_REGISTRY,
    PromptContext,
    PromptTemplate,
    RenderedPrompt,
    build_refine_prompt,
    get_prompt,
)
from app.prompts.funding_match import build_funding_match_prompt
from app.prompts.scoring import build_analysis_prompt

__all__ = [
    "PROMPT_REGISTRY",
    "PromptContext",
    "PromptTemplate",
    "RenderedPrompt",
    "get_prompt",
    "build_refine_prompt",
    "build_analysis_prompt",
    "build_funding_match_prompt",
]
