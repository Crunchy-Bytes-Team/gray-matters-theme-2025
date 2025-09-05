// Fix JavaScript Errors - Development Environment
// This script helps resolve sandbox and CORS issues during development

(function () {
  'use strict';

  // Safely handle localStorage/sessionStorage in sandboxed environment
  function safeStorage(type) {
    try {
      const storage = window[type];
      // Test if storage is available
      storage.setItem('test', 'test');
      storage.removeItem('test');
      return storage;
    } catch (e) {
      console.warn(
        `${type} not available in sandboxed environment, using memory fallback`,
      );
      // Return a memory-based fallback
      const memoryStorage = {};
      return {
        getItem: (key) => memoryStorage[key] || null,
        setItem: (key, value) => {
          memoryStorage[key] = value;
        },
        removeItem: (key) => {
          delete memoryStorage[key];
        },
        clear: () => {
          Object.keys(memoryStorage).forEach(
            (key) => delete memoryStorage[key],
          );
        },
        get length() {
          return Object.keys(memoryStorage).length;
        },
        key: (index) => Object.keys(memoryStorage)[index] || null,
      };
    }
  }

  // Create safe storage objects
  if (typeof window !== 'undefined') {
    window.safeLocalStorage = safeStorage('localStorage');
    window.safeSessionStorage = safeStorage('sessionStorage');

    // Override problematic storage calls
    if (
      window.localStorage === undefined ||
      window.sessionStorage === undefined
    ) {
      Object.defineProperty(window, 'localStorage', {
        value: window.safeLocalStorage,
        writable: false,
      });
      Object.defineProperty(window, 'sessionStorage', {
        value: window.safeSessionStorage,
        writable: false,
      });
    }
  }

  // Handle theme hot reload safely
  if (window.Shopify && window.Shopify.theme) {
    const originalReload = window.Shopify.theme.reload || function () {};
    window.Shopify.theme.reload = function () {
      try {
        originalReload.apply(this, arguments);
      } catch (e) {
        console.warn('Theme reload blocked by sandbox, using fallback');
        // Fallback: just reload the page
        if (window.location) {
          window.location.reload();
        }
      }
    };
  }

  // Prevent CORS errors during development
  document.addEventListener('DOMContentLoaded', function () {
    // Remove any problematic external scripts in development
    const scripts = document.querySelectorAll(
      'script[src*="content.js"], script[src*="tag_assistant"]',
    );
    scripts.forEach((script) => {
      if (
        script.src &&
        (script.src.includes('content.js') ||
          script.src.includes('tag_assistant'))
      ) {
        console.warn('Removing problematic script:', script.src);
        script.remove();
      }
    });
  });

  // Handle CSS loading errors gracefully
  document.addEventListener(
    'error',
    function (e) {
      if (
        e.target &&
        e.target.tagName === 'LINK' &&
        e.target.rel === 'stylesheet'
      ) {
        console.warn('CSS failed to load:', e.target.href);
        // Don't let CSS errors break the page
        e.preventDefault();
      }
    },
    true,
  );
})();
