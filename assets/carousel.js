(function () {
  // Utility helpers
  function qs(el, sel) {
    return el.querySelector(sel);
  }
  function qsa(el, sel) {
    return Array.prototype.slice.call(el.querySelectorAll(sel));
  }
  function clamp(n, min, max) {
    return Math.min(Math.max(n, min), max);
  }
  function isMobile() {
    return window.matchMedia('(max-width: 767px)').matches;
  }

  function initCarousel(root) {
    var viewport = qs(root, '[data-viewport]');
    var track = qs(root, '[data-track]');
    var items = qsa(root, '[data-item]');
    var prevBtn = qs(root, '[data-prev]');
    var nextBtn = qs(root, '[data-next]');
    var progress = qs(root, '[data-progress]');
    if (!viewport || !track || items.length === 0) return;

    var translate = 0; // current translateX in px (mobile only)
    var startX = 0; // pointer down X
    var base = 0; // translate at drag start
    var dragging = false;
    var moved = false;

    function sizes() {
      var vw = viewport.clientWidth;
      var itemW = isMobile() ? vw / 2 : vw / 4; // on desktop JS transform is disabled
      var total = isMobile() ? itemW * items.length : vw; // full width of track on mobile
      var maxNeg = Math.min(0, vw - total); // negative bound (<= 0)
      return { vw: vw, itemW: itemW, total: total, maxNeg: maxNeg };
    }

    function apply(x) {
      translate = x;
      if (isMobile()) {
        track.style.transform = 'translateX(' + x + 'px)';
      } else {
        track.style.transform = 'translateX(0px)';
      }
      // Update progress runner position
      if (progress) {
        if (dragging || !isMobile()) {
          var s = sizes();
          var travel = Math.max(0, root.clientWidth - 100); // bar scrollable distance
          var ratio = s.maxNeg === 0 ? 0 : -translate / -s.maxNeg; // 0..1
          var px = travel * clamp(ratio, 0, 1);
          progress.style.transform = 'translateX(' + px + 'px)';
        }
      }
    }

    function showProgress() {
      if (progress) {
        progress.classList.remove('opacity-0');
        progress.classList.add('opacity-100');
      }
    }
    function hideProgress() {
      if (progress) {
        progress.classList.add('opacity-0');
        progress.classList.remove('opacity-100');
      }
    }

    // Drag handlers (mobile only)
    function onDown(e) {
      if (!isMobile()) return; // enable drag only on mobile
      dragging = true;
      moved = false;
      track.style.transition = 'none';
      startX = e.touches ? e.touches[0].clientX : e.clientX;
      base = translate;
      showProgress();
      root.classList.add('dragging');
      // Avoid image ghost drag
      e.preventDefault();
    }

    function onMove(e) {
      if (!dragging) return;
      var x = e.touches ? e.touches[0].clientX : e.clientX;
      var dx = x - startX;
      if (Math.abs(dx) > 3) moved = true;
      var s = sizes();
      var nx = clamp(base + dx, s.maxNeg, 0);
      apply(nx);
    }

    function onUp() {
      if (!dragging) return;
      dragging = false;
      // keep where released; re-enable transition for arrow clicks
      track.style.transition = '';
      hideProgress();
      root.classList.remove('dragging');
    }

    // Arrow step (mobile only): move by one item width
    function step(dir) {
      // dir: -1 prev, +1 next (visual direction considering translate is negative to go right)
      var s = sizes();
      var nx = clamp(translate + dir * s.itemW, s.maxNeg, 0);
      track.style.transition = 'transform 300ms ease';
      apply(nx);
    }

    // Wire arrows (visible only on mobile via CSS, but also guarded here)
    if (prevBtn) {
      prevBtn.addEventListener('click', function () {
        if (isMobile()) step(+1);
      });
    }
    if (nextBtn) {
      nextBtn.addEventListener('click', function () {
        if (isMobile()) step(-1);
      });
    }

    // Drag listeners
    track.addEventListener('mousedown', onDown);
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    track.addEventListener('mouseleave', onUp);
    track.addEventListener('touchstart', onDown, { passive: false });
    track.addEventListener('touchmove', onMove, { passive: false });
    track.addEventListener('touchend', onUp);
    track.addEventListener('touchcancel', onUp);

    // Desktop: show progress on hover of the carousel root (optional aesthetic)
    root.addEventListener('mouseenter', function () {
      if (!isMobile()) showProgress();
    });
    root.addEventListener('mouseleave', function () {
      if (!isMobile()) hideProgress();
    });

    // Keep position consistent on resize
    window.addEventListener('resize', function () {
      var s = sizes();
      apply(clamp(translate, s.maxNeg, 0));
    });

    // Init
    apply(0);
  }

  // Auto-init on DOM ready
  function ready(fn) {
    if (document.readyState !== 'loading') fn();
    else document.addEventListener('DOMContentLoaded', fn);
  }
  ready(function () {
    var roots = document.querySelectorAll('[data-relprod]');
    Array.prototype.forEach.call(roots, initCarousel);
  });
})();
