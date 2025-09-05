#!/bin/bash

# Tailwind CSS Migration Script for Shopify Dawn Theme
# This script systematically replaces Dawn CSS classes with Tailwind equivalents

echo "🚀 Starting Tailwind CSS Migration..."

# Phase 1: Layout Classes
echo "📐 Replacing layout classes..."
find . -name "*.liquid" -exec sed -i '' 's/page-width--narrow/max-w-4xl mx-auto px-6 md:px-36/g' {} \;
find . -name "*.liquid" -exec sed -i '' 's/page-width/max-w-7xl mx-auto px-6 md:px-20/g' {} \;
find . -name "*.liquid" -exec sed -i '' 's/grid--1-col/grid-cols-1/g' {} \;
find . -name "*.liquid" -exec sed -i '' 's/grid--2-col-tablet/md:grid-cols-2/g' {} \;
find . -name "*.liquid" -exec sed -i '' 's/grid--2-col-desktop/lg:grid-cols-2/g' {} \;
find . -name "*.liquid" -exec sed -i '' 's/grid--3-col-tablet/md:grid-cols-3/g' {} \;
find . -name "*.liquid" -exec sed -i '' 's/grid--4-col-desktop/lg:grid-cols-4/g' {} \;

# Phase 2: Card Components
echo "🃏 Replacing card classes..."
find . -name "*.liquid" -exec sed -i '' 's/card-wrapper/group relative/g' {} \;
find . -name "*.liquid" -exec sed -i '' 's/card card--standard/bg-white rounded-lg border shadow-sm/g' {} \;
find . -name "*.liquid" -exec sed -i '' 's/card card--media/bg-white rounded-lg border shadow-sm overflow-hidden/g' {} \;

# Phase 3: Button Classes
echo "🔘 Replacing button classes..."
find . -name "*.liquid" -exec sed -i '' 's/button button--primary/px-6 py-3 bg-blue-600 text-white rounded-md font-medium hover:bg-blue-700 transition-colors/g' {} \;
find . -name "*.liquid" -exec sed -i '' 's/button button--secondary/px-6 py-3 bg-gray-200 text-gray-900 rounded-md font-medium hover:bg-gray-300 transition-colors/g' {} \;

# Phase 4: Form Classes
echo "📝 Replacing form classes..."
find . -name "*.liquid" -exec sed -i '' 's/field__input/w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500/g' {} \;
find . -name "*.liquid" -exec sed -i '' 's/field__label/block text-sm font-medium text-gray-700 mb-1/g' {} \;

echo "✅ Migration complete! Please review and test your changes."
echo "💡 Remember to:"
echo "   1. Test all pages for visual consistency"
echo "   2. Remove unused CSS files from assets/"
echo "   3. Update any custom CSS that relies on the old classes"
