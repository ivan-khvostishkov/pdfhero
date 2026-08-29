# Color Management Testing Guide — PDFhero Presenter

## Purpose

This guide describes how a developer can verify whether the browser rendering engine, PDF.js, and the OS color pipeline correctly honour embedded ICC profiles when displaying and screenshotting PDF pages. The goal is to determine whether out-of-gamut colors (e.g., ProPhotoRGB primaries that exceed the sRGB display gamut) are correctly mapped, and whether in-gamut colors are reproduced accurately.

---

## Background

PDF files can embed ICC color profiles in their content streams. A PDF/X-4 file, for example, may contain an image encoded in ProPhotoRGB — a very wide-gamut space whose primaries extend well beyond what any current display can reproduce. When a color-managed pipeline encounters such a PDF:

1. It reads the source ICC profile from the PDF.
2. It converts the pixel values through the rendering intent (e.g., Relative Colorimetric) to the display profile (typically sRGB or Display P3).
3. The result is clamped to the display gamut.

A non-color-managed pipeline simply treats the raw numbers as sRGB values, producing incorrect (typically over-saturated) colors.

The test below is designed to expose the difference between the two behaviors by using known probe colors.

---

## Test PDF Construction

### Required probe colors

Use two ProPhotoRGB values that behave differently under color management:

| Label | ProPhotoRGB (R, G, B) | Expected behavior in sRGB pipeline |
|---|---|---|
| **Extreme red** | (255, 0, 0) | Above sRGB gamut → clips to (255, 0, 0) sRGB after conversion or stays (255,0,0) if unmanaged. *Visually indistinguishable either way.* |
| **Mid red** | (50, 0, 0) | Below sRGB gamut boundary for ProPhotoRGB red → converts to a value **less than** (50, 0, 0) sRGB if managed; stays (50, 0, 0) if unmanaged. *Visually distinguishable.* |

> **Why these two?**
> ProPhotoRGB (255, 0, 0) maps to approximately sRGB (242, 0, 0) after Relative Colorimetric conversion (a small but measurable shift). ProPhotoRGB (50, 0, 0) maps to approximately sRGB (35, 0, 0) — a much more visible difference. If the browser is NOT color-managing, you will read back (50, 0, 0); if it IS color-managing, you will read back approximately (35, 0, 0).

### How to create the test PDF

Use any color-accurate tool that can embed ICC profiles:

1. **Adobe InDesign / Illustrator** — Create a new document with Color Mode set to ProPhotoRGB. Place two solid rectangles:
   - Rectangle A: fill `R=255 G=0 B=0` (ProPhotoRGB)
   - Rectangle B: fill `R=50 G=0 B=0` (ProPhotoRGB)
   - Export to PDF/X-4 with "Embed ICC profiles" enabled. Verify with PDFhero that the metadata panel shows "ProPhotoRGB" in the ICC profiles list.

2. **Python + Pillow + pikepdf** — Programmatic alternative:
   ```python
   from PIL import Image
   import numpy as np, pikepdf, io

   # Create a 200x100 test image: left half (255,0,0), right half (50,0,0)
   img = Image.new("RGB", (200, 100))
   pixels = np.array(img)
   pixels[:, :100] = [255, 0, 0]
   pixels[:, 100:] = [50, 0, 0]
   img = Image.fromarray(pixels, "RGB")

   # Assign ProPhotoRGB profile (requires prophoto.icc on disk)
   with open("prophoto.icc", "rb") as f:
       icc_bytes = f.read()
   img_with_profile = img.copy()
   img_with_profile.info["icc_profile"] = icc_bytes

   buf = io.BytesIO()
   img_with_profile.save(buf, format="TIFF", icc_profile=icc_bytes)
   # Then embed in a PDF with pikepdf preserving the ICC profile
   ```

3. **Reference test file** — A pre-built test file can be found in the `/test-assets/` folder of this repository (if present), named `prophoto-probe.pdf`.

---

## Test Procedure

### Tool 1 — PDFhero built-in screenshot (S key)

This tests how PDF.js renders the page through the browser canvas pipeline.

1. Open `PDFhero.html` and select `prophoto-probe.pdf`.
2. Click "Present as a hero".
3. Press **S** to capture a screenshot.
4. Exit with **Q** and click "Download screenshot".
5. Open the PNG in a pixel inspector (e.g., browser DevTools eyedropper, Photoshop, or `python -c "from PIL import Image; img=Image.open('...'); print(img.getpixel((50,50)))"`)
6. Sample the center of Rectangle B (the `(50,0,0)` ProPhotoRGB patch).

| Result | Interpretation |
|---|---|
| Sampled RGB ≈ **(35, 0, 0)** | PDF.js + browser canvas is **color-managing** the ProPhotoRGB image |
| Sampled RGB ≈ **(50, 0, 0)** | PDF.js + browser canvas is **NOT color-managing** — raw values passed through |

Also sample Rectangle A:

| Result | Interpretation |
|---|---|
| Sampled RGB ≈ **(242, 0, 0)** or **(255, 0, 0)** | Either managed (slight clip) or unmanaged — less diagnostic here |

### Tool 2 — OS / system screenshot

This tests whether the OS display compositor applies any color correction on top of what the browser renders.

1. With `PDFhero.html` open and the test PDF loaded in Presenter View (full screen), take a system screenshot:
   - **Windows**: Win + Shift + S (Snipping Tool), or Print Screen → paste into Paint
   - **macOS**: Cmd + Shift + 4 → drag over the slide area
2. Save as PNG and inspect the same pixel coordinates as above.

If the system screenshot shows different values than the PDFhero built-in screenshot:
- The OS is applying its own color correction (ICC-aware display compositing).
- This is expected on macOS with a wide-gamut display (e.g., Display P3).

### Tool 3 — Browser built-in screenshot

This tests the browser's own capture path, which may differ from both the canvas readback and the OS compositor.

1. In the presenter page (or landing page showing the rendered preview), use the browser's built-in screenshot:
   - **Chrome**: DevTools → three-dot menu → More tools → "Capture screenshot" (or `Ctrl+Shift+P` → "Capture full size screenshot")
   - **Firefox**: DevTools → "Take a screenshot of the entire page"
2. Inspect the same pixel location.

---

## Interpreting Results Across Three Tools

| Tool | Color-managed result (Rectangle B) | Non-managed result |
|---|---|---|
| PDFhero S key screenshot | ~(35, 0, 0) | ~(50, 0, 0) |
| OS screenshot | May differ if OS compositor is ICC-aware | Same as screen pixels |
| Browser DevTools screenshot | Usually matches canvas pixels | Same as canvas readback |

If all three tools give different values, this indicates a pipeline where:
- PDF.js applies one transform
- The browser compositor applies another
- The OS display driver applies a third

This is normal on color-managed systems with Display P3 or wide-gamut monitors.

---

## Key Observations for Developers

1. **PDF.js does not perform ICC profile conversion itself** (as of v4.x). It passes decoded pixel data directly to the browser canvas. The browser's canvas `drawImage` API does NOT apply ICC profiles embedded in the image data.

2. **Implication**: If you need verified color accuracy, you must pre-convert the image data from ProPhotoRGB to sRGB (or the display profile) before drawing to canvas. This is outside the scope of PDFhero v1.01.

3. **What PDFhero's screenshot captures**: The raw canvas pixel values after PDF.js renders them — i.e., the browser's interpretation without any ICC correction applied to the image content. This is the same image your audience sees on screen.

4. **The OS display compositor** may apply a separate color profile transform between the canvas values and the actual photons emitted by the display hardware. This means the screenshot you download from PDFhero (canvas readback) may not match what your eyes see on a color-managed display — the display makes the colors look right visually, but the captured pixels are "pre-correction."

5. **For print-accuracy verification**: The correct workflow is Acrobat + AdobeEngine, not a browser-based renderer. PDFhero is designed for screen presentation only.

---

## Quick Reference — Expected Values

Assuming a standard sRGB display and Relative Colorimetric rendering intent, the approximate expected conversions from ProPhotoRGB to sRGB are:

| ProPhotoRGB | → sRGB (approx.) |
|---|---|
| (255, 0, 0) | (242, 0, 0) — slight clip |
| (50, 0, 0) | (35, 0, 0) — visible darkening |
| (0, 255, 0) | (0, 168, 0) — significant clip |
| (0, 0, 255) | (0, 0, 230) — minor clip |

Values are approximate and depend on the specific ICC profiles and CMM used.
