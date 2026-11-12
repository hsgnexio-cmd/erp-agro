# Vidéo de démonstration

Vidéo promotionnelle d'environ une minute de l'ERP Brévanne Traiteur, autour du scénario de référence : un lot de crème contaminé, la traçabilité et le rappel produit.

Elle est fabriquée **avec du code** grâce à [Remotion](https://www.remotion.dev/) (vidéos écrites en React). Ce dossier est indépendant de l'ERP : il a ses propres dépendances et ne touche ni au back-end ni au front-end.

| Élément | Où | Comment |
| --- | --- | --- |
| Texte de la voix off | `script.json` | 8 séquences, une par scène |
| Voix | `public/voix/` | Voix de synthèse Microsoft « Vivienne » (voix multilingue, plus naturelle) (`scripts/tts.py`, bibliothèque edge-tts), avec le repère de chaque mot pour caler les animations |
| Écrans de l'ERP | `public/captures/` | Captures prises sur une démo neuve (`scripts/capture.mjs` et `scripts/plan-captures.json`) |
| Musique | `public/musique.mp3` | **Non fournie** (licence de son auteur) : déposer un MP3 libre de droits à cet endroit |
| Montage | `src/` | `timing.ts` (calage sur la musique), `scenes/` (les 8 scènes), `components/` |

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

Le résultat est `video/out/demo.mp4` (1920 × 1080, 30 images par seconde ; le volume est ramené au niveau habituel des vidéos en ligne, −15 LUFS). `npm run gif` produit l’extrait animé `out/demo.gif` (copié dans `docs/captures/demo.gif` pour le README), `npm run stills 40 300 900` sort des images de contrôle, et `npm run studio` permet de modifier la vidéo en la voyant bouger.

## Changer la musique

Le montage est calé sur le morceau : dans `src/timing.ts`, `BPM` est son tempo et `MUSIC_DROP` l'instant (en secondes) où le rythme démarre ; cet instant tombe à 7 s de la vidéo, quand l'ERP apparaît. Pour un autre morceau, mesurer ces deux valeurs :

```powershell
npx remotion ffmpeg -i public/musique.mp3 -ac 1 -ar 11025 -t 90 out/musique.wav -y
```

```powershell
node scripts/bpm.mjs out/musique.wav
```

## Changer le texte de la voix

Modifier `script.json`, puis régénérer la voix (dans un conteneur jetable, rien ne s'installe sur le PC ; le texte est envoyé au service de lecture vocale de Microsoft). Depuis la racine du projet :

```powershell
docker compose run --rm --no-deps -v "${PWD}\video:/video" backend sh -c "pip install -q --target /tmp/tts edge-tts mutagen && PYTHONPATH=/tmp/tts python /video/scripts/tts.py"
```

Les animations suivent automatiquement les nouveaux repères de mots, mais chaque scène désigne les mots par leur rang : vérifier les scènes dont la phrase a changé.

## Refaire les captures

Les chiffres montrés (23 lots, 8 bloqués, 6 enseignes) viennent de la démo chargée le 12/11/2026. Pour les refaire : lancer l'ERP sur une base de démonstration neuve, créer une session par rôle, ouvrir Edge avec `--headless=new --remote-debugging-port=9333`, puis :

```powershell
node video/scripts/capture.mjs 9333 http://127.0.0.1:5173 sessions.json video/public/captures video/scripts/plan-captures.json
```

`sessions.json` contient l'identifiant de session Django de chaque rôle : `{"direction": "…", "qualite": "…", "commercial": "…"}`.
