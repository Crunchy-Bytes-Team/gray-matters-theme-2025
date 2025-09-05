#!/bin/bash

# Complete Grid Class Migration Script
echo "🔄 Finishing grid class migration to Tailwind..."

# Replace remaining grid classes with Tailwind equivalents
echo "📐 Updating grid column classes..."

# Replace grid column classes
find . -name "*.liquid" -exec sed -i '' 's/grid--1-col-tablet-down/grid-cols-1/g' {} \;
find . -name "*.liquid" -exec sed -i '' 's/grid--2-col-tablet-down/grid-cols-1 md:grid-cols-2/g' {} \;
find . -name "*.liquid" -exec sed -i '' 's/grid--3-col-tablet-down/grid-cols-1 md:grid-cols-3/g' {} \;
find . -name "*.liquid" -exec sed -i '' 's/grid--4-col-tablet-down/grid-cols-1 md:grid-cols-4/g' {} \;

find . -name "*.liquid" -exec sed -i '' 's/grid--1-col-desktop/grid-cols-1/g' {} \;
find . -name "*.liquid" -exec sed -i '' 's/grid--2-col-desktop/lg:grid-cols-2/g' {} \;
find . -name "*.liquid" -exec sed -i '' 's/grid--3-col-desktop/lg:grid-cols-3/g' {} \;
find . -name "*.liquid" -exec sed -i '' 's/grid--4-col-desktop/lg:grid-cols-4/g' {} \;

find . -name "*.liquid" -exec sed -i '' 's/grid--2-col-tablet/md:grid-cols-2/g' {} \;
find . -name "*.liquid" -exec sed -i '' 's/grid--3-col-tablet/md:grid-cols-3/g' {} \;
find . -name "*.liquid" -exec sed -i '' 's/grid--4-col-tablet/md:grid-cols-4/g' {} \;

# Replace other grid utilities
find . -name "*.liquid" -exec sed -i '' 's/grid--gapless/gap-0/g' {} \;
find . -name "*.liquid" -exec sed -i '' 's/grid--peek/gap-4/g' {} \;

echo "✅ Grid migration completed!"
echo "📋 Summary of replacements:"
echo "   - grid--*-col-desktop → lg:grid-cols-*"
echo "   - grid--*-col-tablet → md:grid-cols-*"  
echo "   - grid--*-col-tablet-down → grid-cols-1 md:grid-cols-*"
echo "   - grid--gapless → gap-0"
echo "   - grid--peek → gap-4"
