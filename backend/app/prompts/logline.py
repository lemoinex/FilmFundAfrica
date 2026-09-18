"""Prompt : logline."""

from __future__ import annotations

from app.models.enums import DocumentType
from app.prompts.base import PromptTemplate, register

LOGLINE = register(
    PromptTemplate(
        name="logline",
        version="1.0.0",
        document_type=DocumentType.LOGLINE,
        document_label="Logline",
        mission=(
            "Rédige la logline du projet : une à deux phrases qui posent le protagoniste, "
            "sa situation de départ, l'élément déclencheur, l'objectif et l'obstacle majeur. "
            "Propose ensuite deux variantes alternatives."
        ),
        outline=[
            "Logline principale (1 à 2 phrases)",
            "Variante A",
            "Variante B",
            "Pourquoi cette logline fonctionne (3 puces maximum)",
        ],
        target_pages=(0.25, 0.5),
        style_notes=[
            "Présent de narration, voix active.",
            "Pas de nom de comédien, pas de référence à un autre film.",
            "Le conflit doit être lisible dès la première proposition.",
        ],
        temperature=0.8,
    )
)
