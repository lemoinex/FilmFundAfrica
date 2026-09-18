"""Jeu de données de démonstration.

    python -m scripts.seed          # crée les données si elles n'existent pas
    python -m scripts.seed --reset  # supprime puis recrée les données de démo

IMPORTANT : toutes les opportunités créées ici sont FICTIVES. Elles portent
`is_demo=True`, le statut `UNVERIFIED` et la mention « DEMO DATA — NOT REAL »
dans leur description. Elles ne doivent jamais être présentées à un
utilisateur comme de véritables opportunités de financement.
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select

from app.core.database import SessionLocal, engine
from app.core.security import hash_password
from app.models import Base
from app.models.enums import (
    DocumentType,
    FundingCategory,
    FundingStatus,
    NotificationType,
    PlanCode,
    ProjectStatus,
    ProjectType,
    UserType,
)
from app.models.funding import FundingOpportunity, FundingRequirement
from app.models.project import Character, Project
from app.models.user import Profile, User
from app.services.credit_service import CreditService
from app.services.document_service import DocumentService
from app.services.notification_service import build_notification
from app.services.scoring_service import ScoringService

DEMO_MARKER = "DEMO DATA — NOT REAL"
#: `example.com` et non un domaine en `.test` : les TLD a usage special sont
#: refuses par la validation d'adresse, et un compte de demonstration cree
#: directement en base ne pourrait alors pas se connecter par l'interface.
DEMO_PASSWORD = "Demo2026!"

DEMO_USERS = [
    {
        "email": "auteur.demo@example.com",
        "user_type": UserType.AUTHOR,
        "first_name": "Aïcha",
        "last_name": "Ndiaye",
        "country": "Sénégal",
        "city": "Dakar",
        "profession": "Réalisatrice documentaire",
        "plan": PlanCode.PRO_AUTHOR,
    },
    {
        "email": "producteur.demo@example.com",
        "user_type": UserType.PRODUCER,
        "first_name": "Emmanuel",
        "last_name": "Mbarga",
        "country": "Cameroun",
        "city": "Douala",
        "profession": "Producteur",
        "plan": PlanCode.PRODUCER,
    },
]

ADMIN_USER = {
    "email": "admin.demo@example.com",
    "user_type": UserType.ADMIN,
    "first_name": "Admin",
    "last_name": "FilmFund",
    "country": "Cameroun",
    "city": "Yaoundé",
    "profession": "Administration",
    "plan": PlanCode.PRODUCER,
}

DEMO_PROJECTS = [
    {
        "owner": 0,
        "title": "Les Gardiennes du fleuve",
        "project_type": ProjectType.DOCUMENTARY,
        "genre": "Documentaire de création",
        "country": "Sénégal",
        "language": "Français",
        "duration": 90,
        "status": ProjectStatus.DEVELOPMENT,
        "theme": "Transmission, écologie, rôle des femmes dans la gestion de l'eau",
        "logline": (
            "Sur les rives du fleuve Sénégal, trois femmes de trois générations défendent "
            "un savoir hérité que la montée du sel menace d'effacer."
        ),
        "short_synopsis": (
            "Dans un village du delta, Fatou, soixante-dix ans, a passé sa vie à lire le "
            "fleuve. Sa fille Mariama a quitté l'eau pour la ville ; sa petite-fille Khady "
            "revient avec un diplôme d'hydrologie et des mesures qui contredisent la "
            "mémoire de sa grand-mère. Une saison durant, le film suit la négociation entre "
            "trois manières de connaître un même fleuve, jusqu'à la crue qui les oblige à "
            "décider ensemble."
        ),
        "concept": (
            "Un film de terrain, tourné sur une saison complète, qui met en tension savoir "
            "vernaculaire et mesure scientifique sans arbitrer."
        ),
        "stakes": (
            "La salinisation rend une partie des terres incultivables ; la famille doit "
            "décider de rester ou de partir."
        ),
        "director_vision": (
            "Caméra à hauteur d'épaule, plans longs, son direct. Aucune voix off : le film "
            "se tient à la parole des trois femmes."
        ),
        "objectives": "Festivals documentaires, diffusion TV francophone, circulation scolaire.",
        "target_audience": (
            "Public de documentaires de création, chaînes francophones, secteur éducatif."
        ),
        "characters": [
            {
                "name": "Fatou Sow",
                "role": "Protagoniste",
                "age": "72 ans",
                "description": (
                    "Gardienne de la mémoire du fleuve, lit les courants et les saisons "
                    "sans instrument."
                ),
                "arc": (
                    "Passe du refus de la mesure scientifique à une transmission acceptée, "
                    "à ses conditions."
                ),
            },
            {
                "name": "Khady Sow",
                "role": "Protagoniste",
                "age": "26 ans",
                "description": "Hydrologue formée à Dakar, revenue enquêter sur sa propre famille.",
                "arc": "Découvre que ses données ne disent pas tout de ce que sait sa grand-mère.",
            },
            {
                "name": "Mariama Sow",
                "role": "Personnage secondaire",
                "age": "48 ans",
                "description": "Commerçante en ville, partagée entre deux mondes.",
                "arc": "Devient la médiatrice qu'elle refusait d'être.",
            },
        ],
    },
    {
        "owner": 0,
        "title": "Taxi 237",
        "project_type": ProjectType.TV_SERIES,
        "genre": "Comédie dramatique",
        "country": "Cameroun",
        "language": "Français",
        "duration": 26,
        "status": ProjectStatus.WRITING,
        "theme": "Débrouille urbaine, solidarité, corruption ordinaire",
        "logline": (
            "Un chauffeur de taxi de Douala, endetté jusqu'au cou, devient malgré lui le "
            "confident de toute une ville."
        ),
        "concept": (
            "Série d'épisodes de 26 minutes ; chaque épisode suit une course, un passager, "
            "un fil qui se referme sur la dette du héros."
        ),
        "stakes": "Rembourser en six mois ou perdre le taxi, seul bien de la famille.",
        "target_audience": "18-45 ans, chaînes généralistes africaines et plateformes.",
        "characters": [
            {
                "name": "Blaise Tchamba",
                "role": "Protagoniste",
                "age": "38 ans",
                "description": "Chauffeur de taxi, bavard, incapable de dire non.",
                "arc": "Apprend à poser des limites sans perdre ce qui le rend aimable.",
            },
            {
                "name": "Mme Ngo",
                "role": "Force antagoniste",
                "age": "55 ans",
                "description": "Créancière, propriétaire de la moitié des taxis du quartier.",
                "arc": "Information non fournie.",
            },
        ],
    },
    {
        "owner": 1,
        "title": "La Dernière Récolte",
        "project_type": ProjectType.FEATURE_FILM,
        "genre": "Drame",
        "country": "Cameroun",
        "language": "Français",
        "duration": 110,
        "status": ProjectStatus.IDEA,
        "theme": "Héritage, terre, conflit intergénérationnel",
        "logline": (
            "À la mort de son père, un ingénieur agronome rentre au village pour vendre la "
            "plantation familiale et découvre qu'elle fait vivre trente personnes."
        ),
        "characters": [
            {
                "name": "Serge Etoa",
                "role": "Protagoniste",
                "age": "41 ans",
                "description": "Agronome installé en Europe, revenu pour une semaine.",
                "arc": "Information non fournie.",
            }
        ],
    },
]

DEMO_OPPORTUNITIES = [
    {
        "name": "Fonds Démo Écritures du Sud",
        "organization": "Organisme fictif de démonstration",
        "category": FundingCategory.FUND,
        "description": (
            f"{DEMO_MARKER}. Dispositif entièrement fictif créé pour la démonstration de la "
            "plateforme. Aide à l'écriture pour documentaires et fictions portés par des "
            "auteurs d'Afrique francophone."
        ),
        "country": "France",
        "eligible_countries": "Sénégal,Cameroun,Côte d'Ivoire,Mali,Burkina Faso,Bénin",
        "project_types": "DOCUMENTARY,FEATURE_FILM",
        "genres": "Documentaire de création,Drame",
        "languages": "Français",
        "minimum_budget": 5000,
        "maximum_budget": 15000,
        "currency": "EUR",
        "deadline": date.today() + timedelta(days=38),
        "requirements": "Synopsis, note d'intention, CV du réalisateur, budget prévisionnel",
        "requirement_items": [
            ("Synopsis de 1 à 3 pages", DocumentType.SHORT_SYNOPSIS),
            ("Note d'intention du réalisateur", DocumentType.INTENT_NOTE),
            ("Budget prévisionnel", None),
        ],
    },
    {
        "name": "Résidence Démo Grand Fleuve",
        "organization": "Organisme fictif de démonstration",
        "category": FundingCategory.RESIDENCY,
        "description": (
            f"{DEMO_MARKER}. Résidence d'écriture fictive de huit semaines, utilisée "
            "uniquement pour illustrer le fonctionnement de la veille."
        ),
        "country": "Sénégal",
        "eligible_countries": "Sénégal,Mauritanie,Mali",
        "project_types": "DOCUMENTARY,SHORT_FILM",
        "genres": "Documentaire de création",
        "languages": "Français",
        "minimum_budget": 2000,
        "maximum_budget": 6000,
        "currency": "EUR",
        "deadline": date.today() + timedelta(days=12),
        "requirements": "Synopsis, note d'intention, lettre de motivation",
        "requirement_items": [
            ("Synopsis", DocumentType.SHORT_SYNOPSIS),
            ("Note d'intention", DocumentType.INTENT_NOTE),
        ],
    },
    {
        "name": "Appel Démo Séries Africaines",
        "organization": "Organisme fictif de démonstration",
        "category": FundingCategory.PITCHING_FORUM,
        "description": (
            f"{DEMO_MARKER}. Forum de pitch fictif dédié aux séries, créé pour la "
            "démonstration du module de matching."
        ),
        "country": "Côte d'Ivoire",
        "eligible_countries": "Cameroun,Côte d'Ivoire,Sénégal,Gabon,Togo",
        "project_types": "TV_SERIES,WEB_SERIES",
        "genres": "Comédie dramatique,Drame,Comédie",
        "languages": "Français",
        "minimum_budget": 10000,
        "maximum_budget": 50000,
        "currency": "EUR",
        "deadline": date.today() + timedelta(days=75),
        "requirements": "Bible de série, pilote, pitch écrit",
        "requirement_items": [
            ("Bible de série", DocumentType.SERIES_BIBLE),
            ("Pitch écrit", DocumentType.WRITTEN_PITCH),
        ],
    },
]


def _create_user(db, definition: dict, credits: CreditService) -> User:
    user = User(
        email=definition["email"],
        hashed_password=hash_password(DEMO_PASSWORD),
        user_type=definition["user_type"],
        is_active=True,
        is_verified=True,
    )
    user.profile = Profile(
        first_name=definition["first_name"],
        last_name=definition["last_name"],
        country=definition["country"],
        city=definition["city"],
        profession=definition["profession"],
    )
    db.add(user)
    db.flush()

    plan = credits.get_plan(definition["plan"])
    credits.attach_default_plan(user)
    user.subscription.plan_id = plan.id
    user.ai_credits_remaining = plan.monthly_ai_credits
    db.flush()
    return user


def seed(reset: bool = False, force: bool = False) -> None:
    from app.core.config import settings

    if settings.is_production and not force:
        raise SystemExit(
            "Refus d'exécuter le seed avec ENVIRONMENT=production : il crée un compte "
            "ADMIN dont le mot de passe est publié dans le README. Utilisez --force "
            "uniquement si vous savez ce que vous faites, puis changez immédiatement "
            "ces mots de passe."
        )

    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        credits = CreditService(db)
        credits.ensure_plans()
        db.commit()

        if reset:
            for definition in [*DEMO_USERS, ADMIN_USER]:
                existing = db.scalar(select(User).where(User.email == definition["email"]))
                if existing is not None:
                    db.delete(existing)
            for opportunity in db.scalars(
                select(FundingOpportunity).where(FundingOpportunity.is_demo.is_(True))
            ):
                db.delete(opportunity)
            db.commit()

        if db.scalar(select(User).where(User.email == DEMO_USERS[0]["email"])) is not None:
            print("Les données de démonstration existent déjà. Utilisez --reset pour les recréer.")
            return

        users = [_create_user(db, definition, credits) for definition in DEMO_USERS]
        _create_user(db, ADMIN_USER, credits)
        db.commit()

        documents = DocumentService(db)
        scoring = ScoringService(db)

        for definition in DEMO_PROJECTS:
            owner = users[definition["owner"]]
            project = Project(
                user_id=owner.id,
                title=definition["title"],
                project_type=definition["project_type"],
                genre=definition.get("genre"),
                country=definition.get("country"),
                language=definition.get("language", "Français"),
                duration=definition.get("duration"),
                status=definition.get("status", ProjectStatus.IDEA),
                theme=definition.get("theme"),
                logline=definition.get("logline"),
                short_synopsis=definition.get("short_synopsis"),
                concept=definition.get("concept"),
                stakes=definition.get("stakes"),
                director_vision=definition.get("director_vision"),
                objectives=definition.get("objectives"),
                target_audience=definition.get("target_audience"),
            )
            for index, character in enumerate(definition.get("characters", [])):
                project.characters.append(Character(sort_order=index, **character))
            db.add(project)
            db.flush()

            if definition.get("short_synopsis"):
                documents.create_empty(
                    project, DocumentType.SHORT_SYNOPSIS, definition["short_synopsis"]
                )
            if definition.get("logline"):
                documents.create_empty(project, DocumentType.LOGLINE, definition["logline"])
            db.commit()
            scoring.compute(project)

        now = datetime.now(UTC)
        for definition in DEMO_OPPORTUNITIES:
            requirement_items = definition.pop("requirement_items", [])
            opportunity = FundingOpportunity(
                **definition,
                status=FundingStatus.UNVERIFIED,
                is_demo=True,
                source="seed",
                source_name="Jeu de démonstration FilmFund Africa",
                source_url=None,
                last_verified_at=now,
            )
            for label, document_type in requirement_items:
                opportunity.requirement_items.append(
                    FundingRequirement(
                        label=label,
                        is_mandatory=True,
                        required_document_type=str(document_type) if document_type else None,
                    )
                )
            db.add(opportunity)
        db.commit()

        db.add(
            build_notification(
                user_id=users[0].id,
                notification_type=NotificationType.SYSTEM,
                title_key="notification.welcome.title",
                body_key="notification.welcome.body",
                link="/tableau-de-bord",
            )
        )
        db.commit()

    print("Données de démonstration créées.")
    print(f"  Auteur      : {DEMO_USERS[0]['email']} / {DEMO_PASSWORD}")
    print(f"  Producteur  : {DEMO_USERS[1]['email']} / {DEMO_PASSWORD}")
    print(f"  Admin       : {ADMIN_USER['email']} / {DEMO_PASSWORD}")
    print("  Opportunités fictives : 3 (is_demo=True, statut UNVERIFIED)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed de démonstration FilmFund Africa")
    parser.add_argument("--reset", action="store_true", help="Supprime puis recrée les données")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Autorise l'exécution en environnement de production (déconseillé)",
    )
    args = parser.parse_args()
    try:
        seed(reset=args.reset, force=args.force)
    except Exception as exc:  # noqa: BLE001
        print(f"Échec du seed : {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
