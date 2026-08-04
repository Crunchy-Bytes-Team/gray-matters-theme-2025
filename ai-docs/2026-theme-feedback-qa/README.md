# QA screenshot — feedback tema 2026

Confronti **live** ([graymattersnyc.com](https://www.graymattersnyc.com/)) vs **locale** (`http://127.0.0.1:9292`) dopo le correzioni.

**Prodotto di riferimento:** [Clara Pumps in Taupe](https://www.graymattersnyc.com/products/clara-pumps-taupe) (`/products/clara-pumps-taupe`).

## Struttura

| Cartella | Area | File principali |
|----------|------|-----------------|
| `01-product-page/` | PDP — CTA, prezzo, descrizione, breadcrumbs, size select | `pdp-clara-desktop.png`, `pdp-clara-mobile.png` (+ legacy `pdp-buco-*`) |
| `02-catalogue/` | Griglia collection + overlay big card | `catalogue-all-desktop.png` |
| `03-signup-popup/` | Newsletter popup (no hCaptcha) | `newsletter-popup.png` |
| `04-header/` | Top nav / logo / icone | `header-home-desktop.png`, `header-area-from-pdp.png` |
| `05-search-bar/` | Popular Searches | `search-bar.png` |
| `06-image-text/` | Modulo image+text “Like a Princess” | `like-a-princess.png` |
| `07-footer/` | Footer colonne + newsletter | `footer-desktop.png` |
| `08-announcement/` | Announcement bar (crop top) | `with-announcement-bar.png` |

Ogni cartella ha `live/` e `local/`.

## Stato set (2026-08-04)

| Area | Live | Local | Note |
|------|------|-------|------|
| PDP Clara desktop | OK | OK | Panel bottom, lifestyle bg, Select size + chevron, CTA sopra link |
| PDP Clara mobile | OK | OK | Layout fixed bottom allineato |
| Catalogue | OK | OK | Gap 6px, Sale nascosto |
| Signup popup | OK | OK | Locale: honeypot presente, hCaptcha assente |
| Header | OK | OK | Home locale tipicamente “light” (hero video); crop PDP per confronto tipografia |
| Search | OK | OK | Popular Searches visibile |
| Image+text | OK | OK | Like a Princess / For one day |
| Footer | OK | OK | CLIENT SERVICES plurale |
| Announcement | OK | OK | Barra blu attiva |

## Verifiche chiave (misurate)

| Check | Live | Locale (post-fix) |
|-------|------|---------------------|
| Nav font | 11.5px / 0.8px | 11.5px / 0.8px |
| Label nav | CLIENT SERVICES | CLIENT SERVICES |
| Icon padding | ~10px | ~9.75–12px |
| Catalogue gap | 6px | 6px |
| Big card title | 48px white / 1.25px | 48px white / 1.25px |
| Sale badge card | assente | nascosto |
| PDP CTA disabled | nero | nero + testo #d9d9d9 |
| PDP prezzo ordine | sale → compare | sale → compare |
| PDP descrizione scroll | no | no (`max-height: none`) |
| Shipping links | sotto CTA | sotto CTA |
| Size label | Select size | Select size (12.5px / 700 / top -20px) |
| Announcement bar | sì | abilitata (header-group settings) |
| hCaptcha popup | — | nascosto via CSS + honeypot |

## Residuo noto

- Larghezza **Add to Bag** sul desktop locale resta un po’ più larga del live (~360 vs ~293) perché il pannello info locale ha un’area contenuto più ampia; layout CTA + size select è comunque allineato.

## Note operative

- Preview locale: `npm run dev` → `http://127.0.0.1:9292`
- Dopo modifiche Tailwind: `npm run tailwind:build`
- Hover catalogue: overlay grigio `#6b6b6b` @ 55%
