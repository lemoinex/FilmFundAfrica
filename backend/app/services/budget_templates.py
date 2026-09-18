"""Trames de budget previsionnel, par type de projet.

Une trame propose **la structure** d'un budget — les postes qu'un comite de
lecture s'attend a trouver, dans l'ordre des phases de production. Elle ne
propose **aucun montant** : un tarif de chef operateur a Dakar, a Abidjan ou a
Douala n'a rien de commun, et inventer un chiffre plausible serait exactement
ce que le reste du produit s'interdit (« N'invente jamais »). L'auteur remplit
les quantites et les prix ; le service calcule le reste.

C'est la meme logique que les plans de document : la structure est
professionnelle et imposee, le contenu vient de l'utilisateur.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.models.enums import BudgetCategory, ProjectType


@dataclass(frozen=True, slots=True)
class TemplateLine:
    category: BudgetCategory
    label: str
    unit: str | None = None
    quantity: float = 1.0


#: Postes communs a tout projet audiovisuel, quelle que soit sa forme.
_COMMON: tuple[TemplateLine, ...] = (
    TemplateLine(BudgetCategory.DEVELOPMENT, "Écriture et scénario", "forfait"),
    TemplateLine(BudgetCategory.DEVELOPMENT, "Repérages", "jour", 5),
    TemplateLine(BudgetCategory.DEVELOPMENT, "Droits et autorisations", "forfait"),
    TemplateLine(BudgetCategory.DEVELOPMENT, "Frais de dossier et traductions", "forfait"),
    TemplateLine(BudgetCategory.PRE_PRODUCTION, "Direction de production", "semaine", 4),
    TemplateLine(BudgetCategory.PRE_PRODUCTION, "Casting et figuration", "forfait"),
    TemplateLine(BudgetCategory.PRE_PRODUCTION, "Régie et logistique", "semaine", 4),
    TemplateLine(BudgetCategory.PRE_PRODUCTION, "Assurances", "forfait"),
    TemplateLine(BudgetCategory.PRODUCTION, "Réalisation", "jour", 20),
    TemplateLine(BudgetCategory.PRODUCTION, "Image (chef opérateur et équipe)", "jour", 20),
    TemplateLine(BudgetCategory.PRODUCTION, "Son (ingénieur du son)", "jour", 20),
    TemplateLine(BudgetCategory.PRODUCTION, "Matériel image et son (location)", "jour", 20),
    TemplateLine(BudgetCategory.PRODUCTION, "Transport et défraiements", "jour", 20),
    TemplateLine(BudgetCategory.PRODUCTION, "Hébergement et restauration", "jour", 20),
    TemplateLine(BudgetCategory.POST_PRODUCTION, "Montage image", "semaine", 8),
    TemplateLine(BudgetCategory.POST_PRODUCTION, "Montage et mixage son", "semaine", 3),
    TemplateLine(BudgetCategory.POST_PRODUCTION, "Étalonnage", "forfait"),
    TemplateLine(BudgetCategory.POST_PRODUCTION, "Musique et droits musicaux", "forfait"),
    TemplateLine(BudgetCategory.POST_PRODUCTION, "Sous-titrage et versions", "forfait"),
    TemplateLine(BudgetCategory.DISTRIBUTION, "Frais de festivals et inscriptions", "forfait"),
    TemplateLine(BudgetCategory.DISTRIBUTION, "Matériel promotionnel (affiche, dossier)", "forfait"),
    TemplateLine(BudgetCategory.DISTRIBUTION, "Frais généraux de production", "forfait"),
)

#: Postes supplementaires propres a certaines formes.
_SPECIFIC: dict[ProjectType, tuple[TemplateLine, ...]] = {
    ProjectType.DOCUMENTARY: (
        TemplateLine(BudgetCategory.DEVELOPMENT, "Recherche documentaire et archives", "forfait"),
        TemplateLine(BudgetCategory.PRODUCTION, "Tournage longue durée (immersion)", "jour", 30),
        TemplateLine(BudgetCategory.POST_PRODUCTION, "Droits d'archives et iconographie", "forfait"),
    ),
    ProjectType.FEATURE_FILM: (
        TemplateLine(BudgetCategory.PRE_PRODUCTION, "Décors et construction", "forfait"),
        TemplateLine(BudgetCategory.PRE_PRODUCTION, "Costumes, maquillage, coiffure", "forfait"),
        TemplateLine(BudgetCategory.PRODUCTION, "Interprétation (rôles principaux)", "forfait"),
        TemplateLine(BudgetCategory.PRODUCTION, "Machinerie et éclairage", "jour", 25),
        TemplateLine(BudgetCategory.POST_PRODUCTION, "Effets visuels", "forfait"),
    ),
    ProjectType.SHORT_FILM: (
        TemplateLine(BudgetCategory.PRE_PRODUCTION, "Décors et costumes", "forfait"),
        TemplateLine(BudgetCategory.PRODUCTION, "Interprétation", "forfait"),
    ),
    ProjectType.TV_SERIES: (
        TemplateLine(BudgetCategory.DEVELOPMENT, "Bible et écriture des épisodes", "épisode", 6),
        TemplateLine(BudgetCategory.PRE_PRODUCTION, "Décors récurrents", "forfait"),
        TemplateLine(BudgetCategory.PRODUCTION, "Interprétation (rôles récurrents)", "épisode", 6),
        TemplateLine(BudgetCategory.POST_PRODUCTION, "Générique et habillage", "forfait"),
        TemplateLine(BudgetCategory.DISTRIBUTION, "Livraison aux diffuseurs", "épisode", 6),
    ),
    ProjectType.WEB_SERIES: (
        TemplateLine(BudgetCategory.DEVELOPMENT, "Écriture des épisodes", "épisode", 8),
        TemplateLine(BudgetCategory.POST_PRODUCTION, "Habillage et formats réseaux", "forfait"),
        TemplateLine(BudgetCategory.DISTRIBUTION, "Diffusion et community management", "mois", 6),
    ),
    ProjectType.ANIMATION: (
        TemplateLine(BudgetCategory.DEVELOPMENT, "Character design et univers graphique", "forfait"),
        TemplateLine(BudgetCategory.PRE_PRODUCTION, "Storyboard et animatique", "forfait"),
        TemplateLine(BudgetCategory.PRODUCTION, "Animation (studio)", "minute", 26),
        TemplateLine(BudgetCategory.PRODUCTION, "Décors et compositing", "forfait"),
        TemplateLine(BudgetCategory.POST_PRODUCTION, "Doublage et direction artistique", "forfait"),
    ),
}

#: Ordre d'affichage des categories : celui des phases de production.
CATEGORY_ORDER: tuple[BudgetCategory, ...] = (
    BudgetCategory.DEVELOPMENT,
    BudgetCategory.PRE_PRODUCTION,
    BudgetCategory.PRODUCTION,
    BudgetCategory.POST_PRODUCTION,
    BudgetCategory.DISTRIBUTION,
)


def template_for(project_type: ProjectType) -> list[TemplateLine]:
    """Postes proposes pour ce type de projet, dans l'ordre des phases."""
    lines = list(_COMMON) + list(_SPECIFIC.get(project_type, ()))
    return sorted(lines, key=lambda line: CATEGORY_ORDER.index(line.category))
