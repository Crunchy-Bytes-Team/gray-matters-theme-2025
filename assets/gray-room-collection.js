/**
 * Collection listing autoload.
 *
 * Each Liquid response renders at most 50 products so the page is not cut off
 * by Shopify's per-page cap or the Liquid memory limit. On page 1 this script
 * fetches the following section pages and appends their cards to #product-grid.
 * A facet sort or filter replaces that grid; collection:products-autoload
 * starts a new run and drops any fetch still in flight.
 */
(function () {
  var MAX_EXTRA_PAGES = 30;
  var generation = 0;

  function gridItems(grid) {
    var items = [];
    if (!grid) return items;
    for (var i = 0; i < grid.children.length; i++) {
      if (grid.children[i].tagName === 'LI') items.push(grid.children[i]);
    }
    return items;
  }

  function loadNext(meta, fetched, run) {
    if (run !== generation) return;
    if (meta.getAttribute('data-autoload-state') === 'loading') return;

    var nextUrl = meta.getAttribute('data-next-url') || '';
    var grid = document.getElementById('product-grid');
    if (
      !nextUrl ||
      !grid ||
      grid.tagName !== 'UL' ||
      fetched >= MAX_EXTRA_PAGES
    ) {
      meta.setAttribute('data-autoload-state', 'done');
      return;
    }

    var sectionId = meta.getAttribute('data-section-id') || '';
    var requestUrl = nextUrl;
    if (sectionId && requestUrl.indexOf('section_id=') === -1) {
      requestUrl +=
        (requestUrl.indexOf('?') === -1 ? '?' : '&') +
        'section_id=' +
        encodeURIComponent(sectionId);
    }

    meta.setAttribute('data-autoload-state', 'loading');

    fetch(requestUrl, { credentials: 'same-origin' })
      .then(function (response) {
        if (!response.ok) throw new Error('gray-room-collection');
        return response.text();
      })
      .then(function (html) {
        if (run !== generation || !meta.isConnected) return;

        var doc = new DOMParser().parseFromString(html, 'text/html');
        var nextItems = gridItems(doc.getElementById('product-grid'));
        if (!nextItems.length) {
          meta.setAttribute('data-next-url', '');
          meta.setAttribute('data-autoload-state', 'done');
          return;
        }

        var liveGrid = document.getElementById('product-grid');
        if (!liveGrid || liveGrid.tagName !== 'UL') {
          meta.setAttribute('data-autoload-state', 'idle');
          return;
        }

        nextItems.forEach(function (item) {
          liveGrid.appendChild(document.importNode(item, true));
        });

        var nextMeta = doc.querySelector(
          '[data-gray-room-collection-autoload]',
        );
        var following = nextMeta
          ? nextMeta.getAttribute('data-next-url') || ''
          : '';
        meta.setAttribute('data-next-url', following);
        meta.setAttribute('data-autoload-state', 'idle');

        if (following) {
          loadNext(meta, fetched + 1, run);
        } else {
          meta.setAttribute('data-autoload-state', 'done');
        }
      })
      .catch(function () {
        if (run !== generation || !meta.isConnected) return;
        meta.setAttribute('data-autoload-state', 'idle');
      });
  }

  function boot() {
    var meta = document.querySelector('[data-gray-room-collection-autoload]');
    if (!meta) return;
    if (
      meta.getAttribute('data-autoload-state') === 'loading' ||
      meta.getAttribute('data-autoload-state') === 'done'
    ) {
      return;
    }
    if (Number(meta.getAttribute('data-current-page') || '1') !== 1) return;
    var run = ++generation;
    loadNext(meta, 0, run);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }

  document.addEventListener('shopify:section:load', boot);
  document.addEventListener('collection:products-autoload', boot);
})();
