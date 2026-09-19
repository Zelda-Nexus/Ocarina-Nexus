(function () {
  "use strict";

  const jobList = document.getElementById("jobList");

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  function statusOf(run) {
    if (!run) return { cls: "pending", label: "jamais lancé" };
    if (run.life_cycle_state === "RUNNING" || run.life_cycle_state === "PENDING" || run.life_cycle_state === "QUEUED") {
      return { cls: "running", label: "en cours" };
    }
    if (run.result_state === "SUCCESS") return { cls: "ok", label: "succès" };
    if (run.result_state) return { cls: "fail", label: run.result_state.toLowerCase() };
    return { cls: "pending", label: (run.life_cycle_state || "").toLowerCase() };
  }

  function fmtTime(ms) {
    if (!ms) return "—";
    return new Date(ms).toLocaleString("fr-FR");
  }

  function renderJobRow(job) {
    const st = statusOf(job.latest_run);
    const link = job.latest_run
      ? `<a href="${escapeHtml(job.latest_run.run_page_url)}" target="_blank" rel="noopener">voir sur Databricks ↗</a>`
      : "";
    return `
      <div class="job-row" data-job-id="${job.job_id}">
        <div class="job-info">
          <span class="job-name">${escapeHtml(job.name)}</span>
          <span class="job-meta">${job.latest_run ? "dernier run : " + fmtTime(job.latest_run.start_time) : "aucun run"} ${link}</span>
        </div>
        <div class="job-actions">
          <span class="job-status ${st.cls}">${st.label}</span>
          <button type="button" class="job-run-btn" data-job-id="${job.job_id}">Lancer</button>
        </div>
      </div>`;
  }

  async function runJob(jobId, btn) {
    btn.disabled = true;
    btn.textContent = "Lancement…";
    try {
      const res = await fetch(`/api/jobs/${jobId}/run`, { method: "POST" });
      if (!res.ok) throw new Error((await res.json()).detail || "Erreur inconnue.");
      await load();
    } catch (err) {
      alert("Impossible de lancer le job : " + err.message);
      btn.disabled = false;
      btn.textContent = "Lancer";
    }
  }

  async function load() {
    try {
      const res = await fetch("/api/jobs");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const jobs = await res.json();
      jobList.innerHTML = jobs.map(renderJobRow).join("");
      jobList.querySelectorAll(".job-run-btn").forEach((btn) => {
        btn.addEventListener("click", () => runJob(btn.dataset.jobId, btn));
      });
    } catch (err) {
      jobList.innerHTML = `<div class="error-box">Impossible de charger les pipelines (${escapeHtml(err.message)}).</div>`;
    }
  }

  load();
})();
