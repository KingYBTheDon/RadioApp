from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.routers import auth, player

app = FastAPI(title="RadioApp")

app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)

app.include_router(auth.router, prefix="/auth")
app.include_router(player.router, prefix="/player")

app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/")
async def root():
    return FileResponse("app/static/index.html")
