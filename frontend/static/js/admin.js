document.addEventListener("DOMContentLoaded", () => {
  // Copy share link
  document.querySelectorAll(".btn-copy-link").forEach((btn) => {
    btn.addEventListener("click", () => {
      const url = btn.dataset.url;
      navigator.clipboard.writeText(url).then(() => {
        const orig = btn.textContent;
        btn.textContent = I18n.t("copied");
        setTimeout(() => (btn.textContent = orig), 2000);
      });
    });
  });

  // Delete document with custom confirmation dialog
  document.querySelectorAll(".btn-delete-doc").forEach((btn) => {
    btn.addEventListener("click", async () => {
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
        btn.closest("tr").remove();
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
      if (e.target.closest("a, button")) return;
      window.location.href = tr.dataset.href;
    });
  });
});
