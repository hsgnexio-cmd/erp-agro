# Prochaine étape : après la phase 9

Ce document permet à une nouvelle session de reprendre directement. À lire avec `CLAUDE.md` et `docs/decisions.md` (sections « Phase 9a », « Phase 9b », « Phase 9c » et « Points en suspens »).

## 1. Où en est le projet

- Les phases 1 à 8 sont terminées, ainsi que 9a (prévisions, pull request #12) et 9b (plan de production, pull request #13).
- **Partie 9c – Calcul des besoins (MRP)** : faite sur la branche `phase-9c-mrp` (pull request à créer et fusionner par Nicolas) :
  - `achats/mrp.py` : besoins bruts sur 9 semaines (OF, plan brouillon, prévision), éclatement multiniveau, besoin net (stock, commandes en cours brouillons compris), propositions datées avec le délai fournisseur, minimum de commande, retards ;
  - création des commandes brouillon par fournisseur et par semaine de besoin ;
  - écran React **Besoins d'achat**.
- Avec la 9c, **la phase 9 est terminée**.

## 2. Prochaine étape : à choisir avec Nicolas

Pistes ci-dessous ; présenter un plan et les décisions métier avant de coder.

## 3. Pistes

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
