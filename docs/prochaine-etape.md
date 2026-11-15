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

- ✅ Fait (branche `design-finition`) : badge « Bloqué par ce rappel » sur la fiche d'un rappel, à côté du statut d'avant blocage.
- 💡 Possible : voix off enregistrée par Nicolas lui-même (remplacer `video/public/voix/*.mp3` et les repères de `durations.json`), mise en ligne de la vidéo (LinkedIn, YouTube) et lien dans le README.

## 2 ter. Nouveau design (branches `design` puis `design-ecrans`, 12/11/2026)

✅ Menu latéral par métier, nouveau style commun et revue de tous les écrans (une quarantaine, photographiés un par un ; voir `docs/decisions.md`, section « Design de l'interface »). Captures du README refaites (`docs/captures/*.jpg`). Vidéo, GIF et captures du README refaits avec le nouveau design (branche `video-nouveau-design`) ; dans la vidéo, le menu latéral reste fixe pendant le défilement (`sticky` du composant `Browser`).

## 2 quater. Design system (en cours, depuis le 14/11/2026)

Cahier des charges « SaaS B2B » de Nicolas, par étapes (voir `docs/decisions.md`, section « Design system »).

- ✅ Étape 1a (branche `design-systeme`) : barre du haut (fil d'Ariane, recherche Ctrl+K, aperçu par métier, alertes), menu à icônes compact et repliable, badges normalisés, couleurs de la charte.
- ✅ Étape 1b (branche `design-systeme`, recréée) : composants génériques `components/Drawer.tsx` (tiroir latéral 540 / 680 px, onglets, pied d'actions, Échap) et `components/DataTable.tsx` (en-têtes collants, tri par colonne et multi-colonnes avec Maj + clic, cases à cocher et barre d'actions groupées, chiffres à droite en chasse fixe), avec leurs tests. **Aucune page ne les utilise encore** ; reste l'en-tête de page standard.
- ✅ Étape 2a, pilotage (branche `design-systeme`, recréée) : accueil « cockpit » (date, semaine ISO, statut discret, bandeau « Urgences du jour » sur les alertes critiques, cartes avec icône et compteur tiré des API existantes, sans nouvelle API) ; tableau de bord (grand chiffre, mini-courbe des semaines de la période, jauge avec repère d'objectif, formule dans une infobulle). Délai des tests Vitest porté à 15 s (échecs aléatoires sur machine chargée).
- ✅ Étape 2b, stocks et qualité (branche `design-systeme`, recréée) : lots en `DataTable` (tri, sélection, export CSV) avec fiche et traçabilité en tiroir (`components/LotDrawer.tsx`, bouton rouge « Simuler un rappel ») ; FEFO avec jauge de durée de vie restante (rouge ≤ 2 j, orange ≤ 5 j) ; températures en cartes par chambre froide avec courbe et seuils ; alertes avec onglets Toutes / Critique / Avertissement ; stocks et inventaires triables. Écarts au cahier des charges : pas d'onglet « Info » (ce niveau n'existe pas), commentaire d'alerte toujours obligatoire, lancement d'un rappel toujours sur l'écran de simulation (rôle qualité, motif).
- ✅ Étape 2c, approvisionnements et fabrication (branche `design-systeme`, recréée) : MRP (synthèse, « en retard : rupture probable », bouton « Générer la commande » par ligne), planning (barre de charge par rapport à la capacité, rouge au-delà de 100 %), TRS (Disponibilité × Performance × Qualité = TRS, barre empilée du temps d'ouverture par ligne), achats (tableau triable, étapes d'avancement, respect du délai), ordres de fabrication (tableau triable, avancement produit / prévu).
- ✅ Étape 2d, référentiel : articles (filtres rapides par type, fiche en tiroir), fournisseurs et clients (tableau triable, fiche en tiroir), sites (cartes par site, sans taux d'occupation : donnée absente), calendrier (vue de l'année : week-ends, fériés, fermetures).
- Suite complète relancée le 14/11/2026 : 478 tests serveur, 96 tests écran, lint et build verts.
- ✅ Étape 3, finition (branche `design-finition`, 15/11/2026) : écrans Commercial (ventes, EDI, expéditions et tarifs en tableaux triables avec fiche en tiroir ; taux de service en barres avec repère d'objectif ; tableaux des prévisions harmonisés, grille inchangée), Qualité (rappels avec chiffres clés et bouton rouge de simulation, badge « Bloqué par ce rappel », synthèse de traçabilité) et plan de production (synthèse, totaux par jour, barres de charge). Vérifié : 107 tests écran, lint, build, et chaque écran dans le navigateur (compte `test-verif`, désactivé ensuite). Tests serveur non relancés (aucun fichier serveur modifié).
- ✅ Vidéo refaite avec la nouvelle interface (branche `video-refonte`, 15/11/2026) : voir la section 2 quinquies. Captures du README refaites en même temps.
- ⏳ Reste : La base locale de Nicolas n'a aucun rappel (fiche d'un rappel vérifiée seulement par les tests) : repartir d'une démo neuve pour la voir.
- Après fusion : `docker compose up -d --build` (nouvelle dépendance `lucide-react`). Vidéo et captures du README à régénérer à la fin.

## 2 quinquies. Vidéo « supply chain » (branche `video-refonte`, 15/11/2026)

✅ Vidéo refaite et allongée à 1 min 47, pour un public supply chain (demande de Nicolas : viser des postes de demand planning, S&OP, ordonnancement, pilotage des flux ; la technique n'arrive qu'à la fin). Cinq actes avec cartons de titre : l'équation du frais (accueil, tableau de bord), approvisionner (MRP de la crème, FEFO, températures), de la prévision à l'atelier (prévisions, plan, planning, TRS), le crash-test (recherche, tiroir, traçabilité, rappel), la preuve (vues par métier, 81 tables, 478 + 107 tests, écran de fin). Thème clair (fenêtre flottante sur fond `#F6F7F4`), caméra qui zoome sur les chiffres au moment où la voix en parle, curseur animé, bruitages fabriqués par `video/scripts/sfx.mjs`, musique à −26 dB sous la voix. Mode d'emploi : `video/README.md`.

- Captures prises sur une **copie isolée** de l'ERP (démo neuve du 15/11/2026, supprimée ensuite) : la base de Nicolas n'a pas été touchée.
- 🐞 Vu pendant les captures, à corriger dans l'ERP : le fond assombri de la recherche globale (Ctrl K) ne couvre que le haut de la page, parce que la palette est affichée à l'intérieur de la barre du haut, qui a un `backdrop-filter` ; l'afficher en dehors (portail React) règle le problème. Autre constat : dans « Besoins d'achat », le détail d'un article s'ouvre sous chacune de ses lignes.
- 💡 Possible : faire ouvrir le tiroir du lot par la recherche globale (aujourd'hui elle ouvre la fiche complète ; la vidéo fait une ellipse), voix enregistrée par Nicolas, mise en ligne (LinkedIn, YouTube).

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
