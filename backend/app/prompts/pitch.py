"""Prompts : pitch oral et pitch ecrit."""

from __future__ import annotations

from app.models.enums import DocumentType
from app.prompts.base import PromptTemplate, register

ORAL_PITCH = register(
    PromptTemplate(
        name="oral_pitch",
        version="1.0.0",
        document_type=DocumentType.ORAL_PITCH,
        document_label="Pitch oral",
        mission=(
            "Rédige un pitch oral de trois minutes, destiné à être dit face à un comité "
            "ou dans un forum de coproduction. Texte à dire, pas texte à lire."
        ),
        outline=[
            "Accroche (20 secondes)",
            "Le récit en trois mouvements (90 secondes)",
            "Pourquoi ce film, par moi, maintenant (40 secondes)",
            "État d'avancement et besoin (30 secondes)",
            "Réponses préparées à trois questions probables",
        ],
        target_pages=(1.5, 2),
        style_notes=[
            "Phrases courtes, oralité assumée, aucune subordonnée à rallonge.",
            "Indique les durées indicatives entre parenthèses.",
            "Le besoin de financement n'est chiffré que si le contexte le fournit.",
        ],
        depends_on=(DocumentType.SHORT_SYNOPSIS, DocumentType.INTENT_NOTE),
        temperature=0.8,
    )
)

WRITTEN_PITCH = register(
    PromptTemplate(
        name="written_pitch",
        version="1.0.0",
        document_type=DocumentType.WRITTEN_PITCH,
        document_label="Pitch écrit",
        mission=(
            "Rédige le pitch écrit du projet : le document d'une à deux pages envoyé en "
            "amont à un fonds, un diffuseur ou un coproducteur."
        ),
        outline=[
            "Titre, format, durée, genre, pays",
            "Logline",
            "Le récit en un paragraphe",
            "Intention",
            "Traitement visuel en trois lignes",
            "Public et positionnement",
            "État d'avancement et calendrier envisagé",
        ],
        target_pages=(1, 2),
        style_notes=[
            "Format dense et scannable : un lecteur doit comprendre en 90 secondes.",
            "Aucune donnée chiffrée inventée (budget, audience, financements acquis).",
        ],
        depends_on=(DocumentType.SHORT_SYNOPSIS, DocumentType.INTENT_NOTE),
        temperature=0.7,
    )
)
