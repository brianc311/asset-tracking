function initSiteNameSelect(root) {
  const scope = root || document;
  scope.querySelectorAll('.site-name-fields').forEach((block) => {
    const select = block.querySelector('.site-name-select');
    const newRow = block.querySelector('.new-site-name-row');
    if (!select || !newRow) return;

    function sync() {
      const showNew = select.value === '__new__';
      newRow.style.display = showNew ? 'block' : 'none';
      const newInput = newRow.querySelector('.new-site-name-input');
      if (newInput) {
        newInput.required = showNew;
        if (!showNew) newInput.removeAttribute('required');
      }
    }

    select.addEventListener('change', sync);
    sync();
  });
}

document.addEventListener('DOMContentLoaded', () => initSiteNameSelect());
