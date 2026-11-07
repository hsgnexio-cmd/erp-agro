# Prochaine étape : après la phase 8

Ce document permet à une nouvelle session de reprendre directement. À lire avec `CLAUDE.md` et `docs/decisions.md` (sections « Phase 8a », « Phase 8b » et « Points en suspens »).

## 1. Où en est le projet

- **Les 8 phases du projet sont terminées.** La partie 8b est fusionnée (pull request #10) :
  - utilisateur PostgreSQL `powerbi` en lecture seule sur le schéma `bi` (commande `creer_utilisateur_bi`, mot de passe `BI_DB_PASSWORD` du `.env`) ;
  - requêtes Power Query typées (`bi/power-query/`) et mesures DAX (`bi/mesures-dax.md`) ;
  - export CSV du tableau de bord ;
  - guide de connexion Excel et Power BI pas à pas dans le README.
- Rapport Power BI construit par Nicolas : `bi/powerbi/indicateurs.pbip` (cartes des indicateurs, filtre de période, segment par enseigne, matrice par semaine). Docker Desktop doit être lancé pour actualiser.

## 2. Prochaine étape choisie : phase 9a – Prévisions de vente

Choix de Nicolas (07/11/2026) : la **phase 9 – Prévisions et planification**, découpée en 9a (prévisions de vente) et 9b (plan de production figé à J-2 et calcul des besoins d'achat / MRP).

Pour démarrer la 9a : lire la fiche entreprise (prévisions, promotions, horizon), puis présenter un plan avec les décisions métier à valider avant de coder :

- méthode de prévision (moyenne mobile, saisonnalité hebdomadaire…) à partir de l'historique des ventes (`bi.fact_sales`, commandes clients) ;
- maille (produit × enseigne × semaine ?) et horizon (8 semaines) ;
- corrections manuelles et promotions (annoncées 6 à 8 semaines avant, jusqu'à ×3) : qui saisit (rôle `commercial` ?) ;
- historique des versions de prévision, pour calculer la **fiabilité des prévisions à S-1** (1 − écart absolu ÷ ventes réelles, objectif ≥ 80 %) et l'activer dans le tableau de bord, les vues `bi` et Power BI ;
- données de démonstration : prévisions passées cohérentes avec l'historique de 4 semaines.

Ajouter la phase 9 au tableau des phases de `CLAUDE.md` une fois le plan validé.

## 3. Autres pistes (plus tard)

Tirées des « Points en suspens » de `docs/decisions.md` :

1. **Prévisions de vente et planification avancée** : voir ci-dessus (phase 9).
2. **Saisie des arrêts de ligne** : rendrait disponible le **TRS**.
3. **Jours ouvrés et jours fériés** : heure limite, planning, historique de démonstration.
4. **Accélérer la suite de tests** (≈ 8 min) et le chargement de l'historique (≈ 6 min).
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
