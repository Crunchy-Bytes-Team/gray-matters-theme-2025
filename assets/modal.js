const MODAL_BODY_LOCK_CLASS = 'overflow-hidden';
const DEFAULT_OPEN_CLASSES = ['grid', 'place-items-center'];

// getFocusableElements is defined in global.js - using that instead to avoid duplicate declaration
// Fallback implementation if global.js hasn't loaded yet
const getFocusableElementsSafe = (container) => {
  if (typeof getFocusableElements !== 'undefined') {
    return getFocusableElements(container);
  }
  // Local fallback implementation
  return Array.from(
    container.querySelectorAll(
      "summary, a[href], button:enabled, [tabindex]:not([tabindex^='-']), [draggable], area, input:not([type=hidden]):enabled, select:enabled, textarea:enabled, object, iframe",
    ),
  );
};

document.addEventListener('DOMContentLoaded', () => {
  const modals = Array.from(document.querySelectorAll('[data-modal]'));
  if (!modals.length) return;

  const modalRegistry = new Map();
  const state = {
    activeModal: null,
    lastFocused: null,
  };

  const lockBodyScroll = () =>
    document.body.classList.add(MODAL_BODY_LOCK_CLASS);
  const unlockBodyScroll = () =>
    document.body.classList.remove(MODAL_BODY_LOCK_CLASS);

  const setAriaState = (modal, isOpen) => {
    modal.setAttribute('aria-hidden', String(!isOpen));
  };

  const focusModal = (modal) => {
    const focusableContent =
      modal.querySelector('[data-modal-autofocus]') ||
      modal.querySelector('[data-modal-content]') ||
      getFocusableElementsSafe(modal)[0];

    if (typeof window.trapFocus === 'function') {
      window.trapFocus(modal, focusableContent || modal);
    } else if (
      focusableContent &&
      typeof focusableContent.focus === 'function'
    ) {
      focusableContent.focus();
    }
  };

  const restoreFocus = () => {
    if (state.lastFocused && typeof state.lastFocused.focus === 'function') {
      state.lastFocused.focus();
    }
  };

  const closeModal = (modal) => {
    if (!modal || modal !== state.activeModal) return;

    modal.classList.add('hidden');
    const appliedClasses = modal.dataset.activeModalClasses
      ? modal.dataset.activeModalClasses.split(' ')
      : DEFAULT_OPEN_CLASSES;
    appliedClasses.forEach((className) => modal.classList.remove(className));
    delete modal.dataset.activeModalClasses;
    setAriaState(modal, false);
    if (typeof window.removeTrapFocus === 'function') {
      window.removeTrapFocus(state.lastFocused || null);
    }
    unlockBodyScroll();
    restoreFocus();
    state.activeModal = null;
    state.lastFocused = null;
  };

  const openModal = (modal, trigger) => {
    if (!modal || modal === state.activeModal) return;

    if (state.activeModal) closeModal(state.activeModal);

    state.lastFocused = trigger || document.activeElement;
    modal.classList.remove('hidden');
    const openClasses = modal.dataset.modalOpenClass
      ? modal.dataset.modalOpenClass.split(' ').filter(Boolean)
      : DEFAULT_OPEN_CLASSES;
    openClasses.forEach((className) => modal.classList.add(className));
    modal.dataset.activeModalClasses = openClasses.join(' ');
    setAriaState(modal, true);
    lockBodyScroll();
    state.activeModal = modal;
    focusModal(modal);
  };

  modals.forEach((modal) => {
    const key = modal.dataset.modal || modal.id;
    if (key) {
      modalRegistry.set(key, modal);
    }

    modal.addEventListener('click', (event) => {
      if (
        event.target === modal ||
        event.target.closest('[data-modal-dismiss]')
      ) {
        event.preventDefault();
        closeModal(modal);
      }
    });
  });

  document
    .querySelectorAll('[data-modal-trigger]')
    .forEach((triggerElement) => {
      triggerElement.addEventListener('click', (event) => {
        const targetKey = triggerElement.dataset.modalTrigger;
        if (!targetKey) return;

        const targetModal =
          modalRegistry.get(targetKey) || document.getElementById(targetKey);

        if (!targetModal) return;

        event.preventDefault();
        openModal(targetModal, triggerElement);
      });
    });

  document.addEventListener('keydown', (event) => {
    if (event.key !== 'Escape' || !state.activeModal) return;
    event.preventDefault();
    closeModal(state.activeModal);
  });
});
