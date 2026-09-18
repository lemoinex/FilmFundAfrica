"""Fabrique et rendu des notifications.

Une notification est ecrite une fois et relue plus tard, peut-etre dans une
autre langue que celle qui avait cours a son ecriture : elle stocke donc sa
cle de message et ses parametres, pas sa phrase.

`title` et `body` restent remplis, dans la langue de reference. Ce sont un
cache, utile a deux titres : la deduplication compare des titres, et les
notifications ecrites avant l'internationalisation n'ont que ce texte.
"""

from __future__ import annotations

from typing import Any

from app.core.i18n import Locale, translate
from app.models.enums import NotificationType
from app.models.system import Notification


def build_notification(
    *,
    user_id: str,
    title_key: str,
    body_key: str,
    params: dict[str, Any] | None = None,
    notification_type: NotificationType = NotificationType.SYSTEM,
    link: str | None = None,
) -> Notification:
    """Prepare une notification traduisible. Ne l'ajoute pas a la session."""
    values = params or {}
    return Notification(
        user_id=user_id,
        notification_type=notification_type,
        title_key=title_key,
        body_key=body_key,
        params=values,
        title=translate("fr", title_key, **values),
        body=translate("fr", body_key, **values),
        link=link,
    )


def render_notification(notification: Notification, locale: Locale) -> tuple[str, str]:
    """Titre et corps dans la langue demandee.

    Sans cle — cas des notifications anterieures a cette mecanique — on rend
    le texte stocke : il vaut mieux une phrase dans la mauvaise langue qu'une
    notification vide.
    """
    params = notification.params or {}
    title = (
        translate(locale, notification.title_key, **params)
        if notification.title_key
        else notification.title
    )
    body = (
        translate(locale, notification.body_key, **params)
        if notification.body_key
        else notification.body
    )
    return title, body
