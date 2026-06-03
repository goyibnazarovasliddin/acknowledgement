document.addEventListener("DOMContentLoaded", () => {
  // Remove a table row; if it was the last one, reload so the server-rendered
  // empty state appears immediately (no manual refresh).
  function removeRowOrReload(btn) {
    const tr = btn.closest("tr");
    const tbody = tr ? tr.parentElement : null;
    if (tr) tr.remove();
    if (tbody && tbody.querySelectorAll("tr").length === 0) location.reload();
  }

  // Copy share link
  document.querySelectorAll(".btn-copy-link").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const url = btn.dataset.url;
      navigator.clipboard.writeText(url).then(() => {
        const orig = btn.textContent;
        btn.textContent = I18n.t("copied");
        setTimeout(() => (btn.textContent = orig), 2000);
      });
    });
  });

  // Archive document (soft) — Hujjatlar list
  document.querySelectorAll(".btn-archive-doc").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      e.stopPropagation();
      const title = btn.dataset.docTitle || "";
      const ok = await window.customConfirm({
        title: I18n.t("archive_title"),
        message: I18n.t("archive_msg").replace("{title}", title),
        confirmText: I18n.t("admin_archive"),
        cancelText: I18n.t("dialog_no"),
        danger: false,
      });
      if (!ok) return;
      const res = await fetch(`/admin/documents/${btn.dataset.docId}/archive`, { method: "POST" });
      if (res.ok) removeRowOrReload(btn);
      else await window.customAlert({ message: I18n.t("action_failed") });
    });
  });

  // Restore archived document — Arxiv list
  document.querySelectorAll(".btn-restore-doc").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      e.stopPropagation();
      const title = btn.dataset.docTitle || "";
      const ok = await window.customConfirm({
        title: I18n.t("restore_title"),
        message: I18n.t("restore_msg").replace("{title}", title),
        confirmText: I18n.t("admin_restore"),
        cancelText: I18n.t("dialog_no"),
        danger: false,
      });
      if (!ok) return;
      const res = await fetch(`/admin/documents/${btn.dataset.docId}/unarchive`, { method: "POST" });
      if (res.ok) removeRowOrReload(btn);
      else await window.customAlert({ message: I18n.t("action_failed") });
    });
  });

  // Permanently delete (from Arxiv) with custom confirmation dialog
  document.querySelectorAll(".btn-delete-doc").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      e.stopPropagation();
      const title = btn.dataset.docTitle || "";
      const ok = await window.customConfirm({
        title: I18n.t("delete_title"),
        message: I18n.t("delete_msg").replace("{title}", title),
        confirmText: I18n.t("delete_confirm"),
        cancelText: I18n.t("dialog_no"),
        danger: true,
      });
      if (!ok) return;
      const docId = btn.dataset.docId;
      const res = await fetch(`/admin/documents/${docId}`, { method: "DELETE" });
      if (res.ok) {
        removeRowOrReload(btn);
      } else {
        await window.customAlert({ title: I18n.t("delete_title"), message: I18n.t("delete_failed") });
      }
    });
  });

  // Filter form auto-submit on select change
  document.querySelectorAll(".auto-submit-select").forEach((sel) => {
    sel.addEventListener("change", () => sel.closest("form").submit());
  });

  // Full-row navigation (rows with data-href) — ignore clicks on links/buttons
  document.querySelectorAll("tr.row-link[data-href]").forEach((tr) => {
    tr.addEventListener("click", (e) => {
      // Don't navigate when the click landed on any interactive control.
      if (e.target.closest("a, button, .btn, input, select, .select-wrap, svg")) return;
      window.location.href = tr.dataset.href;
    });
  });

  // ---- Custom dropdown (replaces native <select> options styling) ----
  function closeAllSelects() {
    document.querySelectorAll(".select-wrap.cs-open").forEach((w) => w.classList.remove("cs-open"));
  }

  document.querySelectorAll("select.select-custom").forEach((sel) => {
    const wrap = sel.closest(".select-wrap");
    if (!wrap) return;
    const arrow = wrap.querySelector(".select-arrow");
    sel.style.display = "none";
    if (arrow) arrow.style.display = "none";

    const trig = document.createElement("button");
    trig.type = "button";
    trig.className = "cs-trigger";
    trig.innerHTML =
      '<span class="cs-label"></span>' +
      '<svg class="icon cs-caret" viewBox="0 0 24 24"><polyline points="6 9 12 15 18 9"/></svg>';
    const menu = document.createElement("div");
    menu.className = "cs-menu";
    wrap.appendChild(trig);
    wrap.appendChild(menu);

    function build() {
      menu.innerHTML = "";
      Array.from(sel.options).forEach((opt) => {
        const it = document.createElement("div");
        it.className = "cs-option" + (opt.value === sel.value ? " selected" : "");
        it.textContent = opt.textContent.trim();
        it.dataset.value = opt.value;
        it.addEventListener("click", (e) => {
          e.stopPropagation();
          sel.value = opt.value;
          sync();
          closeAllSelects();
          sel.dispatchEvent(new Event("change", { bubbles: true }));
        });
        menu.appendChild(it);
      });
    }
    function sync() {
      const o = sel.options[sel.selectedIndex];
      trig.querySelector(".cs-label").textContent = o ? o.textContent.trim() : "";
      menu.querySelectorAll(".cs-option").forEach((it) =>
        it.classList.toggle("selected", it.dataset.value === sel.value)
      );
    }
    trig.addEventListener("click", (e) => {
      e.stopPropagation();
      const open = wrap.classList.contains("cs-open");
      closeAllSelects();
      if (!open) wrap.classList.add("cs-open");
    });

    build();
    sync();
    wrap._csRefresh = () => { build(); sync(); };
  });

  document.addEventListener("click", closeAllSelects);

  // Re-sync custom dropdown labels after language toggle
  document.querySelectorAll(".lang-toggle").forEach((b) =>
    b.addEventListener("click", () =>
      setTimeout(() => {
        document.querySelectorAll(".select-wrap").forEach((w) => w._csRefresh && w._csRefresh());
      }, 0)
    )
  );
});
