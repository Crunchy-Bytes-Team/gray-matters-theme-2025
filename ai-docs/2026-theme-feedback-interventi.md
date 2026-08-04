# Feedback tema 2026 — Piano interventi

Documento di analisi del materiale inviato dalla cliente in `ai-docs/2026 theme feedback/`.  
Obiettivo: allineare il comportamento/aspetto del tema attuale (nuovo) a quello del tema precedente (vecchio).

**Stato:** implementazione applicata — QA screenshot in `ai-docs/2026-theme-feedback-qa/`.

---

## Riferimento di verifica (live vs locale)

| Etichetta | Cosa è | Dove |
|-----------|--------|------|
| **Old / tema vecchio** | Tema **attualmente in produzione** sullo store Shopify | [https://www.graymattersnyc.com/](https://www.graymattersnyc.com/) |
| **New / tema nuovo** | Tema in sviluppo in questo repo (Tailwind, 2025) | Preview locale / theme preview Shopify |

**Come usarlo in implementazione e QA**

1. Le screenshot in `ai-docs/2026 theme feedback/` restano la fonte delle *richieste cliente* (annotazioni).
2. Il sito live è la **fonte di verità misurabile** per valori CSS (font-size, gap, colori, layout, stati hover/disabled) e per il risultato atteso.
3. In fase di fix: confrontare elemento per elemento live ↔ locale (Browser / DevTools), senza copiare alla cieca il CSS legacy (il live è pieno di override e non usa Tailwind).
4. Approccio corretto: riprodurre il *comportamento/aspetto* desiderato con le primitive del tema nuovo (Tailwind / CSS attuale), non portare avanti il CSS legacy.

---

## Riepilogo esecutivo

| # | Area | Priorità suggerita | Tipo intervento |
|---|------|--------------------|-----------------|
| 1 | Top Navigation | Media | CSS / spacing + font-size |
| 2 | Drop-down menu (Client Service) | Bassa | Casing testo (uppercase) |
| 3 | Search bar | Media | Font-size Popular Searches |
| 4 | Catalogue page — griglia | Alta | Spessore gap/linee + overlay testo statico/hover |
| 5 | Catalogue page — hover card | Alta | Font-size overlay + colore background grigio |
| 6 | Footer | Media | Linee verticali + spaziatura link |
| 7 | Image Text | Media | Font-size heading/subheading |
| 8 | Product Page — layout CTA | Alta | Riposizionare Add to Bag / Select Size |
| 8b | Product Page — stile CTA disabled | Alta | Add to Bag sempre nero (mai grigio disattivo) |
| 9 | Product Page — breadcrumbs / prezzo | Media | Font-size breadcrumbs; size + posizione prezzo |
| 10 | Product Page — descrizione | Alta | Rimuovere scrollbar interna, testo completo |
| 11 | Sign up pop up | Alta | Rimuovere badge/CAPTCHA hCaptcha |

---

## Convenzioni usate nel documento

- **Old** = tema live in produzione ([graymattersnyc.com](https://www.graymattersnyc.com/)) e relative screenshot di feedback (target comportamentale/visivo).
- **New** = tema 2025 in questo repo e relative screenshot di feedback (punto di partenza).
- Le citazioni in corsivo riprendono le annotazioni italiane presenti sulle immagini.
- Dove utile, sono indicati i file del tema più probabili da toccare (da confermare in fase di implementazione).

---

## 1. Top Navigation

**Cartella:** `Top Navigation/`  
**File di riferimento feedback:**

- Old: `Top navigation old.png`
- New: `Top navigation new.png`

**File tema candidati:** `sections/header.liquid`, eventuali CSS header (`assets/header-navigation.css`, Tailwind classes inline)

### Annotazioni cliente (su New)

1. *«allineare font size navigation a old theme»*
2. *«Aumentare spazio tra icone come old theme»*

### Differenze osservate

| Elemento | Old | New | Intervento previsto |
|----------|-----|-----|---------------------|
| Link nav (`COLLECTION`, `SELECT LANGUAGE`, `CLIENT SERVICE`) | Font-size percepito più piccolo / più “leggero” | Font-size attuale da riallineare | Portare `font-size` (e eventualmente `letter-spacing` / weight) dei link desktop al valore del vecchio tema |
| Icone utility (Instagram, account, search, bag) | Spaziatura orizzontale più generosa | Icone più compatte (`px-1` / `lg:px-2`) | Aumentare padding/gap tra le icone come nel vecchio tema |

### Note aggiuntive da verificare in review

- Nel tema attuale il label è **«CLIENT SERVICE»** (singolare); nel vecchio appare spesso **«CLIENT SERVICES»** (plurale). Non c’è annotazione esplicita su questo punto: da confermare se va ripristinato il plurale.
- Lo screenshot Old include anche l’announcement bar blu superiore; New è croppato sul solo header bianco — fuori scope salvo diversa indicazione.

### Criterio di accettazione

- A confronto side-by-side desktop, font-size dei tre link e spacing delle quattro icone risultano visivamente allineati al vecchio tema.

---

## 2. Drop-down menu (Client Service)

**Cartella:** `Drop-down menu/`  
**File di riferimento feedback:**

- Old: `Drop-down menu old.png`
- New: `Drop-down menu new.png`

**File tema candidati:** `sections/header.liquid` (blocco dropdown Client Service ~righe 110–150), eventualmente `snippets/mobile-menu.liquid` per coerenza mobile

### Annotazioni cliente (su New)

- Cerchio giallo sulla sezione contatti (Email / telefono / orari)
- *«Capitalizzare»*

### Differenze osservate

| Elemento | Old / atteso | New | Intervento previsto |
|----------|--------------|-----|---------------------|
| Label email | Forma capitalizzata richiesta | `Email` (sentence case) | `EMAIL` |
| Orari | Forma capitalizzata richiesta | `Mon-Fri 10am-6pm EST` | `MON-FRI 10AM-6PM EST` |
| Numero telefono | Già numerico | `+1 929 295 0303` | Verificare se anche il numero va lasciato invariato (probabile) |

I link sotto il separatore (`SHIPPING & RETURNS`, `FAQS`, ecc.) sono già in uppercase nel New.

### Criterio di accettazione

- Nella dropdown Client Service, testo contatti in uppercase coerente con i link sottostanti, come richiesto dall’annotazione.

---

## 3. Search bar

**Cartella:** `Search bar/`  
**File di riferimento feedback:**

- Old: `Search bar old.png`
- New: `Search bar new.png`

**File tema candidati:** `sections/header.liquid` (blocco search / Popular Searches ~riga 780+), CSS correlati (`assets/component-search.css`, `assets/search-styling.css`, classi Tailwind inline)

### Annotazioni cliente (su New)

- *«allineare font size a old»*

### Differenze osservate

Layout sostanzialmente identico (input full-width con icona lente + riga `POPULAR SEARCHES` + lista termini).  
La differenza segnalata è tipografica: nel New il font-size di label e/o termini Popular Searches non corrisponde all’Old.

### Intervento previsto

1. Confrontare metriche tipografiche Old vs New su:
   - label `POPULAR SEARCHES`
   - link dei termini suggeriti (`Bianco, Cammello, Classic, …`)
2. Allineare `font-size` (e se necessario `letter-spacing` / weight) al vecchio tema.

### Criterio di accettazione

- Aperti i due search overlay, label e lista Popular Searches hanno lo stesso peso tipografico del vecchio tema.

---

## 4. Catalogue page — griglia e testo overlay

**Cartella:** `Catalogue page/`  
**File di riferimento feedback:**

- Old: `Chrome old.png`
- New: `Safari new.png`

**File tema candidati:**

- `snippets/collection-all.liquid` / `sections/collection-all.liquid`
- `snippets/card-product.liquid` / `snippets/card-collection.liquid`
- CSS griglia (`gap-1` attuale sulla product grid, `assets/product-cards.css`, `assets/template-collection.css`)

### Annotazioni cliente (su New)

1. Cerchio sulla linea verticale bianca tra le celle → *«Spessore Griglia bianca allineare a old»*
2. Cerchio su testo overlay della card grande (`Sandals` / `Always new and newsworthy`) → *«posizione e colore font statico e con hover»*

### Differenze osservate

| Elemento | Old | New | Intervento previsto |
|----------|-----|-----|---------------------|
| Gap / linee bianche tra tile | Spessore di riferimento | Spessore diverso (da allineare) | Aggiustare gap/border della griglia catalogue fino a match visivo con Old |
| Testo overlay card collection grande | Posizione e colore statico/hover di riferimento | Posizione e/o colore non allineati; hover da verificare | Ripristinare posizione e colori (stato default + hover) come nel vecchio tema |

### Criterio di accettazione

- Spessore delle “righe” bianche della griglia uguale all’Old.
- Testo statico sulla tile grande: stessa posizione e stesso colore default/hover dell’Old.

---

## 5. Catalogue page — hover prodotto

**Cartella:** `Catalogue page/`  
**File di riferimento feedback:**

- Old: `Catalogue on hover old.png`
- New: `Catalogue on hover new.png`

**File tema candidati:** `snippets/card-product.liquid` (overlay hover `bg-black` / `opacity-40`, blocco `card__content`), `assets/product-cards.css`

### Annotazioni cliente (su New)

- *«Allineare font size e colore background grigio (troppo scuro )»*

### Differenze osservate

| Elemento | Old | New | Intervento previsto |
|----------|-----|-----|---------------------|
| Overlay hover | Grigio più chiaro / meno invasivo | Overlay troppo scuro (`bg-black` + opacity elevata) | Schiarire il background overlay (colore/opacity) per match Old |
| Tipografia overlay (titolo, prezzo, taglie) | Font-size di riferimento | Font-size da riallineare | Allineare font-size di titolo / prezzo / lista taglie |
| Badge «Sale» | Assente | Presente «Sale» + ordine prezzi diverso | **Nascondere** il badge (decisione review) |

Dettaglio prezzo (osservato):

- Old: `$396` + `$495` barrato (sale price prima)
- New: label `Sale` + `$495` / `$396` (trattamento diverso)

### Criterio di accettazione

- Hover card: overlay grigio non troppo scuro e tipografia allineata all’Old.
- Badge Sale nascosto; ordine prezzi `$sale` → `$compare` come Old.

---

## 6. Footer

**Cartella:** `Footer/`  
**File di riferimento feedback:**

- Old: `Footer Chrome old.png`
- New: `Footer Chrome new.png`

**File tema candidati:** `sections/footer.liquid`, `assets/section-footer.css`

### Annotazioni cliente (su New)

1. Freccia sulla linea verticale tra colonne → *«Muovere linea verticale sotto la griglia»*
2. Cerchi sulle liste link + *«allineare spaziatura testo footer»*

### Differenze osservate

| Elemento | Old | New | Intervento previsto |
|----------|-----|-----|---------------------|
| Separatori verticali tra colonne | Contenuti nel blocco footer, sotto la griglia prodotti | Almeno una linea sembra “entrare” / protrudere verso l’area griglia sopra | Far partire le linee verticali solo all’interno del footer (sotto la griglia), senza sconfinamento verso l’alto |
| Spaziatura verticale link (`COMPANY`, `CLIENT SERVICE`, `CONNECT`) | Ritmo verticale di riferimento | Spaziatura da riallineare | Uniformare `margin`/`padding`/`line-height` delle voci link al vecchio tema |

### Criterio di accettazione

- Nessuna linea verticale del footer invade la griglia prodotti sopra.
- Spaziatura delle tre colonne di link allineata all’Old.

---

## 7. Image Text

**Cartella:** `Image Text/`  
**File di riferimento feedback:**

- Old: `IMAGE TEXT Chrome Old.png`
- New: `IMAGE TEXT Chrome New.png`

**File tema candidati:** `snippets/vertical-image-with-text.liquid` (modulo split testo/immagine su PDP/pagine prodotto), eventuali sezioni image-with-text custom

Contesto UI: layout 50/50 — testo a sinistra (`LOAFERS, REINVENTED` + sottotitolo), immagine prodotto a destra.

### Annotazioni cliente (su New)

- *«ALLINEARE FONT SIZE A OLD THEME»*

### Intervento previsto

1. Confrontare font-size di:
   - heading principale (serif, uppercase)
   - sottotitolo
2. Portare i valori del New a quelli dell’Old (solo size, salvo diversa richiesta su family/weight).

### Criterio di accettazione

- Heading e subheading del blocco Image Text hanno le stesse dimensioni tipografiche del vecchio tema.

---

## 8–10. Product Page

**Cartella:** `Product Page/`  
**File di riferimento feedback:**

| Coppia | Old | New | Focus |
|--------|-----|-----|-------|
| A | `PRODUCT PAGE OLD Chrome.png` | `PRODUCT PAGE NEW Safari.png` | CTA sopra-the-fold + stile nero, breadcrumbs/prezzo |
| B | `pdp old.png` | `pdp new.png` | Descrizione senza scrollbar |

**File tema candidati:** `sections/main-product.liquid`, `assets/section-main-product.css`, `assets/product-info.css`, `assets/product-forms.css` (`.product-form__submit:disabled` → oggi `bg-gray-300`), `snippets/price.liquid`, snippet breadcrumbs, `snippets/color-variant.liquid` (perimetro swatch, se coinvolto indirettamente dal layout)

---

### 8. Riposizionamento CTA «ADD TO BAG»

**Annotazione (su PRODUCT PAGE NEW):**

> *«ho fatto un po di ricerca su ux ecommerce e la CTA Add to Bag dovrebbe essere sempre sott'occhio. Quindi riportiamola sopra come da tema vecchio»*

**Comportamento Old (target):**

- Dopo titolo/prezzo (e tipicamente dopo descrizione breve + swatch colore), blocco acquisto in evidenza:
  - bottone nero `ADD TO BAG`
  - a fianco `SELECT SIZE`
- Link secondari (`Shipping & Returns`, `Size Guide`, `Contact Us`) sotto la CTA

**Comportamento New (da correggere):**

- CTA e Select Size risultano più in basso (spesso sotto description / link), meno immediatamente visibili above-the-fold.

**Intervento previsto:**

1. Ripristinare l’ordine/layout del blocco acquisto come nel vecchio tema (CTA + size picker in alto, sempre visibili).
2. Verificare desktop e breakpoint intermedi (i feedback sono desktop-centric).

**Criterio di accettazione:**

- Su viewport desktop tipico, `ADD TO BAG` + `SELECT SIZE` sono visibili senza scroll, come nel vecchio tema.

---

### 8b. Stile CTA «ADD TO BAG» — mai grigio quando disattivato

**Osservazione dalle screenshot (confermata in review interna):**

- In `PRODUCT PAGE NEW Safari.png` il bottone `ADD TO BAG` appare **grigio chiaro** a basso contrasto (stato disabled tipico, es. finché non è selezionata una taglia).
- In `PRODUCT PAGE OLD Chrome.png` / `pdp old.png` il bottone resta **nero pieno** con testo bianco, quindi sempre “sott’occhio”.

Nel tema attuale lo stile disabled è esplicito in `assets/product-forms.css`:

```css
.product-form__submit:disabled {
  @apply bg-gray-300 text-gray-500 cursor-not-allowed;
}
```

**Intervento previsto (decisione review):**

1. Far restare il bottone **nero** anche in stato `disabled` / non cliccabile (niente `bg-gray-300`).
2. In disabled, testo in **grigio chiaro** (non bianco) per distinguerlo leggermente dallo stato attivo (nero + testo bianco).
3. Mantenere `cursor-not-allowed` quando non cliccabile.
4. Verificare tutti gli stati: size non selezionata, variante non disponibile, loading.

**Criterio di accettazione:**

- `ADD TO BAG` disabled: sfondo nero + testo grigio chiaro, sempre ben visibile; attivo: nero + testo bianco; resta non inviabile quando la selezione non è valida.

---

### 9. Breadcrumbs e prezzo (font-size + posizione)

**Annotazioni (su PRODUCT PAGE NEW):**

- Breadcrumbs (`Home > All > …`) cerchiati → *«allineare font size»*
- Prezzo (incluso prezzo scontato/barrato) cerchiato → *«allineare font size»*

**Differenze prezzo osservate Old vs New (oltre al font-size annotato):**

| Aspetto | Old | New | Intervento previsto |
|---------|-----|-----|---------------------|
| Font-size | Più piccolo / peso tipografico di riferimento | Diverso (cerchiato dalla cliente) | Allineare size (e se serve weight) al vecchio tema |
| Posizione | Allineato a destra nella colonna info; nell’Old spesso più in basso rispetto al solo titolo (allineato verso l’inizio descrizione / area destra del blocco) | Posizionamento diverso rispetto all’Old (più “attaccato” al titolo o con allineamento diverso) | Verificare e ripristinare anche **posizione / allineamento** del prezzo come nel vecchio tema, non solo il font-size |
| Sale display | Es. `$396` + `$495` barrato | Es. `$495` barrato + `$395` (ordine/trattamento diverso) | Allineare ordine **`$sale` → `$compare`** come Old (decisione review) |

**Intervento previsto:**

1. Allineare tipografia breadcrumbs al vecchio tema.
2. Allineare **dimensione** del prezzo al vecchio tema.
3. Allineare **posizione** del prezzo (verticale rispetto a titolo/descrizione + allineamento orizzontale nella colonna destra) al layout Old.
4. Verificare comportamento su prezzo regolare e su prezzo in sconto (compare-at).

**Criterio di accettazione:**

- Breadcrumbs: font-size allineato all’Old.
- Prezzo: stessa dimensione e stessa posizione relativa del vecchio tema (titolo a sinistra, prezzo a destra nel punto corretto della colonna).

---

### 10. Descrizione prodotto senza scrollbar

**Annotazione (su pdp new.png):**

> *«Far comparire tutto il testo senza banda di scorrimento, come tema vecchio»*

**Comportamento Old:**

- Blocco descrizione espanso: tutto il copy (paragrafi + MADE IN ITALY / HEIGHT / FIT / MEASUREMENTS) è leggibile senza scroll interno.

**Comportamento New:**

- Container descrizione con altezza limitata + scrollbar interna (`product-desc-scrollbar` / max-height in `main-product.liquid`).

**Intervento previsto:**

1. Rimuovere (o disabilitare) lo scroll interno della descrizione.
2. Far espandere il contenitore in altezza naturale, come nel vecchio tema.
3. Verificare che il riposizionamento CTA (punto 8) e l’espansione testo restino coerenti (possibile trade-off su prodotti con copy molto lungo → da discutere).

**Criterio di accettazione:**

- Nessuna scrollbar interna sul blocco descrizione; tutto il testo è visibile nel flusso pagina.

---

## 11. Sign up pop up (newsletter)

**Cartella:** `Sign up pop up/`  
**File di riferimento feedback:**

- `Screenshot 2026-08-03 at 3.40.24 PM.png` — popup newsletter con annotazione
- `Screenshot 2026-08-03 at 3.40.10 PM.png` — dettaglio badge hCaptcha

**File tema candidati:** `sections/footer.liquid` (markup `#newsletter-modal`), `assets/newsletter-popup.js`, `assets/custom.css` (stili `.newsletter-modal`), eventuale integrazione Mailchimp / script terze parti che iniettano hCaptcha

### Annotazioni cliente

- Cerchio giallo sul badge blu → *«TOGLIERE CAPTCHA»*

### Differenze / problema

- Sul popup `SUBSCRIBE TO OUR NEWSLETTER` compare il badge **«Protected by hCaptcha»** (icona mano su griglia pixel) che si sovrappone al bottone `SIGN UP`.
- Richiesta esplicita: rimuoverlo.

### Intervento previsto

1. Individuare la fonte del badge (script Mailchimp, widget Shopify, CSS/JS custom, impostazione account Mailchimp).
2. Rimuovere badge e, se presente, la challenge CAPTCHA dal flusso di iscrizione del popup.
3. Verificare che il submit newsletter continui a funzionare senza regressioni anti-spam (honeypot `tripwire` già presente nel form).

### Decisione review

- **Protezione non invasiva** per ora: rimuovere badge/challenge hCaptcha visibile; mantenere honeypot (`tripwire`) e/o equivalenti non invasivi. Niente CAPTCHA interattivo in UI.

### Criterio di accettazione

- Popup newsletter senza badge hCaptcha né challenge visibile; protezione non invasiva attiva; signup funzionante.

---

## Decisioni approvate (review)

| # | Tema | Decisione |
|---|------|-----------|
| 1 | Scope tipografico | Allineare **font-size + letter-spacing** al live/Old |
| 2 | Label nav Client Service | Ripristinare il **plurale**: `CLIENT SERVICES` |
| 3 | Badge «Sale» hover catalogue | **Nascondere** il badge «Sale» (come live); solo i prezzi comunicano lo sconto |
| 4 | Ordine prezzo card hover | Come Old: **`$sale` poi `$compare` barrato** (es. `$396 $495`) |
| 5 | PDP CTA vs descrizione lunga | **Niente sticky**; prova layout CTA in alto + descrizione espansa (accettabile se CTA scende sotto-the-fold su copy lunghi) |
| 6 | PDP CTA disabled | Bottone **nero** anche disabled; testo in **grigio chiaro** (non bianco) per distinguerlo leggermente dallo stato attivo |
| 7 | PDP ordine prezzo sale | Allineare anche l’ordine **`$sale` / `$compare`** come Old |
| 8 | CAPTCHA newsletter | **Protezione non invasiva** per ora (niente badge hCaptcha visibile; honeypot / equivalenti, no challenge invasiva) |
| 9 | Breakpoint | Interventi anche su **tablet/mobile**, non solo desktop |
| 10 | Announcement bar | **In scope**; da verificare se già corretta sul tema nuovo vs live |

### Nota #3 — Badge «Sale» (decisione)

Nelle screenshot hover Old non c’è label «Sale»; il New la mostra (badge Dawn/`card-product`).  
**Decisione:** nascondere il badge «Sale» sulla card catalogue/hover per ora; lo sconto resta comunicato solo da `$sale` + `$compare` barrato.  
*(Eventuale ripristino/restyling lasciato per dopo.)*

### Nota #10 — Announcement bar

In scope. In implementazione: confrontare live vs tema nuovo (testo, stile, link, comportamento) e correggere solo se non allineata. Non è stata annotata esplicitamente nelle screenshot, ma fa parte dell’header/top.

---

## Ordine di implementazione suggerito

1. **Product Page** (CTA posizione + CTA disabled nero/testo grigio chiaro + prezzo size/posizione/ordine + scrollbar descrizione + breadcrumbs) — impatto UX diretto segnalato dalla cliente  
2. **Catalogue** (griglia + hover overlay + ordine prezzi + nascondere badge Sale)  
3. **Sign up popup** (rimuovere hCaptcha visibile, tenere protezione non invasiva)  
4. **Header** (nav font-size + letter-spacing + icon spacing + `CLIENT SERVICES` + capitalizzazione dropdown) + **verifica announcement bar**  
5. **Search bar** + **Image Text** (font-size + letter-spacing)  
6. **Footer** (linee verticali + spacing)  
7. QA anche su **tablet/mobile** per tutti gli interventi sopra

---

## Indice file feedback

```
ai-docs/2026 theme feedback/
├── Top Navigation/
│   ├── Top navigation old.png
│   └── Top navigation new.png
├── Drop-down menu/
│   ├── Drop-down menu old.png
│   └── Drop-down menu new.png
├── Search bar/
│   ├── Search bar old.png
│   └── Search bar new.png
├── Catalogue page/
│   ├── Chrome old.png
│   ├── Safari new.png
│   ├── Catalogue on hover old.png
│   └── Catalogue on hover new.png
├── Footer/
│   ├── Footer Chrome old.png
│   └── Footer Chrome new.png
├── Image Text/
│   ├── IMAGE TEXT Chrome Old.png
│   └── IMAGE TEXT Chrome New.png
├── Product Page/
│   ├── PRODUCT PAGE OLD Chrome.png
│   ├── PRODUCT PAGE NEW Safari.png
│   ├── pdp old.png
│   └── pdp new.png
└── Sign up pop up/
    ├── Screenshot 2026-08-03 at 3.40.10 PM.png
    └── Screenshot 2026-08-03 at 3.40.24 PM.png
```

---

*Documento generato dall’analisi delle screenshot cliente — da validare prima dell’implementazione.*
