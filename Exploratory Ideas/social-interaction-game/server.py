from __future__ import annotations

import argparse
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from engine import SocialInteractionGame


GAME = SocialInteractionGame()
STATIC_DIR = Path(__file__).with_name("web")


def _json_response(handler: BaseHTTPRequestHandler, payload: dict, status: int = 200) -> None:
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _read_json(handler: BaseHTTPRequestHandler) -> dict:
    length = int(handler.headers.get("Content-Length", "0"))
    raw = handler.rfile.read(length) if length > 0 else b"{}"
    if not raw:
        return {}
    return json.loads(raw.decode("utf-8"))


def _observation_payload() -> dict:
    if not GAME.scenario:
        return {}
    payload = GAME.observation()
    payload["debug_rules"] = GAME.secret_rules()
    return payload


class SocialGameHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/scenarios":
            scenarios = [
                {
                    "scenario_id": scenario.scenario_id,
                    "title": scenario.title,
                    "description": scenario.description,
                }
                for scenario in GAME.available_scenarios().values()
            ]
            return _json_response(self, {"scenarios": scenarios})

        if parsed.path == "/api/state":
            return _json_response(self, _observation_payload())

        return self._serve_static(parsed.path)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        data = _read_json(self)

        if parsed.path == "/api/reset":
            scenario_id = data.get("scenario_id")
            procedural_seed = int(data.get("procedural_seed", 0))
            payload = GAME.reset(scenario_id=scenario_id, seed=procedural_seed)
            payload["debug_rules"] = GAME.secret_rules()
            return _json_response(self, payload)

        if parsed.path == "/api/step":
            if not GAME.scenario:
                GAME.reset("job-loss-support")
            response = data.get("response", "")
            result = GAME.step(response)
            payload = {
                "result": {
                    "assistant_response": result.assistant_response,
                    "total_score": result.total_score,
                    "reward": result.reward,
                    "details": [detail.__dict__ for detail in result.details],
                    "done": result.done,
                    "next_user_message": result.next_user_message,
                    "band": result.band,
                    "relationship_summary": result.relationship_summary,
                    "relationship_state": result.relationship_state.__dict__,
                    "metadata": result.metadata,
                },
                "observation": _observation_payload(),
            }
            return _json_response(self, payload)

        if parsed.path == "/api/autoplay":
            if not GAME.scenario:
                GAME.reset("job-loss-support")
            result = GAME.autoplay_step()
            payload = {
                "result": {
                    "assistant_response": result.assistant_response,
                    "total_score": result.total_score,
                    "reward": result.reward,
                    "details": [detail.__dict__ for detail in result.details],
                    "done": result.done,
                    "next_user_message": result.next_user_message,
                    "band": result.band,
                    "relationship_summary": result.relationship_summary,
                    "relationship_state": result.relationship_state.__dict__,
                    "metadata": result.metadata,
                },
                "observation": _observation_payload(),
            }
            return _json_response(self, payload)

        return _json_response(self, {"error": "Not found"}, status=HTTPStatus.NOT_FOUND)

    def log_message(self, format: str, *args) -> None:
        return

    def _serve_static(self, path: str) -> None:
        relative = "index.html" if path in {"/", ""} else path.lstrip("/")
        target = (STATIC_DIR / relative).resolve()
        if not str(target).startswith(str(STATIC_DIR.resolve())) or not target.exists():
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return

        if target.suffix == ".html":
            content_type = "text/html; charset=utf-8"
        elif target.suffix == ".css":
            content_type = "text/css; charset=utf-8"
        elif target.suffix == ".js":
            content_type = "application/javascript; charset=utf-8"
        else:
            content_type = "text/plain; charset=utf-8"

        body = target.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the social interaction game web UI.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    GAME.reset("job-loss-support")
    server = ThreadingHTTPServer((args.host, args.port), SocialGameHandler)
    print(f"Serving social interaction game at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
