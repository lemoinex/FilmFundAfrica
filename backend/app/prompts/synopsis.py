"""Prompts : synopsis court et synopsis long."""

from __future__ import annotations

from app.models.enums import DocumentType
from app.prompts.base import PromptTemplate, register

SHORT_SYNOPSIS = register(
    PromptTemplate(
        name="short_synopsis",
        version="1.0.0",
        document_type=DocumentType.SHORT_SYNOPSIS,
        document_label="Synopsis court",
        mission=(
            "Rédige le synopsis court du projet : une page qui raconte l'histoire du début "
            "à la fin, dénouement compris. Ce document est lu en premier par un comité de "
            "lecture : il doit donner envie sans rien masquer."
        ),
        outline=[
            "Situation initiale et présentation du protagoniste",
            "Élément déclencheur",
            "Développement et montée des enjeux",
            "Point de bascule",
            "Dénouement",
        ],
        target_pages=(1, 1),
        style_notes=[
            "Présent de narration, troisième personne.",
            "Le dénouement est explicite : un synopsis ne ménage pas le suspense.",
            "Aucun dialogue, aucune indication technique.",
            "Uniquement les personnages fournis dans le contexte.",
        ],
        temperature=0.7,
    )
)

LONG_SYNOPSIS = register(
    PromptTemplate(
        name="long_synopsis",
        version="1.0.0",
        document_type=DocumentType.LONG_SYNOPSIS,
        document_label="Synopsis long",
        mission=(
            "Rédige le synopsis long : le déroulé détaillé du récit, séquence par grande "
            "étape, avec l'évolution de chaque personnage principal."
        ),
        outline=[
            "Acte I — exposition et rupture",
            "Acte II — confrontation et complications",
            "Acte III — crise, climax et résolution",
            "Trajectoire des personnages principaux",
            "Thématique et portée du récit",
        ],
        target_pages=(3, 5),
        style_notes=[
            "Présent de narration, troisième personne.",
            "Chaque étape doit être une conséquence de la précédente : pas de coïncidence.",
            "Cohérence stricte avec le synopsis court s'il figure dans le contexte.",
        ],
        depends_on=(DocumentType.SHORT_SYNOPSIS,),
        temperature=0.7,
    )
)
