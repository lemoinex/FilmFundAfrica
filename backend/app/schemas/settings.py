"""Contrats de l'ecran de configuration de l'IA.

**Aucun de ces schemas ne peut transporter une cle vers le client.** La cle
entre par `AIConfigUpdate` et ne ressort jamais : `AIProviderState` n'expose
qu'une empreinte de quatre caracteres. Ce n'est pas une precaution de forme —
une administration reste une page web, et une page web finit par etre lue par
quelqu'un d'autre que son proprietaire.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

#: Les fournisseurs que l'application sait construire.
ProviderName = Literal["anthropic", "openai", "mock"]


class AIProviderState(BaseModel):
    """Etat d'un fournisseur, tel qu'un administrateur peut le lire."""

    name: ProviderName
    #: Vrai des qu'une cle est disponible, d'ou qu'elle vienne.
    configured: bool
    #: Quatre derniers caracteres, jamais davantage. `None` si aucune cle.
    key_hint: str | None = None
    #: `database` (saisie ici), `environment` (variable), `unreadable`
    #: (chiffree avec une cle de serveur qui a change) ou `none`.
    key_source: Literal["database", "environment", "unreadable", "none"] = "none"
    #: Modele applique si aucun n'est saisi. Vide = le fournisseur n'en
    #: propose pas, et le modele devient obligatoire.
    default_model: str = ""
    #: Ce fournisseur exige-t-il une cle pour fonctionner ?
    requires_key: bool = True


class AIConfigRead(BaseModel):
    active_provider: ProviderName
    #: Modele reellement utilise, defaut du fournisseur compris.
    effective_model: str
    #: Modele saisi, s'il l'a ete. Vide = « laisser le defaut ».
    configured_model: str = ""
    model_source: Literal["database", "environment", "provider_default", "none"] = "none"
    providers: list[AIProviderState]


class AIConfigUpdate(BaseModel):
    """Modification demandee. Tous les champs sont facultatifs.

    Un champ absent n'est pas touche ; une chaine vide efface le reglage et
    fait retomber sur l'environnement. La distinction compte : sans elle, on
    ne pourrait jamais revenir a la configuration du serveur une fois une
    valeur saisie ici.
    """

    provider: ProviderName | None = None
    model: str | None = Field(default=None, max_length=120)
    #: Fournisseur auquel la cle appartient. Obligatoire des qu'`api_key`
    #: est fourni : une cle sans destinataire irait au fournisseur actif du
    #: moment, ce qui n'est pas forcement celui qu'on configure.
    key_provider: ProviderName | None = None
    api_key: str | None = Field(default=None, max_length=512)

    @field_validator("model", "api_key")
    @classmethod
    def _strip(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None


class AIConfigTestResult(BaseModel):
    """Resultat d'un appel reel, declenche par l'administrateur."""

    ok: bool
    provider: str
    model: str
    #: Message du fournisseur quand l'appel echoue. C'est la seule chose
    #: utile dans ce cas, et la masquer obligerait a fouiller les journaux.
    detail: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
