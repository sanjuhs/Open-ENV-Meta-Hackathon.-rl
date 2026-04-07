"""FastAPI application for DocEdit Game V2."""

try:
    from openenv.core.env_server.http_server import create_app
except Exception as e:
    raise ImportError("openenv is required. Install with: uv sync") from e

try:
    from ..models import DocEditAction, DocEditObservation
    from .doc_edit_game_v2_environment import DocEditGameV2Environment
except (ImportError, ModuleNotFoundError):
    from models import DocEditAction, DocEditObservation
    from server.doc_edit_game_v2_environment import DocEditGameV2Environment

app = create_app(
    DocEditGameV2Environment,
    DocEditAction,
    DocEditObservation,
    env_name="doc_edit_game_v2",
    max_concurrent_envs=4,
)


def main(host: str = "0.0.0.0", port: int = 8000):
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
