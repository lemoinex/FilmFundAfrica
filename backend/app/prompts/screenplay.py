"""Prompt : scenario avec dialogues, et decoupage technique."""

from __future__ import annotations

from app.models.enums import DocumentType
from app.prompts.base import PromptTemplate, register

SCREENPLAY = register(
    PromptTemplate(
        name="screenplay",
        version="1.0.0",
        document_type=DocumentType.SCREENPLAY,
        document_label="Scénario",
        mission=(
            "Rédige le scénario du projet, en continuité dialoguée, au format standard de "
            "l'industrie. La durée cible détermine le nombre de séquences : 1 page ≈ 1 minute "
            "à l'écran. La longueur doit venir de la densité dramatique, jamais du remplissage."
        ),
        outline=[
            "Page de titre (titre, format, durée cible, auteur si fourni)",
            "Acte I",
            "Acte II",
            "Acte III",
        ],
        target_pages=None,  # pilote par la duree cible du projet
        style_notes=[
            "Format standard : en-tête de séquence en majuscules "
            "(`INT./EXT. LIEU - JOUR/NUIT`), action au présent, nom du personnage centré "
            "en majuscules au-dessus de sa réplique, didascalies entre parenthèses et rares.",
            "Numérote les séquences.",
            "Dialogues complets pour chaque personnage : pas de « ils discutent ».",
            "N'utilise que les personnages fournis dans le contexte ; si un rôle manquant "
            "est indispensable, nomme-le par sa fonction (LA VOISINE) et signale-le en fin "
            "de document.",
            "Aucun plan de caméra sauf s'il est dramatiquement indispensable.",
            "Respecte strictement l'intrigue du traitement ou du synopsis fourni.",
        ],
        depends_on=(
            DocumentType.TREATMENT,
            DocumentType.LONG_SYNOPSIS,
            DocumentType.CHARACTER_SHEET,
        ),
        temperature=0.75,
    )
)
