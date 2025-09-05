#!/bin/bash

# Recreate All Missing CSS Files with Tailwind
echo "🔧 Recreating all missing CSS files..."

# Section Rich Text
cat > assets/section-rich-text.css << 'EOF'
/* Section Rich Text - Tailwind Enhanced */
.rich-text {
  @apply space-y-8;
}
.rich-text__wrapper {
  @apply max-w-4xl mx-auto;
}
.rich-text__blocks {
  @apply space-y-8;
}
.rich-text__heading {
  @apply text-3xl font-bold text-gray-900 mb-6;
}
.rich-text__text {
  @apply prose prose-lg max-w-none;
}
.rich-text__buttons {
  @apply flex flex-col sm:flex-row gap-4 justify-center;
}
.rich-text__buttons--multiple {
  @apply space-y-4 sm:space-y-0 sm:space-x-4;
}
EOF

# Section Image Banner  
cat > assets/section-image-banner.css << 'EOF'
/* Section Image Banner - Tailwind Enhanced */
.banner {
  @apply relative overflow-hidden;
}
.banner__media {
  @apply relative;
}
.banner__content {
  @apply absolute inset-0 flex items-center justify-center z-10;
}
.banner__box {
  @apply text-center space-y-6 p-8;
}
.banner__heading {
  @apply text-4xl md:text-5xl lg:text-6xl font-bold text-white;
}
.banner__text {
  @apply text-lg md:text-xl text-white opacity-90;
}
.banner__buttons {
  @apply flex flex-col sm:flex-row gap-4 justify-center;
}
EOF

# Section Multicolumn
cat > assets/section-multicolumn.css << 'EOF'
/* Section Multicolumn - Tailwind Enhanced */
.multicolumn {
  @apply py-12 md:py-16;
}
.multicolumn-list {
  @apply grid gap-8;
}
.multicolumn-card {
  @apply text-center space-y-4;
}
.multicolumn-card__image-wrapper {
  @apply mb-6;
}
.multicolumn-card__info {
  @apply space-y-4;
}
.multicolumn-card__image {
  @apply w-full h-auto rounded-lg;
}
EOF

# Section Footer
cat > assets/section-footer.css << 'EOF'
/* Section Footer - Tailwind Enhanced */
.footer {
  @apply bg-gray-50 border-t border-gray-200;
}
.footer__content-top {
  @apply py-16;
}
.footer__blocks-wrapper {
  @apply grid gap-8;
}
.footer-block {
  @apply space-y-4;
}
.footer-block__heading {
  @apply text-lg font-semibold text-gray-900 mb-4;
}
.footer__content-bottom {
  @apply border-t border-gray-200 py-8;
}
.footer__copyright {
  @apply text-center space-y-2 text-sm text-gray-600;
}
EOF

echo "✅ All missing CSS files recreated with Tailwind styling!"
echo "📋 Files created:"
echo "   - section-rich-text.css"  
echo "   - section-image-banner.css"
echo "   - section-multicolumn.css"
echo "   - section-footer.css"
