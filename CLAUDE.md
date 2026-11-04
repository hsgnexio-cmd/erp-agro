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
├── docs/            # fiche entreprise, règles métier, décisions, guides
├── backend/         # projet Django, une app par module
│   ├── referentiel/
│   ├── achats/
│   ├── stocks/
│   ├── production/
│   ├── ventes/
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

## 7. Façon de travailler

1. Lire `CLAUDE.md` et les documents de `docs/` concernés par la tâche.
2. Présenter un plan court, attendre la validation.
3. Développer par petites étapes, en lançant les tests.
4. Vérifier que tout fonctionne (tests verts, application qui démarre).
5. Faire un commit Git, puis résumer en français ce qui a été fait.
6. Mettre à jour la documentation (`docs/`, `README.md`) si quelque chose a changé.

Ne jamais : supprimer des données ou des fichiers sans demander, modifier une règle métier sans validation, ajouter une dépendance lourde sans expliquer pourquoi.

## 8. Phases du projet

| Phase | Contenu | Statut |
| --- | --- | --- |
| 1. Fondations | Structure, Docker Compose, PostgreSQL, Django, React, comptes et rôles, tests, GitHub Actions | Terminée |
| 2. Référentiel | Articles, nomenclatures, fournisseurs, clients, sites, emplacements | Terminée |
| 3. Achats et réceptions | Commandes fournisseurs, réception, création des lots, contrôles | Terminée |
| 4. Stocks et lots | Statuts, mouvements, FEFO, DLC, températures, inventaires | Terminée |
| 5. Traçabilité | Traçabilité amont/aval, rappel produit, allergènes | À faire |
| 6. Production | Ordres de fabrication, consommations, rendements | À faire |
| 7. Ventes | Commandes EDI simulées, préparation FEFO, expédition | À faire |
| 8. Pilotage | Indicateurs, connexion Power BI, requêtes Power Query | À faire |

Mettre à jour la colonne Statut à la fin de chaque phase.

## 9. Rôles utilisateurs

`admin`, `direction`, `acheteur`, `magasinier`, `production`, `qualite`, `commercial`. Chaque rôle n'accède qu'aux écrans et actions de son métier ; seul le rôle `qualite` peut libérer ou bloquer un lot.
