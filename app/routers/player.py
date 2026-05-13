from __future__ import annotations

import os

import spotipy
from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, JSONResponse

from app.routers.auth import get_valid_token
from app.services.spotify_service import SpotifyService

router = APIRouter()


def _get_service(request: Request) -> SpotifyService | None:
    token_info = get_valid_token(request)
    if not token_info:
        return None
    return SpotifyService(token_info["access_token"])


def _spotify_error_response(e: Exception) -> JSONResponse:
    msg = str(e)
    if "No active device" in msg or "404" in msg:
        return JSONResponse(
            {"error": "no_device", "message": "Open Spotify on your phone or computer first, then try again."},
            status_code=503,
        )
    return JSONResponse({"error": "spotify_error", "message": msg}, status_code=500)


@router.get("/now-playing")
async def now_playing(request: Request):
    svc = _get_service(request)
    if not svc:
        return JSONResponse({"error": "not_logged_in"}, status_code=401)
    try:
        track = svc.get_current_track()
        return JSONResponse(track or {"nothing_playing": True})
    except spotipy.SpotifyException as e:
        return _spotify_error_response(e)


@router.get("/queue")
async def get_queue(request: Request):
    svc = _get_service(request)
    if not svc:
        return JSONResponse({"error": "not_logged_in"}, status_code=401)
    try:
        return JSONResponse(svc.get_queue())
    except spotipy.SpotifyException as e:
        return _spotify_error_response(e)


@router.post("/play-pause")
async def play_pause(request: Request):
    svc = _get_service(request)
    if not svc:
        return JSONResponse({"error": "not_logged_in"}, status_code=401)
    try:
        result = svc.toggle_play_pause()
        return JSONResponse(result)
    except spotipy.SpotifyException as e:
        return _spotify_error_response(e)


@router.post("/skip")
async def skip(request: Request):
    svc = _get_service(request)
    if not svc:
        return JSONResponse({"error": "not_logged_in"}, status_code=401)
    try:
        svc.skip_next()
        return JSONResponse({"skipped": True})
    except spotipy.SpotifyException as e:
        return _spotify_error_response(e)


@router.post("/previous")
async def previous(request: Request):
    svc = _get_service(request)
    if not svc:
        return JSONResponse({"error": "not_logged_in"}, status_code=401)
    try:
        svc.skip_previous()
        return JSONResponse({"previous": True})
    except spotipy.SpotifyException as e:
        return _spotify_error_response(e)


@router.post("/start-radio")
async def start_radio(request: Request):
    svc = _get_service(request)
    if not svc:
        return JSONResponse({"error": "not_logged_in"}, status_code=401)
    try:
        from app.services.radio_service import build_radio_queue
        result = build_radio_queue(svc)
        uris = result["queue_uris"]
        if not uris:
            return JSONResponse({"error": "empty_queue", "message": "Could not build a queue. Save some songs on Spotify first."})
        svc.sp.start_playback(uris=uris)
        return JSONResponse({
            "started": True,
            "track_count": len(uris),
            "bubble": result["bubble"],
            "podcast": result.get("podcast"),
            "news": result.get("news"),
        })
    except spotipy.SpotifyException as e:
        return _spotify_error_response(e)


@router.get("/playlists")
async def get_playlists(request: Request):
    svc = _get_service(request)
    if not svc:
        return JSONResponse({"error": "not_logged_in"}, status_code=401)
    try:
        return JSONResponse(svc.get_user_playlists())
    except spotipy.SpotifyException as e:
        return _spotify_error_response(e)


@router.post("/vibe-radio")
async def vibe_radio(request: Request):
    svc = _get_service(request)
    if not svc:
        return JSONResponse({"error": "not_logged_in"}, status_code=401)
    try:
        body = await request.json()
        vibe_text = (body.get("vibe") or "").strip()
        if not vibe_text:
            return JSONResponse({"error": "no_vibe", "message": "Tell me your vibe first!"}, status_code=400)

        from app.services.vibe_service import match_vibe
        from app.services.radio_service import build_radio_queue

        playlists = svc.get_user_playlists()
        if not playlists:
            return JSONResponse({"error": "no_playlists", "message": "No playlists found. Create some mood playlists on Spotify first!"})

        match = match_vibe(vibe_text, playlists)
        print(f"[VIBE] playlists found: {[p['name'] for p in playlists]}")
        print(f"[VIBE] matched: {[p['name'] for p in match['matched_playlists']]}")
        matched = match["matched_playlists"]
        audio_targets = match["audio_targets"]
        mood_label = match["mood_label"]

        # Gather tracks from matched playlists
        import random
        playlist_uris = []
        for pl in matched:
            playlist_uris.extend(svc.get_playlist_tracks(pl["id"], limit=30))

        if not playlist_uris:
            return JSONResponse({"error": "empty_playlists", "message": "Matched playlists are empty. Add songs to them first!"})

        # Recommendations seeded from playlist tracks
        seed_ids = [uri.split(":")[-1] for uri in playlist_uris[:5]]
        rec_uris = svc.get_recommendations(seed_ids, audio_targets, limit=25)

        # Mix: 2 recs per 1 playlist track
        random.shuffle(playlist_uris)
        queue = []
        pl_i = rec_i = 0
        while len(queue) < 40:
            for _ in range(2):
                if rec_i < len(rec_uris):
                    queue.append(rec_uris[rec_i]); rec_i += 1
            if pl_i < len(playlist_uris):
                queue.append(playlist_uris[pl_i]); pl_i += 1
            if rec_i >= len(rec_uris) and pl_i >= len(playlist_uris):
                break

        # Slot in podcast + news episodes
        radio = build_radio_queue(svc, include_podcasts=True, include_news=True)
        ep_uris = [u for u in radio.get("queue_uris", []) if ":episode:" in u]
        for i, ep in enumerate(ep_uris):
            pos = 6 + i * 8
            queue.insert(min(pos, len(queue)), ep)

        svc.sp.start_playback(uris=queue[:50])

        return JSONResponse({
            "started": True,
            "mood_label": mood_label,
            "matched_playlists": [p["name"] for p in matched],
            "method": match["method"],
            "podcast": radio.get("podcast"),
            "news": radio.get("news"),
        })
    except spotipy.SpotifyException as e:
        return _spotify_error_response(e)


@router.post("/dj-clip")
async def dj_clip(request: Request):
    """Generate a DJ intro clip for the current track transition."""
    svc = _get_service(request)
    if not svc:
        return JSONResponse({"error": "not_logged_in"}, status_code=401)
    try:
        body = await request.json()
        current = body.get("current")
        next_track = body.get("next")
        news = body.get("news")

        from app.services.dj_service import generate_dj_clip
        filename = generate_dj_clip(current, next_track, news)
        if not filename:
            return JSONResponse({"error": "generation_failed", "detail": "generate_dj_clip returned None"}, status_code=500)

        return JSONResponse({"filename": filename, "url": f"/player/dj-audio/{filename}"})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"error": str(e), "type": type(e).__name__}, status_code=500)


@router.get("/dj-audio/{filename}")
async def dj_audio(filename: str):
    """Serve a generated DJ audio clip."""
    if not filename.endswith(".mp3") or "/" in filename or ".." in filename:
        return JSONResponse({"error": "invalid"}, status_code=400)
    tmp_dir = os.path.join(os.path.dirname(__file__), "..", "..", "tmp")
    filepath = os.path.join(tmp_dir, filename)
    if not os.path.isfile(filepath):
        return JSONResponse({"error": "not_found"}, status_code=404)
    return FileResponse(filepath, media_type="audio/mpeg")
