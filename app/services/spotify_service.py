from __future__ import annotations

import random

import spotipy


class SpotifyService:
    def __init__(self, access_token: str):
        self.sp = spotipy.Spotify(auth=access_token)

    def get_current_track(self) -> dict | None:
        """Return info about the currently playing track or episode."""
        playback = self.sp.current_playback()
        if not playback or not playback.get("item"):
            return None

        item = playback["item"]
        is_playing = playback.get("is_playing", False)
        progress_ms = playback.get("progress_ms", 0)

        if playback.get("currently_playing_type") == "episode":
            return {
                "type": "episode",
                "name": item.get("name", "Unknown Episode"),
                "artist": item.get("show", {}).get("name", "Unknown Show"),
                "album": item.get("show", {}).get("name", ""),
                "image": item.get("images", [{}])[0].get("url") if item.get("images") else None,
                "duration_ms": item.get("duration_ms", 0),
                "progress_ms": progress_ms,
                "is_playing": is_playing,
                "uri": item.get("uri"),
            }

        artists = ", ".join(a["name"] for a in item.get("artists", []))
        images = item.get("album", {}).get("images", [])
        image_url = images[0]["url"] if images else None

        return {
            "type": "track",
            "name": item.get("name", "Unknown Track"),
            "artist": artists,
            "album": item.get("album", {}).get("name", ""),
            "image": image_url,
            "duration_ms": item.get("duration_ms", 0),
            "progress_ms": progress_ms,
            "is_playing": is_playing,
            "uri": item.get("uri"),
        }

    def play(self) -> None:
        self.sp.start_playback()

    def pause(self) -> None:
        self.sp.pause_playback()

    def toggle_play_pause(self) -> dict:
        """Toggle between play and pause. Returns new state."""
        playback = self.sp.current_playback()
        if not playback:
            return {"error": "no_device", "message": "Open Spotify on any device first, then try again."}
        if playback.get("is_playing"):
            self.sp.pause_playback()
            return {"is_playing": False}
        else:
            self.sp.start_playback()
            return {"is_playing": True}

    def skip_next(self) -> None:
        self.sp.next_track()

    def skip_previous(self) -> None:
        self.sp.previous_track()

    def start_radio_from_library(self) -> dict:
        """Shuffle the user's saved tracks and start playing them."""
        results = self.sp.current_user_saved_tracks(limit=50)
        if not results or not results.get("items"):
            return {"error": "empty_library", "message": "No saved tracks found. Save some songs on Spotify first."}

        uris = [item["track"]["uri"] for item in results["items"] if item.get("track")]
        random.shuffle(uris)
        self.sp.start_playback(uris=uris[:50])
        return {"started": True, "track_count": len(uris)}

    def get_top_tracks(self, limit: int = 50) -> list[dict]:
        """Get user's top tracks for discovery-based radio."""
        result = self.sp.current_user_top_tracks(limit=limit, time_range="medium_term")
        return result.get("items", [])

    def get_saved_tracks_sample(self, limit: int = 50) -> list[str]:
        """Return a list of track URIs from the user's saved library."""
        results = self.sp.current_user_saved_tracks(limit=limit)
        if not results:
            return []
        uris = [item["track"]["uri"] for item in results.get("items", []) if item.get("track")]
        random.shuffle(uris)
        return uris

    def get_recommendations(self, seed_track_ids: list, bubble: dict, limit: int = 30) -> list[str]:
        """Return recommended track URIs. Falls back to artist top tracks if recommendations API is unavailable."""
        try:
            result = self.sp.recommendations(
                seed_tracks=seed_track_ids[:5],
                target_energy=bubble.get("target_energy", 0.6),
                target_valence=bubble.get("target_valence", 0.6),
                target_danceability=bubble.get("target_danceability", 0.6),
                limit=limit,
            )
            uris = [t["uri"] for t in result.get("tracks", [])]
            if uris:
                return uris
        except Exception:
            pass

        # Fallback: get top tracks from artists of the seed tracks
        try:
            uris = []
            seen_artists = set()
            for track_id in seed_track_ids[:3]:
                track = self.sp.track(track_id)
                for artist in track.get("artists", [])[:1]:
                    aid = artist["id"]
                    if aid in seen_artists:
                        continue
                    seen_artists.add(aid)
                    top = self.sp.artist_top_tracks(aid)
                    for t in top.get("tracks", [])[:5]:
                        uris.append(t["uri"])
            return uris[:limit]
        except Exception:
            return []

    def get_user_playlists(self, limit: int = 50) -> list[dict]:
        """Return all playlists the user owns or follows."""
        try:
            result = self.sp.current_user_playlists(limit=limit)
            playlists = []
            for pl in result.get("items", []):
                if not pl:
                    continue
                images = pl.get("images", [])
                playlists.append({
                    "id": pl["id"],
                    "name": pl["name"],
                    "track_count": pl.get("tracks", {}).get("total", 0),
                    "image": images[0]["url"] if images else None,
                })
            return playlists
        except Exception:
            return []

    def get_playlist_tracks(self, playlist_id: str, limit: int = 50) -> list[str]:
        """Return track URIs from a playlist, shuffled."""
        try:
            result = self.sp.playlist_tracks(playlist_id, limit=limit)
            items = result.get("items", [])
            uris = []
            for item in items:
                # Spotify returns track under "item" or "track" depending on API version
                track = item.get("item") or item.get("track") if item else None
                if not track:
                    continue
                uri = track.get("uri", "")
                if uri and not uri.startswith("spotify:local:") and not uri.startswith("spotify:episode:"):
                    uris.append(uri)
            random.shuffle(uris)
            return uris
        except Exception:
            return []

    def get_saved_shows(self, limit: int = 10) -> list[dict]:
        """Return the user's saved podcast shows."""
        try:
            result = self.sp.current_user_saved_shows(limit=limit)
            return [item["show"] for item in result.get("items", []) if item.get("show")]
        except Exception:
            return []

    def get_show_latest_episode(self, show_id: str) -> dict | None:
        """Return the most recent episode of a show."""
        try:
            result = self.sp.show_episodes(show_id, limit=1)
            items = result.get("items", [])
            return items[0] if items else None
        except Exception:
            return None

    def get_news_episode(self) -> dict | None:
        """Find the latest episode from a known news show on Spotify."""
        from app.services.radio_service import NEWS_SHOWS
        for show_name in NEWS_SHOWS:
            try:
                results = self.sp.search(q=show_name, type="show", limit=1)
                shows = results.get("shows", {}).get("items", [])
                if not shows:
                    continue
                show = shows[0]
                episodes = self.sp.show_episodes(show["id"], limit=1)
                items = episodes.get("items", [])
                if items:
                    ep = items[0]
                    ep["show"] = show["name"]
                    return ep
            except Exception:
                continue
        return None

    def get_queue(self) -> list[dict]:
        """Return the next few tracks in the queue."""
        try:
            result = self.sp.queue()
            tracks = []
            for item in (result.get("queue") or [])[:5]:
                if item.get("type") == "track":
                    artists = ", ".join(a["name"] for a in item.get("artists", []))
                    images = item.get("album", {}).get("images", [])
                    tracks.append({
                        "name": item.get("name", ""),
                        "artist": artists,
                        "image": images[-1]["url"] if images else None,
                        "type": "track",
                    })
                elif item.get("type") == "episode":
                    images = item.get("images", [])
                    tracks.append({
                        "name": item.get("name", ""),
                        "artist": item.get("show", {}).get("name", "Podcast"),
                        "image": images[0]["url"] if images else None,
                        "type": "episode",
                    })
            return tracks
        except Exception:
            return []
