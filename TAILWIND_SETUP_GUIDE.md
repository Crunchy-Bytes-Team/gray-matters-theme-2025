# 🎨 Tailwind CSS Setup Guide for Shopify Theme

This guide explains how to properly set up and use Tailwind CSS in your Shopify Liquid theme without prefixes.

## 📋 Current Setup Status

✅ **Tailwind CSS is properly configured and working!**

- Tailwind CSS v3.4.1 installed
- Configuration file: `tailwind.config.js`
- Source file: `assets/app-tailwind.css`
- Compiled file: `assets/app.css`
- CSS is loaded in `layout/theme.liquid`

## 🚀 Development Workflow

### 1. **Start Development Server**

```bash
# Start Shopify theme development server
npm run dev
# or
shopify theme dev --store=gray-matters-online-store.myshopify.com
```

### 2. **Compile Tailwind CSS**

#### **One-time compilation:**
```bash
npx tailwindcss -i ./assets/app-tailwind.css -o ./assets/app.css
```

#### **Watch mode (recommended for development):**
```bash
npx tailwindcss -i ./assets/app-tailwind.css -o ./assets/app.css --watch
```

#### **Production build:**
```bash
npx tailwindcss -i ./assets/app-tailwind.css -o ./assets/app.css --minify
```

### 3. **Development Commands**

```bash
# Install dependencies
npm install

# Start development with Tailwind watching
npx tailwindcss -i ./assets/app-tailwind.css -o ./assets/app.css --watch

# In another terminal, start Shopify dev server
npm run dev

# Upload theme to Shopify
npm run upload
```

## 🛠️ Configuration Details

### **Tailwind Config (`tailwind.config.js`)**
```javascript
module.exports = {
  content: [
    './layout/*.liquid',
    './templates/*.liquid',
    './templates/customers/*.liquid',
    './sections/*.liquid',
    './snippets/*.liquid',
  ],
  theme: {
    screens: {
      sm: '320px',
      md: '750px',
      lg: '990px',
      xlg: '1440px',
      x2lg: '1920px',
      pageMaxWidth: '1440px',
    },
    extend: {
      fontFamily: {
        heading: 'var(--font-heading-family)',
      },
    },
  },
  plugins: [],
};
```

### **CSS Files Structure**
- **Source**: `assets/app-tailwind.css` - Contains Tailwind directives
- **Compiled**: `assets/app.css` - Generated CSS with all utilities
- **Loaded in**: `layout/theme.liquid` line 307 (✅ **FIXED**: Now loads compiled CSS)

## 🔄 How Tailwind CSS Compilation Works

### **Understanding the Build Process**

Tailwind CSS uses a **purge-based compilation** system that automatically generates CSS for only the classes you actually use in your templates.

#### **✅ What Happens Automatically:**
- When you run `npm run tailwind:watch` or `npm run tailwind:build`, Tailwind scans your Liquid files
- It finds **only the Tailwind classes you actually use** in your templates
- It generates CSS for **only those specific classes** in `app.css`
- The CSS file stays small and optimized

#### **❌ What Does NOT Happen:**
- Tailwind does **NOT** include ALL possible classes by default
- It uses "purging" to keep the CSS file small and efficient
- Only classes found in your content files get compiled

#### **📋 Example:**

If your templates only use these classes:
```liquid
<div class="max-w-7xl mx-auto px-6">
  <h1 class="text-4xl font-bold">Title</h1>
</div>
```

Then `app.css` will only contain CSS for:
- `.max-w-7xl`
- `.mx-auto` 
- `.px-6`
- `.text-4xl`
- `.font-bold`

**NOT** for unused classes like `.text-5xl`, `.bg-red-500`, etc.

#### **🚀 Live Development Workflow:**

```bash
# Start watching for changes
npm run tailwind:watch

# Now when you add a new class like "bg-blue-500" to a template:
# 1. Tailwind detects the new class
# 2. Automatically adds the CSS for that class to app.css
# 3. Your new styling works immediately
```

#### **⚙️ If You Need ALL Classes Available:**

If you want all Tailwind classes available (useful for admin customization), you can modify your `tailwind.config.js` to include a safelist:

```javascript
module.exports = {
  content: [
    './layout/*.liquid',
    './templates/*.liquid',
    './templates/customers/*.liquid',
    './sections/*.liquid',
    './snippets/*.liquid',
  ],
  safelist: [
    {
      pattern: /.*/,
      variants: ['sm', 'md', 'lg', 'hover', 'group-hover'],
    },
  ],
  // ... rest of config
};
```

**Note:** This will make your CSS file much larger, so only use this if you need all classes available for admin customization.

## 📝 Using Tailwind Classes

### **Standard Classes (No Prefix)**
```liquid
<!-- Container with max width and auto margins -->
<div class="max-w-7xl mx-auto px-6 md:px-20">
  <!-- Content -->
</div>

<!-- Responsive grid -->
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
  <!-- Grid items -->
</div>

<!-- Typography -->
<h1 class="text-4xl font-bold text-gray-900 mb-8">
  Heading
</h1>

<!-- Buttons -->
<button class="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-md transition-colors">
  Click me
</button>
```

### **Responsive Breakpoints**
- `sm:` - 320px and up
- `md:` - 750px and up  
- `lg:` - 990px and up
- `xlg:` - 1440px and up
- `x2lg:` - 1920px and up

## 🚀 Publishing to Shopify

### **Pre-Publication Checklist**

1. **Compile CSS for Production:**
   ```bash
   npx tailwindcss -i ./assets/app-tailwind.css -o ./assets/app.css --minify
   ```

2. **Test Your Theme:**
   ```bash
   # Start development server to test
   npm run dev
   ```

3. **Upload to Shopify:**
   ```bash
   # Upload theme
   npm run upload
   
   # Or use Shopify CLI directly
   shopify theme push
   ```

### **GitHub Actions (Automatic)**

The theme includes GitHub Actions that automatically:
- Compile Tailwind CSS on every push
- Run theme checks
- Generate performance reports

**Workflow file**: `.github/workflows/ci.yml`

## 🔧 Troubleshooting

### **Common Issues**

#### **1. Tailwind Classes Not Working**
- ✅ **Solution**: Ensure `assets/app.css` is compiled and up-to-date
- Run: `npx tailwindcss -i ./assets/app-tailwind.css -o ./assets/app.css`

#### **2. Classes Not Recognized in Templates**
- ✅ **Solution**: Check that your template files are included in `tailwind.config.js` content array
- Current content paths are already configured correctly

#### **3. CSS Not Loading**
- ✅ **Solution**: Verify `app-tailwind.css` is loaded in `layout/theme.liquid`
- It's already configured on line 307

#### **4. Build Errors**
- ✅ **Solution**: Make sure dependencies are installed
- Run: `npm install`

#### **5. Classes Not Compiling**
- ✅ **Solution**: Ensure classes are in the correct file paths
- Check that your templates are in: `layout/`, `templates/`, `sections/`, `snippets/`
- Verify the class syntax is correct (no typos)

#### **6. CSS File Not Updating**
- ✅ **Solution**: Make sure you're running the watch command
- Run: `npm run tailwind:watch`
- Check that the compiled file `assets/app.css` exists and has recent timestamp

#### **7. "npm ERR! could not determine executable to run"**
- ✅ **Solution**: This usually means Tailwind CSS isn't properly installed
- Run: `npm install` to ensure all dependencies are installed
- Then try: `npx tailwindcss --version` to verify installation

### **Development Tips**

1. **Use Watch Mode**: Always run Tailwind in watch mode during development
2. **Check Browser DevTools**: Inspect elements to see if classes are applied
3. **Validate Classes**: Use Tailwind IntelliSense extension in VS Code
4. **Test Responsive**: Check all breakpoints during development

## 📁 File Structure

```
gray-matters-theme-2025/
├── assets/
│   ├── app-tailwind.css    # Source Tailwind file
│   └── app.css            # Compiled CSS (generated)
├── layout/
│   └── theme.liquid       # Main layout (loads CSS)
├── sections/              # Liquid sections
├── templates/             # Page templates
├── snippets/              # Reusable snippets
├── tailwind.config.js     # Tailwind configuration
├── package.json           # Dependencies
└── TAILWIND_SETUP_GUIDE.md # This guide
```

## 🎯 Best Practices

### **1. Class Organization**
```liquid
<!-- Group related classes together -->
<div class="
  max-w-7xl mx-auto px-6 md:px-20
  bg-white shadow-lg rounded-lg
  py-8 md:py-12
">
```

### **2. Responsive Design**
```liquid
<!-- Mobile-first approach -->
<div class="
  text-sm md:text-base lg:text-lg
  p-4 md:p-6 lg:p-8
  grid-cols-1 md:grid-cols-2 lg:grid-cols-3
">
```

### **3. Component Reusability**
```liquid
<!-- Create reusable component classes -->
{% assign button_classes = 'px-6 py-3 rounded-md font-medium transition-colors' %}
<button class="{{ button_classes }} bg-blue-600 hover:bg-blue-700 text-white">
  Primary Button
</button>
```

## 🔄 Workflow Summary

### **Daily Development:**
1. Start Tailwind watch: `npx tailwindcss -i ./assets/app-tailwind.css -o ./assets/app.css --watch`
2. Start Shopify dev: `npm run dev`
3. Make changes to Liquid templates
4. Add Tailwind classes as needed
5. Test in browser

### **Before Publishing:**
1. Compile production CSS: `npx tailwindcss -i ./assets/app-tailwind.css -o ./assets/app.css --minify`
2. Test thoroughly
3. Upload: `npm run upload`

---

## 🆘 Need Help?

- **Tailwind CSS Docs**: https://tailwindcss.com/docs
- **Shopify Liquid Docs**: https://shopify.dev/docs/api/liquid
- **Theme Development**: https://shopify.dev/docs/themes

**Happy coding! 🎨✨**
