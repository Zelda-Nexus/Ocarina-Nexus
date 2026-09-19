(function () {
  "use strict";

  const form = document.getElementById("queryForm");
  const input = document.getElementById("sqlInput");
  const runBtn = document.getElementById("runBtn");
  const status = document.getElementById("queryStatus");
  const resultWrap = document.getElementById("resultWrap");
  const catalogTree = document.getElementById("catalogTree");
  const tableDetail = document.getElementById("tableDetail");

  document.querySelectorAll(".chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      input.value = chip.dataset.sql;
      input.focus();
    });
  });

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  function renderResult(data) {
    if (!data.columns.length) {
      resultWrap.innerHTML = '<p class="muted">Requête exécutée, aucune colonne renvoyée.</p>';
      return;
    }
    const head = data.columns.map((c) => `<th>${escapeHtml(c)}</th>`).join("");
    const body = data.rows
      .map((row) => `<tr>${row.map((cell) => `<td>${cell === null ? '<span class="muted">NULL</span>' : escapeHtml(cell)}</td>`).join("")}</tr>`)
      .join("");
    resultWrap.innerHTML = `
      <div class="table-scroll">
        <table class="data-table">
          <thead><tr>${head}</tr></thead>
          <tbody>${body}</tbody>
        </table>
      </div>`;
  }

  async function runQuery(sql) {
    runBtn.disabled = true;
    status.textContent = "Exécution…";
    resultWrap.innerHTML = "";

    try {
      const res = await fetch("/api/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sql }),
      });
      const data = await res.json();

      if (!res.ok) {
        status.textContent = "";
        resultWrap.innerHTML = `<div class="error-box">${escapeHtml(data.detail || "Erreur inconnue.")}</div>`;
        return;
      }

      status.textContent = `${data.row_count} ligne(s)${data.row_count === 500 ? " (plafond atteint)" : ""}`;
      renderResult(data);
    } catch (err) {
      status.textContent = "";
      resultWrap.innerHTML = `<div class="error-box">${escapeHtml(err.message)}</div>`;
    } finally {
      runBtn.disabled = false;
    }
  }

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const sql = input.value.trim();
    if (sql) runQuery(sql);
  });

  // ---- Catalog sidebar ----

  function renderTableDetail(detail) {
    const cols = detail.columns
      .map((c) => {
        const badges = [
          c.primary_key ? '<span class="key-badge pk">PK</span>' : "",
          c.foreign_key ? '<span class="key-badge fk">FK</span>' : "",
        ].join("");
        const fk = c.foreign_key
          ? `<div class="muted">→ ${escapeHtml(c.foreign_key.schema)}.${escapeHtml(c.foreign_key.table)}.${escapeHtml(c.foreign_key.column)}</div>`
          : "";
        return `<tr>
          <td>${badges}${escapeHtml(c.name)}</td>
          <td class="muted">${escapeHtml(c.type)}</td>
          <td class="muted">${c.nullable ? "" : "NOT NULL"}</td>
          <td>${fk}</td>
        </tr>`;
      })
      .join("");

    const refs = detail.referenced_by.length
      ? `<div class="ref-list">Référencée par : ${detail.referenced_by
          .map((r) => `<code>${escapeHtml(r.schema)}.${escapeHtml(r.table)}.${escapeHtml(r.column)}</code>`)
          .join(", ")}</div>`
      : "";

    tableDetail.innerHTML = `
      <div class="table-detail">
        <h3>${escapeHtml(detail.schema)}.${escapeHtml(detail.table)}</h3>
        <table>
          <thead><tr><th>Colonne</th><th>Type</th><th></th><th>Référence</th></tr></thead>
          <tbody>${cols}</tbody>
        </table>
        ${refs}
      </div>`;
    tableDetail.hidden = false;
  }

  async function loadTableDetail(schema, table) {
    tableDetail.innerHTML = '<div class="table-detail"><p class="muted">Chargement…</p></div>';
    tableDetail.hidden = false;
    try {
      const res = await fetch(`/api/tables/${encodeURIComponent(schema)}/${encodeURIComponent(table)}`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Erreur inconnue.");
      renderTableDetail(data);
    } catch (err) {
      tableDetail.innerHTML = `<div class="error-box">${escapeHtml(err.message)}</div>`;
    }
  }

  function renderCatalogTree(bySchema) {
    catalogTree.innerHTML = Object.entries(bySchema)
      .map(([schema, tables]) => {
        if (!tables.length) return "";
        const rows = tables
          .map(
            (t) => `
            <div class="catalog-table-row">
              <button type="button" class="catalog-table-btn" data-schema="${escapeHtml(schema)}" data-table="${escapeHtml(t.name)}" data-action="query">${escapeHtml(t.name)}</button>
              <button type="button" class="catalog-info-btn" data-schema="${escapeHtml(schema)}" data-table="${escapeHtml(t.name)}" data-action="info" aria-expanded="false" title="Colonnes, clés">ⓘ</button>
            </div>`
          )
          .join("");
        return `<div class="catalog-schema">
          <div class="catalog-schema-name">${escapeHtml(schema)}</div>
          ${rows}
        </div>`;
      })
      .join("");

    catalogTree.querySelectorAll(".catalog-table-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const sql = `SELECT * FROM ${btn.dataset.schema}.${btn.dataset.table} LIMIT 50`;
        input.value = sql;
        runQuery(sql);
      });
    });
    catalogTree.querySelectorAll(".catalog-info-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        catalogTree.querySelectorAll(".catalog-info-btn").forEach((b) => b.setAttribute("aria-expanded", "false"));
        btn.setAttribute("aria-expanded", "true");
        loadTableDetail(btn.dataset.schema, btn.dataset.table);
      });
    });
  }

  async function loadCatalog() {
    try {
      const res = await fetch("/api/tables");
      const data = await res.json();
      renderCatalogTree(data);
    } catch (err) {
      catalogTree.innerHTML = `<p class="muted">Catalogue indisponible (${escapeHtml(err.message)}).</p>`;
    }
  }

  loadCatalog();
})();
