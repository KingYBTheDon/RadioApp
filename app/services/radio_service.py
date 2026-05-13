from __future__ import annotations

import random
from datetime import datetime

BUBBLES = {
    "morning": {
        "name": "Morning Energy",
        "icon": "🌅",
        "target_energy": 0.78,
        "target_valence": 0.72,
        "target_danceability": 0.68,
        "seed_genres": ["pop", "dance", "indie-pop"],
    },
    "afternoon": {
        "name": "Afternoon Flow",
        "icon": "☀️",
        "target_energy": 0.65,
        "target_valence": 0.65,
        "target_danceability": 0.62,
        "seed_genres": ["hip-hop", "r-n-b", "pop"],
    },
    "evening": {
        "name": "Evening Vibes",
        "icon": "🌆",
        "target_energy": 0.50,
        "target_valence": 0.55,
        "target_danceability": 0.50,
        "seed_genres": ["soul", "indie", "alternative"],
    },
    "night": {
        "name": "Late Night",
        "icon": "🌙",
        "target_energy": 0.38,
        "target_valence": 0.40,
        "target_danceability": 0.42,
        "seed_genres": ["chill", "ambient", "sleep"],
    },
}

NEWS_SHOWS = [
    "NPR News Now",
    "Up First",
    "BBC Global News Podcast",
    "The Daily",
]


def get_time_of_day() -> str:
    hour = datetime.now().hour
    if 6 <= hour < 12:
        return "morning"
    elif 12 <= hour < 18:
        return "afternoon"
    elif 18 <= hour < 22:
        return "evening"
    else:
        return "night"


def get_current_bubble() -> dict:
    return BUBBLES[get_time_of_day()]


def build_radio_queue(svc, include_podcasts: bool = True, include_news: bool = True) -> dict:
    bubble = get_current_bubble()

    # Seed tracks from user's top tracks
    top_tracks = svc.get_top_tracks(limit=20)
    seed_ids = [t["id"] for t in random.sample(top_tracks, min(3, len(top_tracks)))]

    # Unknown songs via Spotify recommendations
    rec_uris = svc.get_recommendations(seed_ids, bubble)

    # Known songs from saved library
    saved_uris = svc.get_saved_tracks_sample(limit=50)
    random.shuffle(saved_uris)

    # Interleave: 2 recommended + 1 known
    queue_uris: list[str] = []
    rec_i = known_i = 0
    while len(queue_uris) < 30:
        for _ in range(2):
            if rec_i < len(rec_uris):
                queue_uris.append(rec_uris[rec_i])
                rec_i += 1
        if known_i < len(saved_uris):
            queue_uris.append(saved_uris[known_i])
            known_i += 1
        if rec_i >= len(rec_uris) and known_i >= len(saved_uris):
            break

    # Slot in a podcast episode at position 5
    podcast_info = None
    if include_podcasts:
        shows = svc.get_saved_shows(limit=10)
        if shows:
            show = random.choice(shows)
            episode = svc.get_show_latest_episode(show["id"])
            if episode:
                queue_uris.insert(min(5, len(queue_uris)), episode["uri"])
                podcast_info = {"name": episode["name"], "show": show["name"]}

    # Slot in a news episode at position 11
    news_info = None
    if include_news:
        news_ep = svc.get_news_episode()
        if news_ep:
            queue_uris.insert(min(11, len(queue_uris)), news_ep["uri"])
            news_info = {"name": news_ep["name"], "show": news_ep.get("show", "News")}

    return {
        "bubble": bubble,
        "queue_uris": queue_uris,
        "podcast": podcast_info,
        "news": news_info,
    }
