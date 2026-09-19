"""Reglages modifiables depuis l'administration.

La table `app_settings` existait depuis la migration initiale sans etre lue
par personne. Elle sert ici a ce pour quoi elle avait ete prevue : deplacer
quelques reglages de l'environnement vers l'ecran, pour qu'un exploitant
change de fournisseur d'IA ou remplace une cle expiree sans redeployer.

**L'environnement reste le socle.** Un reglage absent de la base retombe sur
sa variable d'environnement. Un deploiement qui n'a jamais ouvert cet ecran
se comporte exactement comme avant.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.crypto import decrypt_secret, encrypt_secret
from app.models.system import AppSetting

#: Fournisseur actif, quand l'administration en a choisi un.
KEY_AI_PROVIDER = "ai.provider"
#: Modele vise, quand l'administration en a saisi un.
KEY_AI_MODEL = "ai.model"


def ai_key_setting(provider: str) -> str:
    """Nom du reglage portant la cle d'un fournisseur.

    Une cle par fournisseur, et non une cle partagee : passer d'Anthropic a
    OpenAI puis revenir ne doit pas obliger a ressaisir la premiere. Ce sont
    deux comptes chez deux societes, ils n'ont aucune raison de partager un
    emplacement.
    """
    return f"ai.key.{provider.lower()}"


class SettingsService:
    """Lecture/ecriture des reglages, avec chiffrement des secrets."""

    def __init__(self, db: Session) -> None:
        self.db = db

    # ------------------------------------------------------------------
    def _row(self, key: str) -> AppSetting | None:
        return self.db.execute(
            select(AppSetting).where(AppSetting.key == key)
        ).scalar_one_or_none()

    def get(self, key: str) -> str | None:
        """Valeur en clair, ou `None` si le reglage n'existe pas."""
        row = self._row(key)
        if row is None or not row.value:
            return None
        if row.value_type == "secret":
            return decrypt_secret(row.value)
        return row.value

    def set(self, key: str, value: str, *, secret: bool = False,
            description: str | None = None) -> None:
        """Ecrit un reglage. Une valeur vide efface le reglage."""
        row = self._row(key)
        if not value:
            if row is not None:
                self.db.delete(row)
            return
        stored = encrypt_secret(value) if secret else value
        value_type = "secret" if secret else "string"
        if row is None:
            self.db.add(
                AppSetting(
                    key=key, value=stored, value_type=value_type, description=description
                )
            )
        else:
            row.value = stored
            row.value_type = value_type
            if description is not None:
                row.description = description

    def delete(self, key: str) -> None:
        row = self._row(key)
        if row is not None:
            self.db.delete(row)

    # ------------------------------------------------------------------
    def key_hint(self, provider: str) -> str | None:
        """Empreinte affichable d'une cle : jamais la cle elle-meme.

        Un administrateur a besoin de savoir *laquelle* est en place — pour la
        reconnaitre parmi plusieurs, ou verifier qu'une rotation a bien pris.
        Il n'a jamais besoin de la relire en entier, et la renvoyer ferait
        d'un simple XSS sur l'administration une fuite de secret.
        """
        raw = self.get(ai_key_setting(provider))
        if not raw:
            return None
        return f"…{raw[-4:]}" if len(raw) > 4 else "…"
