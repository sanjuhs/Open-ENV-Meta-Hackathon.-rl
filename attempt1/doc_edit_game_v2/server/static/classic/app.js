const modelToolExamples = {
  replace: { target: "recieve", content: "receive" },
  regex_replace: { pattern: "Acme\\s+Corp", replacement: "Vertex Partners" },
  insert: { position: 4, content: "Inserted paragraph text." },
  delete: { target: "This line does not belong" },
  move: { target: "Important Notice", position: 5 },
  format_text: { target: "Agreement", format: "bold" },
  highlight: { target: "Section 3.2", color: "yellow" },
  set_alignment: { line_index: 3, alignment: "center" },
  set_spacing: { line_index: 3, spacing_after: "24" },
  clean_junk_chars: {},
  merge_runs: { line_index: 12 },
  fix_encoding: { target: "â€\"", replacement: "—" },
  add_redline: { target: "Acme Corp", new_text: "Vertex Partners", author: "Reviewer" },
  accept_change: { change_text: "Vertex Partners" },
  reject_change: { change_text: "Acme Corp" },
  add_comment: { target: "Section 3.2", comment_text: "Check this clause", author: "Reviewer" },
  scroll_to: { chunk: 1 },
  search_forward: { query: "agreement" },
  search_backward: { query: "agreement" },
  get_overview: {},
};

const state = {
  sessionId: null,
  current: null,
};

const els = {
  seedInput: document.getElementById("seedInput"),
  corruptionSeedInput: document.getElementById("corruptionSeedInput"),
  difficultySelect: document.getElementById("difficultySelect"),
  domainSelect: document.getElementById("domainSelect"),
  loadSeedButton: document.getElementById("loadSeedButton"),
  reloadExactSeedButton: document.getElementById("reloadExactSeedButton"),
  rerollCorruptionButton: document.getElementById("rerollCorruptionButton"),
  scenarioExposition: document.getElementById("scenarioExposition"),
  instructionText: document.getElementById("instructionText"),
  sessionId: document.getElementById("sessionId"),
  docSeed: document.getElementById("docSeed"),
  corruptionSeedValue: document.getElementById("corruptionSeedValue"),
  difficultyValue: document.getElementById("difficultyValue"),
  domainValue: document.getElementById("domainValue"),
  docTypeValue: document.getElementById("docTypeValue"),
  corruptionValue: document.getElementById("corruptionValue"),
  sourceDocument: document.getElementById("sourceDocument"),
  humanDocument: document.getElementById("humanDocument"),
  submitHumanButton: document.getElementById("submitHumanButton"),
  humanLiveSimilarity: document.getElementById("humanLiveSimilarity"),
  humanCompositeScore: document.getElementById("humanCompositeScore"),
  humanCollateral: document.getElementById("humanCollateral"),
  modelToolSelect: document.getElementById("modelToolSelect"),
  modelParams: document.getElementById("modelParams"),
  applyModelActionButton: document.getElementById("applyModelActionButton"),
  submitModelButton: document.getElementById("submitModelButton"),
  modelDocument: document.getElementById("modelDocument"),
  modelSimilarity: document.getElementById("modelSimilarity"),
  modelReward: document.getElementById("modelReward"),
  modelStepsRemaining: document.getElementById("modelStepsRemaining"),
  modelCompositeScore: document.getElementById("modelCompositeScore"),
  modelObservation: document.getElementById("modelObservation"),
  modelActivity: document.getElementById("modelActivity"),
  runModelMode: document.getElementById("runModelMode"),
  runModelButton: document.getElementById("runModelButton"),
  syncModelButton: document.getElementById("syncModelButton"),
};

function setButtonState(button, disabled, label) {
  button.disabled = disabled;
  if (label) {
    button.dataset.originalText = button.dataset.originalText || button.textContent;
    button.textContent = label;
  } else if (button.dataset.originalText) {
    button.textContent = button.dataset.originalText;
  }
}

function formatScore(value) {
  if (value === null || value === undefined) return "-";
  return Number(value).toFixed(4);
}

function randomSeed() {
  return Math.floor(Math.random() * 999_999_999) + 1;
}

function populateToolSelect() {
  Object.keys(modelToolExamples).forEach((tool) => {
    const option = document.createElement("option");
    option.value = tool;
    option.textContent = tool;
    els.modelToolSelect.appendChild(option);
  });
  els.modelToolSelect.value = "replace";
  applyToolTemplate();
}

function applyToolTemplate() {
  const tool = els.modelToolSelect.value;
  els.modelParams.value = JSON.stringify(modelToolExamples[tool] || {}, null, 2);
}

function renderHumanScores(current) {
  els.humanLiveSimilarity.textContent = formatScore(current.human_similarity_live);
  els.humanCompositeScore.textContent = current.human_result
    ? formatScore(current.human_result.composite_score)
    : "-";
  els.humanCollateral.textContent = current.human_result
    ? formatScore(current.human_result.collateral_damage)
    : "-";
}

function renderModel(current) {
  const obs = current.model_observation;
  els.modelDocument.value = obs.current_document || "";
  els.modelSimilarity.textContent = formatScore(obs.similarity);
  els.modelReward.textContent = formatScore(obs.reward);
  els.modelStepsRemaining.textContent = `${obs.steps_remaining}`;
  els.modelCompositeScore.textContent = current.model_result
    ? formatScore(current.model_result.composite_score)
    : "-";
  els.modelObservation.textContent = JSON.stringify(
    {
      instruction: obs.edit_instruction,
      chunk_index: obs.chunk_index,
      total_chunks: obs.total_chunks,
      overview: obs.document_overview,
      last_tool_success: obs.last_tool_success,
      chunk: obs.document_chunk,
    },
    null,
    2
  );
  els.modelActivity.textContent = JSON.stringify(current.model_activity || [], null, 2);
}

function renderGame(payload) {
  state.current = payload;
  state.sessionId = payload.session_id;

  els.seedInput.value = payload.doc_seed;
  els.corruptionSeedInput.value = payload.corruption_seed;
  els.scenarioExposition.textContent = payload.scenario_exposition;
  els.instructionText.textContent = payload.instruction;
  els.sessionId.textContent = payload.session_id;
  els.docSeed.textContent = payload.doc_seed;
  els.corruptionSeedValue.textContent = payload.corruption_seed;
  els.difficultyValue.textContent = `${payload.difficulty} · ${payload.difficulty_name}`;
  els.domainValue.textContent = payload.domain;
  els.docTypeValue.textContent = payload.doc_type;
  els.corruptionValue.textContent = `${payload.corruption_count} · ${payload.corruption_types.join(", ")}`;
  els.sourceDocument.value = payload.source_document;
  els.humanDocument.value = payload.human_document;

  renderHumanScores(payload);
  renderModel(payload);
}

async function postJson(url, body) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || `Request failed: ${response.status}`);
  }
  return response.json();
}

async function loadGame(mode = "random") {
  setButtonState(els.loadSeedButton, true, "Loading...");
  setButtonState(els.reloadExactSeedButton, true, "Loading...");
  setButtonState(els.rerollCorruptionButton, true, "Loading...");
  try {
    const seedValue = els.seedInput.value.trim();
    const corruptionSeedValue = els.corruptionSeedInput.value.trim();
    const useCurrentSeed = mode === "exact";
    const rerollCorruption = mode === "reroll-corruption";
    const payload = {
      seed: (useCurrentSeed || rerollCorruption) && seedValue ? Number(seedValue) : null,
      corruption_seed: useCurrentSeed
        ? (corruptionSeedValue ? Number(corruptionSeedValue) : null)
        : rerollCorruption
          ? randomSeed()
          : null,
      difficulty: Number(els.difficultySelect.value),
      domain: els.domainSelect.value,
    };
    const data = await postJson("/api/game/new", payload);
    renderGame(data);
  } catch (error) {
    alert(`Could not load a game.\n\n${error.message}`);
  } finally {
    setButtonState(els.loadSeedButton, false);
    setButtonState(els.reloadExactSeedButton, false);
    setButtonState(els.rerollCorruptionButton, false);
  }
}

async function submitHumanDraft() {
  if (!state.sessionId) return;
  setButtonState(els.submitHumanButton, true, "Scoring...");
  try {
    const data = await postJson(`/api/game/${state.sessionId}/submit-human`, {
      edited_document: els.humanDocument.value,
    });
    state.current.human_document = els.humanDocument.value;
    state.current.human_result = data.result;
    state.current.human_similarity_live = data.live_similarity;
    renderHumanScores(state.current);
  } catch (error) {
    alert(`Could not submit human draft.\n\n${error.message}`);
  } finally {
    setButtonState(els.submitHumanButton, false);
  }
}

async function syncModelDraft(force = false) {
  if (!state.sessionId) return;
  if (!force && state.current?.model_observation?.current_document === els.modelDocument.value) {
    return;
  }
  const data = await postJson(`/api/game/${state.sessionId}/model-draft`, {
    edited_document: els.modelDocument.value,
  });
  state.current.model_observation = data.observation;
  state.current.model_result = data.result;
  state.current.model_activity = data.activity || [];
  renderModel(state.current);
}

async function applyModelTool() {
  if (!state.sessionId) return;
  setButtonState(els.applyModelActionButton, true, "Applying...");
  try {
    await syncModelDraft(false);
    const params = JSON.parse(els.modelParams.value || "{}");
    const data = await postJson(`/api/game/${state.sessionId}/model-step`, {
      tool: els.modelToolSelect.value,
      params,
    });
    state.current.model_observation = data.observation;
    state.current.model_result = data.result;
    state.current.model_activity = data.activity || [];
    renderModel(state.current);
  } catch (error) {
    alert(`Could not apply model tool.\n\n${error.message}`);
  } finally {
    setButtonState(els.applyModelActionButton, false);
  }
}

async function runModel() {
  if (!state.sessionId) return;
  setButtonState(els.runModelButton, true, "Running...");
  try {
    await syncModelDraft(false);
    const data = await postJson(`/api/game/${state.sessionId}/run-model`, {
      mode: els.runModelMode.value,
      max_actions: 8,
    });
    state.current.model_observation = data.observation;
    state.current.model_result = data.result;
    state.current.model_activity = data.activity || [];
    renderModel(state.current);
  } catch (error) {
    alert(`Could not run model lane.\n\n${error.message}`);
  } finally {
    setButtonState(els.runModelButton, false);
  }
}

async function submitModelDraft() {
  if (!state.sessionId) return;
  setButtonState(els.submitModelButton, true, "Scoring...");
  try {
    await syncModelDraft(false);
    const data = await postJson(`/api/game/${state.sessionId}/submit-model`, {});
    state.current.model_result = data.result;
    state.current.model_observation = data.observation;
    state.current.model_activity = data.activity || [];
    renderModel(state.current);
  } catch (error) {
    alert(`Could not submit model draft.\n\n${error.message}`);
  } finally {
    setButtonState(els.submitModelButton, false);
  }
}

els.loadSeedButton.addEventListener("click", () => loadGame("random"));
els.reloadExactSeedButton.addEventListener("click", () => loadGame("exact"));
els.rerollCorruptionButton.addEventListener("click", () => loadGame("reroll-corruption"));
els.submitHumanButton.addEventListener("click", submitHumanDraft);
els.applyModelActionButton.addEventListener("click", applyModelTool);
els.submitModelButton.addEventListener("click", submitModelDraft);
els.runModelButton.addEventListener("click", runModel);
els.syncModelButton.addEventListener("click", async () => {
  setButtonState(els.syncModelButton, true, "Syncing...");
  try {
    await syncModelDraft(true);
  } catch (error) {
    alert(`Could not sync the model draft.\n\n${error.message}`);
  } finally {
    setButtonState(els.syncModelButton, false);
  }
});
els.modelToolSelect.addEventListener("change", applyToolTemplate);

populateToolSelect();
loadGame("random");
