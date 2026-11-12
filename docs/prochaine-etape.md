# Prochaine étape : publication, puis pistes

Ce document permet à une nouvelle session de reprendre directement. À lire avec `CLAUDE.md` et `docs/decisions.md` (sections « Équipe de démonstration et comptes par rôle » et « Accès en lecture selon le rôle »).

## 1. Où en est le projet

- Les **11 phases** sont terminées (dernières : 9 planification, 10 TRS, 11 calendrier).
- Depuis : réglages de la démo (pull request #19), **équipe de démonstration** de 10 personnes avec leur fonction (`comptes/demo_users.py`, mot de passe `DEMO_USERS_PASSWORD` du `.env`), **accès en lecture selon le rôle** (`comptes/access.py` : menu filtré, refus du serveur, prix masqués, tableau de bord réservé à la direction).
- Base locale de Nicolas repartie à neuf le 10/11/2026 : démo complète sur 6 semaines, compte administrateur `nicolas`, utilisateur `powerbi` recréé.
- Dépôt GitHub **privé** jusqu'à la publication ; le `.env` n'a jamais été envoyé (vérifié).

## 2. Prochaine étape : finition, dans cet ordre (validé par Nicolas le 10/11/2026)

1. ✅ **Tableau de bord par rôle** : fait (branche `tableau-de-bord-par-role`, voir `docs/decisions.md`, section « Tableau de bord par rôle »).
2. ✅ **GitHub Actions** : vert (capture de Nicolas, 10/11/2026).
3. ✅ **Test « comme un inconnu »** : dépôt cloné dans un dossier vierge (projet Docker `erp-inconnu`, ports 18000 / 15173 / 15432 via un `docker-compose.override.yml` local), README suivi à la lettre : tout démarre, démo chargée (≈ 4 min 30), tests verts. Corrigé : étape `git clone`, chemin générique, lancement en arrière-plan, `BI_DB_PASSWORD` à remplacer, création de l'administrateur, chargement de la démo et première connexion intégrés au premier lancement ; `creer_utilisateur_bi` refuse le mot de passe d'exemple.
4. ✅ **Relecture générale du code** : voir `docs/decisions.md`, section « Relecture générale du code ».
5. ✅ **Accélérer les tests** : pytest-xdist, 7 min 19 → 2 min 25 (voir `docs/decisions.md`). ⚠️ Après la fusion, reconstruire l'image du back-end (`docker compose up -d --build`), sinon pytest ne connaît pas l'option `-n`.

6. ✅ **Publication** (branche `publication`) : licence PolyForm Noncommercial (`LICENSE.md`), accueil du README avec captures d'écran (`docs/captures/`) et parcours « Essayer la démo en 5 minutes », rappel d'un lot de crème ajouté à l'historique de démo, audit de cohérence des données et historique Git vérifié sans secret (voir `docs/decisions.md`, section « Publication »).

Reste à faire par Nicolas : fusionner la pull request, puis passer le dépôt en **public** (GitHub → Settings → General → Danger Zone → Change visibility). Pour voir le rappel dans sa propre base, repartir d'une démo neuve (section 4).

## 2 bis. Vidéo de démonstration (branche `video-demo`, 12/11/2026)

✅ Vidéo de présentation du projet de 63 s en 1080p (ton revu le 12/11/2026 à la demande de Nicolas : montrer ce qu'il a fait, pas vendre un produit ; texte sans « je » car voix féminine), faite avec **Remotion** (dossier `video/`, indépendant de l'ERP, mode d'emploi dans `video/README.md`) : 8 scènes calées sur la musique (128 BPM, le drop tombe à 7 s), voix de synthèse Microsoft « Vivienne » (Nicolas préférait une voix d'homme : « Henri » jugée trop robotique, « Rémy » refusée par le service), sous-titres mot à mot, musique baissée sous la voix. Le MP4 (`video/out/demo.mp4`, 28 Mo) et la musique ne sont pas versionnés ; l'extrait `docs/captures/demo.gif` est dans le README.

- 💡 À proposer : sur la fiche d'un rappel, la colonne Statut montre l'état **avant** blocage (« Libéré ») alors que le bandeau annonce les lots bloqués ; ajouter un badge « Bloqué par ce rappel ».
- 💡 Possible : voix off enregistrée par Nicolas lui-même (remplacer `video/public/voix/*.mp3` et les repères de `durations.json`), mise en ligne de la vidéo (LinkedIn, YouTube) et lien dans le README.

## 2 ter. Nouveau design (branches `design` puis `design-ecrans`, 12/11/2026)

✅ Menu latéral par métier, nouveau style commun et revue de tous les écrans (une quarantaine, photographiés un par un ; voir `docs/decisions.md`, section « Design de l'interface »). Captures du README refaites (`docs/captures/*.jpg`). Vidéo, GIF et captures du README refaits avec le nouveau design (branche `video-nouveau-design`) ; dans la vidéo, le menu latéral reste fixe pendant le défilement (`sticky` du composant `Browser`).

## 3. Pistes

Tirées des « Points en suspens » de `docs/decisions.md` :

1. Accélérer le chargement de l'historique de démonstration (≈ 4 à 6 min).
2. Saisonnalité dans les prévisions (quand l'historique sera plus long).
3. Formulaires React du référentiel, réservation de stock, envoi d'e-mails, « refus à quai ».
4. Facturation (factures, avoirs, TVA, export comptable) et coût de revient des recettes : indispensables avant tout usage réel en entreprise.

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
