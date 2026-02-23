/**
 * Inquire modal: pre-select requested size from trigger's data-inquire-size when modal opens.
 */
function initInquireModal() {
  document.addEventListener('modal:opened', (event) => {
    const { modal, trigger } = event.detail || {};
    if (!modal || modal.id !== 'inquire-modal' || !trigger) return;

    const size = trigger.getAttribute('data-inquire-size');
    if (!size) return;

    const select = modal.querySelector('select[name="contact[Size]"]');
    if (!select) return;

    const option = Array.from(select.options).find((opt) => opt.value === size);
    if (option) {
      select.value = size;
    }
  });
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initInquireModal);
} else {
  initInquireModal();
}
