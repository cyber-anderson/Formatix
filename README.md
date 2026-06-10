# Formatix Image Converter

Formatix is a fast, lightweight batch image converter for Windows. Convert, resize and optimize WEBP, JPEG, PNG, BMP, TIFF, ICO and HEIC images in just a few clicks.

No file limits, no internet connection. Your images never leave your computer.

https://github.com/user-attachments/assets/e02e780b-f78b-439b-9979-90f6eafb6b10

---

## Features

- **Batch conversion** — add hundreds of files at once, convert in one click
- **7 output formats** — WEBP, JPEG, PNG, BMP, TIFF, ICO, HEIC
- **HEIC/HEIF support** — open, convert and export Apple HEIC/HEIF images via pillow-heif
- **5 resize modes:**
  - No change
  - Proportional by width
  - Proportional by height
  - Smart crop (fill exact dimensions, center-cropped)
  - Custom (free width × height, no aspect ratio lock)
- **Сorrect ICO** — automatically generates a full multi-size icon pack (16, 24, 32, 48, 64, 128, 256 px) in a single `*.ico` file
- **Quality control** — adjustable quality slider for JPEG, WEBP and HEIC (disabled automatically for lossless formats)
- **Drag & Drop** support (requires `tkinterdnd2`)
- **Conversion cache** — re-converting with the same settings skips already processed files instantly
- **Atomic file writes** — files are never left in a half-written state
- **Overwrite protection** — warns before replacing existing files, with per-session confirmation
- **File size stats** — shows original vs. converted size after each batch
- **5 interface languages** — English, Русский, Українська, Deutsch, 中文
- **Auto language detection** — picks your system language on first launch (Windows UI language via LCID)
- **Remember settings** — optionally saves format, quality and resize mode between sessions
- **High DPI aware** — crisp rendering on scaled displays

---
## HEIC Support

Formatix Image Converter supports opening and exporting HEIC/HEIF images through the pillow-heif library.

This enables direct conversion between HEIC and other supported formats, including JPEG, PNG, WEBP, BMP, TIFF and ICO.

Color profile processing is applied automatically to improve color accuracy when converting HEIC images containing embedded ICC profiles.

---

## Requirements

* **OS:** Windows (if you are using the pre-compiled `.exe` file)
* **Python:** 3.10+ *(only required if running from source)*
* **Dependencies:** `Pillow`, `pillow-heif`, `tkinterdnd2` *(only required if running from source)*

## Running

### Option 1 — Executable (Windows)
Download the latest `.exe` from [Releases](https://github.com/cyber-anderson/Formatix/releases) and run it directly. No Python required. No installation, no setup — just run.

### Option 2 — From source
To run the script from the source code, you need **Python 3.10+** and the necessary libraries.

1. Install the required dependencies:
```bash
pip install Pillow pillow-heif tkinterdnd2
```
2. Run the application:
```bash
python formatix.py
```

---

## Supported Input Formats

`.jpg` `.jpeg` `.png` `.webp` `.bmp` `.tiff` `.tif` `.gif` `.ico` `.heic` `.heif`

---

## Output Formats

| Format | Type & Quality | Notes |
| :--- | :--- | :--- |
| **WEBP** | Lossy (Adjustable) | Best size-to-quality ratio for web use |
| **JPEG** | Lossy (Adjustable) | Standard format; RGBA transparency auto-converted to RGB |
| **PNG** | Lossless (Fixed) | Ideal for graphics requiring perfect clarity and alpha channel |
| **BMP** | Uncompressed (Fixed) | Raw bitmap files with no compression |
| **TIFF** | Lossless (Fixed) | High-fidelity format used for archival and printing |
| **ICO** | Lossless (Fixed) | Windows icon container (automatically generates sizes up to 256×256) |
| **HEIC** | Lossy (Adjustable) | High Efficiency Image Format (HEIF/HEIC), commonly used by Apple devices |

---

## Settings

Settings are stored in `~/.formatix_image_converter_settings.json`.

You can enable or disable settings persistence in the Settings window — when disabled, the app always starts with default values (the language preference is always remembered regardless).

---
## Roadmap / Future Plans

Here are the features planned for upcoming releases:
- [x] **Correct ICO** — generates a full multi-layered icon pack (16, 24, 32, 48, 64, 128, 256 px) in a single *.ico file.
- [x] **HEIC support** — ability to convert high-efficiency photos from Apple devices into standard web formats (JPEG, PNG, WEBP).
- [ ] **Light Theme support** — a clean, high-contrast alternative to the current dark palette.
- [ ] **File sorting** — ability to sort by name, size, or resolution.
- [ ] **SVG support** — converting vector SVG files into raster formats (PNG, JPEG, WEBP).
- [ ] **Image preview** — quick preview of selected images directly inside the application.
- [ ] **Side-by-side comparison** — a visual tool to compare the original and converted image quality.

---

## ☕ Support the Author

If Formatix saved you time or effort, a small donation is always appreciated.

| Network      | Address |
|--------------|---------|
| Bitcoin      | bc1q8ajkfe5zg26ugwthjlcjqtn06dveh3kehted90 |
| Ethereum     | 0x08bDC7b9d6f400260973B73063Eb81c27A10f1e3 |
| USDT TRC20   | TU2RZTdh8p2fEt2hnKrUTAZNj8trfW6hYE |
| Solana       | 4VAPnL62M7o8SwrYHhE8ZSpHqDM8qvkqCjL4EKaAFj58 |
---

## License

[GPL-3.0](https://github.com/cyber-anderson/Formatix?tab=GPL-3.0-1-ov-file#)
