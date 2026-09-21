# PDFhero

**Present PDFs the way they were meant to be seen — and ink on them with your finger.**

PDFhero is a single-page web app that shows a PDF fullscreen, lets you draw over
it with a finger, a stylus or a mouse, captures what you drew as screenshots or
back into the PDF itself, and tells you exactly what the document is made of —
page geometry, PDF/X level, output intent, embedded ICC profiles.

It is one `index.html` file. No build step, no accounts, no server: the document
never leaves your machine. Install it once and it works on a plane.

👉 [pdfhero@nosocial.net](mailto:pdfhero@nosocial.net)

---

## Why this exists

The presentation tool everyone reaches for is PowerPoint, and on stage with a
touch screen it keeps getting in the way.

**Touch screens are an afterthought.** PowerPoint does not work well with them,
and the inking it does offer is too rudimentary to rely on: there is no real
undo and redo of what you just drew, so one bad stroke in front of an audience
is a stroke you have to live with.

**PDF is the industry standard for publishing, and PowerPoint cannot really get
you there.** Not just PDF, but PDF with built-in colour profiles and output
intents — PDF/X-4 and friends. Those are exactly what PowerPoint cannot easily
produce, and without them the same deck renders slightly differently on
different machines, with slightly different colours. If you care what your
slides look like on someone else's projector, that is not a detail.

**A PowerPoint presentation is also too easy to mess up.** Run past the last
slide on stage and the show simply closes. Work out why your slides look
pixelated and you are digging through OS display settings and document
properties chasing sizes and DPIs that nobody surfaces in one place.

Insisting on the highest standards — one of the Amazon leadership principles —
PDFhero emerged: present the published artefact itself, the PDF, with the
colour fidelity it already carries, on a touch screen that behaves, with
nothing on the critical path that can drop the deck mid-sentence.

---

## What it does

### Presenting

- **Fullscreen, distraction-free.** The slide is centred on black, scaled to
  fit the viewport; the cursor hides itself after two seconds of stillness.
- **Never drops out from under you.** Paging past the last page (or before the
  first) does nothing at all — leaving presenter view takes a deliberate `Q` or
  a deliberate double tap. Nothing else ends the show.
- **Start where you like, resume where you left off.** Set a start page before
  going in; exiting writes the page you were on back into that field, so
  re-entering picks up exactly there.
- **Works where fullscreen does not.** iOS Safari has no fullscreen API, so the
  presenter view sizes itself to the dynamic viewport instead of guessing —
  no slide bottom hidden behind the browser toolbar.

### Inking

- **Draw with a finger, a stylus or a mouse** — one pointer-event path for all
  three, with pointer capture so a stroke that strays off the slide keeps
  drawing, and coalesced events so fast strokes stay smooth.
- **Real undo and redo.** `U` takes the last stroke back, `Z` puts it again;
  `E` clears the page. Annotations are kept per page, so paging away and back
  brings your ink with you.

### Getting your work out

- **Save with annotations** writes the strokes into the PDF as *vector* paths —
  not a flattened screenshot — respecting the page's CropBox and `/Rotate`, so
  the ink lands where you drew it and stays sharp at any zoom.
- **Screenshots.** `S` (or a long press) captures the slide with its ink as a
  PNG onto a stack; download the whole stack at the end, each file named with
  its capture order and page number so they sort the way you presented.
- Nothing is uploaded. Saving is a normal browser download.

### Knowing what you are presenting

The metadata panel answers the questions you would otherwise chase through OS
and document properties — before you find out on stage:

| | |
|---|---|
| **Viewport size** | the pixel size PDFhero will actually render into |
| **Document size** | page geometry, in PDF points |
| **Page count** | |
| **Creator** | what produced the file |
| **PDF/X level** | e.g. PDF/X-4 — the standard the file claims |
| **Output intent** | the rendering condition the colours are defined against |
| **ICC profiles** | the *names* of the profiles actually embedded |
| **Metadata source** | which reader each field came from |

Two readers run over every file: pdfcpu compiled to WebAssembly, and a direct
parser for the fields pdfcpu does not report. Whichever answered is recorded
per field — open the console for a table of exactly where each value came from.

### Making a PDF out of images

**Choose images** turns any number of images into a PDFhero PDF, one page per
image, laid out at **300 dpi** so a 300 dpi source comes out at its physical
size and the result is print-ready. JPEG and PNG are embedded as-is; anything
else your browser can decode (WebP, GIF, BMP, AVIF, CMYK JPEG, 16-bit PNG) is
re-encoded first. Then present it, ink on it, and **Save** — which is also how
you get the PDF onto disk.

### Offline and installable

A service worker caches the app and its libraries, so PDFhero is a progressive
web app: add it to your home screen or install it from the address bar, and it
opens with no network at all. Useful, because conference Wi-Fi is not.

---

## Controls

**Keyboard** (presenter view, except `P`)

| Key | Action |
|---|---|
| `P` | Enter presenter view |
| `→` / `Page Down` | Next page |
| `←` / `Page Up` | Previous page |
| `Q` | Exit presenter view |
| `E` | Erase all annotations on the page |
| `U` / `Z` | Undo / redo the last stroke |
| `S` | Capture a screenshot onto the download stack |

**Touch** — the black margin around the slide carries the same actions, so a
tablet needs no keyboard:

| Gesture | Action |
|---|---|
| Drag on the page | Draw |
| Tap the left fifth of the black area | Previous page |
| Tap the right fifth of the black area | Next page |
| Long press anywhere on the black area | Capture a screenshot |
| Double tap anywhere on the black area | Exit presenter view |

Double tap outranks paging: a double tap on the edges exits rather than turning
two pages.

---

## Running it

Open `index.html` over HTTP — any static server will do:

```sh
python -m http.server 8000   # then visit http://localhost:8000/index.html
```

A server (rather than `file://`) is needed because the service worker, the
PDF.js worker and `pdfcpu.wasm` all require a real origin. The deployable set
is `index.html`, `manifest.json`, `sw.js`, `pdfcpu.wasm` and
`deploy/customHttp.yml`; the `dist` GitHub Actions workflow assembles exactly
that into a zip you can hand straight to a static host.

Built on [PDF.js](https://mozilla.github.io/pdf.js/) for rendering,
[pdf-lib](https://pdf-lib.js.org/) for writing, and
[pdfcpu](https://pdfcpu.io/) (WebAssembly) for metadata.

### Versioning

`APP_VERSION` in `sw.js` is the single source of truth: it names the cache, it
is what the About dialog reports, and it names the release bundle. Bump it on
every change to `index.html` — the app is served cache-first, so an unbumped
change never reaches anyone who already has it installed.

---

## Support

Questions, bugs and ideas: [pdfhero@nosocial.net](mailto:pdfhero@nosocial.net).

If PDFhero saved your presentation, you can
[sponsor it](https://github.com/sponsors/ivan-khvostishkov).

## Licence

MIT — see [LICENSE](LICENSE).

PDFhero by NoSocial.Net and Ivan Khvostishkov, copyright 2026+. Created
together with Kiro and Claude, inspired by Adobe and PowerPoint.
