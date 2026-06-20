let fieldScannerInstance = null;
let fieldScannerTarget = null;

function ensureFieldScanModal() {
  if (document.getElementById('field-scan-modal')) return;

  document.body.insertAdjacentHTML('beforeend', `
    <div id="field-scan-modal" class="modal-overlay" role="dialog" aria-modal="true">
      <div class="modal-box" style="max-width:520px">
        <h3 class="modal-title" id="field-scan-title">Scan into field</h3>
        <p class="modal-body" id="field-scan-hint">Point the camera at the barcode for this field.</p>
        <div id="field-scan-reader" style="width:100%;min-height:220px;margin-bottom:1rem"></div>
        <div class="modal-actions">
          <button type="button" class="btn btn-secondary" id="field-scan-cancel">Cancel</button>
        </div>
      </div>
    </div>
  `);

  document.getElementById('field-scan-cancel').addEventListener('click', closeFieldScanner);
  document.getElementById('field-scan-modal').addEventListener('click', (e) => {
    if (e.target.id === 'field-scan-modal') closeFieldScanner();
  });
}

async function stopFieldScanner() {
  if (fieldScannerInstance) {
    try {
      await fieldScannerInstance.stop();
    } catch (_) {}
    try {
      fieldScannerInstance.clear();
    } catch (_) {}
    fieldScannerInstance = null;
  }
}

async function closeFieldScanner() {
  await stopFieldScanner();
  document.getElementById('field-scan-modal')?.classList.remove('open');
  fieldScannerTarget = null;
}

async function openFieldScanner(inputEl, label) {
  if (!inputEl) return;

  if (!window.isSecureContext) {
    await AppModal.alert(
      'HTTPS required',
      'Camera scanning on your phone requires https://. Use run_dev_https.bat locally, or type the value manually.'
    );
    return;
  }

  if (typeof Html5Qrcode === 'undefined') {
    await AppModal.alert('Scanner unavailable', 'Barcode library did not load. Refresh the page and try again.');
    return;
  }

  ensureFieldScanModal();
  fieldScannerTarget = inputEl;
  document.getElementById('field-scan-title').textContent = 'Scan: ' + (label || 'Field');
  document.getElementById('field-scan-modal').classList.add('open');

  await stopFieldScanner();
  fieldScannerInstance = new Html5Qrcode('field-scan-reader');

  try {
    await fieldScannerInstance.start(
      { facingMode: 'environment' },
      { fps: 10, qrbox: { width: 250, height: 250 } },
      async (decodedText) => {
        fieldScannerTarget.value = decodedText.trim();
        fieldScannerTarget.dispatchEvent(new Event('input', { bubbles: true }));
        await closeFieldScanner();
        await AppModal.alert('Scanned', 'Value added to ' + (label || 'field') + '.');
      },
      () => {}
    );
  } catch (err) {
    await closeFieldScanner();
    let msg = err.message || 'Could not access camera.';
    if (msg.includes('NotAllowed') || msg.includes('Permission')) {
      msg = 'Camera permission denied. Allow camera access in browser settings.';
    }
    await AppModal.alert('Camera Error', msg);
  }
}

function initFieldScanners() {
  document.querySelectorAll('[data-scan-target]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const input = document.getElementById(btn.dataset.scanTarget);
      openFieldScanner(input, btn.dataset.scanLabel || 'field');
    });
  });
}

document.addEventListener('DOMContentLoaded', initFieldScanners);
