# Prochaine étape : après la partie 11a

Ce document permet à une nouvelle session de reprendre directement. À lire avec `CLAUDE.md` et `docs/decisions.md` (section « Phase 11a » et « Points en suspens »).

## 1. Où en est le projet

- Les phases 1 à 10 sont terminées ; rapport Power BI complété (pull request #16).
- **Partie 11a – Calendrier** : faite sur la branche `phase-11a-calendrier` (pull request à créer et fusionner par Nicolas) :
  - `referentiel/calendar.py` : jours fériés, fermetures de site (`SiteClosure`), jours ouvrés par activité ;
  - heure limite et livraisons en jours ouvrés, `ship_by_date` pour le taux de service (Python et vue `bi.fact_service`) ;
  - plan de production, planning, délais fournisseurs et MRP en jours ouvrés ; EDI simulé arrêté les jours fériés ;
  - écran **Calendrier**, jours non ouvrés grisés ; tests sur calendrier 7 j/7 sauf `@pytest.mark.calendrier`.

## 2. Prochaine étape : partie 11b – Historique de démonstration sur le vrai calendrier

Décision validée (09/11/2026) : l'historique rejoue le vrai calendrier. Plan détaillé à présenter :

- commandes reçues du lundi au samedi (heure limite), livraisons du lundi au samedi, expéditions la veille d'un jour de livraison ;
- production du lundi au vendredi seulement (`pilotage/demo_history.py`, `_produce`) : la production du vendredi et la veille d'un jour férié couvre les expéditions jusqu'au jour ouvré suivant (stock de sécurité, DLC courtes) ;
- prévisions figées le lundi, plages de marche et arrêts seulement les jours ouvrés ;
- vérifier les indicateurs de démo (taux de service, TRS, fiabilité, couvertures) et ajuster les réglages si besoin.

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
