import secrets

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, RedirectResponse
from spotipy.oauth2 import SpotifyOAuth

from app.config import settings, SPOTIFY_SCOPES

router = APIRouter()


def _get_oauth() -> SpotifyOAuth:
    return SpotifyOAuth(
        client_id=settings.spotify_client_id,
        client_secret=settings.spotify_client_secret,
        redirect_uri=settings.spotify_redirect_uri,
        scope=SPOTIFY_SCOPES,
        cache_handler=None,
        show_dialog=False,
    )


def get_valid_token(request: Request) -> dict | None:
    """Read the token from session, refresh it if expired, save it back."""
    token_info = request.session.get("token_info")
    if not token_info:
        return None
    sp_oauth = _get_oauth()
    if sp_oauth.is_token_expired(token_info):
        token_info = sp_oauth.refresh_access_token(token_info["refresh_token"])
        request.session["token_info"] = token_info
    return token_info


@router.get("/login")
async def login(request: Request):
    state = secrets.token_urlsafe(16)
    request.session["oauth_state"] = state
    sp_oauth = _get_oauth()
    auth_url = sp_oauth.get_authorize_url(state=state)
    return RedirectResponse(auth_url)


@router.get("/callback")
async def callback(request: Request, code: str = None, state: str = None, error: str = None):
    if error:
        return RedirectResponse("/?error=spotify_denied")

    stored_state = request.session.get("oauth_state")
    if state != stored_state:
        return RedirectResponse("/?error=state_mismatch")

    sp_oauth = _get_oauth()
    token_info = sp_oauth.get_access_token(code, as_dict=True, check_cache=False)
    request.session["token_info"] = token_info
    request.session.pop("oauth_state", None)
    return RedirectResponse("/")


@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/")


@router.get("/status")
async def status(request: Request):
    token_info = get_valid_token(request)
    if not token_info:
        return JSONResponse({"logged_in": False})
    import spotipy
    sp = spotipy.Spotify(auth=token_info["access_token"])
    try:
        user = sp.current_user()
        return JSONResponse({
            "logged_in": True,
            "display_name": user.get("display_name", "Listener"),
            "image": user["images"][0]["url"] if user.get("images") else None,
        })
    except Exception:
        return JSONResponse({"logged_in": False})
