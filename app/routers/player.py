from __future__ import annotations

import spotipy
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

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
        result = svc.start_radio_from_library()
        return JSONResponse(result)
    except spotipy.SpotifyException as e:
        return _spotify_error_response(e)
