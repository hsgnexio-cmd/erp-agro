# ERP Brévanne Traiteur

ERP agroalimentaire pour Brévanne Traiteur SAS (entreprise fictive de plats cuisinés frais), développé dans le cadre d'une formation.
Le contexte métier est décrit dans [`docs/fiche-entreprise.md`](docs/fiche-entreprise.md) et les règles du projet dans [`CLAUDE.md`](CLAUDE.md).

## Technologies

| Couche | Technologie | Version |
| --- | --- | --- |
| Base de données | PostgreSQL | 18 |
| Back-end | Python, Django, Django REST Framework | 3.14, 6.1, 3.18 |
| Historique et filtres | django-simple-history, django-filter | 3.13, 26.2 |
| Tâches de fond | Celery (worker + Beat), Redis | 5.6, 8 |
| Front-end | React, React Router, TypeScript, Vite | 19.3, 8.5, 6.0, 8.3 |
| Tests | pytest, Vitest | 9.2, 5.1 |
| Environnement | Docker Compose | — |

## Les conteneurs

| Service | Rôle | Adresse |
| --- | --- | --- |
| `db` | Base de données PostgreSQL | `localhost:5432` |
| `redis` | File d'attente des tâches de fond | — |
| `backend` | Django : API et administration | http://localhost:8000 |
| `worker` | Celery : exécute les tâches de fond | — |
| `beat` | Celery Beat : déclenche les tâches planifiées | — |
| `frontend` | Application React | http://localhost:5173 |

## Prérequis

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installé et **ouvert**.
- [Git](https://git-scm.com/).
- Python et Node.js sur le PC ne sont pas obligatoires : tout tourne dans Docker.

## Premier lancement

Toutes les commandes se tapent dans **PowerShell**, depuis le dossier du projet.

1. Se placer dans le dossier du projet :

   ```powershell
   cd C:\Users\nicol\Projets\erp-agro
   ```

2. Créer le fichier `.env` à partir du modèle (à faire une seule fois) :

   ```powershell
   Copy-Item .env.example .env
   ```

3. Ouvrir `.env` et remplacer `DJANGO_SECRET_KEY` et `POSTGRES_PASSWORD` par des valeurs aléatoires. Cette commande génère une chaîne aléatoire à copier-coller :

   ```powershell
   -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 50 | ForEach-Object { [char]$_ })
   ```

4. Construire et lancer tous les conteneurs :

   ```powershell
   docker compose up --build
   ```

   Le premier lancement prend quelques minutes. Les logs de tous les services s'affichent dans la fenêtre. Pour arrêter, appuie sur `Ctrl + C`.

## Utilisation au quotidien

Lancer le projet en arrière-plan (la fenêtre PowerShell reste libre) :

```powershell
docker compose up -d
```

Voir l'état des conteneurs :

```powershell
docker compose ps
```

Voir les logs du back-end en direct (`Ctrl + C` pour quitter) :

```powershell
docker compose logs -f backend
```

Arrêter le projet (les données de la base sont conservées) :

```powershell
docker compose down
```

Après un changement dans `requirements.txt` ou `package.json`, reconstruire les images :

```powershell
docker compose up -d --build --renew-anon-volumes
```

## Compte administrateur

Créer un compte administrateur Django (à faire une fois) :

```powershell
docker compose exec backend python manage.py createsuperuser
```

Django demande un nom d'utilisateur, un e-mail (facultatif) et un mot de passe (rien ne s'affiche pendant la saisie, c'est normal).
Ensuite, ouvre http://localhost:8000/admin/ et connecte-toi.

## Données de démonstration

Remplir la base avec des données fictives cohérentes avec la fiche entreprise (sites, enseignes, fournisseurs, matières, recettes, nomenclatures, tarifs, commandes, réceptions et lots). La commande peut être relancée sans créer de doublons :

```powershell
docker compose exec backend python manage.py charger_donnees_demo
```

## Rôles et utilisateurs

Les 7 rôles (`admin`, `direction`, `acheteur`, `magasinier`, `production`, `qualite`, `commercial`) sont des **groupes** Django, créés automatiquement par une migration. Leurs droits sont décrits dans [`docs/decisions.md`](docs/decisions.md).

Créer un utilisateur : administration → **Utilisateurs** → **Ajouter**. Puis, sur sa fiche :

- section **Permissions** → **Groupes** : choisir son rôle ;
- cocher **Statut équipe** s'il doit pouvoir utiliser l'administration (saisie du référentiel).

## Utiliser l'application

| Adresse | Contenu |
| --- | --- |
| http://localhost:5173 | Application React : référentiel (articles, fournisseurs, clients, sites), commandes fournisseurs, réceptions, lots, état des stocks, FEFO, températures, inventaires, alertes, traçabilité, rappels, production, planning |
| http://localhost:8000/admin/ | Administration : saisie du référentiel et des tarifs fournisseurs, historique des modifications |
| http://localhost:8000/api/referentiel/ | API du référentiel (liste des adresses disponibles, une fois connecté) |
| http://localhost:8000/api/achats/ | API des achats : tarifs, commandes, réceptions |
| http://localhost:8000/api/stocks/ | API des stocks : lots et mouvements |

### Le parcours d'achat

1. **L'acheteur** crée une commande (menu **Commandes** → **Nouvelle commande**) : il choisit un fournisseur audité, l'application propose ses articles avec le prix en vigueur. La commande est enregistrée en **brouillon**, puis **envoyée**.
2. **Le magasinier** ouvre la commande et clique sur **Réceptionner** : il saisit pour chaque ligne la quantité, le lot fournisseur, la DLC/DDM et la température.
3. L'application contrôle tout automatiquement et crée un **lot** par ligne : en **quarantaine** s'il est conforme, **bloqué** sinon (avec le motif). Chaque lot a son mouvement d'entrée en stock.

### La vie d'un lot

1. **La qualité** ouvre le lot (menu **Lots** → numéro du lot) et le **libère**, le **bloque** (motif obligatoire), le **débloque** ou le **détruit**.
2. **Le magasinier** le **transfère** : de la quarantaine vers la chambre froide, ou de l'entrepôt vers une usine. Seuls les emplacements à la bonne température sont proposés.
3. Le menu **Stocks** montre le stock par article et par site (libéré, quarantaine, bloqué) ; le menu **FEFO** indique quels lots utiliser en premier pour un besoin donné.

### La surveillance

- **Températures** : saisie des relevés des chambres froides. Un écart bloque automatiquement les lots présents et crée une alerte.
- **Inventaires** : ouverture (les emplacements sont gelés), comptage à l'aveugle, affichage des écarts, validation (les écarts deviennent des mouvements de stock).
- **Alertes** : chaque matin à 6 h, Celery vérifie la péremption proche, les DLC dépassées (lots bloqués) et les relevés manquants. Le compteur rouge du menu indique les alertes à traiter.

### La production

1. **La production** crée un ordre de fabrication (menu **Production** → **Nouvel OF**) : article, quantité, date, ligne compatible (proposée automatiquement) ou usine pour un semi-fini.
2. Elle **lance** l'OF, puis **déclare** ce qui a été produit : l'écran pré-remplit les lots à consommer dans l'ordre FEFO ; prendre un autre lot demande une justification.
3. Chaque déclaration crée un lot fabriqué (en quarantaine) relié aux lots consommés. À la **clôture**, l'OF affiche son rendement matière (objectif 96 %).
4. Le menu **Planning** montre la semaine ligne par ligne : charge en heures, surcharges, et ordre des allergènes à respecter.

### La traçabilité et le rappel produit

- **Traçabilité** : saisir un numéro de lot pour voir son **amont** (de quoi il est fait, à tous les niveaux) et son **aval** (ce qui a été fabriqué avec, jusqu'aux entrepôts clients livrés).
- **Simuler un rappel** depuis cet écran : lots concernés, stocks restants, enseignes livrées avec les quantités. Rien n'est modifié.
- **Lancer le rappel** (rôle qualité) : tous les lots concernés ayant du stock sont bloqués ; la liste des clients à prévenir se télécharge pour Excel (menu **Rappels**).
- Sur la fiche d'un produit fini ou d'un semi-fini, les **allergènes** sont calculés à partir de la nomenclature, avec leur origine.

Lancer la vérification des alertes tout de suite, sans attendre 6 h :

```powershell
docker compose exec backend python manage.py verifier_alertes
```

## Tests

Tests du back-end (pytest) :

```powershell
docker compose exec backend pytest
```

Vérification du style du code Python (ruff) :

```powershell
docker compose exec backend ruff check .
```

Tests du front-end (Vitest) :

```powershell
docker compose exec frontend npm test
```

Les mêmes tests sont lancés automatiquement par GitHub Actions à chaque push (voir [`.github/workflows/tests.yml`](.github/workflows/tests.yml)).

## Structure du dépôt

```
erp-agro/
├── backend/          # Django : config/ (réglages), comptes/ (utilisateurs, rôles, connexion),
│                     # referentiel/ (articles, nomenclatures…), une app par module
├── frontend/         # React + TypeScript (Vite)
├── docs/             # fiche entreprise, décisions (decisions.md)
├── data/             # scripts de données fictives (à venir)
├── bi/               # Power Query, Power BI (à venir)
├── docker-compose.yml
└── .env.example      # modèle de configuration (copier en .env)
```

## Connexion Power BI / Excel (phase 8)

PostgreSQL est accessible depuis le PC sur `localhost`, port `5432` (modifiable avec `POSTGRES_HOST_PORT` dans `.env`). La base, l'utilisateur et le mot de passe sont ceux du fichier `.env`.
