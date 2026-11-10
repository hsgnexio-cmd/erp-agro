# CLAUDE.md — ERP Brévanne Traiteur

Ce fichier est lu par Claude Code au début de chaque session. Il décrit le projet, les règles métier et la façon de travailler.

## 1. Contexte du projet

- **Entreprise (fictive)** : Brévanne Traiteur SAS, ETI de plats cuisinés frais (520 salariés, 165 M€ de CA).
- **Activité** : plats chauds (usine NAN, près de Nantes) et traiteur froid (usine REN, près de Rennes), vendus en grande distribution, sous la marque Brévanne (55 % du CA) et en marque distributeur MDD (45 %).
- **Objectif** : développer un ERP agroalimentaire complet, de qualité professionnelle, dans le cadre d'une formation.
- **Description détaillée de l'entreprise** : voir `docs/fiche-entreprise.md`. La lire avant toute décision métier.

## 2. Le développeur

- Nicolas, à l'aise en supply chain et en Excel, **débutant en code**.
- Toujours expliquer en français, simplement, ce que tu fais et pourquoi, à chaque étape importante.
- Avant une grosse modification, présente ton plan en quelques lignes et attends sa validation.
- Après chaque tâche : résume ce qui a été fait, comment le tester, et ce qui reste à faire.
- Ne jamais supposer qu'il connaît une commande : donne-la complète, prête à copier dans PowerShell.
- Environnement : **Windows**, PowerShell, Git, Python, Node.js, Docker Desktop (via WSL 2).

## 3. Architecture technique

| Couche | Technologie |
| --- | --- |
| Base de données | PostgreSQL |
| Back-end | Python, Django, Django REST Framework |
| Front-end | React + TypeScript (Vite) |
| Tâches de fond | Celery + Redis (alertes péremption, simulation EDI, calculs planifiés) |
| Environnement | Docker + Docker Compose (tous les services lancés en une commande) |
| Tests | pytest (back-end), Vitest (front-end) |
| Intégration continue | GitHub Actions (tests lancés à chaque push) |
| Analyse | Excel / Power Query et Power BI connectés à PostgreSQL |

- Utiliser les dernières versions stables et compatibles entre elles. Vérifier la compatibilité avant de fixer une version.
- Python tourne dans les conteneurs Docker : la version du PC de Nicolas n'impose rien.
- Toute la configuration sensible (mots de passe, clés) va dans un fichier `.env`, jamais dans le code. Fournir un `.env.example`.

### Structure du dépôt (cible)

```
erp-agro/
├── CLAUDE.md
├── README.md
├── docker-compose.yml
├── .env.example
├── docs/            # fiche-entreprise.md, decisions.md, prochaine-etape.md
├── backend/         # projet Django, une app par module
│   ├── referentiel/
│   ├── achats/
│   ├── stocks/
│   ├── production/
│   ├── ventes/
│   ├── previsions/  # prévisions de vente, promotions, versions figées
│   ├── qualite/     # traçabilité, rappels, allergènes, non-conformités
│   └── pilotage/
├── frontend/        # application React + TypeScript
├── data/            # scripts de génération de données fictives, exports
└── bi/              # requêtes Power Query, fichiers Power BI, documentation des indicateurs
```

## 4. Règles métier non négociables

Ces règles doivent être appliquées **dans le back-end** (modèles et services), pas seulement dans l'interface. Toute opération qui les enfreint est refusée avec un message clair. Chaque règle est couverte par des tests.

1. **Traçabilité totale** : chaque lot de produit fini est relié à tous les lots de matières premières, semi-finis et emballages consommés, et à toutes les livraisons clients. Traçabilité amont et aval en une requête.
2. **Lots obligatoires** : tout stock de matière, semi-fini ou produit fini est géré par lot (numéro, date de fabrication ou réception, DLC/DDM, quantité, site, emplacement).
3. **DLC et DDM** : DLC pour les produits frais, DDM pour les produits secs. Les dates des produits finis sont calculées automatiquement à partir de la durée de vie de l'article.
4. **FEFO** : en production comme en préparation de commandes, le système propose toujours le lot qui périme le premier.
5. **DLC minimale client** : chaque enseigne fixe une durée de vie restante minimale à la livraison (ex. 70 % de la DLC totale). Un lot trop court est bloqué pour ce client.
6. **Statuts de lot** : `libéré`, `bloqué`, `quarantaine`, `détruit`. Seul un lot `libéré` peut être consommé ou expédié. Un lot reçu démarre en `quarantaine` jusqu'au contrôle qualité.
7. **Chaîne du froid** : relevés de température enregistrés à la réception, en stockage et à l'expédition. Un écart déclenche une alerte et le blocage du lot.
8. **Allergènes** : les 14 allergènes réglementaires sont suivis par matière. Les allergènes d'une recette sont calculés automatiquement à partir de sa nomenclature.
9. **Rappel produit** : à partir d'un lot (matière ou produit fini), retrouver en quelques secondes tous les lots liés, les stocks restants à bloquer et les clients livrés avec les quantités.
10. **Versions MDD** : une même recette peut exister en plusieurs références (marque Brévanne et une par enseigne), chacune avec sa fiche technique, son emballage et son cahier des charges.
11. **Mouvements de stock** : aucun stock ne change sans mouvement enregistré (qui, quand, quoi, pourquoi). On ne supprime jamais un mouvement : on le corrige par un mouvement inverse.
12. **Historique** : les données de référence et les lots gardent un historique des modifications (audit IFS / BRCGS).

**Scénario test de référence** : un fournisseur signale un lot de crème contaminé. L'ERP doit lister tous les produits finis fabriqués avec ce lot, leurs stocks restants et les enseignes livrées, avec les quantités. Ce scénario doit exister sous forme de test automatisé dès la phase 5.

## 5. Codification

- Produit fini : `PF-[famille]-[recette]-[marque]-[format]` → `PF-PAT-LASBOL-BRE-300`, `PF-PAT-LASBOL-ENS2-1000`
- Semi-fini : `SF-[code]` → `SF-SAUCEBOL`
- Matière première : `MP-[catégorie]-[code]` → `MP-VIA-BOEUF15`
- Emballage : `EM-[type]-[code]` → `EM-BARQ-300N`
- Sites : `NAN`, `REN`, `PFN`, `MPE` · Enseignes : `ENS1` à `ENS6`

## 6. Conventions de code

- **Code en anglais** (noms de variables, fonctions, classes, tables) ; **interface, messages et documentation en français**.
- Commentaires en français, uniquement là où ils aident à comprendre une règle métier.
- Une app Django par module ; la logique métier dans des fichiers `services.py`, pas dans les vues.
- Quantités et prix en `Decimal`, jamais en `float`. Unités toujours explicites (kg, unité, litre).
- Dates en ISO, fuseau `Europe/Paris`.
- Chaque nouvelle règle métier = au moins un test.
- Petits commits, messages clairs en français : `stocks: ajout du calcul FEFO`.

Conventions adoptées en cours de route (détail et raisons dans `docs/decisions.md`) :

- **Aucune voie de contournement** : les modèles du référentiel héritent de `ValidatedModel` (validation complète à chaque enregistrement) ; les opérations passent par des fonctions métier qui relisent et verrouillent le lot (`select_for_update`).
- **Logique métier** : `services.py`, ou un module dédié quand il devient long (`stocks/monitoring.py`, `stocks/inventory.py`, `production/orders.py`, `production/planning.py`, `production/master_plan.py`, `production/oee.py`, `ventes/orders.py`, `ventes/edi.py`, `ventes/shipping.py`, `previsions/forecast.py`, `achats/mrp.py`, `pilotage/indicators.py`).
- **Indicateurs** : calculés dans les vues SQL du schéma `bi` (`pilotage/sql/bi_views.sql`, migration), lues par l'API du tableau de bord et par Power BI ; pour modifier une vue, nouvelle migration qui relance le fichier (ajout de colonnes en fin de vue) ou recrée le schéma. Power BI / Excel se connectent avec l'utilisateur `powerbi` en lecture seule (`creer_utilisateur_bi`, droits remis après chaque `migrate`).
- **Enregistrements jamais modifiés ni supprimés** : mouvements de stock, journal des statuts de lot, relevés de température, rappels, versions et corrections de prévision, arrêts de ligne (annulés avec motif) ; une alerte se marque « traitée ». Les documents d'opération (commandes, réceptions, lots, OF, inventaires) sont en lecture seule dans l'administration.
- **Numérotation** : `referentiel.services.next_document_number` (compteur en base, sans trou). Formats : `CA-`, `REC-`, `LR-`, `LF-`, `TR-`, `INV-`, `RAP-`, `OF-`, `CC-`, `BL-`, `PRV-` (versions de prévision), et `EXP-` pour les expéditions de la phase 5 ; série `SSCC` pour les palettes.
- **Droits** : `comptes.permissions.WriteRolesPermission` + attribut `write_roles` de la vue ; les groupes Django sont synchronisés après chaque `migrate` (`sync_group_permissions`).
- **API** : les décimaux sont renvoyés en texte ; une `ValidationError` Django devient une réponse 400 lisible (`config/exceptions.py`).
- **Données de démonstration** : une seule commande `charger_donnees_demo`, relançable sans doublon ; dates calculées à partir d'aujourd'hui. Elle rejoue aussi 6 semaines d'historique (`pilotage/demo_history.py`, horloge simulée, prévision figée chaque lundi, ≈ 6 min) ; les tests l'appellent avec `sans_historique=True`.
- **Front-end** : hook `useApi`, droits dans `auth/roles.ts`, tests avec `mockApi` / `renderApp` (`src/test/utils.tsx`).

## 7. Façon de travailler

1. Lire `CLAUDE.md`, **`docs/prochaine-etape.md`** (où reprendre) et les documents de `docs/` concernés par la tâche.
2. Présenter un plan court, avec les décisions métier à valider, et attendre la validation.
3. Développer par petites étapes, en lançant les tests.
4. Vérifier que tout fonctionne (tests verts, application qui démarre, écrans vérifiés dans le navigateur).
5. Faire un commit Git, puis résumer en français ce qui a été fait.
6. Mettre à jour la documentation (`docs/decisions.md`, `README.md`, statut des phases ci-dessous).

Ne jamais : supprimer des données ou des fichiers sans demander, modifier une règle métier sans validation, ajouter une dépendance lourde sans expliquer pourquoi.

### Organisation Git et vérifications

- Une branche par phase ou partie de phase (`phase-7b-expedition`…), petits commits, envoi sur GitHub, puis **Nicolas** crée et fusionne la pull request (rappeler de cliquer deux fois sur « Create pull request »). Ensuite : mettre `main` à jour en local et supprimer la branche fusionnée.
- Une phase trop grosse se découpe en deux parties (4a/4b, 7a/7b), chacune avec sa pull request.
- Tests : `docker compose exec backend pytest` (≈ 5 min) et `docker compose exec frontend npm test` ; lint `ruff` et `npm run lint` ; GitHub Actions relance tout à chaque envoi.
- Vérification dans le navigateur : Nicolas est souvent connecté avec son propre compte ; ne jamais le déconnecter ni agir avec son compte. Pour agir, utiliser le compte de test `test-verif` (le réactiver avec un mot de passe aléatoire, puis le désactiver ; il ne peut pas être supprimé car il a fait des mouvements de stock).

## 8. Phases du projet

| Phase | Contenu | Statut |
| --- | --- | --- |
| 1. Fondations | Structure, Docker Compose, PostgreSQL, Django, React, comptes et rôles, tests, GitHub Actions | Terminée |
| 2. Référentiel | Articles, nomenclatures, fournisseurs, clients, sites, emplacements | Terminée |
| 3. Achats et réceptions | Commandes fournisseurs, réception, création des lots, contrôles | Terminée |
| 4. Stocks et lots | Statuts, mouvements, FEFO, DLC, températures, inventaires | Terminée |
| 5. Traçabilité | Traçabilité amont/aval, rappel produit, allergènes | Terminée |
| 6. Production | Ordres de fabrication, consommations, rendements | Terminée |
| 7. Ventes | Commandes EDI simulées, préparation FEFO, expédition | Terminée (7a : tarifs, commandes, EDI simulé ; 7b : préparation FEFO, SSCC, expédition, taux de service, invendables) |
| 8. Pilotage | Indicateurs, connexion Power BI, requêtes Power Query | Terminée (8a : historique de démo, vues SQL `bi`, tableau de bord ; 8b : utilisateur `powerbi` en lecture seule, Power Query, mesures DAX, export CSV) |
| 9. Prévisions et planification | Prévisions de vente à 8 semaines, promotions, fiabilité ; plan figé à J-2, calcul des besoins (MRP) | Terminée (9a : prévisions de vente, promotions, corrections, versions figées, fiabilité à S-1 ; 9b : plan de production hebdomadaire figé à J-2, OF créés au gel ; 9c : calcul des besoins (MRP), propositions d'achat, commandes brouillon) |
| 10. TRS | Arrêts de ligne, plages de marche, rebuts, TRS (disponibilité × performance × qualité) | Terminée |

Mettre à jour la colonne Statut à la fin de chaque phase.

## 9. Rôles utilisateurs

`admin`, `direction`, `acheteur`, `magasinier`, `production`, `qualite`, `commercial`. Chaque rôle n'accède qu'aux écrans et actions de son métier ; seul le rôle `qualite` peut libérer ou bloquer un lot.

Précisions décidées en cours de route : le rôle `admin` peut tout faire, y compris libérer ou bloquer ; l'ERP bloque aussi **automatiquement** un lot (contrôle à réception non conforme, écart de température, DLC dépassée, rappel produit). Tous les rôles consultent tout ; `direction` ne modifie rien.

| Rôle | Actions principales |
| --- | --- |
| `acheteur` | Calcul des besoins (MRP), commandes fournisseurs, tarifs d'achat, fournisseurs |
| `magasinier` | Réceptions, transferts, corrections, inventaires, relevés de température, alertes, préparation et expédition |
| `production` | Plan de production, ordres de fabrication et déclarations (plage de marche, rebuts), arrêts de ligne, articles, recettes, nomenclatures, lignes |
| `qualite` | Statuts des lots, invendables, allergènes, rappels, relevés de température, alertes, articles et nomenclatures |
| `commercial` | Commandes clients, tarifs de vente, EDI, enseignes et entrepôts, prévisions de vente et promotions |
