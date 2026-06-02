(function () {
  const cfg = window.VIEWER_CONFIG;
  if (!cfg) return;

  const IS_PDF = cfg.mimeType === "application/pdf";

  let secondsLeft  = cfg.minSeconds;
  let timerDone    = false;
  let scrollDone   = !IS_PDF;
  let pdfDoc       = null;
  let totalPages   = 0;
  let cssScale     = 1.6;          // visible scale — user changes this with Ctrl+scroll
  const DPR        = window.devicePixelRatio || 1;  // for crisp rendering
  const seenPages  = new Set();
  let renderLocked = false;

  let timerEl, scrollBarEl, scrollPctEl, ackBtn, ackModal, confirmAckBtn, cancelAckBtn;

  // ---------------------------------------------------------------------------
  // Timer
  // ---------------------------------------------------------------------------
  function startTimer() {
    const iv = setInterval(() => {
      secondsLeft = Math.max(0, secondsLeft - 1);
      if (timerEl) {
        const lbl = typeof I18n !== "undefined" ? I18n.t("viewer_sec") : "soniya";
        timerEl.innerHTML = `${secondsLeft} <span style="font-size:.72rem;font-weight:400;color:var(--gray-600);">${lbl}</span>`;
      }
      if (secondsLeft === 0) { timerDone = true; clearInterval(iv); checkUnlock(); }
    }, 1000);
  }

  // ---------------------------------------------------------------------------
  // Progress
  // ---------------------------------------------------------------------------
  function markScrollProgress(pct) {
    pct = Math.min(100, pct);
    if (scrollBarEl) scrollBarEl.style.width = pct.toFixed(1) + "%";
    if (scrollPctEl) scrollPctEl.textContent = pct.toFixed(0) + "%";
    if (pct >= cfg.scrollThreshold * 100) { scrollDone = true; checkUnlock(); }
  }

  function checkUnlock() {
    if (timerDone && scrollDone && ackBtn) {
      ackBtn.disabled = false;
      ackBtn.classList.remove("btn-disabled");
    }
  }

  // ---------------------------------------------------------------------------
  // PDF rendering — high-DPI aware
  // ---------------------------------------------------------------------------
  async function renderAllPages() {
    if (renderLocked) return;
    renderLocked = true;

    const container = document.getElementById("pdf-container");
    container.innerHTML = "";
    seenPages.clear();
    markScrollProgress(0);

    for (let n = 1; n <= totalPages; n++) {
      await renderPage(n, container);
    }

    setupIntersectionObserver();
    renderLocked = false;
  }

  async function renderPage(pageNum, container) {
    const page = await pdfDoc.getPage(pageNum);

    // Render at cssScale * DPR for crisp pixels on retina / high-DPI screens
    const renderScale = cssScale * DPR;
    const viewport    = page.getViewport({ scale: renderScale });

    const wrapper        = document.createElement("div");
    wrapper.className    = "pdf-page-wrapper";
    wrapper.dataset.pageNum = pageNum;
    // CSS size = physical canvas size / DPR → matches cssScale visually
    wrapper.style.width  = (viewport.width  / DPR) + "px";

    const canvas         = document.createElement("canvas");
    canvas.width         = viewport.width;
    canvas.height        = viewport.height;
    canvas.style.width   = "100%";
    canvas.style.display = "block";

    wrapper.appendChild(canvas);
    container.appendChild(wrapper);

    await page.render({ canvasContext: canvas.getContext("2d"), viewport }).promise;
  }

  function setupIntersectionObserver() {
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            seenPages.add(parseInt(e.target.dataset.pageNum, 10));
            markScrollProgress((seenPages.size / totalPages) * 100);
          }
        });
      },
      { threshold: 0.2 }
    );
    document.querySelectorAll(".pdf-page-wrapper").forEach((el) => io.observe(el));
  }

  async function initPdfViewer() {
    const lib = window["pdfjs-dist/build/pdf"];
    lib.GlobalWorkerOptions.workerSrc =
      "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js";

    pdfDoc     = await lib.getDocument(`/d/${cfg.token}/file`).promise;
    totalPages = pdfDoc.numPages;
    await renderAllPages();
  }

  // ---------------------------------------------------------------------------
  // Ctrl+scroll zoom
  //   cursor over PDF container → zoom PDF (preventDefault, no browser zoom)
  //   cursor outside PDF        → return without preventDefault → browser zoom
  // ---------------------------------------------------------------------------
  function initZoom() {
    const scroller = document.getElementById("doc-scroller");
    const pdfWrap  = document.getElementById("pdf-container");
    if (!scroller || !pdfWrap) return;

    let pendingZoom = null;

    // Must be non-passive to allow preventDefault when over PDF
    scroller.addEventListener("wheel", (e) => {
      if (!e.ctrlKey) return;

      // Use cursor coordinates vs bounding rect — reliable regardless of DOM nesting
      const r = pdfWrap.getBoundingClientRect();
      const overPdf = e.clientX >= r.left && e.clientX <= r.right &&
                      e.clientY >= r.top  && e.clientY <= r.bottom;

      if (!overPdf) return; // let browser handle Ctrl+scroll as page zoom

      e.preventDefault();

      const delta = e.deltaY < 0 ? 0.15 : -0.15;
      cssScale = Math.min(5, Math.max(0.4, cssScale + delta));

      clearTimeout(pendingZoom);
      pendingZoom = setTimeout(async () => {
        await renderAllPages();
      }, 160);

    }, { passive: false });
  }

  // ---------------------------------------------------------------------------
  // Non-PDF scroll tracking
  // ---------------------------------------------------------------------------
  function initScrollTracking() {
    const sc = document.getElementById("doc-scroller");
    if (!sc) return;
    sc.addEventListener("scroll", () => {
      const { scrollTop, scrollHeight, clientHeight } = sc;
      if (scrollHeight <= clientHeight) { markScrollProgress(100); return; }
      markScrollProgress(((scrollTop + clientHeight) / scrollHeight) * 100);
    });
  }

  // ---------------------------------------------------------------------------
  // Acknowledge
  // ---------------------------------------------------------------------------
  function initAckFlow() {
    ackBtn.addEventListener("click", () => {
      if (!ackBtn.disabled) ackModal.classList.remove("hidden");
    });
    cancelAckBtn.addEventListener("click", () => ackModal.classList.add("hidden"));

    confirmAckBtn.addEventListener("click", () => {
      confirmAckBtn.disabled = true;
      // Full-page POST navigation so the final page loads normally and i18n
      // applies the user's selected language (document.write would skip it).
      const form = document.createElement("form");
      form.method = "POST";
      form.action = `/d/${cfg.token}/acknowledge`;
      const inp = document.createElement("input");
      inp.type = "hidden";
      inp.name = "attempt_id";
      inp.value = cfg.attemptId;
      form.appendChild(inp);
      document.body.appendChild(form);
      form.submit();
    });

    history.pushState(null, "", location.href);
    window.addEventListener("popstate", () => history.pushState(null, "", location.href));
  }

  // ---------------------------------------------------------------------------
  // Boot
  // ---------------------------------------------------------------------------
  document.addEventListener("DOMContentLoaded", async () => {
    timerEl       = document.getElementById("timer-countdown");
    scrollBarEl   = document.getElementById("scroll-bar");
    scrollPctEl   = document.getElementById("scroll-pct");
    ackBtn        = document.getElementById("btn-acknowledge");
    ackModal      = document.getElementById("ack-modal");
    confirmAckBtn = document.getElementById("btn-confirm-ack");
    cancelAckBtn  = document.getElementById("btn-cancel-ack");

    ackBtn.disabled = true;
    startTimer();

    if (IS_PDF) {
      await initPdfViewer();
      initZoom();
    } else {
      initScrollTracking();
      markScrollProgress(0);
    }

    initAckFlow();
  });
})();
