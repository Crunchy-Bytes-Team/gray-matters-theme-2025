# HTML Style Guide

## Structure Rules
- Use 2 spaces for indentation
- Place nested elements on new lines with proper indentation
- Content between tags should be on its own line when multi-line

## Attribute Formatting
- Place each HTML attribute on its own line
- Align attributes vertically
- Keep the closing `>` on the same line as the last attribute
- In case we are using Slim template engine, remember to add a `\` character at the end of the line, in case of multi-line attributes

## Example HTML Structure

```html
<div class="container">
  <header class="flex flex-col space-y-2
                 md:flex-row md:space-y-0 md:space-x-4">
    <h1 class="text-primary dark:text-primary-300">
      Page Title
    </h1>
    <nav class="flex flex-col space-y-2
                md:flex-row md:space-y-0 md:space-x-4">
      <a href="/"
         class="btn-ghost">
        Home
      </a>
      <a href="/about"
         class="btn-ghost">
        About
      </a>
    </nav>
  </header>
</div>
```

## Example Slim Structure
```Slim
.bg-surface.rounded-lg.shadow-sm.border.border-primary.p-8
  = simple_form_for @manuscript, url: web_manuscripts_path, html: { class: 'space-y-6' } do |f|
    = f.error_notification
    / Basic Information
    .space-y-6
      h3.text-lg.font-medium.text-primary.border-b.border-primary.pb-3 = t('manuscripts.basic_information')
      
      .grid.grid-cols-1.gap-6
        = f.input :title,
          label: t('manuscripts.title'), \
          input_html: { \
            class: 'block w-full border border-primary rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent',\
            placeholder: t('manuscripts.title_placeholder')\
          },\
          required: true,\
          wrapper_html: { class: 'space-y-2' }
```