# Store parity audit

Audit UI/UX deterministico e riprendibile tra lo storefront live Gray Matters
e il tema Shopify preview. Copre mobile, desktop, breakpoint critici, stati
interattivi, accessibilità, errori runtime e confronto visuale.

## Ambiente Docker

Tutti i comandi vanno eseguiti dalla root del repository, senza installare
dipendenze sull'host:

```sh
docker compose -f docker-compose.dev.yml build parity
docker compose -f docker-compose.dev.yml up -d parity
docker compose -f docker-compose.dev.yml exec -T parity pytest
```

## Profili

- `mobile-p0`: homepage, collection e product; header, menu mobile e relativi
  accordion, newsletter, footer e stati principali.
- `smoke`: rappresentanti di tutti i tipi di route, mobile e desktop, con gli
  stati globali e storefront essenziali.
- `full`: inventario completo, tutti gli scenari applicabili e probe ai
  breakpoint dichiarati in `config/default.yml`.

La configurazione YAML sceglie scenari e viewport di ogni profilo. I contratti
degli scenari (landmark, passi e obbligatorietà) sono definiti in
`src/store_parity/scenarios/definitions.py`; nomi non supportati vengono
rifiutati durante il caricamento.

## Esecuzione

Smoke deterministico su una route e un solo caso:

```sh
docker compose -f docker-compose.dev.yml exec -T parity \
  python -m store_parity.cli run \
  --profile smoke \
  --path / \
  --max-representative-routes 1 \
  --max-cases 1 \
  --label homepage-smoke
```

Audit mobile P0 con discovery da sitemap:

```sh
docker compose -f docker-compose.dev.yml exec -T parity \
  python -m store_parity.cli run \
  --profile mobile-p0 \
  --label mobile-p0
```

Audit completo:

```sh
docker compose -f docker-compose.dev.yml exec -T \
  -e STORE_PARITY_CONCURRENCY=6 parity \
  python -m store_parity.cli run \
  --profile full \
  --label full-store
```

Il profilo full evita una seconda cattura `baseline` quando lo stesso stato
iniziale è già coperto dallo scenario tipizzato di collection, product, page,
search o cart. Tutte le route restano incluse; i baseline restano attivi per
homepage e probe breakpoint. `STORE_PARITY_CONCURRENCY` modifica solo il numero
di worker del processo e non altera il digest della configurazione né la
riprendibilità del run.

`--path` è ripetibile. `--max-representative-routes` e `--max-cases` servono
per prove limitate e non devono essere usati per l'audit cliente definitivo.

Il processo restituisce `0` solo quando il run è completo e il gate di parità è
accettato. Restituisce `1` sia per errori tecnici sia per discrepanze bloccanti;
il JSON finale distingue `status`, `accepted`, `error` e `report_path`.

## Ripresa e diagnosi

Un run interrotto o fallito conserva SQLite, manifest e artefatti:

```sh
docker compose -f docker-compose.dev.yml exec -T parity \
  python -m store_parity.cli status runs/<run-id>

docker compose -f docker-compose.dev.yml exec -T parity \
  python -m store_parity.cli run \
  --resume runs/<run-id> \
  --profile smoke \
  --retry-failed
```

Il profilo e il digest della configurazione devono coincidere con il run
originale. Un manifest `COMPLETE` è immutabile e non può essere ripreso.

## Artefatti e report

Ogni run è scritto in `runs/<run-id>/` e contiene:

- `manifest.json`, stato SQLite e registry degli artefatti;
- screenshot live/preview per viewport, pagina e componenti;
- overlay, heatmap, DOM, stili, geometria, icone, Axe e diagnostica runtime;
- finding grezzi registrati e issue consolidate per mantenere il report
  navigabile senza perdere il dettaglio tecnico;
- `report/index.html`, con panoramica, copertura, route, feature, issue, filtri
  persistenti in URL e viewer Affiancato/Slider/Overlay/Blink/Diff/Heatmap.

Gli input del report sono risolti esclusivamente tramite ID presenti nel
registry e verificati con SHA-256. Il report HTML è output derivato: viene
generato e validato prima della chiusura immutabile del manifest, ma non viene
registrato a sua volta per evitare un ciclo manifest-report.

Per consultarlo:

```sh
docker compose -f docker-compose.dev.yml exec -T parity \
  python -m http.server 8766 --directory runs/<run-id>
```

Aprire `http://127.0.0.1:8766/report/index.html`.

## PageFly

PageFly non viene assunto dalla route o dal template. Il runner lo considera
applicabile solo quando trova marker PageFly nel DOM renderizzato. In quel caso
aggiunge stabilizzazione e attesa network-idle limitata; un timeout di
network-idle viene registrato come evidenza perché connessioni terze possono
restare aperte. Le pagine non-home senza marker PageFly restano
`not_applicable` e non bloccano il run.

La preview viene sempre verificata tramite `Shopify.theme.id`, in un browser
context separato dal live. Il live rifiuta cookie/query della preview, evitando
confronti falsamente identici.
