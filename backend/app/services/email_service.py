"""Envoi d'e-mails transactionnels.

Si SMTP n'est pas configure, les messages sont journalises au lieu d'etre
envoyes : l'application reste utilisable en developpement sans serveur mail.
"""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger("filmfund.email")


class EmailService:
    @property
    def enabled(self) -> bool:
        return bool(settings.smtp_host)

    # ------------------------------------------------------------------
    def send(self, to: str, subject: str, body: str) -> bool:
        if not self.enabled:
            logger.warning(
                "SMTP non configuré : e-mail non envoyé",
                extra={"event": "email_skipped"},
            )
            logger.debug("Contenu de l'e-mail non envoyé :\n%s", body)
            return False

        message = EmailMessage()
        message["From"] = settings.smtp_from
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body)

        try:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
                if settings.smtp_tls:
                    server.starttls()
                if settings.smtp_user:
                    server.login(settings.smtp_user, settings.smtp_password)
                server.send_message(message)
        except (smtplib.SMTPException, OSError) as exc:
            # Un echec d'envoi ne doit jamais faire echouer l'action metier.
            logger.error("Échec d'envoi d'e-mail : %s", exc, extra={"event": "email_failed"})
            return False

        logger.info("e-mail envoyé", extra={"event": "email_sent"})
        return True

    # ------------------------------------------------------------------
    def send_password_reset(self, to: str, reset_url: str) -> bool:
        body = (
            "Bonjour,\n\n"
            "Vous avez demandé la réinitialisation de votre mot de passe FilmFund Africa.\n"
            f"Ouvrez ce lien pour choisir un nouveau mot de passe :\n\n{reset_url}\n\n"
            f"Ce lien expire dans {settings.password_reset_expire_minutes} minutes.\n"
            "Si vous n'êtes pas à l'origine de cette demande, ignorez ce message : "
            "votre mot de passe reste inchangé.\n\n"
            "— L'équipe FilmFund Africa"
        )
        return self.send(to, "Réinitialisation de votre mot de passe", body)

    def send_email_verification(self, to: str, verify_url: str) -> bool:
        body = (
            "Bonjour,\n\n"
            "Bienvenue sur FilmFund Africa. Confirmez cette adresse pour activer "
            "votre compte :\n\n"
            f"{verify_url}\n\n"
            f"Ce lien expire dans {settings.email_verification_expire_minutes // 60} heures.\n"
            "Si vous n'êtes pas à l'origine de cette inscription, ignorez ce message : "
            "aucun compte ne sera activé.\n\n"
            "— L'équipe FilmFund Africa"
        )
        return self.send(to, "Confirmez votre adresse e-mail", body)

    def send_registration_attempt(self, to: str) -> bool:
        """Prévient le titulaire qu'on a tenté de s'inscrire avec son adresse.

        C'est la contrepartie de la réponse unique à l'inscription : puisque
        l'API ne dit plus si l'adresse est prise, c'est son propriétaire — et
        lui seul — qui l'apprend.
        """
        body = (
            "Bonjour,\n\n"
            "Quelqu'un vient de tenter de créer un compte FilmFund Africa avec "
            "cette adresse, qui est déjà la vôtre.\n\n"
            "Si c'était vous, connectez-vous simplement : "
            f"{settings.frontend_url}/connexion\n"
            "Mot de passe oublié ? "
            f"{settings.frontend_url}/mot-de-passe-oublie\n\n"
            "Si ce n'était pas vous, il n'y a rien à faire : aucun compte n'a été "
            "créé et le vôtre est inchangé.\n\n"
            "— L'équipe FilmFund Africa"
        )
        return self.send(to, "Tentative d'inscription avec votre adresse", body)

    def send_notification(self, to: str, title: str, body: str) -> bool:
        return self.send(to, f"[FilmFund Africa] {title}", body)
