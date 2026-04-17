"""FastAPI application for DocEdit Game V2."""

import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

try:
    from openenv.core.env_server.http_server import create_app
except Exception:
    create_app = None

try:
    from .human_ui import STATIC_DIR, router as human_ui_router
except (ImportError, ModuleNotFoundError):
    from server.human_ui import STATIC_DIR, router as human_ui_router

app = FastAPI(title="DocEdit Game V2")
app.include_router(human_ui_router)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

if create_app is not None:
    try:
        from ..models import DocEditAction, DocEditObservation
        from .doc_edit_game_v2_environment import DocEditGameV2Environment
    except (ImportError, ModuleNotFoundError):
        from models import DocEditAction, DocEditObservation
        from server.doc_edit_game_v2_environment import DocEditGameV2Environment

    openenv_app = create_app(
        DocEditGameV2Environment,
        DocEditAction,
        DocEditObservation,
        env_name="doc_edit_game_v2",
        max_concurrent_envs=4,
    )
    app.mount("/api/openenv", openenv_app)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "openenv_mounted": create_app is not None,
        "default_ui": os.getenv("DOCEDIT_UI_DEFAULT", "modern"),
    }


def main(host: str = "0.0.0.0", port: int = 8000):
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
