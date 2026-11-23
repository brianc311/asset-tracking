let continuousScanner = null;
let lastScanValue = "";
let lastScanAt = 0;

function csrfHeader(token) {
  return {
    "X-CSRFToken": token,
    "Content-Type": "application/x-www-form-urlencoded",
  };
}

function escapeText(value) {
  const node = document.createElement("span");
  node.textContent = value == null ? "" : String(value);
  return node.innerHTML;
}

function appendContinuousRow(row) {
  const table = document.getElementById("continuous-rows");
  if (!table) return;
  document.getElementById("continuous-empty")?.remove();
  const tr = document.createElement("tr");
  tr.dataset.row = String(row.n);
  if (row.duplicate) tr.classList.add("dup-row");
  const status = row.duplicate
    ? `<span class="badge badge-danger">${escapeText(row.duplicate_reason)}</span>`
    : "OK";
  tr.innerHTML =
    `<td>${escapeText(row.n)}</td>` +
    `<td>${escapeText(row.serial || "—")}</td>` +
    `<td>${escapeText(row.mac || "—")}</td>` +
    `<td>${status}</td>`;
  table.querySelector("tbody").appendChild(tr);
  if (row.duplicate) {
    const banner = document.getElementById("continuous-dup-banner");
    if (banner) {
      banner.style.display = "";
      banner.textContent = row.duplicate_reason;
    }
  }
}

async function postScanValue(addUrl, token, value) {
  const body = new URLSearchParams();
  body.set("value", value);
  const response = await fetch(addUrl, {
    method: "POST",
    headers: csrfHeader(token),
    body,
    credentials: "same-origin",
  });
  return response.json();
}

async function submitScanValue(options, value, statusEl) {
  const trimmed = (value || "").trim();
  if (!trimmed) return;
  const now = Date.now();
  if (trimmed === lastScanValue && now - lastScanAt < 1600) return;
  lastScanValue = trimmed;
  lastScanAt = now;
  try {
    const data = await postScanValue(options.addUrl, options.csrfToken, trimmed);
    if (data.ok && data.row) appendContinuousRow(data.row);
    else if (data.error && statusEl) statusEl.textContent = data.error;
  } catch (_) {
    if (statusEl) statusEl.textContent = "Could not save that scan. Try again.";
  }
}

async function stopContinuousScanner() {
  if (!continuousScanner) return;
  try {
    await continuousScanner.stop();
  } catch (_) {}
  try {
    continuousScanner.clear();
  } catch (_) {}
  continuousScanner = null;
}

function initContinuousScan(options) {
  const startBtn = document.getElementById("continuous-scan-start");
  const statusEl = document.getElementById("continuous-scan-status");
  const manualInput = document.getElementById("continuous-manual-value");
  const manualAdd = document.getElementById("continuous-manual-add");
  if (!startBtn) return;

  const addTyped = async () => {
    const value = manualInput ? manualInput.value : "";
    await submitScanValue(options, value, statusEl);
    if (manualInput) {
      manualInput.value = "";
      manualInput.focus();
    }
  };

  manualAdd?.addEventListener("click", addTyped);
  manualInput?.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      addTyped();
    }
  });

  startBtn.addEventListener("click", async () => {
    if (!window.isSecureContext) {
      await AppModal.alert(
        "HTTPS required",
        "Camera scanning needs https://. Use .\\run_dev_https.bat, then try Scan again."
      );
      manualInput?.focus();
      return;
    }
    if (typeof Html5Qrcode === "undefined") {
      await AppModal.alert("Scanner unavailable", "Barcode library did not load. Refresh and try again.");
      return;
    }
    if (continuousScanner) return;

    continuousScanner = new Html5Qrcode("continuous-scan-reader");
    if (statusEl) statusEl.textContent = "Camera on — keep scanning. Press Done when finished.";
    startBtn.disabled = true;
    try {
      await continuousScanner.start(
        { facingMode: "environment" },
        { fps: 8, qrbox: { width: 250, height: 250 } },
        async (decodedText) => {
          await submitScanValue(options, decodedText, statusEl);
        },
        () => {}
      );
    } catch (err) {
      startBtn.disabled = false;
      if (statusEl) statusEl.textContent = "Could not start the camera. Type values below, or allow camera access.";
      await stopContinuousScanner();
      manualInput?.focus();
    }
  });

  document.getElementById("continuous-scan-done")?.addEventListener("click", () => {
    stopContinuousScanner();
  });
}
