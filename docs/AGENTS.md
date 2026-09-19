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

## Le moteur d'exécution

### Sortie typée, pas de relecture de Markdown

Un agent répond par **un seul objet JSON**, validé par Pydantic en `extra="forbid"`.
Le choix se paie en robustesse à l'entrée — un modèle encadre volontiers sa
réponse d'un bloc de code ou d'une phrase de politesse — et se rembourse
partout ailleurs : une gravité, un verdict ou le destinataire d'un constat sont
des valeurs typées, pas le résultat d'une expression régulière appliquée à de la
prose. Confier une décision d'export à un `re.match` n'était pas défendable.

L'extraction est donc **tolérante** (bloc de code, préambule bavard) et la
validation **stricte**. Une sortie invalide lève une erreur nommant le champ
fautif : mieux vaut une étape qui échoue qu'une étape dont on croit connaître le
verdict.

Le partage : **typé là où ça pilote un comportement** — `findings`, `verdict`,
`modifications`, `state_patch` ; **prose là où le destinataire est humain** —
`analysis`, `rationale`, la prose restant structurée par les blocs déclarés par
chaque agent.

### Ce que le moteur ne croit pas sur parole

`agent` et `version` ne figurent pas dans le contrat de réponse : ils viennent de
la définition. Un modèle qui déclarerait lui-même son rôle pourrait signer la
production d'un autre, et toute la traçabilité reposerait sur sa bonne foi.

Chaque agent constructeur ne peut enrichir **que sa propre section** de l'état
(`state_field`). Les validateurs n'en ont aucune : un `state_patch` de leur part
est refusé franchement, parce qu'un contrôle qui modifie ce qu'il contrôle est un
défaut de conception, pas une donnée à ignorer.

### La boucle, et ce qui l'arrête

Trois garde-fous, pour trois raisons différentes :

| Garde-fou | Pourquoi |
| --- | --- |
| `max_correction_rounds` (3) | deux validateurs qui ne s'accordent pas boucleraient jusqu'à épuisement du budget |
| détection de non-progression | un tour qui ne change rien aux constats ouverts coûte huit appels pour le même résultat |
| aucun export forcé | sortir de la boucle ne vaut pas validation : sans `PASS`, le dossier ne part pas |

La reprise repart du propriétaire **le plus en amont**, pas du plus grave :
corriger le budget avant le scénario laisserait le budget à refaire une fois le
scénario modifié. L'ordre du pipeline est déjà l'ordre des dépendances.

Un constat sans destinataire revient à son émetteur. Le laisser sans propriétaire
le faisait disparaître entre deux filtres — détecté puis perdu, ce qui est pire
que non détecté. C'est un défaut qu'un test a trouvé, pas une précaution
théorique.

### Le mode `mock` ne produit jamais de dossier exportable

Sans clé API, la chaîne se déroule entièrement — c'est nécessaire pour la
développer et la tester — mais chaque agent rend un constat `MAJOR` disant que
rien n'a été rédigé ni contrôlé. Un dossier « validé » par un fournisseur qui
n'analyse rien serait un mensonge utile à personne.

## La persistance

Cinq tables, et un découpage qui n'est pas arbitraire.

| Table | Rôle |
| --- | --- |
| `project_dossiers` | les sections produites par les agents, une ligne par projet |
| `agent_runs` | un passage complet : verdict, tours, garde-fou déclenché |
| `agent_steps` | chaque exécution d'agent, avec sa télémétrie |
| `dossier_findings` | les constats, ouverts ou datés |
| `dossier_modifications` | qui a changé quoi, pourquoi, avec quel impact |

Les **sections** restent en JSON : un plan de production n'a pas la même forme
d'un projet à l'autre, et les figer en colonnes reviendrait à décider aujourd'hui
de ce qu'un agent aura le droit de produire demain.

Les **constats** et les **traces** sont normalisés. On veut pouvoir demander
« quels blocages restent ouverts » ou « qui a touché au budget, et pourquoi »
sans relire du JSON — sans quoi la traçabilité du §17 ne sert à rien.

`project_dossiers` est distinct de `projects` à dessein : ces sections sont
produites par les agents, alors que la fiche projet porte ce que l'auteur a
saisi. Les confondre ferait écraser sa saisie par une production d'agent.

### Deux écarts assumés

**`validation_history` n'est pas stockée.** Chaque étape de validateur porte
déjà son verdict ; elle est reconstituée à la lecture. Deux sources de vérité
finiraient par diverger.

**Un constat résolu est daté, pas supprimé.** Savoir qu'un blocage a existé et
quand il a été levé fait partie de l'histoire du dossier. Un constat qui
disparaît sans trace empêche de savoir s'il a été corrigé ou simplement oublié.

### Reprendre, pas recommencer

C'est le point de la persistance, et c'est ce que les tests vérifient : un second
passage recharge les sections remplies, les constats encore ouverts et
l'historique, puis **l'allonge** au lieu de le réécrire. Un même constat relevé
deux fois reste un constat.

## Ce qui est construit, et ce qui ne l'est pas

**En place** : les huit définitions, les contrats, le registre, le routage des
corrections, le moteur d'exécution, l'orchestrateur, **et la persistance**. La
chaîne accumule un dossier, le garde, et le reprend. **94 tests** la couvrent.

**Pas encore** :

1. **Les routes et l'interface.** Aucun point d'entrée HTTP, aucun écran. Le
   moteur est complet mais rien ne l'expose.
2. **La file.** Un passage complet dépasse largement une requête HTTP : il doit
   passer par le worker, comme la génération de scénario. `agent_runs` porte
   déjà un `status` et un champ `error` pour ça.
3. **Le coût.** Un passage propre, c'est huit appels ; jusqu'à seize avant que
   les garde-fous ne coupent. Le modèle de crédits compte par document généré :
   le brancher tel quel facturerait une chaîne comme un synopsis.
