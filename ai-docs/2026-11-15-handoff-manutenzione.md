---
okf_version: '0.2'
type: Architecture Note
title: Gray Matters theme 2025 — handoff per la manutenzione
description: Guida operativa del tema Shopify Gray Matters 2025 per chi lo mantiene, con architettura, convenzioni e correzioni da agosto a novembre 2026.
tags:
  - gray-matters-theme-2025
  - shopify
  - handoff
  - architecture
status: stable
generated:
  by: agent:cursor
  profile: cursor
  at: '2026-11-15T10:30:00+01:00'
  tools:
    - id: cursor
      role: orchestration-and-authoring
    - id: git
      role: source-retrieval
request_origin:
  requested_by: human:davide-cenzi
  received_at: '2026-11-15T10:30:00+01:00'
  source_kind: other
  source_ref: cursor:workspace:gray-matters-theme-2025:request:2026-11-15T10:30:00+01:00
  source_url: null
  parent_ref: null
  capture_mode: verbatim
sources:
  - id: repo
    resource: file:///Volumes/ExtremeSSD/projects/gray-matters-theme-2025
  - id: git
    resource: git@github.com:Crunchy-Bytes-Team/gray-matters-theme-2025.git
  - id: feedback
    resource: file:///Volumes/ExtremeSSD/projects/gray-matters-theme-2025/ai-docs/2026-theme-feedback-interventi.md
  - id: qa
    resource: file:///Volumes/ExtremeSSD/projects/gray-matters-theme-2025/ai-docs/2026-theme-feedback-qa/README.md
  - id: parity
    resource: file:///Volumes/ExtremeSSD/projects/gray-matters-theme-2025/ai-docs/2026-10-12-parity/README.md
  - id: metafields
    resource: file:///Volumes/ExtremeSSD/projects/gray-matters-theme-2025/.agent-os/product/metafields-quick-reference.md
  - id: live
    resource: https://www.graymattersnyc.com/
---

# Richiesta originaria

> Preparami un documento markdown che presenta in modo dettagliato il progetto, i dettagli tecnici, tutte le recenti correzioni, ecc.
>
> Devo farlo studiare ad un developer che manterrà il progetto di qui in avanti.
>
> Salva il file nella subfolder ai-docs

# Sintesi per operatori

- **Attività:** è stata preparata una guida di passaggio del tema del sito Gray Matters, pensata per chi lo aggiornerà da ora in poi.
- **Risultato:** la guida descrive come è fatto il tema, come si lavora in locale, cosa è stato corretto di recente e quali differenze con il sito pubblico restano aperte.
- **Dubbi o domande:** prima di pubblicare il tema sullo store va ancora deciso se accettare le due differenze visive già note (larghezza del selettore lingua e larghezza del pulsante di acquisto) e va ripetuto il controllo visivo sul sito di anteprima.

# Interpretazione operativa

- **Obiettivo:** dare a un developer nuovo sul progetto un quadro verificabile del tema, delle convenzioni e delle correzioni recenti, senza dover ricostruire la storia dai commit.
- **Output richiesto:** un file Markdown nella cartella `ai-docs` del repository.
- **Vincoli espliciti:** il documento deve presentare il progetto, i dettagli tecnici e le correzioni recenti, e deve stare in `ai-docs`.

# Come usare questo documento

Questo è il punto di ingresso per chi mantiene il tema. È aggiornato al commit `be6fa34` sul branch `develop` (13 novembre 2026). I fatti sotto sono stati riletti dal repository in quella data.

Leggere nell’ordine:

1. Identità e confini del lavoro.
2. Come si avvia il tema e come si pubblica.
3. Architettura (CSS, Liquid, metafield, moduli prodotto).
4. Correzioni recenti, in ordine cronologico.
5. Residui noti e regole da non rompere.
6. Dove trovare le prove visive e gli strumenti di audit.

Il `README.md` in root è il readme dello starter Trellis/Dawn. Diverse istruzioni lì dentro non valgono più per questo tema. In particolare **non** esiste il prefisso Tailwind `twcss-`: una ricerca nel codice trova quella stringa solo nel README.

Lo standard `.agent-os/standards/tech-stack.md` descrive uno stack Rails generico e non questo progetto. Ignorarlo.

# Identità del progetto

Gray Matters è un tema Shopify Online Store 2.0 per lo storefront [graymattersnyc.com](https://www.graymattersnyc.com/). Il punto di partenza è Dawn 15.2.0 con l’integrazione Tailwind dello starter Trellis. Sopra quella base c’è un layer Gray Matters: tipografia Proxima e Stanley, header e footer custom, scheda prodotto guidata da metafield, catalogue, newsletter, menu mobile e homepage PageFly.

| Cosa | Valore |
|------|--------|
| Repository | `git@github.com:Crunchy-Bytes-Team/gray-matters-theme-2025.git` |
| Checkout di lavoro | `/Volumes/ExtremeSSD/projects/gray-matters-theme-2025` |
| Branch di lavoro | `develop`, tracciato su `origin/develop` |
| Commit di riferimento di questo documento | `be6fa34` (2026-11-13) |
| Store di sviluppo dello script `npm run dev` | `gray-matters-online-store.myshopify.com` |
| Store nominato in `quick-help.md` | `crunchy-dev-store.myshopify.com` |
| Sito live (fonte di verità visiva) | `https://www.graymattersnyc.com/` |
| Anteprima locale abituale | `http://127.0.0.1:9292` |
| Tema preview registrato nell’audit | id `187054457141`, parametro `preview_theme_id` |

Il documento `project.md` (19 settembre 2026) indica ancora la directory `/Users/operator/Documents/projects/gray-matters-theme-2025` e `main` come branch predefinito remoto. Il checkout attuale è sul volume esterno e il lavoro recente è su `develop`. Prima di un merge verso `main`, verificare su GitHub quale branch è protetto.

Al momento della stesura, `develop` è allineato a `origin/develop`. L’unica differenza locale nota è la cartella non tracciata `ai-docs/2026-10-12-parity/` (report e screenshot di parità del 12–13 ottobre).

# Cosa significa “allineare al live”

Il tema in produzione oggi è il tema precedente. Questo repository è il tema nuovo. Il lavoro degli ultimi mesi non è un redesign: è la riproduzione del comportamento e dell’aspetto del sito live, usando le primitive del tema nuovo.

Regole usate fin qui:

- Il sito live è la misura. Le screenshot in `ai-docs/2026 theme feedback/` sono le richieste della cliente; i valori CSS si misurano sul live, non si copiano dal CSS legacy.
- Si riproduce l’aspetto con Tailwind e con `assets/custom.css`. Non si reimporta il foglio di stile del tema vecchio.
- Desktop di riferimento per i confronti manuali: 1440 px. Mobile di riferimento: 390 px. Il taglio mobile/desktop del tema è 989 / 990 px.
- Dove una stringa visibile arriva da un menu, da una traduzione o da un metafield Shopify, non si “corregge” nel CSS. Esempio: «LadyGray Club» sul live e «Lady Gray Club» nel tema nuovo sono il titolo del link in navigazione, non uno spazio CSS.

# Avvio, build e pubblicazione

Dipendenze Node (dev): Tailwind CSS 3.4, PostCSS, Autoprefixer, Prettier (`@trelliscommerce/prettier-config`), Husky, lint-staged. Non c’è una test suite JavaScript del tema (`npm test` esce con errore voluto). I test automatici stanno nell’audit Python `audits/store-parity`.

```bash
npm install
npm run dev
```

`npm run dev` esegue:

```bash
shopify theme dev --store=gray-matters-online-store.myshopify.com
```

Shopify CLI crea o aggiorna un development theme e serve l’anteprima, di solito su `http://127.0.0.1:9292`. Sul localhost il banner privacy Shopify (`#shopify-pc__banner`) viene nascosto da uno script in `layout/theme.liquid`, così non copre header e popup durante i confronti.

Build CSS:

| Script | Effetto |
|--------|---------|
| `npm run tailwind:watch` | Ricompila `assets/app.css` a ogni modifica Liquid |
| `npm run tailwind:build` | Compilazione una tantum |
| `npm run tailwind:prod` | Come build, con minify |

`assets/app-tailwind.css` contiene solo le tre direttive `@tailwind`. Le utility nascono dalle classi scritte nei file Liquid. `tailwind.config.js` scansiona `layout`, `templates`, `templates/customers`, `sections` e `snippets`. Una classe scritta solo in un file `.css` o `.js` non entra nel build.

`assets/app.css` è output generato. I commit storici lo modificano perché qualcuno ha rilanciato il build oppure ha patchato il file a mano. Una patch a mano in `app.css` sparisce al prossimo `tailwind:build`. Le regole di parità visiva stabili stanno in `assets/custom.css` e, per il menu mobile, in `assets/mobile-menu.css`.

Pubblicazione, dai promemoria già nel repo:

```bash
shopify theme push --store crunchy-dev-store.myshopify.com --theme gray-matters --unpublished
shopify theme publish --store crunchy-dev-store.myshopify.com --theme <NEW_THEME_ID>
```

`npm run upload` è `shopify theme share`. Prima di un push, `shopify theme list` conferma store e id. Il tema live di produzione non va pubblicato da questo flusso senza una decisione esplicita: il live è ancora il tema precedente, e questo repository è il candidato che lo deve sostituire.

Dopo una pubblicazione del tema, le pagine PageFly vanno ripubblicate sull’tema corrente. Vedi la sezione PageFly.

Husky formatta `*.js` e `*.css` con Prettier al commit. I file Liquid non passano da quella pipeline.

# Architettura

## Albero che conta

```
layout/theme.liquid          documento, font, ordine CSS, script globali
sections/header.liquid        header desktop, search, icone
sections/header-group.json    announcement bar e impostazioni header
snippets/mobile-menu.liquid   cassetto mobile
snippets/message-bar.liquid   alternanza delle due frasi della barra blu
sections/footer.liquid        colonne, form, popup newsletter
assets/footer.js              accordion footer sotto i 990 px
sections/main-product.liquid  scheda prodotto e ordine dei moduli
snippets/card-product.liquid  card catalogue, hover, prezzi
snippets/collection-all.liquid
snippets/collection-standard.liquid
sections/cart-drawer.liquid
assets/cart-drawer.css
assets/cart-drawer.js
templates/*.json              composizione sezioni per route
config/settings_data.json     valori del theme editor
```

File da non usare come sorgente: `sections/header-old.liquid`, `sections/header-bak.liquid`, `sections/footer-old.liquid`, `snippets/card-product copy.liquid`, `css-backup/`. Sono copie di transizione.

## Ordine dei fogli di stile

In `layout/theme.liquid`, dopo `content_for_header`:

1. Sulla sola homepage, `{% render 'pagefly-main-css' %}`.
2. `assets/app.css` (Tailwind compilato).
3. `@font-face` inline per Stanley e per quattro file Proxima (Regular, Bold, ExtraBold, SemiBold). I `@font-face` stanno nel layout perché un asset `.css` servito da Shopify non processa Liquid.
4. `assets/custom.css`.
5. `assets/mobile-menu.css`.
6. `component-cart-items.css` in caricamento differito.

`custom.css` arriva dopo Tailwind, quindi vince a parità di specificità. Molte correzioni di parità usano comunque `!important`, perché utility e stati Dawn (`disabled`, hover, ring) restano aggressivi.

## Tipografia e unità

`html { font-size: 0.8125rem; }` fissa la base a 13 px. Da quel momento `1rem` nel tema vale 13 px, non 16. Qualsiasi utility Tailwind espressa in `rem` (padding, font-size, gap) risulta più piccola del valore “da documentazione Tailwind”. Quando si misura il live, confrontare pixel calcolati, non la classe.

| Famiglia | Uso |
|----------|-----|
| `proxima-reg` | corpo, default di `body` |
| `proxima-semi-bold` | titoli di modulo su mobile, enfasi in descrizione |
| `proxima-bold` / `proxima-xbold` | pesi forti |
| `Stanley` (classe `.font-accent`) | titoli display, heading dei moduli da 990 px in su |

Classi utili già in `custom.css`: `.text-15`, `.text-dark-gray` (`#222323`), `.text-light-gray` (`#a5a5a5`).

Il grigio `#a5a5a5` è il colore hover di alcuni link secondari. Non va applicato alle voci primarie del menu mobile (Collection, Language, Client Services): quelle restano `#333` anche in hover. Le voci utility del menu (ricerca, account, Instagram) possono andare a `#a5a5a5` in hover.

## Breakpoint

`tailwind.config.js` non usa il prefisso e ridefinisce gli schermi:

| Token | Min-width |
|-------|-----------|
| `sm` | 320 px |
| `md` | 750 px |
| `lg` | 990 px |
| `xlg` | 1440 px |
| `x2lg` | 1920 px |
| `pageMaxWidth` | 1440 px |

Il CSS scritto a mano usa quasi sempre `@media (max-width: 989px)` come mondo mobile e `@media (min-width: 990px)` come desktop. `assets/footer.js` rifiuta l’accordion quando `window.innerWidth >= 990`. Ci sono anche soglie locali diverse: la popup newsletter cambia a 761 px, l’animazione della barra annuncio a 767 px, alcuni blocchi prodotto a 1024 px. Prima di introdurre un nuovo taglio, cercare il modulo e riusare la soglia già sua.

L’audit di parità sonda anche 749/750, 989/990/991 e 1024/1025, perché sono i punti in cui un `max-width` e un `min-width` si danno il cambio.

## Header e barra annuncio

La fascia blu non è l’announcement bar Dawn. È la message bar dell’header, configurata in `sections/header-group.json`:

- Sfondo `#1f86e7`, testo bianco.
- Frase principale: spedizione gratuita (`FREE GLOBAL SHIPPING STARTING AT $400 / €450 / £400 / CAD 600...`).
- Frase alternativa: `♡ WE SHIP FROM ITALY AND THE US ♡`.
- Entrambe puntano a `/pages/client-services`.
- `fade_animation: true`. `snippets/message-bar.liquid` alterna le due frasi con un fade. Se manca testo o link alternativo, o se il fade è spento, resta il comportamento precedente.

Desktop: fascia bianca alta circa 45 px, voci Collection / Select language / Client Services, icone Instagram, account, ricerca, carrello. La nav è 11.5 px con letter-spacing 0.8 px. L’etichetta è il plurale `CLIENT SERVICES`. La lente di ricerca è il glifo del sito live, non l’icona Dawn.

Mobile: fascia bianca 70 px, hamburger, logo, carrello. Il cassetto è 285 px (`assets/mobile-menu.css`, commento che cita `.wsmain { max-width: 285px }` del live), fondo grigio, voci con il più, poi ricerca, account e Instagram. L’icona ricerca del cassetto è un SVG pieno, tratto spesso, più compatto di quella Dawn.

La dropdown Client Services tiene i contatti in maiuscolo (`EMAIL`, `MON-FRI 10AM-6PM EST`), allineati ai link già uppercase sotto il separatore.

## Footer e newsletter

Quattro colonne: Company, Client Services, Connect, News. Su desktop hanno larghezza, ritmo verticale dei link, form sottolineato, pulsante Sign up e riga copyright misurati sul live.

Sotto i 990 px:

- Company, Client Services e Connect sono accordion chiusi. Il pulsante ha `border-bottom: 1px solid #d2d2d2`.
- News non è un accordion. Il titolo News non ha quella riga. Il form è già aperto.
- Il rientro di titoli e form è 15 px a sinistra e 45 px a destra (`padding: 15px 45px 15px 15px`).
- Tra il pulsante Sign up e il copyright lo spazio verticale è quello del live (circa 17 px nel controllo del 13 ottobre).

`assets/footer.js` gestisce solo l’accordion Company in modo esplicito sul resize: sopra i 990 px azzera `max-height`, sotto la riporta a 0. Un cambiamento all’elenco delle colonne va verificato anche in quel listener, non solo nel Liquid.

Il form newsletter ha un honeypot (classe `tripwire`, fuori dal layout). Il badge hCaptcha è nascosto in `custom.css` (`.hcaptcha-badge`, iframe `hcaptcha.com`). La decisione di review è: protezione non invasiva, niente challenge visibile.

La popup:

- Da 761 px in su: box 400×295 px, in basso a destra.
- Sotto: larghezza 95%, stacco 20 px dal bordo basso.
- Etichetta taglia: «Shoe Size».
- Stessi campi e stesso pulsante del form footer.

## Catalogue

Griglia con gap 6 px, misurato sul live. L’overlay hover della card è grigio `#6b6b6b` al 55%, non un velo nero. Il badge «Sale» è nascosto in `snippets/card-product.liquid` (commento nel file: lo sconto si comunica solo con i prezzi). L’ordine è prezzo scontato e poi compare-at barrato.

Sulla card grande di collection, titolo 48 px, bianco, letter-spacing 1.25 px. Posizione e colore devono coincidere a riposo e in hover.

## Scheda prodotto

`sections/main-product.liquid` compone la pagina in quest’ordine:

1. Breadcrumbs (`snippets/breadcrumbs.liquid`). Sotto i 989 px i breadcrumbs sono `display: none`. Desktop: 11.5 px, letter-spacing 0.5 px.
2. Galleria (`product-media-gallery`).
3. Pannello info: titolo, prezzo (`snippets/price.liquid`, badge disattivati), varianti colore (`color-variant`), form e `buy-buttons`.
4. Size guide e inquire modal.
5. Moduli sotto la piega, condizionati dai metafield (vedi sotto).
6. Related products.

Decisioni di prodotto già chiuse:

- Add to Bag sta in alto, accanto a Select size, come nel tema live. Non è sticky. Su una descrizione molto lunga la CTA può finire sotto la piega: è accettato.
- Select size: label sopra il campo, 12.5 px, peso 700, offset top −20 px; il select è 12 px / peso 300, largo 150 px, con chevron.
- Disabled: sfondo nero `#000`, testo `#d9d9d9`, `cursor: not-allowed`. Attivo: nero con testo bianco. La regola vive in `custom.css` su `.add_to_cart_button .product-form__submit:disabled` e batte il grigio Dawn.
- Descrizione: `.product-desc-scrollbar { max-height: none; }`. Niente scrollbar interna. Il grassetto della descrizione usa `proxima-semi-bold` per un problema di rendering su Chrome.
- Prezzo: prima lo sale, poi il compare barrato. Stesso ordine in card e in PDP.
- Lo sfondo lifestyle (`product_detail_bg_image`) è un contenitore fixed dietro le bande prodotto, non uno sfondo che scorre con il testo.

Larghezza desktop del bottone Add to Bag: nel QA di agosto il locale era circa 360 px contro circa 293 px del live, perché il pannello info locale è più largo. Il layout (CTA + size select) è considerato allineato. Non “stringere il bottone” senza rimisurare il pannello.

## Moduli sotto la scheda prodotto

Sono guidati da metafield. Se il metafield manca, il modulo non viene renderizzato. I parser in `color-variant.liquid` e `related-products.liquid` accettano più forme (`.value.entries`, `.entries`, stringa JSON): i dati storici dello store non sono uniformi. Non semplificare il parser a un solo accesso.

Ordine di render in `main-product.liquid` (dopo il pannello):

| Modulo | Snippet | Metafield principale |
|--------|---------|----------------------|
| Image row | `image-row`, `image-row-2` | `module.image_row_module_image1` … `image4` |
| Video landscape | `landscape-video` | `module.video_module_video` |
| Video portrait | `vertical-video`, `vertical-video-2` | `module.video_module_video_mobile` |
| UGC legacy | `legacy-ugc-band` | prefissi `ugc_module` e `ugc2_module` |
| UGC | `ugc` | `custom.ugc_content` |
| Image + text | `vertical-image-with-text` | `module.image_text_module_*` |
| Full width | `full-width-module-single-image` | `module.full_width_images` |
| Related | `related-products` | `module.related_products` |
| Colore varianti | `color-variant` | `module.product_variants`, più `custom.primary_color` e `custom.secondary_color` |
| Sfondo PDP | inline in `main-product.liquid` | `module.product_detail_bg_image` |

Dettaglio video (commit del 17 settembre): su mobile si privilegia il video portrait. Il landscape non fa da fallback mobile se il portrait c’è. Le classi di visibilità dei due snippet dipendono dagli URL realmente presenti.

Image + text (commit del 13 novembre): la colonna testo è un flex centrato. Lo stack ha `gap: 17.5px` e padding verticale 20 px sotto i 990 px; da 990 px in su il testo è allineato a sinistra e il padding della colonna torna a zero. I titoli di banda (`.module-band-heading`) sono Proxima 14 px centrati su mobile e Stanley 1.25 rem da 990 px.

Recensioni: `.yotpo-review-snippet { min-height: 100px; }`. Anche senza recensioni resta la banda bianca che separa «You may also like». L’altezza del wrapper Yotpo è stata ritoccata in `theme.liquid` nello stesso commit.

La scheda completa dei metafield, con gli esempi JSON, è in `.agent-os/product/metafields-quick-reference.md` e in `.agent-os/product/metadata-architecture-analysis.md`. Namespace usati: `module` (contenuti), `custom` (colori e UGC), `descriptors` (sottotitolo), `reviews` (rating). Non risultano metafield di collection o di shop usati dal tema per questo sistema.

## Carrello

Il mini cart desktop è un pannello da 400 px agganciato a destra, che sposta la pagina. Titolo `YOUR CART`, chiusura a X, riga di separazione, testo del carrello vuoto allineato per dimensione, peso e colore. Stili in `assets/cart-drawer.css`, comportamento in `assets/cart-drawer.js`. Il template carrello è `templates/cart.json`; le righe sono `sections/main-cart-items.liquid`.

Il commit del 9 ottobre ha allineato anche il carrello mobile al live, insieme a header, catalogue, PDP, footer e newsletter.

## PageFly

La homepage di produzione è costruita con PageFly. Nel tema:

- `snippets/pagefly-main-css.liquid` è il CSS base PageFly, incluso da `theme.liquid` solo quando `template.name == 'index'`.
- `snippets/pagefly-app-header.liquid` esiste e sa scegliere `pf-home-css`, `pf-product-css`, `pf-collection-css` e i template `pf-*`, ma **non è renderizzato** da `layout/theme.liquid`. La nota in `ai-docs/pagefly-theme-sync.md` chiede di includerlo dopo `content_for_header`. Oggi quell’include non c’è.
- `templates/page.pagefly.json` è il template di riserva per una pagina il cui template dedicato non è ancora stato pubblicato.
- Sezioni: `pagefly-home.liquid`, `pagefly-render-section.liquid`.

Procedura dopo un publish del tema, da `ai-docs/pagefly-theme-sync.md`:

1. In PageFly, pubblicare ogni pagina gestita verso il tema live corrente, così PageFly rigenera template `page.pf-*`, snippet `pf-*` e CSS dentro quel tema.
2. In Shopify Admin, per una pagina che resta bianca, impostare il template su `pagefly` finché non esiste il `page.pf-*` dedicato.
3. Verificare che gli asset PageFly arrivino davvero sulla route. Oggi il CSS base è caricato in homepage; l’header snippet completo no.

## Lingue

`locales/en.default.json` e `locales/it.json` sono stati toccati negli allineamenti di ottobre (stringhe di interfaccia, non solo CSS). Una modifica visibile in header, carrello o newsletter va cercata anche lì. Il selettore lingua desktop del tema nuovo è un po’ più stretto del live: sul live la voce riserva spazio per il codice paese. È un residuo accettato nel report del 13 ottobre, non un bug di padding delle altre voci.

## Audit di parità

`audits/store-parity` è un auditor Python (Playwright) che confronta il live con un tema preview. Si esegue solo via Docker, dalla root del repo. Istruzione operativa: `audits/store-parity/README.md`. Compose: `docker-compose.dev.yml`, servizio `parity`, porta 8766. C’è anche un servizio `audit` sulla 8765 per `audits/product-page-parity`.

Profili: `mobile-p0`, `smoke`, `full`. I run scrivono in `runs/<run-id>/` (gitignored) un report HTML con screenshot, overlay e issue. Il processo esce 0 solo se il run è completo e il gate è accettato.

La config `audits/store-parity/config/default.yml` punta live e preview allo stesso host `https://www.graymattersnyc.com`, distinguendo il preview con `preview_theme_id=187054457141`. Quell’id va ricontrollato con `shopify theme list` se il development theme è stato ricreato.

Questo audit non sostituisce il confronto manuale delle screenshot in `ai-docs/`. I report visivi già archiviati sono la memoria delle correzioni accettate.

# Correzioni recenti

Le date sono quelle dei commit su `develop`. Il dettaglio di ogni area cliente è in `ai-docs/2026-theme-feedback-interventi.md`; lo stato QA di agosto è in `ai-docs/2026-theme-feedback-qa/README.md`; il confronto del 13 ottobre è in `ai-docs/2026-10-12-parity/README.md`.

## 4 agosto 2026 — feedback cliente, primo allineamento (`d653a00`)

Implementazione del piano in `ai-docs/2026-theme-feedback-interventi.md`, con screenshot QA. Decisioni chiuse in quel giro:

| Tema | Decisione applicata |
|------|---------------------|
| Tipografia | Font-size e letter-spacing misurati sul live, non solo il size |
| Nav | Plurale `CLIENT SERVICES` |
| Catalogue | Gap 6 px; overlay hover schiarito; badge Sale nascosto; ordine `$sale` poi `$compare` |
| PDP | CTA in alto, non sticky; disabled nero con testo `#d9d9d9`; descrizione senza scroll interno; breadcrumbs e prezzo riallineati |
| Newsletter | Badge hCaptcha nascosto; honeypot tenuto |
| Header | Nav 11.5 px / 0.8 px; spaziatura icone; dropdown contatti in maiuscolo |
| Search | Popular Searches riallineato |
| Image + text | Size di heading e sottotitolo |
| Footer | Linee verticali che non invadono la griglia; ritmo dei link |
| Announcement | Barra blu in scope e verificata accesa |
| Breakpoint | Gli interventi valgono anche su tablet e mobile |

File toccati in quel commit, oltre alle screenshot: `assets/custom.css`, `assets/component-price.css`, `assets/product-forms.css`, `locales/en.default.json`. Il QA segna le aree principali OK, con il residuo della larghezza Add to Bag.

## 5–28 agosto — rifiniture PDP, catalogue, newsletter

- `8140817` (5 agosto): hover dei link footer, visibilità della label Select size, gap e opacità delle griglie collection, link del menu mobile, allineamento di `vertical-image-with-text`.
- `14dabca` (20 agosto): famiglie font, glyphicons del carosello mobile, padding del pannello info prodotto, layout di `color-variant`.
- `5c1e1f3` e `0dd7a18` (28 agosto): pulizia di utility in `app.css`, padding e font dei bottoni, layout della popup newsletter, line-height della descrizione, piccoli ritocchi a footer, buy button e galleria.

## 16–17 settembre — metafield, video, UGC, sfondo PDP

- `a1de8a8`: `color-variant.liquid` e `related-products.liquid` accettano i formati metafield reali dello store (JSON strutturato e stringa).
- `2f0478d`: rebuild Tailwind 3.4.19, variabili e placeholder.
- `8d7fede`: `yarn.lock`; rendering condizionale di video e UGC; nuovo `snippets/legacy-ugc-band.liquid` per il formato UGC storico. `logs/` e `audits/` entrano nel `.gitignore` in questa finestra.
- `34fff85`: primo `docker-compose.dev.yml`; controllo più stretto delle immagini UGC in `main-product.liquid`.
- `873ee51`: padding e font dell’image-text.
- `82d035e`: su mobile il video portrait ha priorità; niente fallback landscape quando il portrait esiste.
- `f05f0d8`: lo sfondo dettaglio prodotto è fixed e sta dietro le bande, non nel flusso del testo.

## 19–22 settembre — contesto e auditor

- `ca74776`: aggiunto `project.md` (contesto ricostruito, oggi in parte superato dal path e dal branch).
- `0273aab`: framework `audits/store-parity` (CLI, scenari, report, test), servizio Docker `parity`, icone SVG del menu e ritocchi a header, menu mobile, PDP e full-width image. È infrastruttura di controllo, non un cambiamento di design.

## 9 ottobre — parità mobile a 390 px (`ce9a9b8`)

Allineamento esplicito dello storefront mobile al tema live: header, menu, catalogue, scheda prodotto, carrello, footer, newsletter e layout homepage PageFly. Il CSS base PageFly viene caricato in homepage.

File principali: `custom.css`, `app.css`, `mobile-menu.css`, `footer.js`, `cart-drawer.js`, `header.liquid`, `main-product.liquid`, `main-cart-items.liquid`, `collection-all.liquid`, `buy-buttons.liquid`, `card-product.liquid`, `templates/cart.json`, `theme.liquid`, locale EN e IT.

## 12 ottobre — header, mini cart, footer, newsletter (`0e716df`)

Consolidamento misurato, documentato il giorno dopo in `ai-docs/2026-10-12-parity/README.md`:

- Header desktop a 45 px, padding voci, icone Instagram / account / ricerca / carrello, glifo della lente uguale al live.
- Mini cart 400 px, titolo YOUR CART, chiusura a X, riga e stato vuoto.
- Footer desktop: quattro colonne, ritmo link, form sottolineato, Sign up, copyright.
- Popup desktop 400×295, etichetta Shoe Size.
- Header mobile a 70 px.
- Menu mobile 285 px; lente piena; voci primarie nere anche in hover (il fix hover è completato il 13).
- Footer mobile: accordion sulle tre colonne, News aperto e senza bordo sotto il titolo, rientri 15/45, spazio prima del copyright.
- Popup mobile al 95% con 20 px dal fondo.

## 13 ottobre — hover del menu e barra a due frasi (`64a86e5`)

Tre correzioni puntuali, dopo il report del 12:

- Il titolo News del footer mobile ereditava il bordo inferiore degli accordion. Il bordo resta solo su Company, Client Services e Connect.
- Padding del blocco newsletter mobile (`12px 30px` sotto i 989 px nel giro di aggiustamento, poi rientro allineato al titolo News: 15 px / 45 px nel report finale). Tra Sign up e copyright restano circa 17 px.
- Aprendo l’hamburger, il puntatore finiva sulla riga Language e l’hover `#a5a5a5` la schiariva. Le voci primarie restano `#333` anche in `:hover` (`assets/mobile-menu.css`). Le utility possono ancora usare `#a5a5a5`.
- `snippets/message-bar.liquid` alterna le due frasi lette dalle impostazioni della sezione, con fade. `header-group.json` ha testo, link e colore della frase alternativa. La lente del menu mobile è l’SVG pieno del live.

Screenshot aggiornati citati dal lavoro di quel giorno: `mobile-menu-local-language.png`, `mobile-footer-local-news.png`, `mobile-footer-local-inset.png`.

## 13 novembre — image-text e banda recensioni (`be6fa34`)

Ultimo commit sul branch:

- Classi `.image-text-module-column` e `.image-text-module-stack` in `custom.css`: centratura verticale delle due righe, gap 17.5 px, comportamento diverso sotto e sopra i 990 px.
- `.module-band-heading` per i titoli dei moduli.
- `.yotpo-review-snippet { min-height: 100px }` così la banda bianca resta anche senza recensioni.
- Classi dei video in `main-product.liquid` riallineate allo spacing dei moduli.
- Struttura di `vertical-image-with-text.liquid` e altezza del wrapper Yotpo in `theme.liquid`.

# Residui e trappole

Cose lasciate aperte di proposito, o facili da rompere.

| Residuo | Perché esiste | Cosa fare |
|---------|---------------|-----------|
| Select language più stretta del live | Il live riserva spazio al codice paese | Non allargare a occhio le altre voci. Se si sistema, misurare solo quel controllo |
| «Lady Gray Club» vs «LadyGray Club» | Titolo del link in navigazione Shopify | Cambiarlo nell’admin, non nel CSS |
| Add to Bag desktop più largo (~360 vs ~293) | Il pannello info è più largo | Toccare il pannello, non solo il bottone |
| `pagefly-app-header` non incluso nel layout | Il CSS base è caricato solo in homepage | Dopo un publish, seguire `ai-docs/pagefly-theme-sync.md` e verificare le route PageFly |
| `README.md` e `project.md` | Starter Trellis e snapshot del 19 settembre | Non seguirli per path, prefisso Tailwind o branch senza verificare |
| `app.css` modificato a mano | Viene rigenerato | Mettere la regola in `custom.css` o rilanciare il build dopo aver aggiunto la classe Liquid |
| `1rem` = 13 px | `html { font-size: 0.8125rem }` | Misurare in px nel browser |
| Parser metafield multipli | Lo store ha JSON in forme diverse | Tenere i rami in `color-variant` e `related-products` |
| File `*-old`, `*-bak`, `css-backup` | Copie | Non ripristinarli sopra i file correnti |
| Cartella `ai-docs/2026-10-12-parity/` | Prove visive di ottobre, non ancora committata | Fa parte della memoria del lavoro; non cancellarla |

# Convenzioni di lavoro per chi continua

1. Partire dal live a 1440 px e a 390 px, poi controllare il taglio 989/990 se il pezzo cambia tra mobile e desktop.
2. Per una correzione visiva, preferire `assets/custom.css`. Per il cassetto, `assets/mobile-menu.css`. Aggiungere una utility Tailwind solo se entra nel sorgente Liquid e si rilancia `npm run tailwind:build` o il watch.
3. Non introdurre un nuovo grigio hover sulle voci primarie del menu. `#333` fermo, `#a5a5a5` solo dove il live lo usa.
4. News nel footer mobile non è un accordion e non ha bordo sotto il titolo.
5. Add to Bag disabled resta nero. Il testo disattivo è `#d9d9d9`.
6. Niente badge Sale. Niente scrollbar interna in descrizione. Niente hCaptcha visibile; il honeypot resta.
7. I testi che vengono da menu, metafield o locale non si hardcodano per “far tornare lo screenshot”, salvo una decisione esplicita sulla stringa.
8. Una modifica a header, footer, PDP, catalogue, carrello o newsletter va riguardata sulla route sorella (home e PDP condividono l’header; footer e popup condividono il form).
9. Gli screenshot di accettazione già fatti stanno in:
   - `ai-docs/2026 theme feedback/` — richieste cliente, agosto 2026
   - `ai-docs/2026-theme-feedback-qa/` — live contro locale dopo il primo giro
   - `ai-docs/2026-10-12-parity/` — header, mini cart, footer, newsletter, menu mobile
10. Per un giro ampio, l’auditor Docker in `audits/store-parity` produce un report confrontabile. Per un fix puntuale basta il prima/dopo nel browser, alle larghezze sopra.

# Mappa dei documenti già nel repo

| File | A cosa serve |
|------|----------------|
| `ai-docs/2026-theme-feedback-interventi.md` | Piano del feedback agosto, area per area, con criteri di accettazione |
| `ai-docs/2026-theme-feedback-qa/README.md` | Esito QA e misure (font, gap, CTA, hCaptcha) |
| `ai-docs/2026-10-12-parity/README.md` | Parità visiva di header, carrello, footer, newsletter |
| `ai-docs/pagefly-theme-sync.md` | Cosa fare in PageFly dopo un publish |
| `.agent-os/product/metafields-quick-reference.md` | Tabella metafield e ordine di render |
| `.agent-os/product/metadata-architecture-analysis.md` | Perché la PDP è metadata-driven |
| `audits/store-parity/README.md` | Come lanciare l’audit Docker |
| `shopify_cli_themes_cheatsheet.md` | Comandi Shopify CLI generici |
| `quick-help.md` | Due comandi di push/publish verso il dev store |
| `project.md` | Contesto ricostruito il 19 settembre; path e branch da riverificare |
| `MIGRATION-COMPLETE.md` | Diario della migrazione Tailwind iniziale; checklist non aggiornata |
| `release-notes.md` | Note Dawn 15.2.0, non il diario Gray Matters |

# Verifica minima prima di considerare chiusa una modifica

- Home, una collection, una PDP con varianti colore e metafield (riferimento storico: Clara Pumps in Taupe, `/products/clara-pumps-taupe`), carrello vuoto, apertura newsletter.
- Desktop 1440 px e mobile 390 px. Se il CSS tocca il taglio, anche 989 e 990.
- Menu mobile aperto, con il puntatore sulla prima voce: il nero resta `#333`.
- Footer mobile: tre accordion con bordo, News senza bordo, form allineato al titolo.
- Add to Bag senza taglia selezionata: bottone nero, testo grigio chiaro, non inviabile.
- Console senza errori nuovi introdotti dal file toccato.

Questo documento descrive lo stato del codice al commit indicato. Non certifica che l’anteprima Shopify di oggi sia ancora pixel-uguale al live: le impostazioni del theme editor e i metafield vivono sullo store e possono divergere dal JSON versionato.
