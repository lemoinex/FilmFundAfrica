"""Resolution des reglages d'IA : administration d'abord, environnement ensuite.

Un fournisseur se construit depuis une requete HTTP, depuis le worker, et
depuis des scripts. Aucun de ces appelants n'a de raison de savoir d'ou vient
la cle. Ce module repond a la seule question qui compte — « quelle cle, quel
fournisseur, quel modele ? » — et garde l'ordre de priorite au meme endroit.

**Pourquoi aucun cache.** Un appel de generation dure plusieurs secondes ;
un `SELECT` sur une colonne unique et indexee ne se mesure pas a cote. Un
cache n'achèterait rien et couterait la question a laquelle il faut toujours
repondre ensuite : combien de temps une cle revoquée reste-t-elle active ?
Ici, la reponse est « le temps du prochain appel ».
"""

from __future__ import annotations

import logging

from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.core.errors import AppError

logger = logging.getLogger("filmfund.ai")


def _from_database(key: str) -> str | None:
    """Lit un reglage, sans jamais empecher l'application de fonctionner.

    Une base injoignable ou une table absente — migrations pas encore
    passees, script hors contexte — ne doit pas rendre l'IA inutilisable
    alors que l'environnement porte tout ce qu'il faut. On retombe donc sur
    l'environnement en le disant au journal.
    """
    try:
        from app.core.database import SessionLocal
        from app.services.settings_service import SettingsService

        with SessionLocal() as db:
            return SettingsService(db).get(key)
    except AppError:
        # Secret illisible : la cle de chiffrement a change. Se taire ferait
        # croire a une absence de configuration ; on laisse remonter.
        raise
    except (SQLAlchemyError, OSError) as exc:
        logger.warning(
            "réglage IA illisible en base, repli sur l'environnement",
            extra={"event": "ai_setting_fallback", "setting": key, "reason": str(exc)},
        )
        return None


def effective_provider() -> str:
    """Fournisseur actif : celui choisi dans l'administration, sinon `AI_PROVIDER`."""
    from app.services.settings_service import KEY_AI_PROVIDER

    return _from_database(KEY_AI_PROVIDER) or settings.ai_provider


def effective_model() -> str:
    """Modele vise. Vide signifie « le defaut du fournisseur »."""
    from app.services.settings_service import KEY_AI_MODEL

    return _from_database(KEY_AI_MODEL) or settings.ai_model


def api_key_for(provider: str) -> str:
    """Cle du fournisseur donne.

    `AI_API_KEY` ne vaut que pour le fournisseur actif : elle appartient a un
    compte chez une societe precise. L'envoyer a l'autre fournisseur parce
    qu'il se trouve etre selectionne reviendrait a presenter une cle Anthropic
    a OpenAI — et a la faire apparaitre dans les journaux d'un tiers.
    """
    from app.services.settings_service import ai_key_setting

    stored = _from_database(ai_key_setting(provider))
    if stored:
        return stored
    if provider.lower() == effective_provider().lower():
        return settings.ai_api_key
    return ""
