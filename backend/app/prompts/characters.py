"""Prompt : presentation des personnages."""

from __future__ import annotations

from app.models.enums import DocumentType
from app.prompts.base import PromptTemplate, register

CHARACTER_SHEET = register(
    PromptTemplate(
        name="character_sheet",
        version="1.0.0",
        document_type=DocumentType.CHARACTER_SHEET,
        document_label="Présentation des personnages",
        mission=(
            "Rédige la présentation des personnages du projet, à partir des seuls "
            "personnages saisis par l'utilisateur. Pour chacun : identité, situation, "
            "désir, obstacle, contradiction interne et arc. N'ajoute aucun personnage."
        ),
        outline=[
            "Protagoniste",
            "Antagoniste ou force antagoniste",
            "Personnages secondaires",
            "Rapports de force et relations",
        ],
        target_pages=(2, 4),
        style_notes=[
            "Une sous-partie par personnage fourni, titrée par son nom.",
            "Si aucun personnage n'a été saisi, écris « Information non fournie. » pour "
            "chaque section et demande à l'utilisateur de les renseigner.",
            "Pas de description physique gratuite : elle doit servir le récit.",
        ],
        temperature=0.7,
    )
)
