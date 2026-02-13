# Product Metafields Quick Reference

## Quick Lookup Table

| Metafield Path | Type | Purpose | Snippet | Required |
|---------------|------|---------|---------|----------|
| `product.metafields.module.product_variants` | JSON | Color variant relationships | `color-variant.liquid` | No |
| `product.metafields.module.product_detail_bg_image` | Image URL | Product page background | `main-product.liquid` | No |
| `product.metafields.module.related_products` | JSON | Related products list | `related-products.liquid` | No |
| `product.metafields.module.full_width_images` | JSON | Full-width image gallery | `full-width-image.liquid` | No |
| `product.metafields.module.image_row_module_image1` | Image URL | Image row image 1 | `image-row.liquid` | No |
| `product.metafields.module.image_row_module_image2` | Image URL | Image row image 2 | `image-row.liquid` | No |
| `product.metafields.module.image_row_module_image3` | Image URL | Image row image 3 | `image-row.liquid` | No |
| `product.metafields.module.image_row_module_image4` | Image URL | Image row image 4 | `image-row.liquid` | No |
| `product.metafields.module.video_module_video` | Video URL | Landscape video embed | `landscape-video.liquid` | No |
| `product.metafields.module.video_module_video_mobile` | Video URL | Vertical video embed | `vertical-video.liquid` | No |
| `product.metafields.module.image_text_module_image` | Image URL | Image-with-text module | `vertical-image-with-text.liquid` | No |
| `product.metafields.module.image_text_module_header` | String | Image-with-text header | `vertical-image-with-text.liquid` | No |
| `product.metafields.module.image_text_module_description` | String | Image-with-text description | `vertical-image-with-text.liquid` | No |
| `product.metafields.custom.primary_color` | Hex Color | Primary color for variant pills | `color-variant.liquid` | No |
| `product.metafields.custom.secondary_color` | Hex Color | Secondary color for variant pills | `color-variant.liquid` | No |
| `product.metafields.custom.ugc_content` | JSON | User-generated content | `ugc.liquid` | No |
| `product.metafields.descriptors.subtitle.value` | String | Product subtitle | `templates/product.json` | No |
| `product.metafields.reviews.rating.value` | Object | Product rating | `main-product.liquid`, `card-product.liquid` | No |
| `product.metafields.reviews.rating_count` | Number | Review count | `main-product.liquid`, `card-product.liquid` | No |

## JSON Structure Examples

### product_variants
```json
{
  "entries": [
    {
      "url": "https://www.graymattersnyc.com/products/product-handle",
      "gid": "gid://shopify/Product/1234567890",
      "product_id": 123
    }
  ]
}
```

### related_products
```json
{
  "entries": [
    {
      "gid": "gid://shopify/Product/1234567890",
      "url": "https://www.graymattersnyc.com/products/product-handle",
      "handle": "product-handle",
      "position": 1
    }
  ]
}
```

### full_width_images
```json
{
  "entries": [
    {
      "url": "https://cdn.shopify.com/...",
      "order": 1
    }
  ]
}
```

### ugc_content
```json
{
  "entries": [
    {
      "image": "https://cdn.shopify.com/...",
      "text": "@username",
      "link": "https://instagram.com/...",
      "is_cover": true
    }
  ]
}
```

### reviews.rating.value
```json
{
  "rating": 4.5,
  "scale_max": 5
}
```

## Usage Patterns

### Basic Access Pattern
```liquid
{% assign metafield = product.metafields.module.xxx %}
{% if metafield != blank %}
  {% assign value = metafield.value %}
  <!-- Use value -->
{% endif %}
```

### JSON Parsing Pattern
```liquid
{% assign metafield = product.metafields.module.xxx %}
{% if metafield != blank %}
  {% if metafield.value.entries != blank %}
    {% assign entries = metafield.value.entries %}
  {% elsif metafield.entries != blank %}
    {% assign entries = metafield.entries %}
  {% else %}
    {% assign parsed = metafield | parse_json %}
    {% if parsed.entries != blank %}
      {% assign entries = parsed.entries %}
    {% endif %}
  {% endif %}
{% endif %}
```

### Color with Default Pattern
```liquid
{% assign primary_color = product.metafields.custom.primary_color | default: '#ffffff' %}
```

## Rendering Order in main-product.liquid

1. Main product info (title, price, form, etc.)
2. `image-row` snippet
3. `image-row-2` snippet
4. `vertical-video` snippet
5. `landscape-video` snippet (desktop only)
6. `ugc` snippet
7. `vertical-image-with-text` snippet
8. `full-width-image` snippet (desktop only)
9. Yotpo reviews wrapper
10. `related-products` snippet

## Namespace Organization

- **`module.*`**: Content modules that appear below product info
- **`custom.*`**: Custom styling and content (colors, UGC)
- **`descriptors.*`**: Product descriptive text
- **`reviews.*`**: Review and rating data

## Common Gotchas

1. **Metafield Format Variations**: Some metafields may be stored as JSON strings, others as structured objects. Always use multiple parsing strategies.

2. **Value Access**: Some metafields use `.value`, others don't. Check both patterns.

3. **Blank Checks**: Always check for `blank` before accessing nested properties to avoid Liquid errors.

4. **Product Resolution**: When using URLs in metafields, extract the handle carefully (split by `/products/`, remove query params and fragments).

5. **Default Values**: Provide sensible defaults for colors and text to ensure graceful degradation.
