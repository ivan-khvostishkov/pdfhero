# Design Document — PDFhero Presenter v1.01

## Overview

PDFhero Presenter is a single self-contained HTML file named `PDFhero.html` that presents PDFs in a fullscreen, distraction-free environment with freehand annotation and screenshot support. The entire application runs client-side with no server, no build step, and no persistent storage. All state is held in memory for the duration of the browser session.

Three external libraries are loaded from CDN at runtime:
- **PDF.js** — renders PDF pages to an HTML canvas
- **pdf-lib** — embeds vector annotation paths and updates creator metadata in the output PDF
- **pdfcpu WASM** — extracts PDF metadata (page count, dimensions, creator, ICC profiles, PDF/X compliance, rendering intent)

---

## Architecture

The application is structured as a finite-state machine with two top-level views and a thin module layer.

```
┌─────────────────────────────────────────────────────┐
│                   Single HTML File                   │
│                                                      │
│  ┌──────────────┐        ┌───────────────────────┐  │
│  │ Landing Page │◄──────►│    Presenter View     │  │
│  │   (DOM)      │        │   (Fullscreen DOM)    │  │
│  └──────┬───────┘        └──────────┬────────────┘  │
│         │                           │               │
│  ┌──────▼───────────────────────────▼────────────┐  │
│  │                  App State                    │  │
│  │  pdfBytes · pdfDoc · pageCount · currentPage  │  │
│  │  strokes[ ] · redoStack[ ] · cursorTimer      │  │
│  └──────┬───────────────────────────────────────┘  │
│         │                                           │
│  ┌──────▼──────────────────────────────────────┐   │
│  │                Module Layer                 │   │
│  │  MetadataModule · RenderModule              │   │
│  │  AnnotationModule · SaveModule              │   │
│  └─────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

### View Switching

The two views are independent DOM sections (`<section id="landing">` and `<section id="presenter">`). Only one is visible at a time via CSS `display` toggling. No routing library is used.

---

## Module Descriptions

### AppState

A single plain JavaScript object holding the complete in-memory application state. No class instances are used for state; modules operate on this object through function calls.

```javascript
const AppState = {
  // PDF data
  pdfBytes: null,          // Uint8Array of the loaded PDF
  pdfJsDoc: null,          // PDF.js PDFDocumentProxy
  pageCount: 0,
  currentPage: 1,

  // Metadata (populated by MetadataModule)
  meta: {
    width: null,           // points
    height: null,          // points
    pageCount: null,
    creator: null,
    pdfXLevel: null,
    renderingIntent: null,
    iccProfiles: [],       // string[]
  },

  // Annotation
  strokes: [],             // Stroke[]  (now Map<pageNum, Stroke[]>)
  redoStack: [],           // Stroke[]  (now Map<pageNum, Stroke[]>)
  activeStroke: null,      // Stroke | null (in-progress)

  // Screenshot
  screenshotBuffer: null,  // Blob | null — in-memory PNG, replaced on each S keypress
  screenshotPage: null,    // number | null — page number captured in the buffer

  // UI
  cursorHideTimer: null,   // setTimeout handle
  isPresenting: false,
  resumePage: 1,           // page number to resume from; updated on exit, shown in start-page input
  originalFileName: null,  // string | null — base name of selected file, without extension
};
```

### MetadataModule

Responsible for invoking pdfcpu WASM and populating `AppState.meta`.

**Key functions:**

```javascript
// Load pdfcpu WASM once at startup
async function initPdfcpu(): Promise<void>

// Extract all metadata from a PDF Uint8Array
// Returns a Meta object; missing fields are set to null
async function extractMetadata(pdfBytes: Uint8Array): Promise<Meta>
```

pdfcpu WASM is initialised once on page load (not deferred to file selection). If a field cannot be extracted, the function returns `null` for that field; the display layer substitutes "N/A".

### RenderModule

Wraps PDF.js page rendering.

**Key functions:**

```javascript
// Initialise PDF.js with the loaded PDF bytes
async function loadPdf(pdfBytes: Uint8Array): Promise<PDFDocumentProxy>

// Render a single page to a canvas element
// Scale factor is always 1.0 (native pixel dimensions)
async function renderPage(doc: PDFDocumentProxy, pageNum: number, canvas: HTMLCanvasElement): Promise<void>
```

The canvas is sized to the exact viewport returned by `page.getViewport({ scale: 1.0 })`. No CSS transforms are applied.

### AnnotationModule

Manages stroke recording, canvas overlay rendering, undo/redo, and erase.

**Key functions:**

```javascript
// Called on mousedown in Presenter View
function beginStroke(x: number, y: number): void

// Called on mousemove while drawing
function continueStroke(x: number, y: number): void

// Called on mouseup
function endStroke(): void

// Undo the most recent stroke
function undo(): void

// Redo the most recently undone stroke
function redo(): void

// Erase all strokes and clear both stacks
function eraseAll(): void

// Redraw all committed strokes onto the canvas
function redrawCanvas(ctx: CanvasRenderingContext2D): void
```

### ScreenshotModule

Captures the composite frame (PDF canvas + annotation canvas) into a PNG Blob.

**Key function:**

```javascript
// Composite pdf-canvas + annotation-canvas into an offscreen canvas
// Encode as PNG Blob and store in AppState.screenshotBuffer
// Record AppState.screenshotPage = AppState.currentPage
// Enable #btn-download-screenshot on landing page
async function captureScreenshot(
  pdfCanvas: HTMLCanvasElement,
  annotationCanvas: HTMLCanvasElement
): Promise<void>
```

Implementation uses `OffscreenCanvas` (or a temporary `<canvas>`) to merge the two layers:

```javascript
async function captureScreenshot(pdfCanvas, annotationCanvas) {
  const w = pdfCanvas.width;
  const h = pdfCanvas.height;
  const offscreen = new OffscreenCanvas(w, h);
  const ctx = offscreen.getContext('2d');
  ctx.drawImage(pdfCanvas, 0, 0);          // PDF layer
  ctx.drawImage(annotationCanvas, 0, 0);   // annotation layer on top
  AppState.screenshotBuffer = await offscreen.convertToBlob({ type: 'image/png' });
  AppState.screenshotPage = AppState.currentPage;
}
```

If `OffscreenCanvas` is unavailable, falls back to a temporary `<canvas>` element.

Produces the Output PDF using pdf-lib, and handles screenshot download.

**Key functions:**

```javascript
// Embed strokes into the PDF and trigger download
// Output filename: {originalName}-PDFhero.pdf
async function saveWithAnnotations(
  pdfBytes: Uint8Array,
  strokes: Map<number, Stroke[]>,
  version: string,
  originalFileName: string
): Promise<void>

// Download the in-memory screenshot buffer as PNG
// Output filename: {originalName}-{pageNum:03d}-PDFhero.png
function downloadScreenshot(
  buffer: Blob,
  originalFileName: string,
  pageNum: number
): void
```

On error, functions catch exceptions and call `showError(message)` without re-throwing.

---

## Component Design

### Landing Page DOM Structure

```html
<section id="landing">
  <h1>PDFhero</h1>
  <button id="btn-about">About</button>

  <div id="shortcut-legend">
    <!-- 9 shortcut rows — includes S: screenshot -->
  </div>

  <input type="file" id="file-input" accept=".pdf" />
  <div id="metadata-panel"><!-- filename + all metadata fields populated after load --></div>

  <div id="present-controls">
    <label for="start-page-input">Start page:</label>
    <input type="number" id="start-page-input" value="1" min="1" />
    <button id="btn-present" disabled>Present as a hero</button>
  </div>

  <button id="btn-save">Save with annotations</button>
  <button id="btn-download-screenshot" disabled>Download screenshot</button>
</section>

<dialog id="about-dialog">
  <p>PDFhero by NoSocial.Net and Ivan Khvostishkov, copyright 2026+.<br>Created together with Kiro.</p>
  <button id="btn-about-close">Close</button>
</dialog>
```

The `<dialog>` element provides native accessibility. The "Present as a hero" button is enabled after successful metadata extraction. The "Download screenshot" button is enabled only after `AppState.screenshotBuffer` is non-null. The Start-Page Input is updated to `AppState.resumePage` each time `exitPresenterView()` is called.

### Presenter View DOM Structure

```html
<section id="presenter" style="display:none">
  <div id="slide-container" style="position:relative; display:inline-block">
    <canvas id="pdf-canvas"></canvas>
    <canvas id="annotation-canvas"
            style="position:absolute; top:0; left:0; cursor:none"></canvas>
  </div>
</section>
```

Both canvases share identical `width` and `height` attributes, set programmatically on each page render. The annotation canvas sits on top with `pointer-events` enabled.

---

## Data Models

### Stroke

```typescript
interface Point {
  x: number;  // canvas pixel coordinate
  y: number;
}

interface Stroke {
  points: Point[];   // all recorded pointer positions
  color: string;     // CSS colour string, default "#FF0000"
  lineWidth: number; // default 3
}
```

Strokes are stored as arrays of raw pointer positions. Rendering always re-interpolates using quadratic bezier curves (see Rendering Algorithm below).

### Meta

```typescript
interface Meta {
  width: number | null;           // PDF page width in points
  height: number | null;          // PDF page height in points
  pageCount: number | null;
  creator: string | null;
  pdfXLevel: string | null;       // e.g. "PDF/X-4"
  renderingIntent: string | null; // e.g. "RelativeColorimetric"
  iccProfiles: string[];          // e.g. ["sRGB", "AdobeRGB"]
}
```

---

## Rendering Algorithm — Smooth Bezier Strokes

Strokes are rendered using the midpoint quadratic bezier technique to avoid sharp corners.

```javascript
function drawStroke(ctx, stroke) {
  const pts = stroke.points;
  if (pts.length < 2) return;

  ctx.beginPath();
  ctx.moveTo(pts[0].x, pts[0].y);

  for (let i = 1; i < pts.length - 1; i++) {
    const mx = (pts[i].x + pts[i + 1].x) / 2;
    const my = (pts[i].y + pts[i + 1].y) / 2;
    ctx.quadraticCurveTo(pts[i].x, pts[i].y, mx, my);
  }

  // Draw to final point
  const last = pts[pts.length - 1];
  ctx.lineTo(last.x, last.y);
  ctx.stroke();
}
```

During an active stroke (`continueStroke`), the partial path is redrawn each frame by clearing the annotation canvas and calling `redrawCanvas()` followed by the partial stroke.

---

## Cursor Hide / Show Logic

```javascript
const CURSOR_HIDE_DELAY_MS = 0; // hidden immediately on mousedown / when stationary

// On mousemove (presenter view only):
function onMouseMove() {
  showCursor();
  clearTimeout(AppState.cursorHideTimer);
  // No auto-hide on move — cursor stays visible while moving
}

// On mousedown:
function onMouseDown(e) {
  hideCursor();
  beginStroke(e.offsetX, e.offsetY);
}

// On mouseup:
function onMouseUp(e) {
  endStroke();
  // Cursor remains hidden after mouseup
}

function showCursor() {
  annotationCanvas.style.cursor = 'crosshair';
}

function hideCursor() {
  annotationCanvas.style.cursor = 'none';
}
```

The cursor starts hidden (initial CSS `cursor: none` on `#presenter`). Any mouse movement shows the crosshair cursor. Pressing the mouse button hides it again.

---

## Save Flow (pdf-lib)

```
User clicks "Save with annotations"
        │
        ▼
Load original pdfBytes into PDFDocument.load()
        │
        ▼
For each page that has strokes:
  Get PDFPage
  For each Stroke on that page:
    Convert canvas coordinates → PDF coordinate space (y-axis flip)
    Draw path using page.drawPath() with stroke color and width
        │
        ▼
Update Info dict: creator = "PDFhero by NoSocial.Net v1.01"
        │
        ▼
doc.save() → Uint8Array
        │
        ▼
Derive output filename: "{originalName}-PDFhero.pdf"
        │
        ▼
Create Blob → object URL → <a download="{filename}"> click → revoke URL
```

## Screenshot Download Flow

```
User clicks "Download screenshot" on Landing Page
        │
        ▼
Read AppState.screenshotBuffer (Blob) and AppState.screenshotPage
        │
        ▼
Derive filename: "{originalName}-{screenshotPage:03d}-PDFhero.png"
  e.g. "slides-003-PDFhero.png"
        │
        ▼
Create object URL from Blob → <a download="{filename}"> click → revoke URL
```

**Coordinate transform** (canvas origin top-left → PDF origin bottom-left):

```javascript
function canvasToPdfY(canvasY, canvasHeight, pdfHeight) {
  return pdfHeight - (canvasY / canvasHeight) * pdfHeight;
}

function canvasToPdfX(canvasX, canvasWidth, pdfWidth) {
  return (canvasX / canvasWidth) * pdfWidth;
}
```

Strokes are recorded per-page. When the user navigates pages, `AppState.strokes` stores strokes indexed by page number.

---

## Data Structure — Per-Page Stroke Storage

```typescript
// AppState.strokes is a Map<pageNumber, Stroke[]>
// AppState.redoStack is a Map<pageNumber, Stroke[]>

// When current page changes, annotation module switches context
// Canvas is cleared and redrawn for the new page's strokes
```

Undo/redo operates on the current page's stroke list. The E (erase) key clears only the current page's strokes and redo stack.

---

## Fullscreen Lifecycle

```javascript
async function enterPresenterView() {
  const startPage = parseInt(document.getElementById('start-page-input').value, 10) || 1;
  AppState.currentPage = Math.max(1, Math.min(startPage, AppState.pageCount));
  showPresenterSection();
  await renderPage(AppState.pdfJsDoc, AppState.currentPage, pdfCanvas);
  syncAnnotationCanvasSize();
  redrawCanvas(annotationCtx);
  await document.documentElement.requestFullscreen();
  AppState.isPresenting = true;
}

function exitPresenterView() {
  if (document.fullscreenElement) document.exitFullscreen();
  AppState.isPresenting = false;
  AppState.resumePage = AppState.currentPage;
  document.getElementById('start-page-input').value = AppState.resumePage;
  showLandingSection();
}

// Listen for user-triggered fullscreen exit (Esc key native behavior)
document.addEventListener('fullscreenchange', () => {
  if (!document.fullscreenElement && AppState.isPresenting) {
    exitPresenterView();
  }
});
```

---

## Keyboard Event Handling

All shortcut keys are handled by a single `keydown` listener on `document`. Inside the handler, `event.preventDefault()` is called first for all 8 keys, then the corresponding action is dispatched.

```javascript
const SHORTCUT_ACTIONS = {
  ArrowRight: () => navigatePage(+1),
  ArrowLeft:  () => navigatePage(-1),
  PageDown:   () => navigatePage(+1),
  PageUp:     () => navigatePage(-1),
  q:          () => exitPresenterView(),
  Q:          () => exitPresenterView(),
  e:          () => AnnotationModule.eraseAll(),
  E:          () => AnnotationModule.eraseAll(),
  u:          () => AnnotationModule.undo(),
  U:          () => AnnotationModule.undo(),
  z:          () => AnnotationModule.redo(),
  Z:          () => AnnotationModule.redo(),
  s:          () => ScreenshotModule.captureScreenshot(pdfCanvas, annotationCanvas),
  S:          () => ScreenshotModule.captureScreenshot(pdfCanvas, annotationCanvas),
};

document.addEventListener('keydown', (event) => {
  if (!AppState.isPresenting) return;
  const action = SHORTCUT_ACTIONS[event.key];
  if (action) {
    event.preventDefault();
    action();
  }
});
```

---

## Error Handling Strategy

| Failure point | Behaviour |
|---|---|
| pdfcpu WASM init fails | Display "Metadata unavailable" banner; file selection still works |
| pdfcpu metadata field missing | Show "N/A" in metadata panel |
| PDF.js cannot load PDF | Show error banner on Landing Page; do not enable Present button |
| PDF.js page render error | Show error overlay in Presenter View; stay in presenter mode |
| pdf-lib save error | Show error toast; Landing Page remains functional |
| Fullscreen request denied | Enter presenter-like view without fullscreen; continue normally |
| Screenshot capture fails | Show error toast inside Presenter View; do not exit or disrupt slide |
| Screenshot download with empty buffer | "Download screenshot" button remains disabled; no action |

Errors are surfaced via a `showError(message)` utility that renders a dismissible `<div role="alert">` without any navigation.

---

## CDN Asset Loading

```html
<!-- PDF.js -->
<script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.4.168/pdf.min.mjs" type="module"></script>

<!-- pdf-lib -->
<script src="https://unpkg.com/pdf-lib@1.17.1/dist/pdf-lib.min.js"></script>

<!-- pdfcpu WASM is fetched at runtime via fetch() from a CDN or bundled inline -->
```

pdfcpu WASM is initialised with `WebAssembly.instantiateStreaming()` using a CDN URL. The `wasm_exec.js` glue file is inlined in the HTML to avoid a second network dependency.

---

## File / Asset Layout (Logical)

Since the app is delivered as three companion files, the logical layout is:

```
PDFhero.html          ← main app (single file)
  ├── <style>           CSS for both views
  ├── <script>          wasm_exec.js (inlined)
  ├── <script type="module">
  │     ├── AppState
  │     ├── MetadataModule
  │     ├── RenderModule
  │     ├── AnnotationModule
  │     ├── ScreenshotModule
  │     ├── SaveModule
  │     └── UI event wiring (main) + SW registration
  └── CDN <script> tags (PDF.js, pdf-lib)

manifest.json         ← PWA manifest (name, version, icons, display)
sw.js                 ← Service worker (cache-first, versioned cache)

tools/
  fetch_cdn_libs.py   ← Developer utility: download + SHA-256 archive CDN libs
vendor/
  manifest.json       ← SHA-256 hashes of downloaded libs (generated by script)
  pdf.js/             ← Archived PDF.js files
  pdf-lib/            ← Archived pdf-lib files
  pdfcpu/             ← Archived pdfcpu WASM + glue
```

### PWA / Service Worker Notes

The service worker uses a **cache-first** strategy for all assets. The cache name is versioned (e.g., `pdfhero-v1.01`) and must be updated alongside `manifest.json` whenever the app version or any CDN URL changes. On activation, old caches are deleted automatically.

```javascript
// sw.js — key constants (must match manifest.json version)
const CACHE_NAME = 'pdfhero-v1.01';
const CACHED_URLS = [
  './PDFhero.html',
  './manifest.json',
  'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.4.168/pdf.min.mjs',
  'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.4.168/pdf.worker.min.mjs',
  'https://unpkg.com/pdf-lib@1.17.1/dist/pdf-lib.min.js',
];
```

---

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: No Persistent Storage

*For any* sequence of user interactions (file selection, page navigation, annotation drawing, save), the application SHALL NOT write to `localStorage`, `sessionStorage`, `document.cookie`, or any `IndexedDB` store at any point during the session.

**Validates: Requirements 1.4**

---

### Property 2: Present Button State Mirrors PDF Load State

*For any* application state, the "Present as a hero" button SHALL be enabled if and only if a PDF file has been successfully selected and its metadata has been fully extracted; in all other states the button SHALL be disabled.

**Validates: Requirements 2.5**

---

### Property 3: Metadata Extraction Completeness

*For any* PDF file, every metadata field (width, height, page count, creator, PDF/X level, rendering intent, ICC profiles) SHALL be populated with its extracted value or with the placeholder "N/A" — never with `undefined`, `null`, or an empty string visible to the user.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8**

---

### Property 4: Native-Resolution Rendering

*For any* PDF page with declared dimensions W × H points, the PDF canvas element in Presenter View SHALL have `width = W` and `height = H` (with scale factor 1.0), and the annotation canvas SHALL have identical dimensions.

**Validates: Requirements 4.2**

---

### Property 5: Page Navigation Stays Within Bounds

*For any* PDF with N pages and current page index P in [1..N], pressing a next-page key (ArrowRight, PageDown) SHALL result in page index `min(P+1, N)`, and pressing a prev-page key (ArrowLeft, PageUp) SHALL result in page index `max(P-1, 1)`.

**Validates: Requirements 4.5, 4.6, 4.7, 4.8**

---

### Property 6: Stroke Recording Round-Trip

*For any* sequence of pointer-move events captured between a mousedown and mouseup, the resulting Stroke object SHALL contain all recorded points in order, SHALL be appended to the current page's stroke history, and the redo stack for that page SHALL be empty immediately after finalisation.

**Validates: Requirements 5.2, 5.3, 5.4, 5.5, 6.6**

---

### Property 7: Smooth Bezier Rendering

*For any* Stroke with three or more recorded points, the canvas drawing sequence SHALL include at least one `quadraticCurveTo` or `bezierCurveTo` call, and SHALL NOT consist exclusively of `lineTo` calls between consecutive points.

**Validates: Requirements 5.6**

---

### Property 8: Erase Clears All Annotation State

*For any* annotation state (any number of strokes in history and any number of strokes in the redo stack), pressing E SHALL result in an empty stroke history, an empty redo stack, and a blank annotation canvas for the current page.

**Validates: Requirements 6.1**

---

### Property 9: Undo Reduces History and Grows Redo Stack

*For any* current-page stroke history containing N ≥ 1 strokes, pressing U SHALL reduce the stroke history length to N−1 and add the removed stroke (the most recently finalised one) to the top of the redo stack, with the annotation canvas redrawn to reflect the N−1 remaining strokes.

**Validates: Requirements 6.2, 6.3**

---

### Property 10: Redo Restores Stroke From Redo Stack

*For any* redo stack containing M ≥ 1 strokes, pressing Z SHALL reduce the redo stack length to M−1 and append the restored stroke to the current-page stroke history, with the annotation canvas redrawn to reflect the added stroke.

**Validates: Requirements 6.4, 6.5**

---

### Property 11: Saved PDF Embeds All Current Strokes as Vectors

*For any* collection of strokes drawn across pages, the Output PDF produced by pdf-lib SHALL contain one vector path object per stroke per page, with path geometry equivalent (after coordinate transformation) to the canvas stroke coordinates.

**Validates: Requirements 7.1**

---

### Property 12: Saved PDF Preserves Original Content and Updates Creator

*For any* input PDF with N pages and an arbitrary set of metadata fields, the Output PDF SHALL contain exactly N pages with content identical to the input, SHALL update the creator field to `"PDFhero by NoSocial.Net v1.01"`, and SHALL preserve all other Info dict fields.

**Validates: Requirements 7.2, 7.5**

---

### Property 13: All Shortcut Keys Trigger Correct Action and Suppress Default

*For any* key event with key value in `{ArrowRight, ArrowLeft, PageDown, PageUp, Q, E, U, Z, S}` received while in Presenter View, `event.preventDefault()` SHALL be called and the corresponding defined action SHALL be invoked exactly once.

**Validates: Requirements 8.1, 8.3**

---

### Property 14: Screenshot Buffer Replaced on Each Capture

*For any* state where `AppState.screenshotBuffer` is non-null and the S key is pressed, the buffer SHALL be replaced with a new PNG Blob and `AppState.screenshotPage` SHALL be updated to the current page number. The previous buffer SHALL NOT be retained.

**Validates: Requirements 9.1, 9.2**

---

### Property 15: Screenshot Filename Encodes Page Number

*For any* screenshot download triggered with `screenshotPage = P` and `originalFileName = F`, the downloaded filename SHALL be `F + '-' + String(P).padStart(3,'0') + '-PDFhero.png'`.

**Validates: Requirements 9.3**

---

### Property 16: Resume Page Persists Across Sessions Within Same Load

*For any* Presenter View exit at page P, `AppState.resumePage` SHALL equal P, the Start-Page Input value SHALL equal P, and the next `enterPresenterView()` call SHALL begin rendering at page P (clamped to [1, pageCount]).

**Validates: Requirements 4.1 (updated), 4.9, 2.7**

---

### Property 17: Output PDF Filename Contains Original Name Plus Suffix

*For any* save triggered with `originalFileName = F`, the downloaded filename SHALL be `F + '-PDFhero.pdf'`.

**Validates: Requirements 7.3**
