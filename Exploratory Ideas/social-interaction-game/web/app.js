const scenarioSelect = document.getElementById("scenarioSelect");
const proceduralSeed = document.getElementById("proceduralSeed");
const resetScenarioButton = document.getElementById("resetScenario");
const resetProceduralButton = document.getElementById("resetProcedural");
const autoplayButton = document.getElementById("autoplay");
const submitResponseButton = document.getElementById("submitResponse");
const responseInput = document.getElementById("responseInput");
const historyContainer = document.getElementById("history");
const scenarioMeta = document.getElementById("scenarioMeta");
const scoreCard = document.getElementById("scoreCard");
const worldState = document.getElementById("worldState");
const debugRules = document.getElementById("debugRules");

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json();
}

function renderObservation(observation) {
  scenarioMeta.textContent = `${observation.title} · ${observation.relationship_stage}`;
  historyContainer.innerHTML = "";
  for (const item of observation.history || []) {
    const message = document.createElement("article");
    message.className = `message ${item.role}`;
    message.innerHTML = `<span class="role">${item.role}</span><div>${item.text}</div>`;
    historyContainer.appendChild(message);
  }

  worldState.innerHTML = `
    <div class="stat">
      <div class="stat-label">Persona</div>
      <div class="stat-value">${observation.persona_name}</div>
    </div>
    <div class="stat">
      <div class="stat-label">Turn</div>
      <div class="stat-value">${observation.turn_index}/${observation.max_turns}</div>
    </div>
    <div class="stat">
      <div class="stat-label">Summary</div>
      <div class="stat-value">${observation.relationship_summary}</div>
    </div>
    <div class="stat">
      <div class="stat-label">Context</div>
      <div class="stat-value">${observation.visible_context}</div>
    </div>
  `;

  debugRules.textContent = JSON.stringify(observation.debug_rules || {}, null, 2);
}

function renderResult(result) {
  const relationship = result.relationship_state;
  const details = result.details
    .map(
      (detail) => `
        <div class="detail-row ${detail.passed ? "pass" : "fail"}">
          <div class="detail-head">
            <strong>${detail.name}</strong>
            <span>${detail.score.toFixed(2)}</span>
          </div>
          <div>${detail.reason}</div>
        </div>
      `
    )
    .join("");

  scoreCard.classList.remove("empty");
  scoreCard.innerHTML = `
    <div class="score-summary">
      <div class="score-pill">
        <div class="stat-label">Band</div>
        <div class="stat-value">${result.band}</div>
      </div>
      <div class="score-pill">
        <div class="stat-label">Score</div>
        <div class="stat-value">${result.total_score.toFixed(3)}</div>
      </div>
      <div class="score-pill">
        <div class="stat-label">Reward</div>
        <div class="stat-value">${result.reward.toFixed(3)}</div>
      </div>
    </div>
    <div class="detail-list">${details}</div>
    <div class="score-summary" style="margin-top: 16px;">
      <div class="score-pill">
        <div class="stat-label">Trust</div>
        <div class="stat-value">${relationship.trust.toFixed(2)}</div>
      </div>
      <div class="score-pill">
        <div class="stat-label">Closeness</div>
        <div class="stat-value">${relationship.closeness.toFixed(2)}</div>
      </div>
      <div class="score-pill">
        <div class="stat-label">Irritation</div>
        <div class="stat-value">${relationship.irritation.toFixed(2)}</div>
      </div>
    </div>
  `;
}

async function loadScenarios() {
  const payload = await api("/api/scenarios");
  scenarioSelect.innerHTML = payload.scenarios
    .map(
      (scenario) =>
        `<option value="${scenario.scenario_id}">${scenario.title} (${scenario.scenario_id})</option>`
    )
    .join("");
}

async function resetScenario(mode = "hand-authored") {
  const body =
    mode === "procedural"
      ? { procedural_seed: Number(proceduralSeed.value || 0) }
      : { scenario_id: scenarioSelect.value };
  const payload = await api("/api/reset", {
    method: "POST",
    body: JSON.stringify(body),
  });
  renderObservation(payload);
  scoreCard.classList.add("empty");
  scoreCard.textContent = "Play a turn to see verifier output.";
  responseInput.value = "";
}

async function submitResponse() {
  const response = responseInput.value.trim();
  if (!response) return;
  const payload = await api("/api/step", {
    method: "POST",
    body: JSON.stringify({ response }),
  });
  renderResult(payload.result);
  renderObservation(payload.observation);
  responseInput.value = "";
}

async function autoplayTurn() {
  const payload = await api("/api/autoplay", {
    method: "POST",
    body: JSON.stringify({}),
  });
  renderResult(payload.result);
  renderObservation(payload.observation);
}

resetScenarioButton.addEventListener("click", () => resetScenario("hand-authored"));
resetProceduralButton.addEventListener("click", () => resetScenario("procedural"));
submitResponseButton.addEventListener("click", submitResponse);
autoplayButton.addEventListener("click", autoplayTurn);

loadScenarios()
  .then(() => resetScenario("hand-authored"))
  .catch((error) => {
    scoreCard.classList.remove("empty");
    scoreCard.textContent = error.message;
  });
