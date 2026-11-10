# Prochaine étape : après la phase 11

Ce document permet à une nouvelle session de reprendre directement. À lire avec `CLAUDE.md` et `docs/decisions.md` (sections « Phase 11a », « Phase 11b » et « Points en suspens »).

## 1. Où en est le projet

- Les phases 1 à 10 sont terminées ; rapport Power BI complété (pull request #16).
- **Phase 11 – Calendrier** : deux branches à fusionner **dans l'ordre** par Nicolas :
  1. `phase-11a-calendrier` : calendrier (jours fériés, fermetures de site), heure limite, taux de service, plan, planning, délais fournisseurs et MRP en jours ouvrés, écran **Calendrier** ;
  2. `phase-11b-historique` (construite sur la 11a) : historique de démonstration sur le vrai calendrier.
- La base locale de Nicolas garde son ancien historique (7 j/7) ; pour voir la nouvelle démo, repartir d'une base neuve (section 4).

## 2. Prochaine étape : à choisir avec Nicolas

Pistes ci-dessous ; présenter un plan et les décisions métier avant de coder.

## 3. Pistes

Tirées des « Points en suspens » de `docs/decisions.md` :

1. **Accélérer la suite de tests** (≈ 9 min) et le chargement de l'historique (≈ 6 min).
2. Saisonnalité dans les prévisions (quand l'historique sera plus long).
3. Formulaires React du référentiel, réservation de stock, envoi d'e-mails, « refus à quai ».

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
