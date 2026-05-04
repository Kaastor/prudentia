const state = { workspace: "" };

function el(id) { return document.getElementById(id); }
function linesToArray(value) { return value.split(/\n|;/).map((x) => x.trim()).filter(Boolean); }
function show(id, value) {
  const target = el(id);
  target.textContent = typeof value === "string" ? value : JSON.stringify(value, null, 2);
}
async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail || data));
  return data;
}
function requireWorkspace() {
  if (!state.workspace) throw new Error("Open or create a workspace first.");
  return state.workspace;
}
async function refreshStatus() {
  if (!state.workspace) return;
  const data = await api(`/api/workspace/status?workspace=${encodeURIComponent(state.workspace)}`);
  state.workspace = data.workspace;
  el("workspace-path").value = state.workspace;
  show("status-output", { workspace: data.workspace, status: data.metadata.status, artifacts: data.artifacts });
  const progress = await api(`/api/progress?workspace=${encodeURIComponent(state.workspace)}`);
  const last = (progress.progress_events || []).slice(-6).map((event) => `${event.created_at} ${event.event_kind}: ${event.message}`).join("\n");
  show("progress-output", last || "No progress events yet.");
}

el("create-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const payload = {
      root: el("create-root").value,
      title: el("create-title").value,
      course: el("create-course").value,
      topic: el("create-topic").value,
      difficulty: el("create-difficulty").value,
      estimated_minutes: Number(el("create-minutes").value || 45),
      learning_objectives: linesToArray(el("create-objectives").value),
      constraints: linesToArray(el("create-constraints").value),
    };
    const data = await api("/api/workspaces", { method: "POST", body: JSON.stringify(payload) });
    state.workspace = data.workspace;
    await refreshStatus();
  } catch (error) { show("status-output", String(error)); }
});

el("open-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const data = await api("/api/workspace/open", { method: "POST", body: JSON.stringify({ path: el("workspace-path").value }) });
    state.workspace = data.workspace;
    await refreshStatus();
  } catch (error) { show("status-output", String(error)); }
});

el("doctor-button").addEventListener("click", async () => {
  try { show("doctor-output", await api("/api/doctor")); }
  catch (error) { show("doctor-output", String(error)); }
});

document.querySelectorAll("[data-generate]").forEach((button) => {
  button.addEventListener("click", async () => {
    try {
      const result = await api("/api/generate", {
        method: "POST",
        body: JSON.stringify({
          workspace: requireWorkspace(),
          step: button.dataset.generate,
          use_codex: el("use-codex").checked,
          allow_native_execution: el("allow-native").checked,
        }),
      });
      show("context-output", result);
      await refreshStatus();
    } catch (error) { show("context-output", String(error)); }
  });
});

el("context-button").addEventListener("click", async () => {
  try {
    const task = el("context-task").value;
    const data = await api(`/api/context?workspace=${encodeURIComponent(requireWorkspace())}&task_kind=${encodeURIComponent(task)}`);
    show("context-output", data);
  } catch (error) { show("context-output", String(error)); }
});

document.querySelectorAll("[data-artifact]").forEach((button) => {
  button.addEventListener("click", async () => {
    try {
      const data = await api(`/api/artifact?workspace=${encodeURIComponent(requireWorkspace())}&path=${encodeURIComponent(button.dataset.artifact)}`);
      show("artifact-output", data.content || "File is missing.");
    } catch (error) { show("artifact-output", String(error)); }
  });
});

document.querySelectorAll("[data-approve]").forEach((button) => {
  button.addEventListener("click", async () => {
    try {
      const data = await api("/api/approve", { method: "POST", body: JSON.stringify({ workspace: requireWorkspace(), artifact: button.dataset.approve }) });
      show("status-output", data);
      await refreshStatus();
    } catch (error) { show("status-output", String(error)); }
  });
});

el("validate-button").addEventListener("click", async () => {
  try {
    const data = await api("/api/validate", { method: "POST", body: JSON.stringify({ workspace: requireWorkspace(), allow_native_execution: el("allow-native").checked }) });
    show("validation-output", data);
    await refreshStatus();
  } catch (error) { show("validation-output", String(error)); }
});

el("simulate-button").addEventListener("click", async () => {
  try {
    const data = await api("/api/simulate", { method: "POST", body: JSON.stringify({ workspace: requireWorkspace(), allow_native_execution: el("allow-native").checked }) });
    show("validation-output", data);
    await refreshStatus();
  } catch (error) { show("validation-output", String(error)); }
});

el("report-button").addEventListener("click", async () => {
  try {
    const data = await api("/api/report", { method: "POST", body: JSON.stringify({ workspace: requireWorkspace() }) });
    show("validation-output", data);
    await refreshStatus();
  } catch (error) { show("validation-output", String(error)); }
});

document.querySelectorAll("[data-export]").forEach((button) => {
  button.addEventListener("click", async () => {
    try {
      const data = await api(`/api/export/${button.dataset.export}`, { method: "POST", body: JSON.stringify({ workspace: requireWorkspace() }) });
      show("export-output", data);
      await refreshStatus();
    } catch (error) { show("export-output", String(error)); }
  });
});

api("/api/health").then((health) => {
  if (health.preselected_workspace) {
    state.workspace = health.preselected_workspace;
    el("workspace-path").value = state.workspace;
    refreshStatus().catch((error) => show("status-output", String(error)));
  }
});
