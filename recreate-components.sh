#!/bin/bash

# Recreate Missing Component CSS Files with Tailwind
echo "🎨 Recreating missing component CSS files with Tailwind styling..."

# Component Modal Video
cat > assets/component-modal-video.css << 'EOF'
/* Component Modal Video - Tailwind Enhanced */

.modal-video {
  @apply fixed inset-0 z-50 flex items-center justify-center p-4 bg-black bg-opacity-75;
}

.modal-video__content {
  @apply relative bg-black rounded-lg overflow-hidden max-w-4xl w-full aspect-video;
}

.modal-video__close {
  @apply absolute top-4 right-4 z-10 p-2 bg-white bg-opacity-20 text-white rounded-full hover:bg-opacity-30 transition-colors duration-200;
}

.modal-video__close .svg-wrapper {
  @apply w-5 h-5;
}

.modal-video video,
.modal-video iframe {
  @apply w-full h-full;
}
EOF

# Component Cart Notification
cat > assets/component-cart-notification.css << 'EOF'
/* Component Cart Notification - Tailwind Enhanced */

cart-notification {
  @apply block;
}

.cart-notification-wrapper {
  @apply relative;
}

.cart-notification {
  @apply fixed top-4 right-4 z-50 bg-white border border-gray-200 rounded-lg shadow-xl max-w-sm w-full transform translate-x-full transition-transform duration-300;
}

.cart-notification.active {
  @apply translate-x-0;
}

.cart-notification__header {
  @apply flex items-center justify-between p-4 border-b border-gray-200;
}

.cart-notification__heading {
  @apply flex items-center space-x-2 text-green-600 font-medium;
}

.cart-notification__close {
  @apply p-1 text-gray-400 hover:text-gray-600 rounded transition-colors duration-200;
}

.cart-notification-product {
  @apply p-4;
}

.cart-notification__links {
  @apply p-4 space-y-3 bg-gray-50;
}
EOF

# Component Menu Drawer  
cat > assets/component-menu-drawer.css << 'EOF'
/* Component Menu Drawer - Tailwind Enhanced */

header-drawer {
  @apply block;
}

.menu-drawer-container {
  @apply relative;
}

.menu-drawer {
  @apply fixed inset-0 z-50 bg-white transform translate-x-full transition-transform duration-300;
}

.menu-drawer-container[open] .menu-drawer {
  @apply translate-x-0;
}

.menu-drawer__inner-container {
  @apply h-full flex flex-col;
}

.menu-drawer__navigation-container {
  @apply flex-1 overflow-y-auto p-6;
}

.menu-drawer__navigation {
  @apply space-y-4;
}

.menu-drawer__menu {
  @apply space-y-2;
}

.menu-drawer__menu-item {
  @apply block py-3 px-4 text-gray-700 hover:text-gray-900 hover:bg-gray-50 rounded-md transition-colors duration-200;
}

.menu-drawer__menu-item--active {
  @apply text-blue-600 bg-blue-50 font-semibold;
}

.menu-drawer__submenu {
  @apply pl-4 mt-2 space-y-1;
}

.menu-drawer__close-button {
  @apply flex items-center py-2 px-4 text-gray-600 hover:text-gray-900;
}

.menu-drawer__utility-links {
  @apply border-t border-gray-200 p-6 space-y-4;
}
EOF

# Component Search
cat > assets/component-search.css << 'EOF'
/* Component Search - Tailwind Enhanced */

.header__search {
  @apply relative;
}

.search-modal {
  @apply fixed inset-0 z-50 flex items-start justify-center pt-16 px-4;
}

.search-modal__content {
  @apply relative bg-white rounded-lg shadow-xl max-w-2xl w-full;
}

.search-modal__form {
  @apply p-6;
}

.search__input {
  @apply w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-lg;
}

.search__button,
.reset__button {
  @apply absolute right-3 top-1/2 transform -translate-y-1/2 p-2 text-gray-400 hover:text-gray-600;
}

.predictive-search {
  @apply border-t border-gray-200 max-h-80 overflow-y-auto;
}

.predictive-search__item {
  @apply flex items-center p-3 hover:bg-gray-50 transition-colors duration-200;
}

.search-modal__close-button {
  @apply absolute top-4 right-4 p-2 text-gray-400 hover:text-gray-600;
}
EOF

echo "✅ Component CSS files recreated!"
