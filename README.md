# ERP Brévanne Traiteur

ERP agroalimentaire pour Brévanne Traiteur SAS (entreprise fictive de plats cuisinés frais), développé dans le cadre d'une formation.
Le contexte métier est décrit dans [`docs/fiche-entreprise.md`](docs/fiche-entreprise.md) et les règles du projet dans [`CLAUDE.md`](CLAUDE.md).

## Technologies

| Couche | Technologie | Version |
| --- | --- | --- |
| Base de données | PostgreSQL | 18 |
| Back-end | Python, Django, Django REST Framework | 3.14, 6.1, 3.18 |
| Tâches de fond | Celery (worker + Beat), Redis | 5.6, 8 |
| Front-end | React, TypeScript, Vite | 19.3, 6.0, 8.3 |
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

## Rôles

Les 7 rôles (`admin`, `direction`, `acheteur`, `magasinier`, `production`, `qualite`, `commercial`) sont des **groupes** Django, créés automatiquement par une migration.
Pour donner un rôle à quelqu'un : administration → **Utilisateurs** → choisir l'utilisateur → section **Permissions** → **Groupes**.
Les droits précis de chaque rôle seront ajoutés au fil des phases (par exemple, en phase 4, seul `qualite` pourra libérer ou bloquer un lot).

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
├── backend/          # Django : config/ (réglages), comptes/ (utilisateurs, rôles), une app par module
├── frontend/         # React + TypeScript (Vite)
├── docs/             # fiche entreprise, règles métier, décisions
├── data/             # scripts de données fictives (à venir)
├── bi/               # Power Query, Power BI (à venir)
├── docker-compose.yml
└── .env.example      # modèle de configuration (copier en .env)
```

## Connexion Power BI / Excel (phase 8)

PostgreSQL est accessible depuis le PC sur `localhost`, port `5432` (modifiable avec `POSTGRES_HOST_PORT` dans `.env`). La base, l'utilisateur et le mot de passe sont ceux du fichier `.env`.
