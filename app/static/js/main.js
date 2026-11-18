/**
 * LocalBizMart - Vanilla JavaScript Helpers
 */

document.addEventListener('DOMContentLoaded', function () {
  // 1. Auto-dismiss flash alerts after 6 seconds (or click close)
  const alerts = document.querySelectorAll('.alert');
  alerts.forEach(function (alert) {
    const closeBtn = alert.querySelector('.alert-close');
    if (closeBtn) {
      closeBtn.addEventListener('click', function () {
        alert.style.transition = 'opacity 0.3s ease';
        alert.style.opacity = '0';
        setTimeout(() => alert.remove(), 300);
      });
    }

    setTimeout(function () {
      if (alert.parentElement) {
        alert.style.transition = 'opacity 0.5s ease';
        alert.style.opacity = '0';
        setTimeout(() => alert.remove(), 500);
      }
    }, 6000);
  });

  // 2. Setup image preview for file upload inputs
  const imageInputs = document.querySelectorAll('input[type="file"][accept*="image"]');
  imageInputs.forEach(function (input) {
    input.addEventListener('change', function (e) {
      const file = e.target.files[0];
      if (file) {
        if (file.size > 2 * 1024 * 1024) {
          alert('Warning: File size exceeds 2 MB. Please choose a smaller image.');
          input.value = '';
          return;
        }

        const previewContainer = document.getElementById(input.dataset.previewTarget || 'imagePreview');
        if (previewContainer) {
          const reader = new FileReader();
          reader.onload = function (event) {
            previewContainer.src = event.target.result;
            previewContainer.style.display = 'block';
          };
          reader.readAsDataURL(file);
        }
      }
    });
  });

  // 3. Confirm prompts on dangerous actions
  const confirmForms = document.querySelectorAll('form[data-confirm]');
  confirmForms.forEach(function (form) {
    form.addEventListener('submit', function (e) {
      const message = form.getAttribute('data-confirm') || 'Are you sure you want to perform this action?';
      if (!confirm(message)) {
        e.preventDefault();
      }
    });
  });
});

/**
 * Copies text from a specific element ID to the user's clipboard
 */
function copyToClipboard(elementId, buttonId) {
  const targetElement = document.getElementById(elementId);
  if (!targetElement) return;

  const textToCopy = targetElement.innerText || targetElement.value;
  navigator.clipboard.writeText(textToCopy).then(
    function () {
      const btn = document.getElementById(buttonId);
      if (btn) {
        const originalText = btn.innerHTML;
        btn.innerHTML = '✓ Copied to Clipboard!';
        btn.classList.add('btn-primary');
        setTimeout(function () {
          btn.innerHTML = originalText;
          btn.classList.remove('btn-primary');
        }, 2500);
      }
    },
    function () {
      alert('Could not copy automatically. Please select and copy the text manually.');
    }
  );
}
