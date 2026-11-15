# Vidéo de démonstration

Vidéo de présentation de l'ERP Brévanne Traiteur, d'environ 1 min 47, pensée pour un public supply chain (direction supply chain, S&OP, recrutement industriel). Elle suit le flux en 5 actes, chacun ouvert par un carton de titre :

| Acte | Contenu | Écrans montrés |
| --- | --- | --- |
| 1. L'équation du frais | Tension permanente du traiteur frais, indicateurs d'arbitrage | Accueil (urgences du jour), tableau de bord |
| 2. Approvisionner | Calcul des besoins nets (MRP), FEFO, chaîne du froid | Besoins d'achat, FEFO, températures |
| 3. De la prévision à l'atelier | Prévision à 8 semaines, plan figé à J-2, charge des lignes, TRS | Prévisions, plan de production, planning, TRS |
| 4. Le crash-test | Rappel d'un lot de crème contaminé | Recherche globale, tiroir du lot, traçabilité, fiche du rappel |
| 5. La preuve | Chaîne modélisée, vues par métier, tests, technologies | Aperçu par métier, écran de fin |

Elle est fabriquée **avec du code** grâce à [Remotion](https://www.remotion.dev/) (vidéos écrites en React). Ce dossier est indépendant de l'ERP : il a ses propres dépendances et ne touche ni au back-end ni au front-end.

| Élément | Où | Comment |
| --- | --- | --- |
| Texte de la voix off | `script.json` | 11 phrases, une par scène |
| Voix | `public/voix/` | Voix de synthèse Microsoft « Vivienne » (`scripts/tts.py`, bibliothèque edge-tts), avec le repère de chaque mot pour caler les animations |
| Écrans de l'ERP | `public/captures/` | Captures prises sur une démo neuve (`scripts/capture.mjs` et `scripts/plan-captures.json`) ; `rects.json` contient la position des éléments mesurés |
| Bruitages | `public/sfx/` | Fabriqués par calcul (`scripts/sfx.mjs`) : clic, touche, glissement, carton, validation, alerte |
| Musique | `public/musique.mp3` | **Non fournie** (licence de son auteur) : déposer un MP3 libre de droits à cet endroit |
| Montage | `src/` | `timing.ts` (durées calculées d'après la voix, cartons), `scenes/Act1.tsx` à `Act5.tsx`, `components/` |

## Les briques du montage

- `components/Stage.tsx` : la fenêtre de navigateur flottante sur fond clair, la **caméra** (zoom et déplacement vers un point de la page, avec départ et arrivée ralentis), le défilement de la page, le **curseur** animé avec ses clics, et `Spot`, le cadre qui entoure une zone.
- `components/Note.tsx` : l'étiquette posée dans un coin (titre court, chiffre clé).
- `components/Carton.tsx` : le carton de titre d'un acte (vert forêt, texte crème, 1,1 s).
- `components/Subtitles.tsx` : les sous-titres mot à mot, jamais plus d'une ligne.
- `components/Sfx.tsx` : un bruitage à une image donnée.

Dans une scène, tout est calé sur la voix : `said('a2a', 'Stock')` donne l'image où la voix prononce ce mot. Les positions sont exprimées dans le repère de la page de l'ERP (1440 × 900), celui des captures.

## Produire la vidéo

Node.js suffit (Remotion télécharge lui-même un navigateur invisible et ffmpeg, environ 300 Mo la première fois).

```powershell
cd video
```

```powershell
npm install
```

```powershell
npm run render
```

Le résultat est `video/out/demo.mp4` (1920 × 1080, 30 images par seconde ; le volume est ramené au niveau habituel des vidéos en ligne, −15 LUFS). `npm run gif` produit l'extrait animé `out/demo.gif` (copié dans `docs/captures/demo.gif` pour le README), `npm run stills 40 300 900` sort des images de contrôle dans `out/stills/`, et `npm run studio` permet de modifier la vidéo en la voyant bouger.

## Musique et bruitages

La musique reste très en retrait sous la voix (environ −26 dB) et remonte à peine dans les silences : réglages `MUSIC` dans `src/Demo.tsx`. Le temps fort du morceau (`MUSIC_DROP`, en secondes, dans `src/timing.ts`) tombe sur le carton de l'acte 2. Pour un autre morceau, mesurer cet instant :

```powershell
npx remotion ffmpeg -i public/musique.mp3 -ac 1 -ar 11025 -t 90 out/musique.wav -y
```

```powershell
node scripts/bpm.mjs out/musique.wav
```

Pour refaire les bruitages (volumes dans `src/components/Sfx.tsx`) :

```powershell
npm run sfx
```

## Changer le texte de la voix

Modifier `script.json`, puis régénérer la voix (dans un conteneur jetable, rien ne s'installe sur le PC ; le texte est envoyé au service de lecture vocale de Microsoft). Depuis la racine du projet :

```powershell
docker compose run --rm --no-deps -e TTS_RATE=+0% -v "${PWD}\video:/video" backend sh -c "pip install -q --target /tmp/tts edge-tts mutagen && PYTHONPATH=/tmp/tts python /video/scripts/tts.py"
```

La durée de chaque scène suit automatiquement celle de sa phrase. Les animations désignent les mots par leur texte (`said`) : si un mot cité dans une scène disparaît de la phrase, le rendu s'arrête avec un message qui le nomme. Écrire les nombres en lettres, pour que les sous-titres restent alignés sur la voix.

## Refaire les captures

Les chiffres montrés (rappel `RAP-2026-00001` du lot `LR-261113-0005` : 14 lots, 6 bloqués, 6 enseignes ; MRP de la crème ; FEFO sur `MP-LAI-CREME35`) viennent d'une démo chargée le 15/11/2026. Sur une autre démo, les numéros de lot et les chiffres changent : il faut alors adapter le plan de captures, le texte de la voix et les étiquettes des scènes.

1. Lancer l'ERP sur une base de démonstration neuve (une copie isolée du dépôt, sur d'autres ports, évite de toucher à sa base habituelle), avec un compte administrateur.
2. Créer une session Django pour ce compte et l'écrire dans `sessions.json` : `{"admin": "<identifiant de session>"}`.
3. Ouvrir Edge avec `--headless=new --remote-debugging-port=9333`, puis :

```powershell
node video/scripts/capture.mjs 9333 http://127.0.0.1:5173 sessions.json video/public/captures video/scripts/plan-captures.json
```

`CAPTURE_ONLY=mrp,fefo` limite la reprise à certains écrans (champ `name` du plan). Le plan décrit, écran par écran, les actions à jouer (clic, frappe, choix dans une liste, défilement), les captures à prendre et les éléments à mesurer.

Deux écarts assumés entre la vidéo et l'application :

- Le fond assombri de la recherche globale ne couvre aujourd'hui que le haut de la page (la barre du haut a un effet de flou qui le limite). Le plan de captures neutralise ce flou le temps de la capture ; la correction dans l'ERP reste à faire.
- Dans l'application, valider un résultat de la recherche ouvre la fiche complète du lot. La vidéo enchaîne directement sur le tiroir du lot, ouvert depuis la liste des lots.
