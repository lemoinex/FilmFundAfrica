"""Création ou promotion d'un compte administrateur.

    python -m scripts.create_admin --email admin@exemple.com
    python -m scripts.create_admin --email admin@exemple.com --promote

Le mot de passe n'est JAMAIS passé en argument ni écrit dans un fichier : il
est demandé à la saisie, masqué, et confirmé. Un mot de passe en ligne de
commande se retrouverait dans l'historique du shell et dans la liste des
processus de la machine.

Pour un déploiement automatisé, la variable d'environnement
`FILMFUND_ADMIN_PASSWORD` est acceptée — à condition qu'elle ne soit pas
écrite dans un fichier versionné.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import UTC, datetime, timedelta
from getpass import getpass

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.billing import Subscription
from app.models.enums import PlanCode, SubscriptionStatus, UserType
from app.models.user import Profile, User
from app.schemas.auth import MIN_PASSWORD_LENGTH, _validate_password_strength
from app.services.credit_service import CreditService


def read_password() -> str:
    """Lit le mot de passe sans jamais l'afficher ni le stocker."""
    from_env = os.environ.get("FILMFUND_ADMIN_PASSWORD")
    if from_env:
        try:
            return _validate_password_strength(from_env)
        except ValueError as exc:
            # Message lisible plutôt qu'une trace : l'utilisateur doit juste
            # corriger sa variable d'environnement.
            raise SystemExit(f"FILMFUND_ADMIN_PASSWORD refusé : {exc}") from None

    if not sys.stdin.isatty():
        raise SystemExit(
            "Aucun terminal interactif : renseignez FILMFUND_ADMIN_PASSWORD "
            "pour un usage automatisé."
        )

    while True:
        password = getpass("Mot de passe : ")
        try:
            _validate_password_strength(password)
        except ValueError as exc:
            print(f"  ✕ {exc}")
            continue
        if password != getpass("Confirmation  : "):
            print("  ✕ Les deux saisies diffèrent.")
            continue
        return password


def create_admin(email: str, *, promote_only: bool = False) -> None:
    email = email.strip().lower()

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))

        if user is not None:
            was_admin = user.user_type == UserType.ADMIN
            user.user_type = UserType.ADMIN
            user.is_active = True
            user.is_verified = True

            if not promote_only:
                user.hashed_password = hash_password(read_password())
                # Invalide les sessions ouvertes avec l'ancien mot de passe.
                user.token_version += 1

            db.commit()
            action = "déjà administrateur, compte mis à jour" if was_admin else "promu administrateur"
            print(f"✓ {email} — {action}.")
            return

        if promote_only:
            raise SystemExit(f"Aucun compte ne correspond à {email}.")

        password = read_password()
        first_name = input("Prénom        : ").strip() or "Administrateur"
        last_name = input("Nom           : ").strip() or "FilmFund"

        user = User(
            email=email,
            hashed_password=hash_password(password),
            user_type=UserType.ADMIN,
            is_active=True,
            is_verified=True,
        )
        user.profile = Profile(first_name=first_name, last_name=last_name)
        db.add(user)
        db.flush()

        # L'administration a besoin de l'export et du matching : offre Producteur.
        credits = CreditService(db)
        credits.ensure_plans()
        plan = credits.get_plan(PlanCode.PRODUCER)
        now = datetime.now(UTC)
        user.subscription = Subscription(
            plan_id=plan.id,
            status=SubscriptionStatus.ACTIVE,
            started_at=now,
            current_period_end=now + timedelta(days=365),
        )
        user.ai_credits_remaining = plan.monthly_ai_credits
        user.ai_credits_period_start = now

        db.commit()
        print(f"✓ {email} — compte administrateur créé (offre {plan.name}).")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Crée un compte administrateur, ou promeut un compte existant.",
        epilog=(
            f"Le mot de passe doit faire au moins {MIN_PASSWORD_LENGTH} caractères "
            "et mêler lettres et chiffres."
        ),
    )
    parser.add_argument("--email", required=True, help="Adresse e-mail du compte")
    parser.add_argument(
        "--promote",
        action="store_true",
        help="Promeut un compte existant sans toucher à son mot de passe",
    )
    args = parser.parse_args()

    create_admin(args.email, promote_only=args.promote)


if __name__ == "__main__":
    main()
