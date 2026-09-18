"""Prompt : note d'intention."""

from __future__ import annotations

from app.models.enums import DocumentType
from app.prompts.base import PromptTemplate, register

INTENT_NOTE = register(
    PromptTemplate(
        name="intent_note",
        version="1.0.0",
        document_type=DocumentType.INTENT_NOTE,
        document_label="Note d'intention",
        mission=(
            "Rédige la note d'intention du réalisateur : pourquoi ce film, pourquoi "
            "maintenant, pourquoi par cet auteur. C'est un texte à la première personne "
            "qui engage un point de vue, pas un résumé de l'histoire."
        ),
        outline=[
            "Origine du projet et rapport personnel au sujet",
            "Le sujet et le point de vue défendu",
            "Pourquoi ce film maintenant : nécessité et contexte",
            "Ce que le film cherche à provoquer chez le spectateur",
            "Ancrage culturel et territorial",
            "Public visé et circulation envisagée",
        ],
        target_pages=(2, 3),
        style_notes=[
            "Première personne du singulier, ton engagé mais sobre.",
            "Ne résume pas l'intrigue : la note d'intention défend un regard.",
            "Cohérence stricte avec le sujet et le synopsis présents dans le contexte.",
            "Si la vision du réalisateur n'est pas renseignée, ne l'invente pas.",
        ],
        depends_on=(DocumentType.SHORT_SYNOPSIS,),
        temperature=0.75,
    )
)
