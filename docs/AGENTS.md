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

## Les routes, et pourquoi c'est une tâche

Un passage enchaîne huit appels au fournisseur, davantage avec les reprises.
Le tenir dans la requête HTTP la ferait expirer, et une coupure perdrait tout.
Le lancement passe donc par la **même file** que la génération de documents —
réservation de crédits, battement de cœur, reprise des tâches abandonnées,
repli en ligne quand aucun worker n'écoute. Rien de tout cela n'a été réécrit.

| Route | Rôle |
| --- | --- |
| `POST /projects/{id}/dossier/run` | lance un passage, rend une tâche (202) |
| `GET /projects/{id}/dossier` | le dossier tel qu'il est |
| `GET /projects/{id}/dossier/status` | le dossier peut-il partir ? |
| `GET /projects/{id}/dossier/findings` | constats ouverts, les plus graves d'abord |
| `GET /projects/{id}/dossier/modifications` | qui a changé quoi, et pourquoi |
| `GET /projects/{id}/dossier/runs` | historique des passages |
| `GET /projects/{id}/dossier/runs/{run_id}` | le détail, agent par agent |

L'avancement se suit sur `GET /jobs/{id}`, exactement comme une génération.

### Le battement de cœur n'est pas décoratif

Huit appels de trois minutes dépassent `JOB_TIMEOUT_SECONDS` (900 s). Sans
signe de vie après chaque agent, le surveillant déclarerait morte une chaîne
qui travaille et rembourserait les crédits d'un passage en cours. L'orchestrateur
signale donc chaque étape.

### Un passage coûte huit crédits, pas un

`AIOperation.RUN_AGENT_CHAIN` est facturée **par agent**. Une offre gratuite,
qui accorde un crédit, ne peut donc pas lancer de chaîne — et le refus tombe
avant le premier appel au fournisseur, pas après huit appels déjà payés.

Les reprises ne sont pas réservées d'avance : on ne sait pas encore s'il y en
aura. Elles sont journalisées à l'exécution.

### Une tâche réussie n'est pas un dossier validé

Ce sont deux choses distinctes, et les confondre serait dangereux : une chaîne
qui conclut `BLOCKED` a parfaitement fait son travail. La tâche est donc
`SUCCEEDED`, et c'est `exportable` qui dit non. **Le dossier est sauvegardé quel
que soit le verdict** — le jeter obligerait à tout refaire, à huit appels la
tentative, pour corriger un seul point.

## L'écran

`/projets/{id}/dossier`, accessible depuis la fiche projet. Il montre, dans cet
ordre : **si le dossier peut partir**, le bouton pour lancer un passage avec son
coût annoncé **avant**, les constats les plus graves d'abord, les sections du
dossier, l'historique des modifications, puis les passages dépliables agent par
agent.

Trois choix d'affichage méritent d'être dits :

**Le coût est annoncé avant, pas découvert après.** Huit crédits s'affichent à
côté du bouton.

**Un passage enlisé ou épuisé le dit sur la ligne du passage**, pas seulement
juste après l'avoir lancé. Sans cela, on recharge la page, on voit « à
corriger », et on relance sans comprendre pourquoi rien ne bouge. C'est un
manque que la capture d'écran a révélé, pas les tests.

**Rien ne se présente comme validé.** Quand le dossier est exportable, l'écran
rappelle qu'une relecture humaine reste due.

## L'export PDF

`GET /projects/{id}/export/dossier/pdf`, et un bouton sur l'écran.

**Deux documents différents selon l'état, et la différence est voulue.**

Validé, le PDF est propre : page de garde, sections dans l'ordre de la chaîne,
rien d'autre. C'est le document qu'un comité de lecture peut recevoir.

Non validé, le même contenu porte **« BROUILLON — dossier non validé »** en rouge
dès la première page, le nom du fichier le dit aussi, et les constats à traiter
sont annexés. C'est la seule raison de produire ce PDF-là.

**L'export n'est jamais refusé.** Un auteur a le droit de lire son travail en
cours ; ce qui est interdit, c'est qu'un brouillon puisse passer pour un
document abouti. D'où la double marque, dans le fichier *et* dans son nom : un
fichier renommé perdrait l'une, pas l'autre.

**Les constats restent dehors quand le dossier est validé.** Ce sont des notes
d'assurance qualité interne ; les exposer à un financeur desservirait le projet.
Un constat mineur ne bloque donc pas l'export, et ne s'y retrouve pas non plus.

**Une information non vérifiée est signalée comme telle.** Une logline au statut
`ASSUMPTION` ou `TO_BE_VERIFIED` est suivie d'une mention explicite plutôt que
présentée comme un fait — c'est la règle « l'IA n'invente rien » appliquée au
document qui sort.

Les tests lisent le PDF produit (`pypdf`, dépendance de test uniquement) plutôt
que de se contenter de vérifier qu'un fichier commence par `%PDF` : ce qui
compte est ce que le document dit, pas qu'il existe.

## Ce qui est construit, et ce qui ne l'est pas

**En place** : les huit agents, les contrats, le moteur, l'orchestrateur, la
persistance, la file, les routes, l'écran, **et l'export PDF**. La chaîne est
utilisable de bout en bout, du lancement au document téléchargeable.
**123 tests backend** la couvrent, plus 3 parcours de bout en bout.

**Pas encore** :

1. **Le worker en production.** Le code le gère, mais tant que `REDIS_URL` est
   vide, l'API exécute le passage elle-même — vingt minutes de requête ouverte.
   Sur un hébergement sans worker, c'est la limite décrite dans
   [`deploy/VERCEL.md`](../deploy/VERCEL.md).
2. **L'export DOCX du dossier.** Le PDF existe ; certains fonds demandent du
   Word. La brique est là (`document_to_docx`), il reste à l'appliquer au
   dossier.
3. **Une décision produit à prendre** : l'offre gratuite accorde **un** crédit,
   une chaîne en coûte **huit**. Un compte gratuit ne peut donc jamais essayer
   la fonction principale du produit. Le refus est propre et lisible, mais c'est
   un arbitrage commercial, pas un défaut technique.
