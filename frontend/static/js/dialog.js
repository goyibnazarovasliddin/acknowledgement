/* Reusable custom dialog (confirm / alert) — replaces window.confirm/alert. */
(function () {
  function t(key, fallback) {
    return (typeof I18n !== "undefined" && I18n.t(key) !== key) ? I18n.t(key) : fallback;
  }

  function buildOverlay(inner) {
    const overlay = document.createElement("div");
    overlay.className = "modal-overlay";
    overlay.innerHTML = `<div class="modal-box">${inner}</div>`;
    document.body.appendChild(overlay);
    return overlay;
  }

  const ICON_WARN = '<svg class="icon" viewBox="0 0 24 24"><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>';

  function customConfirm(opts) {
    opts = opts || {};
    const title   = opts.title   || t("dialog_confirm_title", "Tasdiqlang");
    const message = opts.message || "";
    const okText  = opts.confirmText || t("dialog_yes", "Ha");
    const noText  = opts.cancelText  || t("dialog_no", "Bekor qilish");
    const danger  = opts.danger !== false;
    const okClass = danger ? "btn-danger" : "btn-success";

    return new Promise((resolve) => {
      const overlay = buildOverlay(`
        <div class="modal-icon" style="${danger ? "background:#fef2f2;border-color:#fecaca;color:var(--danger);" : ""}">${ICON_WARN}</div>
        <h3 class="modal-title">${title}</h3>
        <p class="modal-msg">${message}</p>
        <div class="modal-actions">
          <button class="btn btn-ghost" data-act="cancel" style="flex:1;">${noText}</button>
          <button class="btn ${okClass}" data-act="ok" style="flex:1;">${okText}</button>
        </div>`);

      function close(val) { overlay.remove(); resolve(val); }
      overlay.querySelector('[data-act="ok"]').onclick = () => close(true);
      overlay.querySelector('[data-act="cancel"]').onclick = () => close(false);
      overlay.onclick = (e) => { if (e.target === overlay) close(false); };
      document.addEventListener("keydown", function esc(e) {
        if (e.key === "Escape") { document.removeEventListener("keydown", esc); close(false); }
      });
    });
  }

  function customAlert(opts) {
    opts = (typeof opts === "string") ? { message: opts } : (opts || {});
    const title   = opts.title   || t("dialog_notice", "Ma'lumot");
    const message = opts.message || "";
    const okText  = opts.confirmText || "OK";
    return new Promise((resolve) => {
      const overlay = buildOverlay(`
        <div class="modal-icon">${ICON_WARN}</div>
        <h3 class="modal-title">${title}</h3>
        <p class="modal-msg">${message}</p>
        <div class="modal-actions">
          <button class="btn btn-primary" data-act="ok" style="flex:1;">${okText}</button>
        </div>`);
      function close() { overlay.remove(); resolve(); }
      overlay.querySelector('[data-act="ok"]').onclick = close;
      overlay.onclick = (e) => { if (e.target === overlay) close(); };
    });
  }

  window.customConfirm = customConfirm;
  window.customAlert = customAlert;
})();
