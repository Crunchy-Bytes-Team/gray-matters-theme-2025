(function () {
  var MOBILE_QUERY = '(max-width: 767px)';

  function isMobile() {
    return window.matchMedia(MOBILE_QUERY).matches;
  }

  function init(root) {
    if (!root || root.__imageRowInitialized) return;

    var viewport = root.querySelector('[data-viewport]');
    var track = root.querySelector('[data-track]');
    var items = Array.prototype.slice.call(
      root.querySelectorAll('[data-item]'),
    );
    var prev = root.querySelector('[data-prev]');
    var next = root.querySelector('[data-next]');
    if (!viewport || !track || items.length === 0) return;

    root.__imageRowInitialized = true;

    var index = 0;
    var resizeRaf = null;

    function setButtonState() {
      var disabled = !isMobile();
      if (prev) prev.disabled = disabled || index === 0;
      if (next) next.disabled = disabled || index >= items.length - 1;
    }

    function applyDesktopStyles() {
      track.style.transform = 'translateX(0px)';
      track.style.width = '';
      items.forEach(function (item) {
        item.style.flex = '';
        item.style.width = '';
      });
    }

    function applyMobileStyles(width) {
      track.style.width = width * items.length + 'px';
      items.forEach(function (item) {
        item.style.flex = '0 0 ' + width + 'px';
        item.style.width = width + 'px';
      });
    }

    function updateTransform(width) {
      track.style.transform = 'translateX(' + -index * width + 'px)';
    }

    function update() {
      index = Math.max(0, Math.min(index, items.length - 1));

      if (!isMobile()) {
        applyDesktopStyles();
        setButtonState();
        return;
      }

      var width = viewport.getBoundingClientRect().width;
      if (!width) return;

      applyMobileStyles(width);
      updateTransform(width);
      setButtonState();
    }

    function onResize() {
      if (resizeRaf) window.cancelAnimationFrame(resizeRaf);
      resizeRaf = window.requestAnimationFrame(function () {
        resizeRaf = null;
        update();
      });
    }

    if (prev) {
      prev.addEventListener('click', function (event) {
        event.preventDefault();
        index = Math.max(0, index - 1);
        update();
      });
    }

    if (next) {
      next.addEventListener('click', function (event) {
        event.preventDefault();
        index = Math.min(items.length - 1, index + 1);
        update();
      });
    }

    window.addEventListener('resize', onResize);
    update();

    root.__imageRowCleanup = function () {
      window.removeEventListener('resize', onResize);
      root.__imageRowInitialized = false;
      delete root.__imageRowCleanup;
    };
  }

  function initAll(context) {
    var scope = context || document;
    scope.querySelectorAll('[data-imagerow]').forEach(init);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      initAll();
    });
  } else {
    initAll();
  }

  document.addEventListener('shopify:section:load', function (event) {
    initAll(event.target);
  });

  document.addEventListener('shopify:section:unload', function (event) {
    event.target.querySelectorAll('[data-imagerow]').forEach(function (root) {
      if (root.__imageRowCleanup) root.__imageRowCleanup();
    });
  });
})();
