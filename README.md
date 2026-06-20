

<h1 align="center">
<sub>
<img src="icon.ico" height="38" width="38" alt="Formatix Image Converter logo">
</sub>
Formatix Image Converter


![Version](https://img.shields.io/github/v/release/cyber-anderson/Formatix)
![License](https://img.shields.io/github/license/cyber-anderson/Formatix)
![Platform](https://img.shields.io/badge/platform-Windows-blue)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
</h1>
<p align="center">
  <strong>A fast, lightweight, and 100% offline batch image converter and resizer for Windows.</strong>
</p>

Formatix Image Converter is a powerful desktop application designed to batch convert, resize, and optimize images in just a few clicks. Whether you need to convert Apple's HEIC formats to JPG, turn SVG vector graphics into PNG, or compress heavy images into next-generation AVIF and WEBP formats, this program handles it all instantly.

**No file limits, no internet connection required** — everything happens locally, with zero uploads and a strictly ad-free experience.

<img width="2286" height="797" alt="Light and dark themes, drag and drop, HEIC AVIF WEBP PNG JPEG conversion UI" src="https://github.com/user-attachments/assets/bb39361f-f6fe-47a8-8f32-92bde7073219" />

---

## Why Formatix Image Converter?

**✅ 100% offline** — images never leave your computer  
**✅ No plugins needed** — works out of the box, no extra downloads or setup  
**✅ Free for everyone** — including commercial use, licensed under GPL-3.0  
**✅ Open source** — auditable, no hidden telemetry, no ads, ever  
**✅ Modern UI** — dark and light theme, drag & drop, clean interface  
**✅ Popular Conversions Supported** — HEIC, JPEG, PNG, WEBP, AVIF, SVG, ICO [and other popular image formats](#supported-input-formats)

---

## Key Features

* **Batch Processing** — convert, resize, and optimize hundreds of images in a single operation
* **8 Output Formats** — export to AVIF, WEBP, JPEG, HEIC/HEIF, PNG, BMP, TIFF, and ICO
* **Multi-threaded Conversion** — utilizes your CPU efficiently to convert multiple images simultaneously for lightning-fast batch operations
* **Advanced Image Resizer** — 5 resize modes including proportional scaling, smart crop, and custom dimension adjustments
* **Color Profile Management** — ICC-based color space conversion via Pillow ImageCms guarantees high color accuracy
* **Multi-size ICO Generation** — automatically creates Windows icon packs
* **Adjustable Quality Settings** — fine-tune compression levels for JPEG, WEBP, AVIF, and HEIC
* **Drag & Drop** — instantly add folders or individual files
* **Smart Conversion Cache** — automatically skips files already converted with identical settings to save time
* **Safe Processing** — features atomic file writes (prevents partially written output files) and overwrite protection
* **Built-in Image Comparison** — easily compare the source file with the processed result side-by-side
* **Multilingual UI** — 5 interface languages: English, Русский, Українська, Deutsch, 中文
* **Light & Dark Mode** — switch between themes in Settings

---

## Requirements

* **OS:** Windows (if using the pre-compiled `.exe` standalone app)
* **Python:** 3.10+ *(only required if running from source)*
* **Dependencies:** `Pillow`, `pillow-heif`, `tkinterdnd2`, `resvg-py` *(only required if running from source)*

---

## Installation & Running

### Option 1 — Standalone Executable (Windows)
Download the latest portable `.exe` from [Releases](https://github.com/cyber-anderson/Formatix/releases) and run it directly. No Python required, no installation, and no complex setup — just click and convert.

### Option 2 — Run from Source
To run the script from the source code, you need **Python 3.10+** and the necessary libraries.

1. Install the required dependencies:
```bash
pip install Pillow pillow-heif tkinterdnd2 resvg-py
```
2. Run the application:
```bash
python formatix.py
```

---

## Supported Input Formats

`JPEG (.jpg, .jpeg)` `PNG (.png)` `WEBP (.webp)` `AVIF (.avif)` `HEIC / HEIF (.heic, .heif)` `SVG (.svg)` `BMP (.bmp)` `TIFF (.tiff, .tif)` `GIF (.gif)` `ICO (.ico)`

---

## Output Formats & Specifications

| Format | Compression Type | Notes for Users |
| :--- | :--- | :--- |
| **AVIF** | Lossy (Adjustable) | Next-generation format; offers superior compression with high visual quality. |
| **WEBP** | Lossy (Adjustable) | Best size-to-quality ratio for modern web development. |
| **JPEG** | Lossy (Adjustable) | Standard universal format; RGBA transparency is auto-converted to RGB. |
| **HEIC** | Lossy (Adjustable) | High Efficiency Image Format, commonly used by Apple iOS devices. |
| **PNG** | Lossless (Fixed) | Ideal for graphics requiring perfect clarity and an alpha channel (transparency). |
| **BMP** | Uncompressed (Fixed)| Raw bitmap files with absolutely no compression. |
| **TIFF** | Lossless (Fixed) | High-fidelity format used for professional printing and archival storage. |
| **ICO** | Lossless (Fixed) | Windows icon container (automatically generates sizes up to 256×256 px). |

---

## Settings & Configuration

Settings are stored locally in `~/.formatix_image_converter_settings.json`.

You can enable or disable settings persistence in the Settings window. When disabled, the application always starts with default values (note: the language preference is always remembered regardless of this setting).

---

## ❤️ Support the Project

If this offline batch image converter saved you time or effort, a small donation to support further development is always appreciated!

| Currency | Network | Address |
|----------|---------|---------|
| BTC | Bitcoin | `bc1q8ajkfe5zg26ugwthjlcjqtn06dveh3kehted90` |
| ETH / USDT / BNB | ERC-20 / BEP-20 | `0x08bDC7b9d6f400260973B73063Eb81c27A10f1e3` |
| USDT | TRC-20 | `TU2RZTdh8p2fEt2hnKrUTAZNj8trfW6hYE` |
| SOL | Solana | `4VAPnL62M7o8SwrYHhE8ZSpHqDM8qvkqCjL4EKaAFj58` |
| TON | Toncoin  | `UQBPQAbGEsyCGNEZAXZoUBOcaTYglXl9FAZSu-7gQdxE-k7O` |

---

## License

This project is licensed under the [GPL-3.0 License](https://github.com/cyber-anderson/Formatix?tab=GPL-3.0-1-ov-file#).
