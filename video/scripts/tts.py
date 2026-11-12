"""Génère la voix off (voix neuronale Microsoft, via edge-tts) à partir de script.json.

Écrit public/voix/<id>.mp3 et public/voix/durations.json (durée et repères de mots).
Lancement : voir video/README.md.
"""

import asyncio
import json
import pathlib

import edge_tts
from mutagen.mp3 import MP3

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "public" / "voix"
VOICE = "fr-FR-HenriNeural"
RATE = "+10%"


async def speak(item: dict) -> dict:
    target = OUT / f"{item['id']}.mp3"
    words = []
    try:
        communicate = edge_tts.Communicate(item["text"], VOICE, rate=RATE, boundary="WordBoundary")
    except TypeError:  # anciennes versions d'edge-tts
        communicate = edge_tts.Communicate(item["text"], VOICE, rate=RATE)
    with target.open("wb") as audio:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                words.append({"t": round(chunk["offset"] / 1e7, 3), "w": chunk["text"]})
    return {"id": item["id"], "duration": round(MP3(target).info.length, 3), "words": words}


async def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    items = json.loads((ROOT / "script.json").read_text(encoding="utf-8"))
    result = [await speak(item) for item in items]
    (OUT / "durations.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    for row in result:
        print(row["id"], row["duration"], "s", len(row["words"]), "mots")
    print("total", round(sum(r["duration"] for r in result), 1), "s")


asyncio.run(main())
