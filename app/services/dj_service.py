from __future__ import annotations

import os
import time
import uuid
import httpx
import anthropic

# ElevenLabs voice ID — "Charlie": warm, natural radio host voice
ELEVENLABS_VOICE_ID = "IKne3meq5aSn9XLyUdCD"
ELEVENLABS_MODEL    = "eleven_monolingual_v1"
TMP_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "tmp")


def _claude_script(current_track: dict | None, next_track: dict | None, news: str | None = None) -> str:
    """Ask Claude to write a short radio DJ script."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return ""

    client = anthropic.Anthropic(api_key=api_key)

    parts = []
    if current_track:
        parts.append(f"Song just finished: \"{current_track['name']}\" by {current_track['artist']}")
    if next_track:
        parts.append(f"Song coming up next: \"{next_track['name']}\" by {next_track['artist']}")
    if news:
        parts.append(f"News headline to weave in (optional, only if it flows naturally): {news}")

    context = "\n".join(parts)

    prompt = (
        "You are Alex, a cool and charismatic radio DJ on a personalised Spotify radio station. "
        "Write a short spoken DJ intro — exactly as it would be spoken aloud, no stage directions, no emojis.\n\n"
        f"{context}\n\n"
        "Rules:\n"
        "- Maximum 40 words\n"
        "- Sound natural and conversational, like a real radio host\n"
        "- Vary your style: sometimes hype the next song, sometimes share a quick artist fact, sometimes bridge the two songs\n"
        "- Never say 'ladies and gentlemen' or sound corporate\n"
        "- Output ONLY the spoken words, nothing else"
    )

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=120,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


def _elevenlabs_tts(text: str, api_key: str) -> bytes | None:
    """Convert text to MP3 bytes via ElevenLabs."""
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    payload = {
        "text": text,
        "model_id": ELEVENLABS_MODEL,
        "voice_settings": {"stability": 0.55, "similarity_boost": 0.80},
    }
    try:
        with httpx.Client(timeout=20) as client:
            response = client.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                return response.content
    except Exception:
        pass
    return None


def generate_dj_clip(current_track: dict | None, next_track: dict | None, news: str | None = None) -> str | None:
    """
    Generate a DJ audio clip and save it to tmp/.
    Returns the filename (not full path) or None if generation failed.
    """
    elevenlabs_key = os.environ.get("ELEVENLABS_API_KEY", "")
    if not elevenlabs_key:
        return None

    script = _claude_script(current_track, next_track, news)
    if not script:
        return None

    audio = _elevenlabs_tts(script, elevenlabs_key)
    if not audio:
        return None

    os.makedirs(TMP_DIR, exist_ok=True)

    # Clean up clips older than 10 minutes
    now = time.time()
    for f in os.listdir(TMP_DIR):
        fpath = os.path.join(TMP_DIR, f)
        if f.endswith(".mp3") and os.path.isfile(fpath):
            if now - os.path.getmtime(fpath) > 600:
                os.remove(fpath)

    filename = f"dj_{uuid.uuid4().hex[:8]}.mp3"
    filepath = os.path.join(TMP_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(audio)

    return filename
