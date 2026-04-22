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

  // Delete document with confirmation
  document.querySelectorAll(".btn-delete-doc").forEach((btn) => {
    btn.addEventListener("click", async () => {
      if (!confirm("Delete this document? This cannot be undone.")) return;
      const docId = btn.dataset.docId;
      const res = await fetch(`/admin/documents/${docId}`, { method: "DELETE" });
      if (res.ok) {
        btn.closest("tr").remove();
      } else {
        alert("Delete failed.");
      }
    });
  });

  // Filter form auto-submit on select change
  document.querySelectorAll(".auto-submit-select").forEach((sel) => {
    sel.addEventListener("change", () => sel.closest("form").submit());
  });
});
