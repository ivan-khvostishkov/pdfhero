# Requirements Document

## Introduction

PDFhero Presenter (v1.01) is a single self-contained HTML file named `PDFhero.html` that enables local PDF presentation with freehand annotation and screenshot capabilities. The application requires no server, no build step, and no browser extensions. It operates over both `file://` and `http(s)://` protocols. PDF metadata extraction is performed via pdfcpu WASM, page rendering via PDF.js, and annotation embedding via pdf-lib. No data is persisted to cookies, sessions, or localStorage — all state is in-memory for the duration of the session.

## Glossary

- **App**: The single self-contained HTML file implementing PDFhero Presenter.
- **Landing Page**: The initial view presented to the user before a PDF file is selected.
- **File Selector**: A browser-native file input control that opens a local file picker without uploading data to any server.
- **Presenter View**: The full-screen, distraction-free mode used to display PDF pages during a presentation.
- **Canvas Overlay**: A transparent HTML canvas element layered on top of the rendered PDF page, used for freehand annotation.
- **Stroke**: A single continuous freehand pen path drawn on the Canvas Overlay from mousedown to mouseup.
- **Annotation**: One or more Strokes drawn on the Canvas Overlay that may be embedded as vector objects in the output PDF.
- **Redo Stack**: The ordered list of Strokes that were undone and are available for redo.
- **pdfcpu WASM**: The WebAssembly build of the pdfcpu library used for PDF metadata extraction, ICC profile detection, output intent reading, and PDF/X validation.
- **PDF.js**: Mozilla's JavaScript library used to render PDF pages in the browser canvas.
- **pdf-lib**: A JavaScript library used to embed vector annotation objects and update creator metadata in the saved PDF.
- **ICC Profile**: An International Color Consortium color profile embedded in the PDF (sRGB, AdobeRGB, or ProPhotoRGB).
- **PDF/X Compliance**: Conformance level of the PDF to the PDF/X ISO standard family, as reported by pdfcpu WASM.
- **Rendering Intent**: The ICC rendering intent declared in the PDF's output intent.
- **Output PDF**: The file produced when the user saves, containing the original PDF content, any embedded vector annotations, and updated creator metadata.
- **Screenshot Buffer**: An in-memory PNG bitmap capture of the composite slide (PDF render + annotations) for the current page at the moment the S key is pressed. Only one screenshot is held at a time; each S keypress replaces the previous buffer.
- **Resume Page**: The page number stored in AppState when the user exits Presenter View, used to pre-populate the start-page input on the Landing Page so the next session resumes from where the last one ended.
- **Start-Page Input**: An editable numeric field on the Landing Page, adjacent to the "Present as a hero" button, that controls which page Presenter View opens on.

---

## Requirements

### Requirement 1 — Self-Contained Delivery

**User Story:** As a presenter, I want a single HTML file that needs no server or build step, so that I can open it directly from disk or any web server without installation.

#### Acceptance Criteria

1. THE App SHALL be delivered as a single file named `PDFhero.html` with all JavaScript, CSS, and WASM assets either inline or loaded from CDN URLs, requiring no build toolchain to produce or run.
2. THE App SHALL function correctly when opened via the `file://` protocol in a modern browser.
3. THE App SHALL function correctly when served over `http://` or `https://`.
4. THE App SHALL store no user data in cookies, `localStorage`, `sessionStorage`, or any browser-persistent storage mechanism.

---

### Requirement 2 — Landing Page Layout

**User Story:** As a user, I want a clear landing page with an app title, shortcut legend, and an About popup, so that I understand the tool at a glance.

#### Acceptance Criteria

1. THE App SHALL display the application title "PDFhero" on the Landing Page.
2. THE App SHALL display a keyboard shortcut legend on the Landing Page listing all supported keys and their actions.
3. THE App SHALL provide an About popup accessible from the Landing Page that displays the text "PDFhero by NoSocial.Net and Ivan Khvostishkov, copyright 2026+. Created together with Kiro.".
4. THE App SHALL display a File Selector on the Landing Page that opens a local file picker restricted to PDF files.
5. THE App SHALL display a "Present as a hero" button on the Landing Page that is enabled only after a PDF file has been selected and its metadata loaded.
6. THE App SHALL display a "Save with annotations" button on the Landing Page that is visible at all times.
7. THE App SHALL display a Start-Page Input field adjacent to the "Present as a hero" button, initialised to 1, editable by the user, and updated to the Resume Page number each time the user exits Presenter View.
8. THE App SHALL display a "Download screenshot" button on the Landing Page that is enabled only after a Screenshot Buffer exists; the button SHALL be disabled on initial load and after a new PDF is selected before any screenshot has been taken.

---

### Requirement 3 — PDF Metadata Extraction

**User Story:** As a presenter, I want to see key metadata about my PDF after selecting it, so that I can verify the file is correct before presenting.

#### Acceptance Criteria

1. WHEN a PDF file is selected via the File Selector, THE App SHALL extract and display the PDF document size (width × height in points or pixels) using pdfcpu WASM.
2. WHEN a PDF file is selected via the File Selector, THE App SHALL extract and display the current viewport size (browser window width × height in CSS pixels).
3. WHEN a PDF file is selected via the File Selector, THE App SHALL extract and display the total page count using pdfcpu WASM.
4. WHEN a PDF file is selected via the File Selector, THE App SHALL extract and display the PDF creator field value using pdfcpu WASM.
5. WHEN a PDF file is selected via the File Selector, THE App SHALL extract and display the PDF/X compliance level using pdfcpu WASM.
6. WHEN a PDF file is selected via the File Selector, THE App SHALL extract and display the rendering intent declared in the PDF output intent using pdfcpu WASM.
7. WHEN a PDF file is selected via the File Selector, THE App SHALL detect and display which built-in ICC color profiles (sRGB, AdobeRGB, ProPhotoRGB) are embedded in the PDF using pdfcpu WASM.
8. IF pdfcpu WASM cannot extract a metadata field, THEN THE App SHALL display a placeholder value (e.g., "N/A") for that field rather than leaving it blank or throwing an error.
9. WHEN a PDF file is selected via the File Selector, THE App SHALL display the filename of the selected file in the metadata panel.

---

### Requirement 4 — Presenter View

**User Story:** As a presenter, I want a full-screen, distraction-free view of my PDF pages, so that my audience sees only the slide content.

#### Acceptance Criteria

1. WHEN the user activates "Present as a hero", THE App SHALL enter Presenter View by requesting the browser Fullscreen API, beginning at the page number specified in the Start-Page Input.
2. WHILE in Presenter View, THE App SHALL render the current PDF page at its native pixel dimensions such that a 1920×1080-point PDF displayed on a 1920×1080-pixel screen requires no scaling.
3. WHILE in Presenter View, THE App SHALL hide all browser toolbars, scrollbars, and UI chrome to the extent permitted by the Fullscreen API.
4. WHILE in Presenter View, THE App SHALL hide the mouse cursor by default when the mouse is stationary.
5. WHEN the right arrow key or Page Down key is pressed in Presenter View, THE App SHALL advance to the next PDF page.
6. WHEN the left arrow key or Page Up key is pressed in Presenter View, THE App SHALL navigate to the previous PDF page.
7. WHILE the current page is the first page in Presenter View, THE App SHALL ignore left arrow and Page Up key presses and perform no navigation.
8. WHILE the current page is the last page in Presenter View, THE App SHALL ignore right arrow and Page Down key presses and perform no navigation.
9. WHEN the Q key is pressed in Presenter View, THE App SHALL exit Presenter View, record the current page number as the Resume Page, update the Start-Page Input on the Landing Page, and return to the Landing Page.

---

### Requirement 5 — Annotation Drawing

**User Story:** As a presenter, I want to draw freehand strokes on top of slides with a pen tool, so that I can highlight content during a presentation.

#### Acceptance Criteria

1. WHILE in Presenter View, THE App SHALL display a transparent Canvas Overlay positioned precisely over the rendered PDF page.
2. WHEN the mouse moves in Presenter View, THE App SHALL make the mouse cursor visible.
3. WHEN the mouse button is pressed (mousedown) in Presenter View, THE App SHALL hide the mouse cursor and begin recording a new Stroke on the Canvas Overlay.
4. WHILE the mouse button is held down in Presenter View, THE App SHALL render the Stroke as a smooth freehand curve using the recorded pointer positions.
5. WHEN the mouse button is released (mouseup) in Presenter View, THE App SHALL finalise the current Stroke, add it to the annotation history, and keep the cursor hidden.
6. THE App SHALL render Strokes as smooth curves (e.g., using canvas bezier or quadratic curve interpolation) rather than jagged polylines.

---

### Requirement 6 — Annotation Management

**User Story:** As a presenter, I want to undo, redo, and erase my annotations, so that I can correct mistakes during a live presentation.

#### Acceptance Criteria

1. WHEN the E key is pressed in Presenter View, THE App SHALL erase all current Annotations from the Canvas Overlay and clear the annotation history and Redo Stack.
2. WHEN the U key is pressed in Presenter View and at least one Stroke exists in the annotation history, THE App SHALL remove the most recently added Stroke from the Canvas Overlay and move it to the Redo Stack.
3. WHEN the U key is pressed in Presenter View and no Strokes exist in the annotation history, THE App SHALL perform no action.
4. WHEN the Z key is pressed in Presenter View and the Redo Stack is non-empty, THE App SHALL restore the most recently undone Stroke to the Canvas Overlay and remove it from the Redo Stack.
5. WHEN the Z key is pressed in Presenter View and the Redo Stack is empty, THE App SHALL perform no action.
6. WHEN a new Stroke is finalised in Presenter View, THE App SHALL clear the Redo Stack.

---

### Requirement 7 — Save with Annotations

**User Story:** As a presenter, I want to save the annotated PDF to a local file, so that I can share or archive the marked-up slides.

#### Acceptance Criteria

1. WHEN the user activates "Save with annotations" and at least one Stroke has been drawn, THE App SHALL embed all current Strokes as vector annotation objects in the Output PDF using pdf-lib.
2. WHEN the user activates "Save with annotations" regardless of whether any Strokes have been drawn, THE App SHALL update the PDF creator metadata field to "PDFhero by NoSocial.Net vX.Y" (where X.Y is the current version number) in the Output PDF using pdf-lib.
3. WHEN the Output PDF has been generated, THE App SHALL trigger a browser file download with a filename derived from the original filename by appending the suffix `-PDFhero` before the `.pdf` extension (e.g., `slides.pdf` → `slides-PDFhero.pdf`).
4. IF pdf-lib encounters an error during save, THEN THE App SHALL display an error message to the user describing the failure without crashing the App.
5. THE App SHALL preserve all original PDF content, pages, and non-annotation metadata in the Output PDF.

---

### Requirement 8 — Keyboard Shortcut Completeness

**User Story:** As a user, I want all keyboard shortcuts to be documented on the Landing Page and consistently handled, so that I can learn and rely on them.

#### Acceptance Criteria

1. THE App SHALL handle the following keys in Presenter View: right arrow (next page), left arrow (previous page), Page Down (next page), Page Up (previous page), Q (exit), E (erase all), U (undo last stroke), Z (redo), S (capture screenshot).
2. THE App SHALL display all nine shortcuts listed in requirement 8.1 in the keyboard shortcut legend on the Landing Page.
3. WHILE in Presenter View, THE App SHALL suppress default browser behaviour for all nine shortcut keys so that the browser does not process those keys for its own navigation or other functions.

---

### Requirement 9 — In-Presenter Screenshot

**User Story:** As a presenter, I want to capture a bitmap screenshot of the current slide with my annotations visible, so that I can download the exact image my audience saw.

#### Acceptance Criteria

1. WHEN the S key is pressed in Presenter View, THE App SHALL composite the rendered PDF canvas and the annotation canvas into a single offscreen canvas and encode the result as a PNG, storing it in the Screenshot Buffer in memory.
2. WHEN the S key is pressed in Presenter View and a Screenshot Buffer already exists, THE App SHALL replace the previous buffer with the new capture.
3. WHEN the user activates "Download screenshot" on the Landing Page and a Screenshot Buffer exists, THE App SHALL trigger a browser file download of the PNG with a filename in the format `{originalName}-{pageNumber:03d}-PDFhero.png` (e.g., `slides-003-PDFhero.png`), where `{pageNumber}` is the page that was active when the screenshot was captured.
4. WHEN the S key is pressed in Presenter View, THE App SHALL NOT exit Presenter View or disrupt the current slide state in any way.
5. IF canvas-to-PNG encoding fails, THEN THE App SHALL display an error message without crashing or exiting Presenter View.
