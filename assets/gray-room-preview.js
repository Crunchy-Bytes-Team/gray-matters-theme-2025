/**
 * Gray Room / Archive Sale preview via ?gr=1
 *
 * Shopify strips custom query params from Liquid, so this runs client-side:
 * - reveals Archive Sale nav ([data-gray-room-preview])
 * - on PDP, simulates vendor GRAY ROOM:
 *   - hide related products
 *   - keep only the current color-variant dot
 *   - treat sold-out sizes as no-Inquire (Archive Sale)
 */
(function () {
  var PREVIEW_RE = /(?:^|[?&])gr=1(?:&|$)/;
  var applied = false;

  function isPreview() {
    return PREVIEW_RE.test(window.location.search || '');
  }

  function revealNav() {
    document
      .querySelectorAll('[data-gray-room-preview]')
      .forEach(function (node) {
        node.removeAttribute('hidden');
      });
  }

  function hideRelated() {
    document
      .querySelectorAll('.relative-products-snippet, [data-gray-room-related]')
      .forEach(function (el) {
        // Tailwind `flex` overrides the HTML [hidden] attribute's display:none.
        el.setAttribute('hidden', '');
        el.style.setProperty('display', 'none', 'important');
        el.classList.add('hidden');
        el.setAttribute('data-gray-room-preview-hidden', 'related');
      });
  }

  function hideSiblingColorDots() {
    document
      .querySelectorAll('.color-variant .color-variant-dot')
      .forEach(function (dot) {
        if (dot.tagName === 'A') {
          dot.style.display = 'none';
          dot.setAttribute('data-gray-room-preview-hidden', 'color');
          return;
        }
        if (dot.getAttribute('aria-current') === 'true') return;
        // Fallback path: current is a DIV; hide any unexpected non-current DIVs that wrap links
        if (dot.querySelector('a')) {
          dot.style.display = 'none';
          dot.setAttribute('data-gray-room-preview-hidden', 'color');
        }
      });
  }

  function outOfStockLabel() {
    return (
      (window.variantStrings && window.variantStrings.inventoryOutOfStock) ||
      'Out of stock'
    );
  }

  function rewriteSoldOutOptions() {
    var label = outOfStockLabel();
    document
      .querySelectorAll(
        '.product-form__input--dropdown-size select option, variant-selects select option',
      )
      .forEach(function (opt) {
        if (!opt.value) return;
        var text = (opt.textContent || '').trim();
        var isSoldOut =
          opt.hasAttribute('data-soldout-option') ||
          opt.hasAttribute('data-no-inquire') ||
          /inquire/i.test(text) ||
          /out of stock|esaurito|sold out/i.test(text);
        if (!isSoldOut) return;

        var sizeLabel = text.replace(/\s*[-–]\s*.*$/, '').trim() || opt.value;
        opt.textContent = sizeLabel + ' - ' + label;
        opt.setAttribute('data-soldout-option', '');
        opt.setAttribute('data-no-inquire', '');
      });
  }

  function forceNoInquireOnForm() {
    document.querySelectorAll('product-form').forEach(function (form) {
      form.dataset.productOnSale = 'true';
      form.dataset.grayRoomPreview = '1';
    });
  }

  function refreshBuyButton() {
    var sizeSelect = document.querySelector(
      '.product-form__input--dropdown-size select',
    );
    if (!sizeSelect || !sizeSelect.value) return;
    sizeSelect.dispatchEvent(new Event('change', { bubbles: true }));
  }

  function applyPdpSimulation() {
    var productInfo = document.querySelector('product-info');
    if (!productInfo) return;

    document.documentElement.dataset.grayRoomPreview = '1';
    productInfo.dataset.grayRoomPreview = '1';

    hideRelated();
    hideSiblingColorDots();
    forceNoInquireOnForm();
    rewriteSoldOutOptions();

    if (!applied) {
      applied = true;
      refreshBuyButton();
    }
  }

  function run() {
    if (!isPreview()) return;
    revealNav();
    applyPdpSimulation();
  }

  function bindResync() {
    if (!isPreview()) return;

    if (
      typeof subscribe === 'function' &&
      typeof PUB_SUB_EVENTS !== 'undefined'
    ) {
      subscribe(PUB_SUB_EVENTS.variantChange, function () {
        hideSiblingColorDots();
        forceNoInquireOnForm();
        rewriteSoldOutOptions();
      });
      if (PUB_SUB_EVENTS.optionValueSelectionChange) {
        subscribe(PUB_SUB_EVENTS.optionValueSelectionChange, function () {
          window.setTimeout(function () {
            hideSiblingColorDots();
            forceNoInquireOnForm();
            rewriteSoldOutOptions();
          }, 0);
        });
      }
    }

    document.addEventListener('shopify:section:load', run);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      run();
      bindResync();
    });
  } else {
    run();
    bindResync();
  }
})();
