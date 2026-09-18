"""Suivi des erreurs (Sentry), avec expurgation des donnees personnelles.

Sans `SENTRY_DSN`, rien n'est initialise : l'application tourne exactement
comme avant, et aucune requete ne part vers un tiers. C'est le meme principe
que `AI_PROVIDER=mock` ou `PAYMENT_PROVIDER=manual` — l'installation par
defaut ne depend d'aucun service externe.

**Ce que ce module ne doit jamais laisser partir.** Un rapport d'erreur part
chez un tiers : il ne peut pas emporter ce que les gens nous ont confie.
Trois categories sont expurgees avant l'envoi :

* les **identifiants** — en-tetes `Authorization`, cookies, jetons de
  reinitialisation ou de confirmation qui trainent dans une URL ;
* les **donnees personnelles** — adresses e-mail, numeros de telephone ;
* le **contenu des dossiers** — synopsis, scenarios, budgets : c'est le
  travail des auteurs, il n'a rien a faire dans un outil d'observabilite.

L'expurgation ci-dessous reconnait ce qu'elle nomme. Trois reglages ferment
ce qu'elle ne peut pas nommer, parce que le SDK le joint sous des noms
arbitraires : le corps des requetes (`max_request_body_size="never"`), les
donnees d'identification (`send_default_pii=False`) et les variables locales
de chaque frame (`include_local_variables=False`) — ces dernieres portent les
prompts, les segments de scenario et les lignes de budget sous les noms de
variables du code. On perd en confort de diagnostic ce qu'on gagne a ne pas
exfiltrer le travail des auteurs.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from app.core.config import settings

logger = logging.getLogger("filmfund.observability")

#: Faux tant que `setup_sentry()` n'a pas abouti. Evite d'importer le SDK a
#: chaque requete quand le suivi n'est pas configure, c'est-a-dire toujours
#: en developpement et dans les tests.
_enabled = False

#: Cles d'en-tetes et de donnees a retirer, quelle que soit leur casse.
SENSITIVE_KEYS = frozenset(
    {
        "authorization",
        "cookie",
        "set-cookie",
        "x-api-key",
        "x-payment-signature",
        "password",
        "current_password",
        "new_password",
        "token",
        "access_token",
        "refresh_token",
        "hashed_password",
        "jwt_secret",
        "ai_api_key",
        "payment_webhook_secret",
        "n8n_api_key",
    }
)

#: Champs porteurs du travail des auteurs : jamais transmis.
CONTENT_KEYS = frozenset(
    {
        "content",
        "logline",
        "short_synopsis",
        "long_synopsis",
        "concept",
        "stakes",
        "director_vision",
        "payload",
        "provider_payload",
        "body",
    }
)

REDACTED = "[expurgé]"

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
#: Jeton passe dans une URL de confirmation ou de reinitialisation.
_TOKEN_IN_URL_RE = re.compile(r"(token=)[^&\s]+", flags=re.IGNORECASE)
#: Numero de telephone international, tel qu'utilise par le mobile money.
_PHONE_RE = re.compile(r"\+?\d[\d\s.-]{7,}\d")


def scrub_text(value: str) -> str:
    """Retire d'une chaine ce qui identifie une personne."""
    value = _EMAIL_RE.sub(REDACTED, value)
    value = _TOKEN_IN_URL_RE.sub(r"\1" + REDACTED, value)
    return _PHONE_RE.sub(REDACTED, value)


def scrub(value: Any, key: str | None = None) -> Any:
    """Expurge recursivement une structure avant envoi.

    Le nom de la cle decide : une valeur sensible est remplacee sans etre
    inspectee, ce qui evite de dependre de la forme de son contenu.
    """
    if key is not None:
        lowered = key.lower()
        if lowered in SENSITIVE_KEYS or lowered in CONTENT_KEYS:
            return REDACTED

    if isinstance(value, dict):
        return {name: scrub(item, name) for name, item in value.items()}
    if isinstance(value, list | tuple):
        return [scrub(item) for item in value]
    if isinstance(value, str):
        return scrub_text(value)
    return value


def before_send(event: dict[str, Any], hint: dict[str, Any] | None = None) -> dict[str, Any]:
    """Dernier filtre avant l'envoi d'un evenement."""
    return scrub(event)


def setup_sentry() -> bool:
    """Initialise Sentry si un DSN est configure. Renvoie l'etat obtenu."""
    global _enabled

    dsn = settings.sentry_dsn.strip()
    if not dsn:
        return False

    try:
        import sentry_sdk
    except ModuleNotFoundError:  # pragma: no cover - installation incomplete
        logger.warning(
            "SENTRY_DSN est défini mais le paquet `sentry-sdk` n'est pas installé : "
            "aucune erreur ne sera remontée."
        )
        return False

    sentry_sdk.init(
        dsn=dsn,
        environment=settings.sentry_environment or settings.environment,
        release=settings.sentry_release or None,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        # Ce que l'expurgation par nom de clé ne peut pas couvrir : on le
        # ferme à la source plutôt que d'espérer le reconnaître.
        send_default_pii=False,
        max_request_body_size="never",
        include_local_variables=False,
        before_send=before_send,
    )
    _enabled = True
    logger.info(
        "suivi des erreurs actif",
        extra={"event": "sentry_enabled"},
    )
    return True


def tag_request(request_id: str) -> None:
    """Rattache l'identifiant de requete a l'evenement Sentry.

    C'est ce qui rend un rapport exploitable : le meme `request_id` figure
    dans les journaux JSON et dans l'en-tete `X-Request-ID` renvoye a
    l'appelant, si bien qu'une erreur remontee se relie a la trace complete
    de la requete sans avoir a joindre son contenu.
    """
    if not _enabled:
        return
    import sentry_sdk

    sentry_sdk.set_tag("request_id", request_id)


def sentry_status() -> str:
    """Etat du suivi des erreurs, pour la sonde de sante."""
    if not settings.sentry_dsn.strip():
        return "disabled"
    try:
        import sentry_sdk
    except ModuleNotFoundError:  # pragma: no cover
        return "unavailable"
    return "active" if sentry_sdk.get_client().is_active() else "disabled"
