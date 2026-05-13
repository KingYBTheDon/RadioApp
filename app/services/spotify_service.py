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
                    })
            return tracks
        except Exception:
            return []

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
