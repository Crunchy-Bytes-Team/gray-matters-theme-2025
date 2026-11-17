(function () {
  function ready(fn) {
    if (document.readyState !== 'loading') {
      fn();
    } else {
      document.addEventListener('DOMContentLoaded', fn);
    }
  }
  ready(function () {
    var btn = document.querySelector('.toggle-desc-btn');
    var panel = document.querySelector('[id^="MobileProductDesc-"]');
    var icon = btn ? btn.querySelector('span') : null;
    if (!btn || !panel || !icon) return;
    function clearPanelTransition() {
      panel.removeEventListener('transitionend', onPanelTransitionEnd);
    }

    function onPanelTransitionEnd(e) {
      if (e.propertyName !== 'max-height') return;
      clearPanelTransition();
      if (btn.getAttribute('aria-expanded') === 'true') {
        panel.style.maxHeight = 'none';
      } else {
        panel.classList.add('hidden');
      }
    }

    btn.addEventListener('click', function () {
      var isOpen = btn.getAttribute('aria-expanded') === 'true';
      panel.style.transition =
        'max-height 500ms ease-in-out, opacity 500ms ease-in-out';
      clearPanelTransition();

      if (!isOpen) {
        panel.classList.remove('hidden');
        panel.setAttribute('aria-hidden', 'false');
        panel.style.maxHeight = '0px';
        panel.style.opacity = '0';
        panel.offsetHeight;
        requestAnimationFrame(function () {
          panel.style.maxHeight = panel.scrollHeight + 'px';
          panel.style.opacity = '1';
        });
        panel.addEventListener('transitionend', onPanelTransitionEnd);
        btn.setAttribute('aria-expanded', 'true');
        btn.classList.add('is-open');
      } else {
        panel.setAttribute('aria-hidden', 'true');
        panel.style.maxHeight = panel.scrollHeight + 'px';
        panel.style.opacity = '1';
        panel.offsetHeight;
        requestAnimationFrame(function () {
          panel.style.maxHeight = '0px';
          panel.style.opacity = '0';
        });
        panel.addEventListener('transitionend', onPanelTransitionEnd);
        btn.setAttribute('aria-expanded', 'false');
        btn.classList.remove('is-open');
      }
    });
  });
})();
