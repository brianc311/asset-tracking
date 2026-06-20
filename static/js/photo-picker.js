function initPhotoPicker(containerSelector) {
  document.querySelectorAll(containerSelector).forEach((container) => {
    const fileInput = container.querySelector('.photo-file-input, input[type="file"]');
    const preview = container.querySelector('.photo-picker-preview');
    const takeBtn = container.querySelector('.photo-take-btn');
    const galleryBtn = container.querySelector('.photo-gallery-btn');
    const clearBtn = container.querySelector('.photo-clear-btn');

    if (!fileInput || !preview) return;

    function showPreview(file) {
      if (!file) return;
      const url = URL.createObjectURL(file);
      preview.innerHTML = `<img src="${url}" alt="Selected photo">`;
      if (clearBtn) clearBtn.style.display = 'inline-flex';
    }

    function openPicker(useCamera) {
      const temp = document.createElement('input');
      temp.type = 'file';
      temp.accept = 'image/*';
      if (useCamera) {
        temp.setAttribute('capture', 'environment');
      }
      temp.addEventListener('change', () => {
        if (!temp.files || !temp.files.length) return;
        const file = temp.files[0];
        try {
          const dt = new DataTransfer();
          dt.items.add(file);
          fileInput.files = dt.files;
        } catch {
          /* Fallback for older browsers */
          fileInput.type = '';
          fileInput.type = 'file';
        }
        showPreview(file);
      });
      temp.click();
    }

    takeBtn?.addEventListener('click', () => openPicker(true));
    galleryBtn?.addEventListener('click', () => openPicker(false));

    clearBtn?.addEventListener('click', () => {
      fileInput.value = '';
      preview.innerHTML = '<span class="photo-picker-placeholder">No photo yet</span>';
      clearBtn.style.display = 'none';
    });

    fileInput.addEventListener('change', () => {
      if (fileInput.files && fileInput.files[0]) {
        showPreview(fileInput.files[0]);
      }
    });

    if (preview.querySelector('img')) {
      clearBtn.style.display = 'inline-flex';
    }
  });
}
