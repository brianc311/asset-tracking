function getThemePreference() {
  const stored = document.documentElement.getAttribute('data-user-theme');
  if (stored && stored !== 'system') return stored;
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function applyTheme(theme) {
  const resolved = theme === 'system'
    ? (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
    : theme;
  document.documentElement.setAttribute('data-theme', resolved);
}

function initTheme() {
  const pref = document.documentElement.getAttribute('data-user-theme') || 'system';
  applyTheme(pref);
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
    if ((document.documentElement.getAttribute('data-user-theme') || 'system') === 'system') {
      applyTheme('system');
    }
  });
}

function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme');
  const next = current === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-user-theme', next);
  applyTheme(next);

  const csrf = document.querySelector('[name=csrfmiddlewaretoken]')?.value
    || document.cookie.match(/csrftoken=([^;]+)/)?.[1];
  if (csrf) {
    fetch('/api/theme/', {
      method: 'POST',
      headers: { 'X-CSRFToken': csrf, 'Content-Type': 'application/x-www-form-urlencoded' },
      body: 'theme=' + encodeURIComponent(next),
    }).catch(() => {});
  }
}

/* Custom modal — replaces browser alert/confirm */
const AppModal = {
  overlay: null,
  init() {
    if (document.getElementById('app-modal')) return;
    const html = `
      <div id="app-modal" class="modal-overlay" role="dialog" aria-modal="true">
        <div class="modal-box">
          <h3 class="modal-title" id="modal-title"></h3>
          <p class="modal-body" id="modal-body"></p>
          <div class="modal-actions" id="modal-actions"></div>
        </div>
      </div>`;
    document.body.insertAdjacentHTML('beforeend', html);
    this.overlay = document.getElementById('app-modal');
    this.overlay.addEventListener('click', (e) => {
      if (e.target === this.overlay) this.close();
    });
  },
  alert(title, message) {
    this.init();
    return new Promise((resolve) => {
      document.getElementById('modal-title').textContent = title;
      document.getElementById('modal-body').textContent = message;
      document.getElementById('modal-actions').innerHTML =
        '<button class="btn btn-primary" id="modal-ok">OK</button>';
      document.getElementById('modal-ok').onclick = () => { this.close(); resolve(); };
      this.overlay.classList.add('open');
    });
  },
  confirm(title, message) {
    this.init();
    return new Promise((resolve) => {
      document.getElementById('modal-title').textContent = title;
      document.getElementById('modal-body').textContent = message;
      document.getElementById('modal-actions').innerHTML =
        '<button class="btn btn-secondary" id="modal-cancel">Cancel</button>' +
        '<button class="btn btn-primary" id="modal-confirm">Confirm</button>';
      document.getElementById('modal-cancel').onclick = () => { this.close(); resolve(false); };
      document.getElementById('modal-confirm').onclick = () => { this.close(); resolve(true); };
      this.overlay.classList.add('open');
    });
  },
  close() {
    if (this.overlay) this.overlay.classList.remove('open');
  },
};

document.addEventListener('DOMContentLoaded', initTheme);

/* Bulk selection helpers */
function initBulkSelect(tableId, formId) {
  const table = document.getElementById(tableId);
  const form = document.getElementById(formId);
  if (!table || !form) return;

  const selectAll = table.querySelector('.select-all');
  const checkboxes = table.querySelectorAll('.row-select');
  const idsField = form.querySelector('[name=asset_ids]');

  function updateIds() {
    const ids = [...checkboxes].filter(c => c.checked).map(c => c.value);
    idsField.value = ids.join(',');
    return ids;
  }

  if (selectAll) {
    selectAll.addEventListener('change', () => {
      checkboxes.forEach(c => { c.checked = selectAll.checked; });
      updateIds();
    });
  }
  checkboxes.forEach(c => c.addEventListener('change', updateIds));

  const actionButtons = [
    ...form.querySelectorAll('[data-bulk-action]'),
    ...document.querySelectorAll(`[data-bulk-action][form="${form.id}"]`),
  ];
  actionButtons.forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.preventDefault();
      const ids = updateIds();
      if (!ids.length) {
        await AppModal.alert('No selection', 'Please select at least one item.');
        return;
      }
      const action = btn.dataset.bulkAction;
      const labels = { archive: 'archive', delete: 'permanently delete' };
      const ok = await AppModal.confirm(
        'Confirm action',
        `Are you sure you want to ${labels[action] || action} ${ids.length} item(s)?`
      );
      if (ok) {
        form.querySelector('[name=action]').value = action;
        form.submit();
      }
    });
  });
}
