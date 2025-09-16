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
    if (!btn || !panel) return;
    btn.addEventListener('click', function () {
      var isHidden = panel.classList.contains('hidden');
      // Ensure transitions are applied
      panel.style.transition =
        'max-height 500ms ease-in-out, opacity 500ms ease-in-out';

      if (isHidden) {
        // SHOW: remove display:none, then animate from 0 to scrollHeight
        panel.classList.remove('hidden');
        panel.setAttribute('aria-hidden', 'false');
        panel.style.maxHeight = '0px';
        panel.style.opacity = '0';
        // next frame -> expand
        requestAnimationFrame(function () {
          panel.style.maxHeight = panel.scrollHeight + 'px';
          panel.style.opacity = '1';
        });
        // after transition, clear maxHeight so content can grow
        var onOpenEnd = function (e) {
          if (e.propertyName === 'max-height') {
            panel.style.maxHeight = 'none';
            panel.removeEventListener('transitionend', onOpenEnd);
          }
        };
        panel.addEventListener('transitionend', onOpenEnd);

        btn.setAttribute('aria-expanded', 'true');
        btn.textContent = '−';
      } else {
        // HIDE: collapse to current height, then to 0, then add hidden
        panel.setAttribute('aria-hidden', 'true');
        // lock current height before collapsing
        panel.style.maxHeight = panel.scrollHeight + 'px';
        panel.style.opacity = '1';
        requestAnimationFrame(function () {
          panel.style.maxHeight = '0px';
          panel.style.opacity = '0';
        });
        var onCloseEnd = function (e) {
          if (e.propertyName === 'max-height') {
            panel.classList.add('hidden');
            panel.removeEventListener('transitionend', onCloseEnd);
          }
        };
        panel.addEventListener('transitionend', onCloseEnd);

        btn.setAttribute('aria-expanded', 'false');
        btn.textContent = '+';
      }
    });
  });
})();
