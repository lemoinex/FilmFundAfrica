"""Prompt : note de realisation."""

from __future__ import annotations

from app.models.enums import DocumentType
from app.prompts.base import PromptTemplate, register

DIRECTING_NOTE = register(
    PromptTemplate(
        name="directing_note",
        version="1.0.0",
        document_type=DocumentType.DIRECTING_NOTE,
        document_label="Note de réalisation",
        mission=(
            "Rédige la note de réalisation : comment le film sera concrètement mis en "
            "scène. Chaque parti pris doit être justifié par le sujet et cohérent avec "
            "la note d'intention."
        ),
        outline=[
            "Parti pris de mise en scène",
            "Traitement de l'image : cadre, focale, mouvements, format",
            "Lumière et couleur",
            "Décors, lieux de tournage et direction artistique",
            "Direction d'acteurs ou rapport aux personnes filmées",
            "Son, musique et espace sonore",
            "Montage, rythme et structure",
            "Moyens techniques envisagés et faisabilité",
        ],
        target_pages=(3, 5),
        style_notes=[
            "Première personne, ton concret et technique sans jargon gratuit.",
            "Chaque choix formel est relié à une intention narrative.",
            "Pour un documentaire, préciser le dispositif de tournage et la place de l'équipe.",
            "Ne cite aucun matériel de marque précis si le contexte ne le fournit pas.",
        ],
        depends_on=(DocumentType.SHORT_SYNOPSIS, DocumentType.INTENT_NOTE),
        temperature=0.7,
    )
)
