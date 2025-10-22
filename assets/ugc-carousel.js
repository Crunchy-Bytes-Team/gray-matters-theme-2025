(function () {
  function isMobile() {
    return window.matchMedia('(max-width: 767px)').matches;
  }
  function init(root) {
    if (!root || root.dataset.carouselInit === 'true') return;
    root.dataset.carouselInit = 'true';

    const viewport = root.querySelector('[data-viewport]');
    const track = root.querySelector('[data-track]');
    const items = Array.from(track ? track.children : []);
    const prev = root.querySelector('[data-prev]');
    const next = root.querySelector('[data-next]');
    if (!viewport || !track || items.length === 0) {
      delete root.dataset.carouselInit;
      return;
    }

    let index = 0;

    function update() {
      if (items.length === 0) return;
      if (!isMobile()) {
        index = 0;
        track.style.transform = 'translateX(0px)';
        items.forEach(function (item) {
          item.style.minWidth = '';
          item.style.flex = '';
          item.style.maxWidth = '';
        });
        if (prev) prev.disabled = true;
        if (next) next.disabled = true;
        return;
      }
      index = Math.min(index, items.length - 1);
      const w = viewport.clientWidth;
      items.forEach(function (item) {
        item.style.minWidth = w + 'px';
        item.style.flex = '0 0 ' + w + 'px';
        item.style.maxWidth = w + 'px';
      });
      track.style.transform = 'translateX(' + -index * w + 'px)';
      if (prev) prev.disabled = index === 0;
      if (next) next.disabled = index >= items.length - 1;
    }

    if (prev) {
      prev.addEventListener('click', function (e) {
        e.preventDefault();
        if (!isMobile()) return;
        index = Math.max(0, index - 1);
        update();
      });
    }
    if (next) {
      next.addEventListener('click', function (e) {
        e.preventDefault();
        if (!isMobile()) return;
        index = Math.min(items.length - 1, index + 1);
        update();
      });
    }

    function onResize() {
      update();
    }

    window.addEventListener('resize', onResize);
    window.addEventListener('load', onResize);
    root._ugcCleanup = function () {
      window.removeEventListener('resize', onResize);
      window.removeEventListener('load', onResize);
      delete root.dataset.carouselInit;
    };
    update();
  }

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('[data-ugc-carousel]').forEach(init);
  });

  document.addEventListener('shopify:section:load', function (event) {
    if (!event || !event.target) return;
    event.target.querySelectorAll('[data-ugc-carousel]').forEach(init);
  });

  document.addEventListener('shopify:section:unload', function (event) {
    if (!event || !event.target) return;
    event.target
      .querySelectorAll('[data-ugc-carousel]')
      .forEach(function (root) {
        if (root._ugcCleanup) {
          root._ugcCleanup();
          delete root._ugcCleanup;
        }
      });
  });
})();
