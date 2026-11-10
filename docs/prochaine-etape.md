# Prochaine étape : après la partie 11a

Ce document permet à une nouvelle session de reprendre directement. À lire avec `CLAUDE.md` et `docs/decisions.md` (section « Phase 11a » et « Points en suspens »).

## 1. Où en est le projet

- Les phases 1 à 10 sont terminées ; rapport Power BI complété (pull request #16).
- **Partie 11a – Calendrier** : faite sur la branche `phase-11a-calendrier` (pull request à créer et fusionner par Nicolas) :
  - `referentiel/calendar.py` : jours fériés, fermetures de site (`SiteClosure`), jours ouvrés par activité ;
  - heure limite et livraisons en jours ouvrés, `ship_by_date` pour le taux de service (Python et vue `bi.fact_service`) ;
  - plan de production, planning, délais fournisseurs et MRP en jours ouvrés ; EDI simulé arrêté les jours fériés ;
  - écran **Calendrier**, jours non ouvrés grisés ; tests sur calendrier 7 j/7 sauf `@pytest.mark.calendrier`.

## 2. En cours : partie 11b – Historique de démonstration sur le vrai calendrier

Travail en cours sur la branche `phase-11b-historique` (partie de `phase-11a-calendrier` : fusionner la 11a d'abord). Décisions prises avec Nicolas le 10/11/2026 :

- un produit dont la DLC restante serait trop courte à la livraison (produits à 8 jours livrés le lundi, piémontaise pour ENS4) **n'est pas commandé** ce jour-là ;
- dans l'historique, la qualité **libère à 14 h** la production du matin (dans l'application, la libération reste manuelle).

Déjà fait (`pilotage/demo_history.py`) : commandes et expéditions du lundi au samedi, production du lundi au vendredi couvrant les expéditions jusqu'au jour de production suivant, pas de stock de sécurité avant une fermeture, invendables selon la prochaine expédition, achats frais sur 4 jours, incidents au premier jour ouvré, première prévision figée après une semaine complète de commandes.

Dernière mesure (avant le dernier réglage de la prévision) : démarque 1,49 %, TRS 75 %, taux de service 99,5 à 99,7 % sur les semaines complètes, fiabilité 72 à 92 % hors première semaine.

Reste à faire :

1. recharger la démo dans une base temporaire et vérifier les indicateurs (fiabilité attendue ≥ 80 % sur 3 semaines) ;
2. lancer toute la suite de tests ;
3. documenter (`docs/decisions.md` : section 11b ; `CLAUDE.md` : phase 11 terminée ; README) ;
4. envoyer la branche et faire créer la pull request par Nicolas.

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
