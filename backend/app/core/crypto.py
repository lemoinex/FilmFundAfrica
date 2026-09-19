"""Chiffrement des secrets conserves en base.

Une cle de fournisseur d'IA depense de l'argent. La stocker en clair
reviendrait a faire d'une sauvegarde de base, d'un export CSV ou d'une
injection SQL en lecture seule une facture ouverte chez Anthropic ou OpenAI.
Elle est donc chiffree avant d'etre ecrite, et la base ne contient jamais que
le chiffre.

**Ce que cela protege, et ce que cela ne protege pas.** La cle de chiffrement
vit dans l'environnement du serveur, pas dans la base : quiconque obtient une
copie de la base seule n'a rien. Quiconque obtient l'environnement du serveur
a tout — ce n'est pas la menace visee, et aucun chiffrement applicatif n'y
change quoi que ce soit.
"""

from __future__ import annotations

import base64

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from app.core.config import settings
from app.core.errors import AppError

#: Prefixe de version du format stocke.
#:
#: Sans lui, changer de schema de chiffrement rendrait les anciennes valeurs
#: indechiffrables *en silence* : on lirait des octets valides comme du
#: charabia. Avec lui, on sait tout de suite qu'on ne sait pas lire.
SCHEME = "v1"

#: Contexte de derivation. Il isole cet usage de tout autre derive du meme
#: secret : un jeton JWT et une cle de fournisseur ne doivent jamais se
#: retrouver chiffres avec la meme cle effective.
_INFO = b"filmfund.secret-box.v1"


def _fernet() -> Fernet:
    """Cle de chiffrement derivee du secret du serveur.

    `SECRETS_KEY` d'abord, `JWT_SECRET` a defaut : imposer une variable de plus
    ferait echouer les deploiements existants au demarrage pour une
    fonctionnalite optionnelle. Le prix de ce repli est reel et documente —
    faire tourner `JWT_SECRET` rend les cles stockees illisibles.
    """
    secret = settings.secrets_key or settings.jwt_secret
    material = HKDF(
        algorithm=hashes.SHA256(), length=32, salt=None, info=_INFO
    ).derive(secret.encode("utf-8"))
    return Fernet(base64.urlsafe_b64encode(material))


def encrypt_secret(plaintext: str) -> str:
    """Chiffre une valeur destinee a la base."""
    token = _fernet().encrypt(plaintext.encode("utf-8")).decode("ascii")
    return f"{SCHEME}:{token}"


def decrypt_secret(stored: str) -> str:
    """Dechiffre une valeur lue en base.

    Echoue franchement plutot que de rendre une chaine vide : une cle vide
    serait prise pour « aucune cle configuree », et l'exploitant chercherait
    une cle absente alors qu'elle est la, simplement illisible.
    """
    scheme, _, token = stored.partition(":")
    if not token or scheme != SCHEME:
        raise AppError("secret.unreadable", code="secret_unreadable", status_code=500)
    try:
        return _fernet().decrypt(token.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise AppError(
            "secret.unreadable", code="secret_unreadable", status_code=500
        ) from exc
