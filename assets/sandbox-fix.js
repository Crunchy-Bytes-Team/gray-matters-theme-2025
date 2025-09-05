// Sandbox Fix for Development Environment
// This script must load BEFORE any other scripts to prevent sandbox errors

(function () {
  'use strict';

  // Create a safe storage polyfill immediately
  function createSafeStorage() {
    const memoryStorage = {};
    return {
      getItem: function (key) {
        return memoryStorage[key] || null;
      },
      setItem: function (key, value) {
        memoryStorage[key] = String(value);
      },
      removeItem: function (key) {
        delete memoryStorage[key];
      },
      clear: function () {
        Object.keys(memoryStorage).forEach((key) => delete memoryStorage[key]);
      },
      get length() {
        return Object.keys(memoryStorage).length;
      },
      key: function (index) {
        const keys = Object.keys(memoryStorage);
        return keys[index] || null;
      },
    };
  }

  // Override storage properties BEFORE any scripts load
  try {
    // Test if storage is accessible
    window.localStorage.setItem('test', 'test');
    window.localStorage.removeItem('test');
    window.sessionStorage.setItem('test', 'test');
    window.sessionStorage.removeItem('test');
  } catch (e) {
    // Storage is sandboxed, create safe replacements
    console.warn('Storage sandboxed, using memory fallback');

    // Replace with safe versions
    Object.defineProperty(window, 'localStorage', {
      value: createSafeStorage(),
      writable: false,
      configurable: false,
    });

    Object.defineProperty(window, 'sessionStorage', {
      value: createSafeStorage(),
      writable: false,
      configurable: false,
    });
  }

  // Prevent content.js from breaking
  window.addEventListener('error', function (e) {
    if (e.filename && e.filename.includes('content.js')) {
      console.warn('Suppressed content.js error:', e.message);
      e.preventDefault();
      return false;
    }
  });

  // Override problematic functions that content.js might use
  const originalAddEventListener = EventTarget.prototype.addEventListener;
  EventTarget.prototype.addEventListener = function (type, listener, options) {
    try {
      return originalAddEventListener.call(this, type, listener, options);
    } catch (e) {
      if (e.name === 'SecurityError') {
        console.warn('Blocked sandboxed addEventListener:', type);
        return;
      }
      throw e;
    }
  };
})();

// Additional protection for Shopify development environment
if (window.Shopify && window.Shopify.theme) {
  const originalMethods = {};

  // Safely wrap Shopify theme methods
  ['reload', 'load', 'unload'].forEach((method) => {
    if (window.Shopify.theme[method]) {
      originalMethods[method] = window.Shopify.theme[method];
      window.Shopify.theme[method] = function () {
        try {
          return originalMethods[method].apply(this, arguments);
        } catch (e) {
          console.warn(`Shopify.theme.${method} blocked:`, e.message);
          return false;
        }
      };
    }
  });
}
