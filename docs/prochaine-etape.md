# Prochaine étape : après la partie 9a

Ce document permet à une nouvelle session de reprendre directement. À lire avec `CLAUDE.md` et `docs/decisions.md` (sections « Phase 9a » et « Points en suspens »).

## 1. Où en est le projet

- Les phases 1 à 8 sont terminées. Rapport Power BI de Nicolas : `bi/powerbi/indicateurs.pbip`.
- **Partie 9a – Prévisions de vente** : faite sur la branche `phase-9a-previsions` (pull request à créer et fusionner par Nicolas) :
  - app `previsions` : prévision à 8 semaines par produit × enseigne × semaine (moyenne pondérée des 4 dernières semaines de commandes, arrondie au colis de 12), promotions (jusqu'à ×3, avertissement si annoncée à moins de 6 semaines), corrections manuelles, versions figées `PRV-` chaque lundi à 5 h et à la demande ;
  - fiabilité à S-1 dans l'écran **Prévisions**, le tableau de bord, la vue `bi.fact_forecast_accuracy`, Power Query et DAX ;
  - historique de démonstration porté à 6 semaines (≈ 6 min), avec une promotion réalisée et une version figée chaque lundi.
- **À faire par Nicolas après la fusion** :
  - sa base locale n'a pas encore de version figée : la première arrivera lundi à 5 h (ou bouton « Figer une version »). Pour voir tout de suite l'historique de prévisions, repartir d'une base neuve (section 4) ;
  - ajouter `fact_forecast_accuracy` et la mesure « Fiabilité prévisions » au rapport Power BI (README, section « Ouvrir le rapport Power BI existant »).

## 2. Prochaine étape : partie 9b – Plan de production et besoins d'achat

Pour démarrer la 9b : lire la fiche entreprise (planification : plan hebdomadaire figé à J-2, MDD à la commande, marque Brévanne sur stock), puis présenter un plan avec les décisions métier à valider :

- plan de production hebdomadaire à partir de la prévision (dernière version figée) et des commandes reçues : marque Brévanne sur stock (prévision + stock de sécurité − stock), MDD à la commande ;
- gel du plan à J-2 : qui fige, ce qui reste modifiable, lien avec les OF existants (`production/orders.py`, `production/planning.py`) et la capacité des lignes ;
- calcul des besoins (MRP) : explosion des nomenclatures (pertes comprises), stock disponible, commandes fournisseurs en cours, délais fournisseurs, minimums de commande → propositions de commandes d'achat pour l'acheteur ;
- données de démonstration et tests.

## 3. Autres pistes (plus tard)

Tirées des « Points en suspens » de `docs/decisions.md` :

1. **Saisie des arrêts de ligne** : rendrait disponible le **TRS**.
2. **Jours ouvrés et jours fériés** : heure limite, planning, historique de démonstration.
3. **Accélérer la suite de tests** (≈ 5 min) et le chargement de l'historique (≈ 6 min).
4. Saisonnalité dans les prévisions (quand l'historique sera plus long).
5. Formulaires React du référentiel, réservation de stock, envoi d'e-mails, « refus à quai ».

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
