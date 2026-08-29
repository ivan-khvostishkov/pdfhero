# Implementation Plan: PDFhero Presenter v1.01

## Overview

Build `PDFhero.html` as a single self-contained file with all JavaScript inline. The file loads PDF.js, pdf-lib, and pdfcpu WASM from CDN, and implements a finite-state machine with Landing Page and Presenter View, freehand annotation with undo/redo, in-presenter screenshot capture, resume-from-last-page, and save-to-PDF functionality.

---

## Tasks

- [x] 1. Scaffold PDFhero.html with CDN imports, CSS, and DOM skeleton
  - [x] 1.1 Create `PDFhero.html` with full page structure and PWA support
    - Add `<section id="landing">` with:
      - App title, shortcut legend (9 shortcuts including S), About button
      - File input, metadata panel (filename + all metadata fields)
      - Present controls row: `<label>Start page:</label>` + `<input type="number" id="start-page-input" value="1" min="1">` + `<button id="btn-present" disabled>`
      - `<button id="btn-save">Save with annotations</button>`
      - `<button id="btn-download-screenshot" disabled>Download screenshot</button>`
    - Add `<section id="presenter">` with `#slide-container`, `#pdf-canvas`, and `#annotation-canvas` (overlay, `position:absolute`, `cursor:none`)
    - Add `<dialog id="about-dialog">` with text "PDFhero by NoSocial.Net and Ivan Khvostishkov, copyright 2026+. Created together with Kiro." and close button
    - Include CDN `<script>` tags for PDF.js (`pdf.min.mjs`, type="module") and pdf-lib
    - Inline placeholder `<script type="module">` block (empty — filled in subsequent tasks)
    - Add base CSS: fullscreen body, landing layout, presenter fullscreen + cursor-none, hidden presenter section
    - **Progressive Web App (PWA) support** — so the app works fully offline with locally cached code:
      - Create `manifest.json` alongside `PDFhero.html` with fields: `name`, `short_name`, `version` (matching app version e.g. `"1.01"`), `start_url`, `display: "standalone"`, `background_color`, `theme_color`, and an `icons` array (at minimum a 192×192 and 512×512 PNG icon)
      - Add `<link rel="manifest" href="manifest.json">` in `<head>` of `PDFhero.html`
      - Create `sw.js` (service worker) alongside `PDFhero.html` with a cache-first strategy:
        - On `install`: cache `PDFhero.html`, `manifest.json`, the PDF.js CDN URL, and the pdf-lib CDN URL under a versioned cache name (e.g. `pdfhero-v1.01`)
        - On `activate`: delete any old caches whose name does not match the current version string
        - On `fetch`: serve from cache if available, fall back to network, cache the response
      - Register the service worker in the inline `<script>` block: `if ('serviceWorker' in navigator) navigator.serviceWorker.register('./sw.js')`
      - The cache name in `sw.js` and the `version` field in `manifest.json` MUST be updated together whenever the app version changes
    - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 4.3_

  - [ ]* 1.2 Write property test for Present button initial state
    - **Property 2: Present Button State Mirrors PDF Load State**
    - **Validates: Requirements 2.5**
    - Assert button is disabled when no PDF is loaded; assert enabled only after successful metadata extraction

- [x] 2. Implement AppState and utility functions
  - [x] 2.1 Define `AppState` object and `showError` / `dismissError` helpers
    - Declare `AppState` with all fields: `pdfBytes`, `pdfJsDoc`, `pageCount`, `currentPage`, `meta`, `strokes` (Map), `redoStack` (Map), `activeStroke`, `screenshotBuffer`, `screenshotPage`, `cursorHideTimer`, `isPresenting`, `resumePage`, `originalFileName`
    - Implement `showError(message)` — renders dismissible `<div role="alert">` without page navigation
    - Implement `dismissError()` — removes the alert element
    - _Requirements: 1.4_

  - [ ]* 2.2 Write property test for no persistent storage
    - **Property 1: No Persistent Storage**
    - **Validates: Requirements 1.4**
    - Spy on `localStorage.setItem`, `sessionStorage.setItem`, `document.cookie` setter, and `indexedDB.open`; run a simulated session through all interactions and assert none were called

- [x] 3. Implement MetadataModule (pdfcpu WASM)
  - [x] 3.1 Inline `wasm_exec.js` glue and implement `initPdfcpu()`
    - Embed the Go `wasm_exec.js` runtime as an inline `<script>` block
    - Implement `initPdfcpu()`: fetch pdfcpu WASM from CDN using `WebAssembly.instantiateStreaming()`; initialise once at page load
    - If init fails, display "Metadata unavailable" banner and continue (file selection still enabled)
    - _Requirements: 1.1, 1.2, 1.3_

  - [x] 3.2 Implement `extractMetadata(pdfBytes)`
    - Call pdfcpu WASM to extract: width, height, pageCount, creator, pdfXLevel, renderingIntent, iccProfiles
    - For any field that cannot be extracted, return `null` (display layer substitutes "N/A")
    - Populate `AppState.meta` with the returned object
    - _Requirements: 3.1, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8_

  - [ ]* 3.3 Write property test for metadata extraction completeness
    - **Property 3: Metadata Extraction Completeness**
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8**
    - For a corpus of test PDFs (including one with missing fields), assert every displayed field is a non-empty string (never `undefined`, `null`, or `""`)

- [x] 4. Implement file selection and metadata display
  - [x] 4.1 Wire file input to load pipeline
    - On `change` event of `#file-input`, read file as `ArrayBuffer`, convert to `Uint8Array`, store as `AppState.pdfBytes`
    - Store the filename (without extension) in `AppState.originalFileName`
    - Display filename at the top of `#metadata-panel`
    - Call `extractMetadata(pdfBytes)` and populate `#metadata-panel` with all fields (width×height, viewport size, page count, creator, PDF/X, rendering intent, ICC profiles); show "N/A" for null fields
    - Also display current viewport size (`window.innerWidth × window.innerHeight`)
    - Reset `AppState.screenshotBuffer = null`, `AppState.screenshotPage = null`; disable `#btn-download-screenshot`
    - Reset `AppState.resumePage = 1`; set `#start-page-input` value to `1`
    - On success, enable `#btn-present`; on failure, show error banner and keep button disabled
    - _Requirements: 2.4, 2.5, 2.7, 2.8, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9_

  - [x] 4.2 Implement About dialog open/close
    - Wire `#btn-about` to call `document.getElementById('about-dialog').showModal()`
    - Wire `#btn-about-close` to call `.close()` on the dialog
    - _Requirements: 2.3_

- [x] 5. Implement RenderModule (PDF.js)
  - [x] 5.1 Implement `loadPdf(pdfBytes)` and `renderPage(doc, pageNum, canvas)`
    - `loadPdf`: call `pdfjsLib.getDocument({ data: pdfBytes }).promise`; store result in `AppState.pdfJsDoc`; store `numPages` in `AppState.pageCount`; return `PDFDocumentProxy`
    - `renderPage`: call `doc.getPage(pageNum)`, get viewport with `scale: 1.0`, set `canvas.width` and `canvas.height` to viewport dimensions, render to canvas context
    - On `loadPdf` error, show error banner and keep Present button disabled
    - On `renderPage` error, show error overlay inside Presenter View without exiting
    - _Requirements: 4.1, 4.2_

  - [ ]* 5.2 Write property test for native-resolution rendering
    - **Property 4: Native-Resolution Rendering**
    - **Validates: Requirements 4.2**
    - After `renderPage` completes, assert `pdf-canvas.width === pageViewport.width` and `annotation-canvas.width === pdf-canvas.width` (and same for height)

- [ ] 6. Implement AnnotationModule
  - [ ] 6.1 Implement stroke begin / continue / end and canvas redraw
    - Implement `beginStroke(x, y)`: clear `redoStack` for current page, create new `Stroke` `{points:[{x,y}], color:'#FF0000', lineWidth:3}`, assign to `AppState.activeStroke`
    - Implement `continueStroke(x, y)`: push `{x,y}` to `activeStroke.points`; clear annotation canvas; call `redrawCanvas(ctx)` for all committed strokes; then draw active stroke using bezier algorithm
    - Implement `endStroke()`: push `activeStroke` to `AppState.strokes.get(currentPage)`; set `activeStroke = null`
    - Implement `redrawCanvas(ctx)`: iterate committed strokes for current page, call `drawStroke(ctx, stroke)` for each
    - Implement `drawStroke(ctx, stroke)` using midpoint quadratic bezier algorithm: `moveTo` first point, loop `quadraticCurveTo` through midpoints, `lineTo` final point
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 6.6_

  - [ ]* 6.2 Write property test for stroke recording round-trip
    - **Property 6: Stroke Recording Round-Trip**
    - **Validates: Requirements 5.2, 5.3, 5.4, 5.5, 6.6**
    - Simulate mousedown → N mousemoves → mouseup; assert resulting stroke has N+1 points in order, is appended to current page history, and redo stack is empty

  - [ ]* 6.3 Write property test for smooth bezier rendering
    - **Property 7: Smooth Bezier Rendering**
    - **Validates: Requirements 5.6**
    - Spy on `CanvasRenderingContext2D.quadraticCurveTo`; for a stroke with ≥ 3 points, assert it is called at least once

  - [~] 6.4 Implement `undo()`, `redo()`, and `eraseAll()`
    - `undo()`: if current-page history has ≥ 1 stroke, pop last stroke, push to redo stack, redraw canvas
    - `redo()`: if redo stack has ≥ 1 stroke, pop from redo stack, push to history, redraw canvas
    - `eraseAll()`: clear history and redo stack for current page, clear annotation canvas
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

  - [ ]* 6.5 Write property test for undo reduces history and grows redo stack
    - **Property 9: Undo Reduces History and Grows Redo Stack**
    - **Validates: Requirements 6.2, 6.3**

  - [ ]* 6.6 Write property test for redo restores stroke from redo stack
    - **Property 10: Redo Restores Stroke From Redo Stack**
    - **Validates: Requirements 6.4, 6.5**

  - [ ]* 6.7 Write property test for erase clears all annotation state
    - **Property 8: Erase Clears All Annotation State**
    - **Validates: Requirements 6.1**

- [ ] 7. Implement ScreenshotModule
  - [~] 7.1 Implement `captureScreenshot(pdfCanvas, annotationCanvas)`
    - Create `OffscreenCanvas(w, h)` (fall back to temp `<canvas>` if unavailable)
    - `ctx.drawImage(pdfCanvas, 0, 0)` then `ctx.drawImage(annotationCanvas, 0, 0)`
    - Encode as PNG: `offscreen.convertToBlob({ type: 'image/png' })`
    - Store result in `AppState.screenshotBuffer`; store `AppState.screenshotPage = AppState.currentPage`
    - Enable `#btn-download-screenshot` on the landing page
    - On error, call `showError(message)` without exiting Presenter View
    - _Requirements: 9.1, 9.2, 9.4, 9.5_

  - [ ]* 7.2 Write property test for screenshot buffer replacement
    - **Property 14: Screenshot Buffer Replaced on Each Capture**
    - **Validates: Requirements 9.1, 9.2**
    - Call `captureScreenshot` twice; assert second call replaces first buffer and `screenshotPage` reflects second call's page

- [ ] 8. Implement Presenter View lifecycle, cursor logic, and resume-page
  - [~] 8.1 Implement `enterPresenterView()`, `exitPresenterView()`, and `fullscreenchange` listener
    - `enterPresenterView()`:
      - Read `#start-page-input` value; clamp to [1, pageCount]; set `AppState.currentPage`
      - Show `#presenter` section (hide `#landing`), set `AppState.isPresenting = true`
      - Call `renderPage`, `syncAnnotationCanvasSize`, `redrawCanvas`
      - Call `document.documentElement.requestFullscreen()`; if denied, continue without fullscreen
    - `exitPresenterView()`:
      - Call `document.exitFullscreen()` if active
      - Set `AppState.isPresenting = false`
      - Set `AppState.resumePage = AppState.currentPage`
      - Update `#start-page-input` value to `AppState.resumePage`
      - Show `#landing` (hide `#presenter`)
    - Add `fullscreenchange` listener: if `!document.fullscreenElement && isPresenting`, call `exitPresenterView()`
    - Implement `syncAnnotationCanvasSize()`: match annotation canvas dimensions to `pdf-canvas`
    - _Requirements: 2.7, 4.1, 4.3, 4.9_

  - [~] 8.2 Implement pointer event handlers and cursor hide/show
    - `mousemove` on annotation canvas: show crosshair cursor; if `activeStroke`, call `continueStroke(e.offsetX, e.offsetY)`
    - `mousedown` on annotation canvas: hide cursor, call `beginStroke(e.offsetX, e.offsetY)`
    - `mouseup` on annotation canvas: call `endStroke()`; cursor stays hidden
    - Initial state: annotation canvas CSS `cursor: none`
    - _Requirements: 5.2, 5.3, 5.4, 5.5, 4.4_

  - [ ]* 8.3 Write property test for resume page
    - **Property 16: Resume Page Persists Across Sessions Within Same Load**
    - **Validates: Requirements 4.9, 2.7**
    - Call `exitPresenterView()` with `currentPage = P`; assert `AppState.resumePage === P`, `#start-page-input.value === String(P)`; simulate `enterPresenterView()` and assert `currentPage === P`

- [ ] 9. Implement keyboard shortcut handler and page navigation
  - [~] 9.1 Implement `navigatePage(delta)` and keyboard dispatch (9 shortcuts)
    - `navigatePage(+1)`: if `currentPage < pageCount`, increment, re-render
    - `navigatePage(-1)`: if `currentPage > 1`, decrement, re-render
    - Add single `keydown` listener on `document`; guard with `if (!AppState.isPresenting) return`
    - Dispatch all 9 shortcut keys including `s/S → captureScreenshot`; call `event.preventDefault()` for each matched key
    - _Requirements: 4.5, 4.6, 4.7, 4.8, 6.1, 6.2, 6.4, 8.1, 8.3, 9.1, 9.4_

  - [ ]* 9.2 Write property test for page navigation bounds
    - **Property 5: Page Navigation Stays Within Bounds**
    - **Validates: Requirements 4.5, 4.6, 4.7, 4.8**

  - [ ]* 9.3 Write property test for all shortcut keys suppress default and trigger action
    - **Property 13: All Shortcut Keys Trigger Correct Action and Suppress Default**
    - **Validates: Requirements 8.1, 8.3**
    - Include S key in the test matrix

- [~] 10. Checkpoint — Ensure core navigation, annotation, and screenshot work end-to-end
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 11. Implement SaveModule (pdf-lib) and screenshot download
  - [~] 11.1 Implement `saveWithAnnotations(pdfBytes, strokes, version, originalFileName)`
    - Call `PDFLib.PDFDocument.load(pdfBytes)`
    - For each page with strokes: get `PDFPage`, iterate strokes, convert coordinates, draw path
    - Update creator: `doc.setCreator('PDFhero by NoSocial.Net v1.01')`
    - Derive output filename: `originalFileName + '-PDFhero.pdf'`
    - `doc.save()` → Blob → `<a download="{filename}">` click → revoke URL
    - On error, catch and call `showError(message)`
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

  - [~] 11.2 Implement `downloadScreenshot(buffer, originalFileName, pageNum)`
    - Wire `#btn-download-screenshot` click handler
    - Guard: if `AppState.screenshotBuffer === null`, do nothing (button is disabled anyway)
    - Derive filename: `originalFileName + '-' + String(pageNum).padStart(3, '0') + '-PDFhero.png'`
    - Create object URL from `buffer` Blob → `<a download="{filename}">` click → revoke URL
    - _Requirements: 9.3_

  - [ ]* 11.3 Write property test for saved PDF embeds all strokes as vectors
    - **Property 11: Saved PDF Embeds All Current Strokes as Vectors**
    - **Validates: Requirements 7.1**

  - [ ]* 11.4 Write property test for saved PDF preserves content and updates creator
    - **Property 12: Saved PDF Preserves Original Content and Updates Creator**
    - **Validates: Requirements 7.2, 7.5**

  - [ ]* 11.5 Write property test for output PDF filename
    - **Property 17: Output PDF Filename Contains Original Name Plus Suffix**
    - **Validates: Requirements 7.3**
    - For `originalFileName = "slides"`, assert downloaded filename equals `"slides-PDFhero.pdf"`

  - [ ]* 11.6 Write property test for screenshot filename encodes page number
    - **Property 15: Screenshot Filename Encodes Page Number**
    - **Validates: Requirements 9.3**
    - For `originalFileName = "slides"` and `screenshotPage = 3`, assert filename equals `"slides-003-PDFhero.png"`

- [ ] 12. Wire all modules together in `<script type="module">`
  - [~] 12.1 Assemble main entry point and event wiring
    - Call `initPdfcpu()` at DOMContentLoaded (non-blocking)
    - Wire `#btn-present` → `enterPresenterView()`
    - Wire `#btn-save` → `saveWithAnnotations(...)`
    - Wire `#btn-download-screenshot` → `downloadScreenshot(...)`
    - Wire `#btn-about` / `#btn-about-close` → dialog open/close
    - Wire `#file-input` change → load pipeline (tasks 3.2, 4.1, 5.1 combined)
    - Confirm all 9 keyboard shortcuts registered and functional
    - _Requirements: 1.1, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 4.1, 8.1, 8.2, 8.3, 9.1_

- [~] 13. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 14. Create Python CDN library archival script
  - [~] 14.1 Create `tools/fetch_cdn_libs.py` — downloads pinned CDN libraries to local disk
    - The script is standalone, requires only Python 3.8+ stdlib (`urllib.request`, `hashlib`, `json`, `pathlib`) — no pip installs
    - Define a `LIBRARIES` list at the top of the script. Each entry is a dict with:
      - `name`: human-readable name (e.g. `"PDF.js"`)
      - `url`: exact CDN URL used in `PDFhero.html` (e.g. `"https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.4.168/pdf.min.mjs"`)
      - `local_path`: relative output path under `vendor/` (e.g. `"vendor/pdf.js/pdf.min.mjs"`)
    - Include all CDN assets referenced by `PDFhero.html` and `sw.js`:
      - PDF.js `pdf.min.mjs` and its worker `pdf.worker.min.mjs` (same version)
      - pdf-lib `pdf-lib.min.js`
      - pdfcpu WASM binary and its `wasm_exec.js` glue (if loaded from CDN)
    - For each library:
      1. Download the file with `urllib.request.urlretrieve`
      2. Compute SHA-256 of the downloaded bytes with `hashlib`
      3. Write the file to `local_path` (create parent dirs with `pathlib.Path.mkdir(parents=True, exist_ok=True)`)
      4. Append an entry to `vendor/manifest.json`: `{ "name", "url", "local_path", "sha256", "fetched_at" (ISO 8601 UTC) }`
    - If a file already exists at `local_path`, compare its SHA-256 to the previously recorded value in `vendor/manifest.json`:
      - If **unchanged**: print `[OK] {name} — unchanged`
      - If **changed**: print `[CHANGED] {name} — SHA-256 mismatch! Previous: {old}, Current: {new}` (this is the change-detection signal)
    - Print a final summary line: `Fetched N files. M changed. Saved to vendor/`
    - Usage: `python tools/fetch_cdn_libs.py` from the project root
    - The `vendor/` directory and `vendor/manifest.json` are intended for archival and debugging; they are NOT loaded by `PDFhero.html` unless the developer manually swaps CDN URLs for local paths
    - _Requirements: 1.1 (supports offline/validation workflow)_

---

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP delivery
- All app code lives in a single `PDFhero.html`; PWA support adds `manifest.json` and `sw.js` as companion files
- The `sw.js` cache name and `manifest.json` version field must be kept in sync — bump both when the app version changes
- Property tests can be implemented with a lightweight in-page test harness or a separate test HTML file
- Checkpoints (Tasks 10, 13) validate the integrated state at key milestones
- No build step, no npm, no bundler — all code is browser-native ES2022+
- The `OffscreenCanvas` API is supported in all modern browsers; the fallback to a temp `<canvas>` covers older environments
- Task 14 (`fetch_cdn_libs.py`) is a developer utility — run it once to snapshot current CDN versions, and re-run after any CDN URL bump to detect silent changes

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["2.1", "1.2"] },
    { "id": 2, "tasks": ["2.2", "3.1"] },
    { "id": 3, "tasks": ["3.2", "4.2"] },
    { "id": 4, "tasks": ["3.3", "4.1", "5.1"] },
    { "id": 5, "tasks": ["5.2", "6.1"] },
    { "id": 6, "tasks": ["6.2", "6.3", "6.4", "7.1", "8.1"] },
    { "id": 7, "tasks": ["6.5", "6.6", "6.7", "7.2", "8.2", "8.3", "9.1"] },
    { "id": 8, "tasks": ["9.2", "9.3", "11.1", "11.2"] },
    { "id": 9, "tasks": ["11.3", "11.4", "11.5", "11.6", "12.1"] },
    { "id": 10, "tasks": ["14.1"] }
  ]
}
```
