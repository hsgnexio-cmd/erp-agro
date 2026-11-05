# Prochaine étape : phase 8b – Power BI et Power Query

Ce document permet à une nouvelle session de reprendre directement. À lire avec `CLAUDE.md`, `docs/decisions.md` (section « Phase 8a ») et `bi/README.md`.

## 1. Où en est le projet (fin de la partie 8a)

- Phases 1 à 7 terminées. Partie 8a sur la branche `phase-8a-indicateurs`, à fusionner par Nicolas :
  - historique de démonstration de 4 semaines (`pilotage/demo_history.py`, dans `charger_donnees_demo`, ≈ 6 min ; option `--sans-historique`) ;
  - vues SQL du schéma `bi` (`pilotage/sql/bi_views.sql`, migration `pilotage/0001_vues_bi`), décrites dans `bi/README.md` ;
  - calcul des indicateurs (`pilotage/indicators.py`) et API `/api/pilotage/indicators/?start=…&end=…&site=…&customer=…` ;
  - écran React **Tableau de bord** (`/tableau-de-bord`) : une tuile par indicateur, évolution par semaine.
- Décisions validées : TRS et fiabilité des prévisions « non disponibles » ; valorisation au prix de vente moyen (produits finis) et au prix d'achat en vigueur (matières) ; vues SQL communes ; historique de démo de 4 semaines.
- PostgreSQL est accessible depuis le PC (`localhost:5432`, identifiants du `.env`).

## 2. Contenu de la partie 8b

1. **Utilisateur PostgreSQL en lecture seule** (ex. `powerbi`) : droit de lecture sur le schéma `bi` uniquement (vues et fonctions), rien sur les tables de l'application. Mot de passe dans `.env` (`POWERBI_PASSWORD`), ajouté à `.env.example`. À créer par une commande Django relançable (ex. `creer_utilisateur_bi`) plutôt que par une migration, pour ne pas mettre de mot de passe dans le code.
2. **Requêtes Power Query** (`bi/power-query/*.pq`) : une par vue utile (dimensions et faits), avec les types de colonnes.
3. **Modèle Power BI** si possible (`bi/`) : relations entre faits et dimensions, mesures DAX des indicateurs, une page par thème. Sinon, un classeur Excel avec Power Query et des tableaux croisés.
4. **Documentation pas à pas** dans le README : installer le pilote PostgreSQL si besoin, se connecter depuis Excel (Données → Obtenir des données → PostgreSQL) et depuis Power BI Desktop, actualiser.
5. Test : l'utilisateur `powerbi` lit `bi.fact_service` mais ne peut ni lire `stocks_lot`, ni écrire.

## 3. Points à faire valider au début de la session

1. Nom de l'utilisateur PostgreSQL (`powerbi` ?) et création par commande Django.
2. Livrable : fichier Power BI (`.pbix`, binaire, créé à la main dans Power BI Desktop par Nicolas avec les requêtes fournies) ou seulement les requêtes `.pq` et la documentation.
3. Faut-il ajouter au tableau de bord un export CSV des indicateurs (pour Excel sans Power Query) ?

## 4. Fin de la phase 8 (liste de contrôle)

- [ ] Tests back-end et front-end verts, lint propre, migrations à jour.
- [ ] Connexion testée depuis Excel (Power Query) ou Power BI Desktop, avec l'utilisateur en lecture seule.
- [ ] `docs/decisions.md` : section « Phase 8b » + mise à jour des points en suspens.
- [ ] `README.md` : connexion Power BI pas à pas.
- [ ] `CLAUDE.md` : phase 8 → « Terminée ».
- [ ] Commits, envoi de la branche, pull request créée et fusionnée par Nicolas.

## 5. Repartir d'une base de démonstration neuve (si besoin)

⚠️ Efface toutes les données locales, y compris le compte administrateur. À ne faire qu'avec l'accord de Nicolas.

```powershell
docker compose down -v
```

```powershell
docker compose up -d
```

```powershell
docker compose exec backend python manage.py createsuperuser
```

```powershell
docker compose exec backend python manage.py charger_donnees_demo
```
