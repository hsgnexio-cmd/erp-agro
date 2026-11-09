# Prochaine étape : après la partie 9b

Ce document permet à une nouvelle session de reprendre directement. À lire avec `CLAUDE.md` et `docs/decisions.md` (sections « Phase 9a », « Phase 9b » et « Points en suspens »).

## 1. Où en est le projet

- Les phases 1 à 8 sont terminées. Partie 9a (prévisions de vente) fusionnée (pull request #12).
- **Partie 9b – Plan de production** : faite sur la branche `phase-9b-plan-production` (pull request à créer et fusionner par Nicolas) :
  - `production/master_plan.py` : plan de la semaine S+1 (marque Brévanne sur stock avec stock de sécurité, MDD à la commande), arrondi au colis de 12, réparti du lundi au vendredi sur la première ligne compatible ;
  - ajustements du brouillon (quantités, ligne, ajout d'un produit), charge des lignes ;
  - gel à J-2 (samedi 12 h, Celery, ou bouton) : un OF planifié par produit et par jour ; écarts entre le plan figé et les OF ;
  - champ « stock de sécurité (jours de demande) » sur l'article ;
  - écran React **Plan de production** ; démo : plan de S+1 en brouillon.
- **À faire par Nicolas après la fusion** : relancer `charger_donnees_demo` (rien n'est recréé, seul le plan de la semaine prochaine est calculé) ou cliquer sur « Calculer le plan » dans l'écran.

## 2. Prochaine étape : partie 9c – Calcul des besoins (MRP)

Décisions déjà validées avec Nicolas (09/11/2026), à reprendre dans le plan détaillé :

- besoins bruts sur **8 semaines** : plan figé pour S+1, plan calculé depuis la prévision pour S+2 à S+8 (`master_plan.calculate`) ;
- éclatement des nomenclatures à tous les niveaux (semi-finis compris), pertes comprises (`production.orders.theoretical_needs`), semaine par semaine ;
- besoin net = besoin brut − stock disponible − commandes fournisseurs en cours (reste à recevoir) ;
- propositions chez le fournisseur principal audité : date de commande = semaine du besoin − délai fournisseur ; quantité relevée au minimum de commande ; « en retard » si la date est passée ;
- l'acheteur sélectionne des propositions → une commande **brouillon** par fournisseur (`achats`), qu'il vérifie puis envoie ;
- écran « Besoins d'achat », démo (dont un emballage MDD à long délai), tests.

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
