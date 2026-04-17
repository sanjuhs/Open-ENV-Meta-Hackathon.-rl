#!/usr/bin/env python3
"""Local dataset viewer and editor for Love Game JSONL files."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from love_game.common import DATASETS_DIR, dedupe_rows, list_dataset_files, read_jsonl, write_jsonl


HTML = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Love Game Dataset Viewer</title>
  <style>
    body { font-family: ui-sans-serif, system-ui, sans-serif; margin: 0; background: #f7f4ef; color: #241f1a; }
    .wrap { max-width: 1400px; margin: 0 auto; padding: 20px; }
    h1 { margin: 0 0 8px; }
    .sub { color: #6a5d4d; margin-bottom: 18px; }
    .toolbar, .row { display: grid; gap: 12px; }
    .toolbar { grid-template-columns: 220px 1fr 120px 120px 120px; margin-bottom: 18px; }
    .row { grid-template-columns: 1.2fr 1fr; min-height: 72vh; }
    .panel { background: white; border: 1px solid #e6dccd; border-radius: 18px; box-shadow: 0 10px 30px rgba(55, 35, 0, 0.05); }
    .panel-head { padding: 14px 16px; border-bottom: 1px solid #eee3d4; font-weight: 700; display:flex; justify-content:space-between; }
    .panel-body { padding: 14px 16px; }
    select, input, textarea, button { font: inherit; border-radius: 12px; border: 1px solid #d9cdbd; padding: 10px 12px; }
    button { background: #a84f2c; color: white; border: none; cursor: pointer; }
    button.secondary { background: #efe7dd; color: #3a2a1d; }
    button.warn { background: #7f3127; }
    table { width: 100%; border-collapse: collapse; }
    th, td { text-align: left; padding: 10px 8px; border-bottom: 1px solid #f0e8dc; vertical-align: top; }
    th { font-size: 12px; text-transform: uppercase; letter-spacing: .04em; color: #7a6b59; }
    tr:hover { background: #faf7f2; }
    tr.active { background: #fff0df; }
    .preview { color: #5d5143; font-size: 13px; line-height: 1.35; }
    .cell { color: #5d5143; font-size: 13px; line-height: 1.35; max-width: 320px; white-space: pre-wrap; word-break: break-word; }
    textarea { width: 100%; min-height: 420px; resize: vertical; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
    .meta { color: #7a6b59; font-size: 13px; }
    .actions { display:flex; gap: 10px; flex-wrap: wrap; margin-top: 10px; }
    .status { margin-top: 12px; color: #7a6b59; white-space: pre-wrap; }
    .small { font-size: 12px; color: #7a6b59; }
  </style>
</head>
<body>
  <div class="wrap">
    <h1>Love Game Dataset Viewer</h1>
    <div class="sub">Browse, edit, append, delete, and dedupe the synthetic JSONL datasets.</div>
    <div class="toolbar">
      <select id="dataset"></select>
      <input id="query" placeholder="Search by text, scenario_id, tags, or JSON content">
      <button onclick="loadRows()">Refresh</button>
      <button class="secondary" onclick="dedupeDataset()">Dedupe</button>
      <button class="secondary" onclick="newRow()">New Row</button>
    </div>
    <div class="row">
      <div class="panel">
        <div class="panel-head">
          <span>Rows</span>
          <span id="stats" class="small"></span>
        </div>
        <div class="panel-body">
          <table id="rowsTable">
            <thead>
              <tr><th>#</th><th>Scenario</th><th>Preview</th></tr>
            </thead>
            <tbody></tbody>
          </table>
        </div>
      </div>
      <div class="panel">
        <div class="panel-head">
          <span>Raw JSON Editor</span>
          <span id="rowMeta" class="small"></span>
        </div>
        <div class="panel-body">
          <textarea id="editor"></textarea>
          <div class="actions">
            <button onclick="saveRow()">Save Row</button>
            <button class="secondary" onclick="appendRow()">Append As New</button>
            <button class="warn" onclick="deleteRow()">Delete Selected</button>
          </div>
          <div class="status" id="status"></div>
        </div>
      </div>
    </div>
  </div>
  <script>
    let currentDataset = "";
    let currentIndex = null;
    let currentColumns = [];

    const DATASET_COLUMNS = {
      "sft_train.jsonl": ["scenario_id", "tags", "context", "user_message", "assistant_reply"],
      "dpo_train.jsonl": ["scenario_id", "context", "user_message", "chosen", "rejected", "preference_reason"],
      "rl_train.jsonl": ["scenario_id", "context", "user_message", "candidate_reply", "latent_state", "reward"],
      "reward_model_train.jsonl": ["scenario_id", "prompt", "chosen", "rejected", "preference_reason"],
      "rm_pointwise_train.jsonl": ["scenario_id", "source", "label", "prompt", "response"],
      "rlhf_pairs_train.jsonl": ["scenario_id", "prompt", "preferred_response", "dispreferred_response", "preference_reason"],
      "ppo_prompts.jsonl": ["scenario_id", "tags", "prompt", "reference_reply"],
      "grpo_prompts.jsonl": ["scenario_id", "prompt", "candidate_reply", "expected_goodness", "latent_state", "reward"]
    };

    async function api(path, opts={}) {
      const res = await fetch(path, opts);
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Request failed");
      return data;
    }

    function valuePreview(value) {
      if (value === null || value === undefined) return "";
      if (typeof value === "string") return value.slice(0, 160);
      if (Array.isArray(value)) {
        if (!value.length) return "[]";
        const rendered = value.slice(0, 3).map(item => {
          if (typeof item === "string") return item;
          return JSON.stringify(item);
        }).join(" | ");
        return value.length > 3 ? `${rendered} …` : rendered;
      }
      if (typeof value === "object") return JSON.stringify(value).slice(0, 160);
      return String(value);
    }

    function previewText(row) {
      const keys = ["assistant_reply", "chosen", "candidate_reply", "reference_reply", "response", "prompt", "user_message"];
      for (const key of keys) {
        if (row[key]) return String(row[key]).slice(0, 160);
      }
      return JSON.stringify(row).slice(0, 160);
    }

    function renderTableHeader(columns) {
      const head = document.querySelector("#rowsTable thead");
      const cells = ["<th>#</th>"].concat(columns.map(col => `<th>${col}</th>`));
      head.innerHTML = `<tr>${cells.join("")}</tr>`;
    }

    function renderRowCells(item, columns) {
      const cells = [`<td>${item.index}</td>`];
      for (const col of columns) {
        cells.push(`<td class="cell">${valuePreview(item.row[col])}</td>`);
      }
      return cells.join("");
    }

    async function loadDatasets() {
      const data = await api("/api/datasets");
      const select = document.getElementById("dataset");
      select.innerHTML = "";
      data.datasets.forEach(name => {
        const opt = document.createElement("option");
        opt.value = name;
        opt.textContent = name;
        select.appendChild(opt);
      });
      currentDataset = select.value;
      select.onchange = async () => {
        currentDataset = select.value;
        currentIndex = null;
        await loadRows();
      };
      await loadRows();
    }

    async function loadRows() {
      currentDataset = document.getElementById("dataset").value;
      const query = encodeURIComponent(document.getElementById("query").value);
      const data = await api(`/api/rows?dataset=${encodeURIComponent(currentDataset)}&query=${query}`);
      currentColumns = DATASET_COLUMNS[currentDataset] || data.columns || ["scenario_id", "preview"];
      renderTableHeader(currentColumns);
      const body = document.querySelector("#rowsTable tbody");
      body.innerHTML = "";
      document.getElementById("stats").textContent = `${data.filtered_count} shown / ${data.total_count} total`;
      data.rows.forEach(item => {
        const tr = document.createElement("tr");
        tr.onclick = () => selectRow(item.index, item.row, tr);
        tr.innerHTML = renderRowCells(item, currentColumns);
        body.appendChild(tr);
      });
      document.getElementById("status").textContent = "";
    }

    function selectRow(index, row, tr) {
      document.querySelectorAll("#rowsTable tbody tr").forEach(node => node.classList.remove("active"));
      tr.classList.add("active");
      currentIndex = index;
      document.getElementById("editor").value = JSON.stringify(row, null, 2);
      document.getElementById("rowMeta").textContent = `dataset=${currentDataset} row=${index}`;
    }

    function newRow() {
      currentIndex = null;
      document.querySelectorAll("#rowsTable tbody tr").forEach(node => node.classList.remove("active"));
      document.getElementById("editor").value = JSON.stringify({
        scenario_id: "new_scenario_id",
        user_message: "",
        context: ""
      }, null, 2);
      document.getElementById("rowMeta").textContent = `dataset=${document.getElementById("dataset").value} new row`;
      document.getElementById("status").textContent = "New row mode.";
    }

    async function saveRow() {
      if (currentIndex === null) {
        document.getElementById("status").textContent = "No row selected. Use 'Append As New' or click a row.";
        return;
      }
      const row = JSON.parse(document.getElementById("editor").value);
      const data = await api("/api/save_row", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({dataset: document.getElementById("dataset").value, index: currentIndex, row})
      });
      document.getElementById("status").textContent = data.message;
      await loadRows();
    }

    async function appendRow() {
      const row = JSON.parse(document.getElementById("editor").value);
      const data = await api("/api/add_row", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({dataset: document.getElementById("dataset").value, row})
      });
      document.getElementById("status").textContent = data.message;
      await loadRows();
    }

    async function deleteRow() {
      if (currentIndex === null) {
        document.getElementById("status").textContent = "Select a row first.";
        return;
      }
      const data = await api("/api/delete_row", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({dataset: document.getElementById("dataset").value, index: currentIndex})
      });
      currentIndex = null;
      document.getElementById("editor").value = "";
      document.getElementById("status").textContent = data.message;
      await loadRows();
    }

    async function dedupeDataset() {
      const data = await api("/api/dedupe", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({dataset: document.getElementById("dataset").value})
      });
      document.getElementById("status").textContent = data.message;
      await loadRows();
    }

    loadDatasets();
  </script>
</body>
</html>
"""


def dataset_path(name: str) -> Path:
    path = DATASETS_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {name}")
    return path


class Handler(BaseHTTPRequestHandler):
    def _json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _html(self, text: str) -> None:
        body = text.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        data = self.rfile.read(length) if length else b"{}"
        return json.loads(data.decode("utf-8"))

    def log_message(self, format: str, *args) -> None:
        return

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)
        if parsed.path == "/":
            self._html(HTML)
            return
        if parsed.path == "/api/datasets":
            self._json({"datasets": [path.name for path in list_dataset_files()]})
            return
        if parsed.path == "/api/rows":
            try:
                dataset = query.get("dataset", [""])[0]
                search = query.get("query", [""])[0].strip().lower()
                rows = read_jsonl(dataset_path(dataset))
                indexed = list(enumerate(rows))
                if search:
                    indexed = [
                        (index, row)
                        for index, row in indexed
                        if search in json.dumps(row, ensure_ascii=False).lower()
                    ]
                columns: list[str] = []
                for row in rows[:25]:
                    for key in row.keys():
                        if key not in columns:
                            columns.append(key)
                payload = {
                    "dataset": dataset,
                    "total_count": len(rows),
                    "filtered_count": len(indexed),
                    "columns": columns,
                    "rows": [{"index": index, "row": row} for index, row in indexed[:500]],
                }
                self._json(payload)
            except Exception as exc:
                self._json({"error": str(exc)}, status=400)
            return
        self._json({"error": "Not found"}, status=404)

    def do_POST(self) -> None:
        try:
            payload = self._read_json()
            dataset = payload.get("dataset", "")
            path = dataset_path(dataset)
            rows = read_jsonl(path)

            if self.path == "/api/save_row":
                index = int(payload["index"])
                rows[index] = payload["row"]
                write_jsonl(path, rows)
                self._json({"message": f"Saved row {index} in {dataset}."})
                return

            if self.path == "/api/add_row":
                rows.append(payload["row"])
                write_jsonl(path, rows)
                self._json({"message": f"Appended a new row to {dataset}."})
                return

            if self.path == "/api/delete_row":
                index = int(payload["index"])
                rows.pop(index)
                write_jsonl(path, rows)
                self._json({"message": f"Deleted row {index} from {dataset}."})
                return

            if self.path == "/api/dedupe":
                deduped = dedupe_rows(rows)
                removed = len(rows) - len(deduped)
                write_jsonl(path, deduped)
                self._json({"message": f"Deduped {dataset}. Removed {removed} duplicate rows."})
                return

            self._json({"error": "Not found"}, status=404)
        except Exception as exc:
            self._json({"error": str(exc)}, status=400)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8891)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Love Game dataset viewer running at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
