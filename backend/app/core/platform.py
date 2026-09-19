"""Cycle de vie de la plateforme : beta interne, puis ouverture commerciale.

FilmFund Africa traverse deux phases. En `internal`, l'equipe eprouve le
produit en conditions reelles ; lui opposer ses propres quotas d'offre
n'aurait aucun sens — elle ne s'achete pas un abonnement a elle-meme. En
`public`, les regles d'offre s'appliquent a tout le monde.

**Ce module ne repond qu'a une question**, et elle est strictement
commerciale : *cette contrainte d'offre s'applique-t-elle a cet
utilisateur ?* Il ne dit rien de l'authentification, du role, de la
propriete d'une ressource ni d'aucune regle de securite — celles-ci sont
verifiees avant lui, partout, dans les deux modes. Un mode « interne » n'est
pas un mode « sans controle » : c'est un mode sans facturation.

**La portee de l'exemption est volontairement etroite** : les
administrateurs, et eux seuls. Un utilisateur ordinaire garde exactement les
regles qu'il aurait en phase commerciale, y compris pendant la beta. Ouvrir
l'exemption a tous ferait de la phase interne une phase gratuite pour le
public, ce qui n'est pas la meme chose.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.config import settings

if TYPE_CHECKING:  # pragma: no cover
    from app.models.user import User


def is_internal() -> bool:
    """Vrai quand la plateforme est en beta privee."""
    return settings.platform_mode == "internal"


def commercial_rules_apply(user: User | None) -> bool:
    """Faut-il opposer les contraintes d'offre a cet utilisateur ?

    Repond `False` dans un seul cas : un administrateur, pendant la phase
    interne. Partout ailleurs — phase publique, ou utilisateur ordinaire en
    phase interne — la reponse est `True` et rien ne change.

    Un utilisateur inconnu repond `True` : en cas de doute sur l'identite,
    la regle s'applique. L'inverse ferait d'un defaut d'identification une
    exemption.
    """
    if not is_internal():
        return True
    if user is None:
        return True
    return not user.is_admin


def platform_status() -> dict[str, str | bool]:
    """Etat affichable du cycle de vie, pour la sonde et l'administration.

    Les dates sont rendues telles quelles, sans etre comparees a l'heure
    courante : **rien ici ne declenche de bascule**. Depasser la date cible
    ne fait pas passer la plateforme en mode public ; seul un changement
    explicite de `PLATFORM_MODE` le fait.
    """
    return {
        "mode": settings.platform_mode,
        "internal": is_internal(),
        "start_date": settings.internal_start_date,
        "target_end_date": settings.internal_target_end_date,
    }
