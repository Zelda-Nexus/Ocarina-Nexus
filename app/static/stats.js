(function () {
  "use strict";

  function fmt(n) {
    return new Intl.NumberFormat("fr-FR").format(n);
  }

  function renderTiles(stats) {
    const tiles = document.querySelectorAll("#tiles .tile");
    const values = [stats.entities, stats.relations, stats.sources, stats.relation_types];
    tiles.forEach((tile, i) => {
      tile.classList.remove("skeleton");
      tile.querySelector(".tile-value").textContent = fmt(values[i]);
    });
  }

  function renderBars(breakdown) {
    const root = document.getElementById("relationBars");
    if (!breakdown.length) {
      root.innerHTML = '<p class="muted">Aucune relation.</p>';
      return;
    }
    const max = Math.max(...breakdown.map((r) => r.count));
    root.innerHTML = breakdown
      .map(
        (r) => `
        <div class="bar-row">
          <span class="bar-label">${escapeHtml(r.relation_type)}</span>
          <span class="bar-track"><span class="bar-fill" style="width:${(r.count / max) * 100}%"></span></span>
          <span class="bar-value">${fmt(r.count)}</span>
        </div>`
      )
      .join("");
  }

  function renderTopEntities(rows) {
    const tbody = document.querySelector("#topEntitiesTable tbody");
    if (!rows.length) {
      tbody.innerHTML = '<tr><td colspan="3" class="muted">Aucune donnée.</td></tr>';
      return;
    }
    tbody.innerHTML = rows
      .map(
        (r) => `
        <tr>
          <td>${escapeHtml(r.title || "")}</td>
          <td class="muted">${escapeHtml((r.entity_types || []).join(", "))}</td>
          <td class="num">${r.pagerank.toFixed(5)}</td>
        </tr>`
      )
      .join("");
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  async function load() {
    try {
      const res = await fetch("/api/stats");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const stats = await res.json();
      renderTiles(stats);
      renderBars(stats.relation_breakdown || []);
      renderTopEntities(stats.top_entities || []);
    } catch (err) {
      document.getElementById("relationBars").innerHTML =
        '<p class="muted">Impossible de charger les statistiques (' + escapeHtml(err.message) + ").</p>";
    }
  }

  load();
})();
