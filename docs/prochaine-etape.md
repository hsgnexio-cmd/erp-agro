# Prochaine étape : finition avant publication

Ce document permet à une nouvelle session de reprendre directement. À lire avec `CLAUDE.md` et `docs/decisions.md` (sections « Équipe de démonstration et comptes par rôle » et « Accès en lecture selon le rôle »).

## 1. Où en est le projet

- Les **11 phases** sont terminées (dernières : 9 planification, 10 TRS, 11 calendrier).
- Depuis : réglages de la démo (pull request #19), **équipe de démonstration** de 10 personnes avec leur fonction (`comptes/demo_users.py`, mot de passe `DEMO_USERS_PASSWORD` du `.env`), **accès en lecture selon le rôle** (`comptes/access.py` : menu filtré, refus du serveur, prix masqués, tableau de bord réservé à la direction).
- Base locale de Nicolas repartie à neuf le 10/11/2026 : démo complète sur 6 semaines, compte administrateur `nicolas`, utilisateur `powerbi` recréé.
- Dépôt GitHub **privé** ; le `.env` n'a jamais été envoyé (vérifié).

## 2. Prochaine étape : finition, dans cet ordre (validé par Nicolas le 10/11/2026)

1. ✅ **Tableau de bord par rôle** : fait (branche `tableau-de-bord-par-role`, voir `docs/decisions.md`, section « Tableau de bord par rôle »).
2. ✅ **GitHub Actions** : vert (capture de Nicolas, 10/11/2026).
3. ✅ **Test « comme un inconnu »** : dépôt cloné dans un dossier vierge (projet Docker `erp-inconnu`, ports 18000 / 15173 / 15432 via un `docker-compose.override.yml` local), README suivi à la lettre : tout démarre, démo chargée (≈ 4 min 30), tests verts. Corrigé : étape `git clone`, chemin générique, lancement en arrière-plan, `BI_DB_PASSWORD` à remplacer, création de l'administrateur, chargement de la démo et première connexion intégrés au premier lancement ; `creer_utilisateur_bi` refuse le mot de passe d'exemple.
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
