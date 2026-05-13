from __future__ import annotations

import os
import re

# ---------------------------------------------------------------------------
# Mood keyword map — used for both playlist scoring and recommendation targets
# ---------------------------------------------------------------------------
MOOD_MAP = {
    "energetic":  {
        "keywords": ["energy", "energetic", "hype", "pump", "power", "intense", "beast",
                     "fire", "lit", "banger", "hard", "electric", "rush", "explosive"],
        "target_energy": 0.88, "target_valence": 0.70, "target_danceability": 0.75,
    },
    "workout": {
        "keywords": ["gym", "workout", "exercise", "run", "running", "training",
                     "fitness", "sweat", "cardio", "lift", "grind"],
        "target_energy": 0.90, "target_valence": 0.65, "target_danceability": 0.72,
    },
    "chill": {
        "keywords": ["chill", "relax", "calm", "mellow", "easy", "peaceful",
                     "smooth", "soft", "quiet", "lowkey", "vibes", "laid"],
        "target_energy": 0.35, "target_valence": 0.55, "target_danceability": 0.42,
    },
    "happy": {
        "keywords": ["happy", "joy", "fun", "upbeat", "cheerful", "good",
                     "positive", "smile", "bright", "sunny", "feel good", "feelgood"],
        "target_energy": 0.72, "target_valence": 0.88, "target_danceability": 0.70,
    },
    "sad": {
        "keywords": ["sad", "cry", "crying", "emotional", "melancholy", "heartbreak",
                     "blue", "down", "hurt", "pain", "miss", "grief", "lonely"],
        "target_energy": 0.30, "target_valence": 0.20, "target_danceability": 0.35,
    },
    "dark": {
        "keywords": ["dark", "moody", "deep", "heavy", "serious", "brooding",
                     "gloomy", "noir", "raw", "intense", "aggressive"],
        "target_energy": 0.68, "target_valence": 0.25, "target_danceability": 0.50,
    },
    "party": {
        "keywords": ["party", "dance", "club", "turn up", "celebration", "rave",
                     "night out", "pregame", "bop", "groove", "dancefloor"],
        "target_energy": 0.85, "target_valence": 0.80, "target_danceability": 0.88,
    },
    "focus": {
        "keywords": ["focus", "study", "work", "concentrate", "productive",
                     "coding", "reading", "homework", "flow", "deep work", "studying"],
        "target_energy": 0.42, "target_valence": 0.45, "target_danceability": 0.38,
    },
    "nostalgic": {
        "keywords": ["nostalgic", "nostalgia", "throwback", "old school", "memories",
                     "classic", "retro", "childhood", "remember", "back in"],
        "target_energy": 0.55, "target_valence": 0.58, "target_danceability": 0.55,
    },
    "romantic": {
        "keywords": ["romantic", "romance", "love", "date", "intimate",
                     "slow", "cuddle", "cozy", "tender", "sweet"],
        "target_energy": 0.40, "target_valence": 0.65, "target_danceability": 0.44,
    },
    "sleep": {
        "keywords": ["sleep", "night", "bedtime", "dream", "ambient",
                     "tired", "wind down", "rest", "late night"],
        "target_energy": 0.20, "target_valence": 0.38, "target_danceability": 0.25,
    },
    "morning": {
        "keywords": ["morning", "wake up", "sunrise", "breakfast", "start",
                     "fresh", "new day", "rise"],
        "target_energy": 0.70, "target_valence": 0.72, "target_danceability": 0.62,
    },
    "angry": {
        "keywords": ["angry", "anger", "mad", "rage", "vent", "frustrated",
                     "aggressive", "furious", "pissed"],
        "target_energy": 0.92, "target_valence": 0.18, "target_danceability": 0.55,
    },
    "road_trip": {
        "keywords": ["road trip", "drive", "driving", "car", "highway",
                     "cruise", "travel", "journey", "road"],
        "target_energy": 0.68, "target_valence": 0.70, "target_danceability": 0.60,
    },
}

STOPWORDS = {"i", "im", "i'm", "a", "an", "the", "and", "or", "but", "to", "of",
             "in", "on", "for", "with", "is", "am", "are", "was", "be", "feel",
             "feeling", "want", "need", "some", "something", "really", "very",
             "my", "me", "just", "like", "bit", "little", "kinda", "kind", "so"}


def _tokenize(text: str) -> set[str]:
    text = text.lower()
    words = re.findall(r"[a-z']+", text)
    return {w for w in words if w not in STOPWORDS and len(w) > 1}


def _detect_moods(vibe_text: str) -> list[tuple[str, float]]:
    """Return list of (mood_name, score) sorted by score descending."""
    tokens = _tokenize(vibe_text)
    full_text = vibe_text.lower()
    scores: dict[str, float] = {}

    for mood, data in MOOD_MAP.items():
        score = 0.0
        for kw in data["keywords"]:
            if " " in kw:
                if kw in full_text:
                    score += 2.0
            elif kw in tokens:
                score += 1.0
        if score > 0:
            scores[mood] = score

    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


def _score_playlist(playlist_name: str, vibe_tokens: set[str], detected_moods: list[tuple[str, float]]) -> float:
    name_tokens = _tokenize(playlist_name)
    name_lower = playlist_name.lower()
    score = 0.0

    # Direct token overlap between vibe and playlist name
    overlap = vibe_tokens & name_tokens
    score += len(overlap) * 2.0

    # Check if playlist name contains keywords from detected moods
    for mood, mood_score in detected_moods[:3]:
        for kw in MOOD_MAP[mood]["keywords"]:
            if " " in kw:
                if kw in name_lower:
                    score += mood_score * 1.5
            elif kw in name_tokens:
                score += mood_score * 1.0

    return score


def _get_audio_targets(detected_moods: list[tuple[str, float]]) -> dict:
    """Blend audio targets from top detected moods, weighted by score."""
    if not detected_moods:
        return {"target_energy": 0.6, "target_valence": 0.6, "target_danceability": 0.55}

    total = sum(s for _, s in detected_moods[:3])
    energy = valence = dance = 0.0
    for mood, score in detected_moods[:3]:
        w = score / total
        energy += MOOD_MAP[mood]["target_energy"] * w
        valence += MOOD_MAP[mood]["target_valence"] * w
        dance   += MOOD_MAP[mood]["target_danceability"] * w

    return {"target_energy": round(energy, 2), "target_valence": round(valence, 2), "target_danceability": round(dance, 2)}


# ---------------------------------------------------------------------------
# Public interface — returns matched playlists + audio targets
# Claude drops in here when the API key is available
# ---------------------------------------------------------------------------

def match_vibe(vibe_text: str, playlists: list[dict]) -> dict:
    """
    Match the user's vibe text to their Spotify playlists.

    Returns:
        {
            "matched_playlists": [{"id": ..., "name": ..., "score": ...}, ...],
            "audio_targets": {"target_energy": ..., "target_valence": ..., "target_danceability": ...},
            "mood_label": "Chill & Focused",   # human-readable summary
            "method": "keywords" | "claude",
        }
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if api_key:
        return _match_with_claude(vibe_text, playlists, api_key)
    return _match_with_keywords(vibe_text, playlists)


def _match_with_keywords(vibe_text: str, playlists: list[dict]) -> dict:
    vibe_tokens = _tokenize(vibe_text)
    detected_moods = _detect_moods(vibe_text)

    scored = []
    for pl in playlists:
        name = pl.get("name", "")
        score = _score_playlist(name, vibe_tokens, detected_moods)
        if score > 0:
            scored.append({**pl, "score": score})

    scored.sort(key=lambda x: x["score"], reverse=True)
    matched = scored[:3] if scored else playlists[:2]

    mood_names = [m.replace("_", " ").title() for m, _ in detected_moods[:2]]
    mood_label = " & ".join(mood_names) if mood_names else "Mixed Vibes"

    return {
        "matched_playlists": matched,
        "audio_targets": _get_audio_targets(detected_moods),
        "mood_label": mood_label,
        "method": "keywords",
    }


def _match_with_claude(vibe_text: str, playlists: list[dict], api_key: str) -> dict:
    """Claude-powered vibe matching — used automatically when ANTHROPIC_API_KEY is set."""
    import anthropic, json

    client = anthropic.Anthropic(api_key=api_key)
    playlist_list = "\n".join(f"- {pl['name']} (id: {pl['id']})" for pl in playlists)

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        messages=[{
            "role": "user",
            "content": (
                f"The user's radio vibe: \"{vibe_text}\"\n\n"
                f"Their Spotify playlists:\n{playlist_list}\n\n"
                "Pick 1–3 playlists that best match the vibe. "
                "Also output a short mood label (3–5 words) and "
                "Spotify audio targets (energy, valence, danceability each 0.0–1.0).\n\n"
                "Respond with ONLY valid JSON in this exact shape:\n"
                '{"matched_ids": ["id1", "id2"], "mood_label": "...", '
                '"target_energy": 0.0, "target_valence": 0.0, "target_danceability": 0.0}'
            ),
        }],
    )

    data = json.loads(message.content[0].text)
    matched = [pl for pl in playlists if pl["id"] in data["matched_ids"]]
    return {
        "matched_playlists": matched,
        "audio_targets": {
            "target_energy": data["target_energy"],
            "target_valence": data["target_valence"],
            "target_danceability": data["target_danceability"],
        },
        "mood_label": data["mood_label"],
        "method": "claude",
    }
