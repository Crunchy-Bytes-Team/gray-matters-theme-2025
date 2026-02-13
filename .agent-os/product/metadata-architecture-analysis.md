# Shopify Theme Metadata Architecture Analysis

## Overview

This Shopify custom theme (Gray Matters) uses **product metafields** extensively to dynamically control template appearance, behavior, and content structure. The theme implements a **metadata-driven rendering system** where product pages adapt their layout, styling, and functionality based on metafield data.

## Key Architecture Principles

1. **Product-Centric Metadata**: All dynamic behavior is driven by product metafields (no collection or shop metafields currently used)
2. **Namespace Organization**: Metafields are organized into logical namespaces (`module`, `custom`, `descriptors`, `reviews`)
3. **Graceful Degradation**: All snippets check for metafield existence before rendering, ensuring products without metadata still display correctly
4. **Flexible JSON Parsing**: Multiple parsing strategies handle different metafield storage formats (value objects, direct JSON, string JSON)

## Metafield Namespaces & Usage

### 1. `product.metafields.module.*` - Content Modules

These metafields control dynamic content modules that appear below the main product information.

#### `product.metafields.module.product_variants`
- **Purpose**: Defines color/style variant relationships
- **Format**: JSON with `entries` array containing product URLs/GIDs
- **Usage**: Rendered via `color-variant.liquid` snippet
- **Example Structure**:
```json
{
  "entries": [{
    "url": "https://www.graymattersnyc.com/products/egg-mules-bianco",
    "gid": "gid://shopify/Product/4418476769385",
    "product_id": 131
  }]
}
```
- **Rendering**: Creates color pill navigation linking to variant products
- **Location**: Product description area, mobile/desktop views

#### `product.metafields.module.product_detail_bg_image`
- **Purpose**: Sets background image for product detail page
- **Format**: Image URL string
- **Usage**: Applied as fixed background on desktop, inline image on mobile
- **Rendering**: Creates full-height background on right side of product page (desktop), mobile image below gallery

#### `product.metafields.module.related_products`
- **Purpose**: Defines manually curated related products
- **Format**: JSON with `entries` array
- **Usage**: Rendered via `related-products.liquid` snippet
- **Features**:
  - Supports multiple entry formats (GID, URL, handle)
  - Sorts by `position` field if available
  - Filters out current product and duplicates
  - Mobile carousel, desktop grid layout

#### `product.metafields.module.full_width_images`
- **Purpose**: Gallery of full-width images below product content
- **Format**: JSON with `entries` array containing image objects with `url` and `order`
- **Usage**: Rendered via `full-width-image.liquid` snippet
- **Features**: Sorts images by `order` field, lazy loading

#### `product.metafields.module.image_row_module_image1` through `image4`
- **Purpose**: Row of 1-4 images in responsive grid
- **Format**: Image URL strings (4 separate metafields)
- **Usage**: Rendered via `image-row.liquid` snippet
- **Features**:
  - Dynamically adjusts grid columns based on image count (1-4 columns)
  - Mobile carousel, desktop grid
  - Responsive layout

#### `product.metafields.module.video_module_video`
- **Purpose**: Landscape/desktop video embed
- **Format**: Video URL (iframe src)
- **Usage**: Rendered via `landscape-video.liquid` snippet
- **Features**: Aspect ratio maintained, full-width display

#### `product.metafields.module.video_module_video_mobile`
- **Purpose**: Vertical/mobile video embed
- **Format**: Video URL (iframe src)
- **Usage**: Rendered via `vertical-video.liquid` snippet
- **Features**: 16:9 aspect ratio, split layout with text module

#### `product.metafields.module.image_text_module_image`
- **Purpose**: Image for image-with-text module
- **Format**: Image URL string
- **Usage**: Rendered via `vertical-image-with-text.liquid` snippet
- **Features**: Split layout (text left, image right)

#### `product.metafields.module.image_text_module_header`
- **Purpose**: Header text for image-with-text module
- **Format**: String
- **Default**: "Gray Matters"
- **Usage**: Paired with `image_text_module_image`

#### `product.metafields.module.image_text_module_description`
- **Purpose**: Description text for image-with-text module
- **Format**: String
- **Default**: "Gray Matters"
- **Usage**: Paired with `image_text_module_image`

### 2. `product.metafields.custom.*` - Custom Styling & Content

#### `product.metafields.custom.primary_color`
- **Purpose**: Primary color for product color variant pills
- **Format**: Hex color string (e.g., "#FF5733")
- **Usage**: Used in `color-variant.liquid` to render current product's color pill
- **Default**: "#ffffff" if not set
- **Rendering**: Creates circular color swatch, can be split with secondary color

#### `product.metafields.custom.secondary_color`
- **Purpose**: Secondary color for two-tone color variant pills
- **Format**: Hex color string
- **Usage**: Paired with `primary_color` to create split-color pills
- **Rendering**: If present, creates top/bottom split color pill

#### `product.metafields.custom.ugc_content`
- **Purpose**: User-generated content (Instagram/social media embeds)
- **Format**: JSON with `entries` array
- **Usage**: Rendered via `ugc.liquid` snippet
- **Example Structure**:
```json
{
  "entries": [{
    "image": "https://cdn...",
    "text": "@username",
    "link": "https://instagram.com/...",
    "is_cover": true
  }]
}
```
- **Features**: 
  - Multiple parsing strategies (value object, direct JSON, string JSON)
  - Supports cover image flagging
  - Grid/carousel layout

### 3. `product.metafields.descriptors.*` - Product Descriptors

#### `product.metafields.descriptors.subtitle.value`
- **Purpose**: Product subtitle/caption
- **Format**: String
- **Usage**: Displayed in product template JSON as subtitle text block
- **Location**: Product title area, below vendor

### 4. `product.metafields.reviews.*` - Review System

#### `product.metafields.reviews.rating.value`
- **Purpose**: Product rating data
- **Format**: Object with `rating` (number) and `scale_max` (number)
- **Usage**: Rendered in product cards and main product page
- **Features**:
  - Calculates half-star ratings (0.3-0.7 = 0.5, >0.7 = 1)
  - CSS custom properties for star rendering
  - Accessible ARIA labels

#### `product.metafields.reviews.rating_count`
- **Purpose**: Number of reviews
- **Format**: Number
- **Usage**: Displayed alongside rating
- **Features**: Hidden from screen readers (shown with aria-hidden), accessible version in visually-hidden span

## Dynamic Rendering System

### Module Rendering Flow

The `main-product.liquid` section renders modules in a fixed order below the main product information:

```liquid
1. Image Row (image-row.liquid)
2. Image Row 2 (image-row-2.liquid)
3. Vertical Video (vertical-video.liquid)
4. Landscape Video (landscape-video.liquid) - Desktop only
5. UGC Content (ugc.liquid)
6. Vertical Image with Text (vertical-image-with-text.liquid)
7. Full Width Images (full-width-image.liquid) - Desktop only
8. Yotpo Reviews (static wrapper)
9. Related Products (related-products.liquid)
```

### Conditional Rendering Pattern

Each snippet follows this pattern:

```liquid
{% assign metafield = product.metafields.module.xxx %}
{% if metafield != blank %}
  <!-- Render content -->
{% endif %}
```

This ensures:
- Modules only render when data exists
- No empty/broken sections
- Graceful degradation for products without metadata

### JSON Parsing Strategy

The theme uses multiple parsing strategies to handle different metafield storage formats:

1. **Direct Value Access**: `metafield.value.entries`
2. **Direct Property Access**: `metafield.entries`
3. **JSON String Parsing**: `metafield | parse_json`
4. **JSON Serialization**: `metafield | json | parse_json`

This flexibility handles:
- Metafields stored as JSON strings
- Metafields stored as structured objects
- Metafields with nested value objects
- Legacy format compatibility

## Styling & Behavior Control

### Background Image System

The `product_detail_bg_image` metafield controls:
- **Desktop**: Fixed-position background covering right half of viewport
- **Mobile**: Inline image below product gallery
- **Implementation**: CSS `background-image` with fixed positioning

### Color Variant System

The color variant system (`color-variant.liquid`) provides:
- **Current Product**: Highlighted pill with border (border-2 border-gray-900)
- **Variant Products**: Clickable pills linking to variant products
- **Two-Tone Support**: Split-color pills using primary + secondary colors
- **Responsive**: Flexbox layout with margin spacing

### Responsive Behavior

Many modules adapt layout based on viewport:
- **Mobile**: Carousel/slider layouts with navigation controls
- **Desktop**: Grid layouts (2-4 columns based on content)
- **Breakpoint**: `lg:` (1024px) typically used as breakpoint

## Template Integration Points

### Product Template JSON

The `templates/product.json` file uses metafields in block settings:

```json
{
  "caption": {
    "type": "text",
    "settings": {
      "text": "{{ product.metafields.descriptors.subtitle.value }}",
      "text_style": "subtitle"
    }
  }
}
```

### Product Cards

Product cards (`card-product.liquid`) use:
- `card_product.metafields.reviews.rating.value` - Star ratings
- `card_product.metafields.reviews.rating_count` - Review counts

## Data Flow Example

### Color Variant Rendering Flow

1. **Extract Metafield**: `product.metafields.module.product_variants`
2. **Parse Entries**: Multiple parsing strategies to extract `entries` array
3. **Extract Current Colors**: `product.metafields.custom.primary_color` and `secondary_color`
4. **Render Current Pill**: Display current product's color with active styling
5. **Loop Variants**: For each entry in `entries`:
   - Extract product handle from URL
   - Load variant product via `all_products[handle]`
   - Extract variant's color metafields
   - Render clickable color pill linking to variant
6. **Output**: Flexbox row of color pills

### Related Products Flow

1. **Extract Metafield**: `product.metafields.module.related_products`
2. **Parse Entries**: Handle multiple JSON formats
3. **Sort**: Sort by `position` if available
4. **Filter**: Remove current product and duplicates
5. **Resolve Products**: Convert GIDs/URLs/handles to product objects
6. **Render**: Grid (desktop) or carousel (mobile) with product images

## Best Practices Observed

1. **Defensive Programming**: All metafield access wrapped in existence checks
2. **Default Values**: Sensible defaults provided (e.g., "#ffffff" for missing colors)
3. **Accessibility**: ARIA labels, visually-hidden text for screen readers
4. **Performance**: Lazy loading for images, conditional script loading
5. **Maintainability**: Clear namespace organization, documented snippets
6. **Flexibility**: Multiple parsing strategies handle various data formats

## Extension Points

### Adding New Modules

To add a new metadata-driven module:

1. Create snippet in `snippets/` directory
2. Access metafield: `product.metafields.module.your_module_name`
3. Parse and validate data
4. Render conditionally: `{% if metafield != blank %}`
5. Add render call in `main-product.liquid` after line 798

### Adding New Namespaces

Current namespaces:
- `module.*` - Content modules
- `custom.*` - Custom styling/content
- `descriptors.*` - Product descriptors
- `reviews.*` - Review system

New namespaces can be added following the same pattern.

## Current Limitations

1. **No Collection Metafields**: Collection-level metadata not currently used
2. **No Shop Metafields**: Shop-level metadata not currently used
3. **Fixed Module Order**: Module rendering order is hardcoded in `main-product.liquid`
4. **No Module Toggle**: All modules render if data exists (no enable/disable flag)

## Recommendations for Enhancement

1. **Dynamic Module Order**: Store module order in metafield
2. **Module Visibility Control**: Add enable/disable flags per module
3. **Collection-Level Overrides**: Use collection metafields for collection-wide settings
4. **Shop-Level Defaults**: Use shop metafields for theme-wide defaults
5. **Module Configuration**: Store module-specific settings (columns, spacing, etc.) in metafields
