#!/bin/bash

# CSS Cleanup Script - Remove unused CSS files after Tailwind migration
# This script moves unused CSS files to a backup folder for safety

echo "🧹 Starting CSS cleanup after Tailwind migration..."

# Create backup directory
mkdir -p css-backup/components
mkdir -p css-backup/sections

echo "📦 Backing up CSS files..."

# Move component CSS files to backup (keeping essential ones)
for file in assets/component-*.css; do
    if [[ -f "$file" ]]; then
        filename=$(basename "$file")
        # Keep essential files that might still be needed
        case "$filename" in
            "component-cart-items.css"|"component-cart.css"|"component-totals.css"|"component-price.css"|"component-discounts.css")
                echo "⚠️  Keeping essential file: $filename"
                ;;
            *)
                echo "📁 Backing up: $filename"
                mv "$file" "css-backup/components/"
                ;;
        esac
    fi
done

# Move section CSS files to backup (keeping essential ones)  
for file in assets/section-*.css; do
    if [[ -f "$file" ]]; then
        filename=$(basename "$file")
        # Keep files that might have critical functionality
        case "$filename" in
            "section-password.css")
                echo "⚠️  Keeping essential file: $filename"
                ;;
            *)
                echo "📁 Backing up: $filename"
                mv "$file" "css-backup/sections/"
                ;;
        esac
    fi
done

# Check for any remaining CSS imports in theme.liquid
echo "🔍 Checking for CSS imports in theme.liquid..."
grep -n "\.css.*asset_url.*stylesheet_tag" layout/theme.liquid | head -5

echo "✅ CSS cleanup complete!"
echo "📋 Summary:"
echo "   - Component CSS files backed up to: css-backup/components/"
echo "   - Section CSS files backed up to: css-backup/sections/"
echo "   - Essential CSS files kept in assets/"
echo ""
echo "💡 Next steps:"
echo "   1. Test your theme thoroughly"
echo "   2. If everything works, you can delete the css-backup folder"
echo "   3. If issues occur, restore files from css-backup/"
