# Prochaine étape : après la phase 10

Ce document permet à une nouvelle session de reprendre directement. À lire avec `CLAUDE.md` et `docs/decisions.md` (section « Phase 10 » et « Points en suspens »).

## 1. Où en est le projet

- Les phases 1 à 9 sont terminées (9c fusionnée : pull request #14).
- **Phase 10 – Arrêts de ligne et TRS** : faite sur la branche `phase-10-trs` (pull request à créer et fusionner par Nicolas) :
  - plage de marche et rebuts à la déclaration de production ; arrêts de ligne (saisie, annulation avec motif) ;
  - `production/oee.py` : TRS = disponibilité × performance × qualité, par ligne et par jour ;
  - vues `bi.fact_line_time` et `bi.fact_line_stop`, tuile TRS du tableau de bord, Power Query et DAX ;
  - écran React **TRS des lignes** ; historique de démo avec plages, arrêts et rebuts.
- **À faire par Nicolas après la fusion** : la base locale actuelle n'a aucune plage de marche (TRS « pas de donnée ») ; pour voir le TRS de démo, repartir d'une base neuve (section 4). Ajouter `fact_line_time`, `fact_line_stop` et la mesure TRS au rapport Power BI (`bi/mesures-dax.md`).

## 2. Prochaine étape : à choisir avec Nicolas

Pistes ci-dessous ; présenter un plan et les décisions métier avant de coder.

## 3. Pistes

Tirées des « Points en suspens » de `docs/decisions.md` :

1. **Jours ouvrés et jours fériés** : heure limite, planning, historique de démonstration.
2. **Accélérer la suite de tests** (≈ 9 min) et le chargement de l'historique (≈ 6 min).
3. Saisonnalité dans les prévisions (quand l'historique sera plus long).
4. Formulaires React du référentiel, réservation de stock, envoi d'e-mails, « refus à quai ».

## 4. Repartir d'une base de démonstration neuve (si besoin)

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
