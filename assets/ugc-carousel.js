(function () {
  function isMobile() {
    return window.matchMedia('(max-width: 767px)').matches;
  }
  function init(root) {
    const viewport = root.querySelector('[data-viewport]');
    const track = root.querySelector('[data-track]');
    const items = Array.from(track ? track.children : []);
    const prev = root.querySelector('[data-prev]');
    const next = root.querySelector('[data-next]');
    if (!viewport || !track || items.length === 0) return;

    let index = 0;

    function update() {
      if (!isMobile()) {
        track.style.transform = 'translateX(0px)';
        if (prev) prev.disabled = true;
        if (next) next.disabled = true;
        return;
      }
      const w = viewport.clientWidth;
      track.style.transform = 'translateX(' + -index * w + 'px)';
      if (prev) prev.disabled = index === 0;
      if (next) next.disabled = index >= items.length - 1;
    }

    if (prev) {
      prev.addEventListener('click', function (e) {
        e.preventDefault();
        index = Math.max(0, index - 1);
        update();
      });
    }
    if (next) {
      next.addEventListener('click', function (e) {
        e.preventDefault();
        index = Math.min(items.length - 1, index + 1);
        update();
      });
    }

    window.addEventListener('resize', update);
    update();
  }

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('[data-imagerow]').forEach(init);
  });
})();
