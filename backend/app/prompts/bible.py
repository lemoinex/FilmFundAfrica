"""Prompt : bible de serie / bible de projet.

La bible est le document de reference qui presente l'identite, la structure et
les regles du projet, et montre comment il restera coherent dans la duree.
"""

from __future__ import annotations

from app.models.enums import DocumentType
from app.prompts.base import PromptTemplate, register

SERIES_BIBLE = register(
    PromptTemplate(
        name="series_bible",
        version="1.0.0",
        document_type=DocumentType.SERIES_BIBLE,
        document_label="Bible du projet",
        mission=(
            "Rédige la bible du projet : le document de référence qui présente en détail "
            "l'identité, la structure et les règles du projet audiovisuel, et démontre à un "
            "producteur, un diffuseur ou un financeur comment il fonctionnera et restera "
            "cohérent dans le temps."
        ),
        outline=[
            "Concept",
            "Positionnement et public cible",
            "Univers et identité",
            "Format",
            "Personnages et évolution",
            "Narration, ton et rythme",
            "Structure des épisodes",
            "Thèmes",
            "Direction artistique",
            "Image, couleurs, décors, costumes, lumière",
            "Son et musique",
            "Principes de réalisation",
            "Exemples d'épisodes",
            "Règles de continuité",
        ],
        # Longueur adaptee au type de projet : pilotee par le nombre de sections.
        target_pages=(12, 25),
        style_notes=[
            "Adapte la profondeur de chaque section au format du projet : une série "
            "développe la structure des épisodes et les règles de continuité, un long "
            "métrage les condense.",
            "Les « Exemples d'épisodes » ne sont rédigés que pour une série ; sinon, "
            "remplace la section par des séquences-clés du film.",
            "Les règles de continuité doivent être opposables : ce qui est interdit, ce qui "
            "revient à chaque épisode, ce qui peut évoluer.",
            "Aucun personnage ni lieu absent du contexte.",
        ],
        depends_on=(
            DocumentType.LONG_SYNOPSIS,
            DocumentType.CHARACTER_SHEET,
            DocumentType.DIRECTING_NOTE,
        ),
        temperature=0.7,
    )
)
