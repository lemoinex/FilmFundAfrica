"""Prompt : traitement (continuite dialoguee non comprise)."""

from __future__ import annotations

from app.models.enums import DocumentType
from app.prompts.base import PromptTemplate, register

TREATMENT = register(
    PromptTemplate(
        name="treatment",
        version="1.0.0",
        document_type=DocumentType.TREATMENT,
        document_label="Traitement",
        mission=(
            "Rédige le traitement : le déroulé séquence par séquence du film, au présent, "
            "sans dialogue écrit. C'est la dernière étape avant le scénario."
        ),
        outline=[
            "Note liminaire : structure et durée visée",
            "Séquencier — Acte I",
            "Séquencier — Acte II",
            "Séquencier — Acte III",
            "Arcs des personnages étape par étape",
            "Points de tension et respirations",
        ],
        target_pages=(8, 15),
        style_notes=[
            "Numérote les séquences ; indique lieu, moment et personnages présents.",
            "Présent de narration, pas de dialogue rédigé (les intentions de parole suffisent).",
            "Cohérence absolue avec le synopsis long s'il figure dans le contexte.",
        ],
        depends_on=(DocumentType.LONG_SYNOPSIS, DocumentType.SHORT_SYNOPSIS),
        temperature=0.7,
    )
)
