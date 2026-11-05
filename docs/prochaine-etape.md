# Prochaine étape : après la phase 8

Ce document permet à une nouvelle session de reprendre directement. À lire avec `CLAUDE.md` et `docs/decisions.md` (sections « Phase 8a », « Phase 8b » et « Points en suspens »).

## 1. Où en est le projet

- **Les 8 phases du projet sont terminées.** La partie 8b est sur la branche `phase-8b-power-bi`, à fusionner par Nicolas :
  - utilisateur PostgreSQL `powerbi` en lecture seule sur le schéma `bi` (commande `creer_utilisateur_bi`, mot de passe `BI_DB_PASSWORD` du `.env`) ;
  - requêtes Power Query typées (`bi/power-query/`) et mesures DAX (`bi/mesures-dax.md`) ;
  - export CSV du tableau de bord ;
  - guide de connexion Excel et Power BI pas à pas dans le README.
- Reste côté Nicolas : construire le rapport Power BI dans Power BI Desktop (à installer, gratuit) et l'enregistrer en `.pbip` dans `bi/power-bi/`.

## 2. Pistes pour la suite (à choisir avec Nicolas)

Tirées des « Points en suspens » de `docs/decisions.md` :

1. **Prévisions de vente et planification avancée** : prévisions à 8 semaines, plan figé à J-2, promotions (×3), calcul des besoins d'achat (MRP). Rendrait disponible l'indicateur « fiabilité des prévisions ».
2. **Saisie des arrêts de ligne** : rendrait disponible le **TRS**.
3. **Jours ouvrés et jours fériés** : heure limite, planning, historique de démonstration.
4. **Accélérer la suite de tests** (≈ 8 min) et le chargement de l'historique (≈ 6 min).
5. Formulaires React du référentiel, réservation de stock, envoi d'e-mails, « refus à quai ».

## 3. Repartir d'une base de démonstration neuve (si besoin)

⚠️ Efface toutes les données locales, y compris le compte administrateur et l'utilisateur `powerbi`. À ne faire qu'avec l'accord de Nicolas.

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

```powershell
docker compose exec backend python manage.py creer_utilisateur_bi
```
