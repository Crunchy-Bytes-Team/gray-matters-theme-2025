/**
 * Delayed bottom-right newsletter popup. Idempotent init for full page loads.
 */
(function () {
  var DELAY_MS = 5000;
  var STORAGE_KEY = 'gm-newsletter-popup-dismissed';
  var initScheduled = false;

  function getModal() {
    return document.getElementById('newsletter-modal');
  }

  function hideNewsletterPopup() {
    var modal = getModal();
    if (!modal) return;
    modal.classList.remove('newsletter-popup--visible');
    modal.setAttribute('aria-hidden', 'true');
    try {
      sessionStorage.setItem(STORAGE_KEY, '1');
    } catch (e) {
      /* ignore */
    }
  }

  window.hideNewsletterPopup = hideNewsletterPopup;

  function shouldSkipShow(modal) {
    try {
      if (sessionStorage.getItem(STORAGE_KEY)) return true;
    } catch (e) {
      /* ignore */
    }
    if (modal.querySelector('.form-message--success')) {
      try {
        sessionStorage.setItem(STORAGE_KEY, '1');
      } catch (e2) {
        /* ignore */
      }
      return true;
    }
    return false;
  }

  function showPopup() {
    var modal = getModal();
    if (!modal) return;
    if (shouldSkipShow(modal)) return;
    modal.classList.add('newsletter-popup--visible');
    modal.setAttribute('aria-hidden', 'false');
  }

  function bindClose(modal) {
    if (modal.dataset.popupBound === 'true') return;
    modal.dataset.popupBound = 'true';

    var closeBtn = modal.querySelector('[data-newsletter-popup-close]');
    if (closeBtn) {
      closeBtn.addEventListener('click', hideNewsletterPopup);
    }

    document.addEventListener('keydown', function (e) {
      if (
        e.key === 'Escape' &&
        modal.classList.contains('newsletter-popup--visible')
      ) {
        hideNewsletterPopup();
      }
    });
  }

  function init() {
    if (initScheduled) return;
    var modal = getModal();
    if (!modal) return;
    initScheduled = true;

    bindClose(modal);
    window.setTimeout(showPopup, DELAY_MS);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
