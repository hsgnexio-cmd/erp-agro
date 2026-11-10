# Prochaine étape : finition avant publication

Ce document permet à une nouvelle session de reprendre directement. À lire avec `CLAUDE.md` et `docs/decisions.md` (sections « Équipe de démonstration et comptes par rôle » et « Accès en lecture selon le rôle »).

## 1. Où en est le projet

- Les **11 phases** sont terminées (dernières : 9 planification, 10 TRS, 11 calendrier).
- Depuis : réglages de la démo (pull request #19), **équipe de démonstration** de 10 personnes avec leur fonction (`comptes/demo_users.py`, mot de passe `DEMO_USERS_PASSWORD` du `.env`), **accès en lecture selon le rôle** (`comptes/access.py` : menu filtré, refus du serveur, prix masqués, tableau de bord réservé à la direction).
- Base locale de Nicolas repartie à neuf le 10/11/2026 : démo complète sur 6 semaines, compte administrateur `nicolas`, utilisateur `powerbi` recréé.
- Dépôt GitHub **privé** ; le `.env` n'a jamais été envoyé (vérifié).

## 2. Prochaine étape : finition, dans cet ordre (validé par Nicolas le 10/11/2026)

1. **Tableau de bord par rôle** : chaque rôle voit les indicateurs de son métier, la direction voit tout avec les montants en euros. Proposition à valider :
   qualité → conformité réception, délai de traçabilité, démarque en % ; production → rendement matière, TRS, couverture matières ; achats → couverture matières, conformité réception ; commercial → taux de service, fiabilité des prévisions ; magasinier → taux de service, couverture produits finis. Domaine `pilotage` de `comptes/access.py` à ouvrir aux autres rôles, avec un filtrage des tuiles (et de l'export CSV) côté serveur ; pas de montants en euros hors direction.
2. **GitHub Actions** : demander à Nicolas une capture de l'onglet Actions (dépôt privé) et corriger s'il est rouge.
3. **Test « comme un inconnu »** : cloner le dépôt dans un dossier vierge (autre nom de projet Docker et autres ports, sans toucher à la base de Nicolas), suivre le README à la lettre, corriger tout ce qui bloque.
4. **Relecture générale du code** (revue de qualité avant que d'autres le lisent).
5. **Accélérer les tests** (≈ 9 min en local).

Ensuite : **publication** (README d'accueil avec captures d'écran et parcours de démonstration, licence, passage du dépôt en public guidé pas à pas).

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
