# La chaîne d'agents du dossier de financement

Huit agents spécialisés construisent puis contrôlent un dossier. Chacun reçoit
l'état du projet et le travail de ceux qui l'ont précédé, et rend une production
structurée que l'orchestrateur peut lire, comparer et router.

Le code est dans `backend/app/agents/`. Un agent y est **déclaré et versionné**,
comme un prompt de document : aucune consigne n'est écrite en dur dans une route,
et on peut comparer la qualité d'une étape d'une version à l'autre.

## Qui fait quoi

| # | Agent | Fonction | Ce qu'il ne tranche pas |
| --- | --- | --- | --- |
| 1 | `DEVELOPMENT` | De l'idée au projet défendable | structure dramatique, budget, financement |
| 2 | `SCREENWRITER` | Architecture dramatique | découpage technique, faisabilité de tournage |
| 3 | `DIRECTOR` | Vision cinématographique et sa faisabilité | réécriture du scénario, chiffrage |
| 4 | `PRODUCER` | Du projet artistique à la production réelle | plan de financement, arbitrages artistiques |
| 5 | `FINANCING` | Stratégie financière et dispositifs compatibles | chiffrage du budget, démonstration d'impact |
| 6 | `IMPACT` | Pertinence culturelle, sociale, économique | stratégie de financement, arbitrages narratifs |
| 7 | `CONSISTENCY_VALIDATOR` | Audit transversal des contradictions | la correction elle-même, le verdict d'export |
| 8 | `FUNDING_PACKAGE_VALIDATOR` | Contrôle final avant export | la correction, la vérification humaine |

La colonne de droite n'est pas décorative. C'est elle qui évite qu'un agent
tranche à la place d'un autre, et `test_no_agent_claims_a_domain_it_does_not_own`
échoue si un agent ne la renseigne pas.

Les six premiers **construisent**, les deux derniers **statuent**. Un validateur
qui corrigerait ne serait plus une instance indépendante — c'est testé.

## Ce que chaque agent reçoit, ce qu'il rend

```text
ProjectState + productions précédentes + rôle + exigences du fonds + contexte
        ↓
ANALYSIS · DECISIONS · MODIFICATIONS · RATIONALE · UPDATED_STATE · NEXT_AGENT_INSTRUCTIONS
```

Aucun agent ne travaille en silo : il reçoit systématiquement l'état entier et ce
que les autres ont produit.

## Les quatre garanties

Elles sont portées par `contracts.py` et injectées dans la consigne de **chaque**
agent — `test_the_common_rules_reach_every_agent` le vérifie pour les huit.

**Non-destruction** (`ChangeSet`). Un agent qui touche au travail d'un autre
déclare ce qu'il conserve, modifie, retire et ajoute, avec la raison de chaque
changement. Sans cela, une chaîne de huit agents perd en route ce que l'auteur
avait validé — et c'est lui qui devra défendre le dossier devant un comité.

**Protocole de décision** (`DecisionRecord`). OBSERVATION → ANALYSIS → RISK →
DECISION → MODIFICATION → VALIDATION. Une modification sans observation ni risque
identifié est une préférence, pas une décision.

**Traçabilité** (`ModificationTrace`). Qui, quand, quoi, pourquoi, avec quel
impact, et validé ou non.

**Incertitude** (`TrackedFact`). Aucune information n'est nue : elle porte son
statut — `VERIFIED`, `PROVIDED_BY_USER`, `INFERRED`, `ASSUMPTION`,
`TO_BE_VERIFIED`, `UNKNOWN`. Le statut n'est pas un commentaire :
`is_usable_for_funding()` refuse qu'une hypothèse serve de critère d'éligibilité,
et **le défaut est le plus prudent** — un fait dont on a oublié de déclarer la
provenance n'est pas utilisable.

C'est la même exigence que la règle produit « l'IA n'invente rien » (README
section 16), appliquée à la chaîne plutôt qu'à un document isolé.

## Verdicts et boucle de correction

La gravité la plus forte l'emporte, sans indulgence :

| Constat le plus grave | Verdict | Export |
| --- | --- | --- |
| aucun | `PASS` | oui |
| `MINOR` | `PASS_WITH_WARNINGS` | oui |
| `MAJOR` | `REQUIRES_CORRECTION` | non |
| `CRITICAL` | `BLOCKED` | non |

Un seul constat critique bloque. C'est volontairement brutal : un fonds ne se
représente souvent qu'une fois par an, et une pièce obligatoire manquante n'est
pas rattrapable après dépôt.

Chaque constat (`Finding`) porte l'agent capable de le corriger. Sans ce
destinataire, un problème détecté ne serait jamais traité. La reprise ne repart
jamais du seul agent fautif :

```text
correction_route(PRODUCER)
  → PRODUCER → FINANCING → IMPACT → CONSISTENCY → FUNDING_PACKAGE
```

Corriger le producteur seul corrigerait le symptôme, pas ses conséquences : un
budget revu change le plan de financement, qui change ce que le validateur doit
relire.

## Ce qui est construit, et ce qui ne l'est pas

**En place** : les huit définitions, les contrats, le registre, l'ordre du
pipeline, le routage des corrections, la logique de verdict, le rendu des
consignes. **51 tests** couvrent les périmètres, les garanties et la boucle.

**Pas encore** — et rien n'est exécutable sans ces pièces :

1. **Le moteur d'exécution.** Rien n'appelle encore le fournisseur d'IA avec la
   consigne d'un agent, ni ne relit sa réponse pour en extraire `AgentOutput`.
   C'est le chantier suivant, et le plus gros : la sortie est du Markdown
   structuré, il faut la reparser de façon robuste ou passer à une sortie typée.
2. **La persistance de `ProjectState`.** Le modèle existe en mémoire ; il n'a ni
   table ni migration. L'historique des modifications et les constats non résolus
   doivent survivre à une session.
3. **Les routes et l'interface.** Aucun point d'entrée HTTP, aucun écran.
4. **Le coût.** Une passe complète, c'est huit appels au fournisseur, davantage
   avec les boucles de correction. Le modèle de crédits actuel compte par
   document généré ; il ne sait pas compter une chaîne.

Tant que 1 et 2 ne sont pas faits, la chaîne est une spécification exécutable :
elle se teste, elle ne produit pas encore de dossier.
