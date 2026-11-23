function syncSkipMac2() {
  const skip = document.getElementById('id_skip_mac_2');
  const wrap = document.getElementById('mac-2-wrap');
  const input = document.getElementById('id_mac_address_2');
  if (!skip || !wrap) return;
  const on = skip.checked;
  wrap.hidden = on;
  if (on && input) input.value = '';
}

document.addEventListener('DOMContentLoaded', () => {
  const skip = document.getElementById('id_skip_mac_2');
  if (skip) {
    skip.addEventListener('change', syncSkipMac2);
    syncSkipMac2();
  }
});
