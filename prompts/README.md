# Prompts

Les prompts vivent dans **`backend/app/prompts/`** : ce sont des modules Python importables,
qui reçoivent le contexte structuré d'un projet et non du texte libre.

```text
backend/app/prompts/
├── base.py            PromptContext, PromptTemplate, registre, prompts de retravail
├── logline.py
├── synopsis.py        synopsis court + synopsis long
├── intention.py       note d'intention
├── realization.py     note de réalisation
├── treatment.py
├── characters.py
├── pitch.py           pitch oral + pitch écrit
├── bible.py           bible du projet
├── screenplay.py      scénario dialogué
├── scoring.py         analyse qualitative du dossier
└── funding_match.py   explication d'un rapprochement projet / financement
```

## Règles

1. **Aucun prompt n'est écrit en dur dans une route API.** Une route appelle un service, qui
   récupère le template dans le registre.
2. **Chaque prompt porte un numéro de version** (`version="1.0.0"`), enregistré dans
   `document_versions.prompt_version` et `ai_usage.prompt_version`. Toute modification du texte
   d'un prompt doit s'accompagner d'une incrémentation, afin de pouvoir comparer la qualité des
   générations dans le temps.
3. **Structure et longueur cible sont imposées** par le template, jamais improvisées.
4. **L'IA n'invente rien.** Une information manquante produit « Information non fournie. » et
   figure dans la section finale « Informations à compléter ».
5. **Chaque prompt déclare ses dépendances** (`depends_on`) : le service injecte alors le
   contenu de ces documents pour garantir la cohérence du dossier.

## Ajouter un document

1. Ajouter la valeur dans `DocumentType` (`backend/app/models/enums.py`).
2. Créer le module de prompt et l'enregistrer avec `register(PromptTemplate(...))`.
3. L'importer dans `backend/app/prompts/__init__.py`.
4. Ajouter son libellé dans `frontend/src/lib/labels.ts`.

Le test `test_every_document_type_has_a_prompt` échoue tant qu'un type de document n'a pas son
prompt : l'oubli est impossible.
