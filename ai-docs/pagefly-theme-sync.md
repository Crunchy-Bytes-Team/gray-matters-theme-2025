# PageFly after a new theme publish

1. In **PageFly**, open each managed page and **Publish** (or bulk sync) targeting the **current live theme** so PageFly generates `page.pf-*` templates, `pf-*` snippets, and CSS assets in that theme.
2. In **Shopify Admin → Online Store → Pages**, for any page that stays blank, set **Theme template** to **pagefly** (uses [`templates/page.pagefly.json`](../templates/page.pagefly.json)) until PageFly has published a dedicated `page.pf-*` template for that page.
3. Confirm [`layout/theme.liquid`](../layout/theme.liquid) includes `{% render 'pagefly-app-header' %}` after `{{ content_for_header }}` so PageFly CSS/JS load on those routes.
