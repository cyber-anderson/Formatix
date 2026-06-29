<h1 align="center">
<sub>
<img src="icon.ico" height="38" width="38" alt="Logo">
</sub>
Formatix Image Converter
  
[![Download](https://img.shields.io/github/v/release/cyber-anderson/Formatix?label=Download&style=flat&color=green&logo=download)](https://github.com/cyber-anderson/Formatix/releases/latest)
[![License](https://img.shields.io/github/license/cyber-anderson/Formatix)](https://github.com/cyber-anderson/Formatix/blob/main/LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows-blue)](https://github.com/cyber-anderson/Formatix#requirements)
[![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/downloads/)

</h1>
<p align="center">
  <strong>A fast, lightweight, and 100% offline batch image converter and resizer for Windows.</strong>
</p>

Formatix Image Converter is a powerful desktop application designed to batch convert, resize, and optimize images in just a few clicks. Whether you need to convert Apple's HEIC formats to JPG, turn SVG vector graphics into PNG, or compress heavy images into next-generation AVIF and WEBP formats, this program handles it all instantly.

**No file limits, no internet connection required** — everything happens locally, with zero uploads and a strictly ad-free experience.

<img width="2286" height="797" alt="Light and dark themes, drag and drop, HEIC AVIF WEBP PNG JPEG conversion UI" src="https://github.com/user-attachments/assets/bb39361f-f6fe-47a8-8f32-92bde7073219" />

---

## Table of Contents

- [Why Formatix Image Converter?](#why-formatix-image-converter)
- [Key Features](#key-features)
- [Requirements](#requirements)
- [Installation & Running](#installation--running)
- [Supported Input Formats](#supported-input-formats)
- [Output Formats & Specifications](#output-formats--specifications)
- [Settings & Configuration](#settings--configuration)
- [FAQ](#faq)
- [Support the Project](#️-support-the-project)
- [License](#license)

---

## Why Formatix Image Converter?

**✅ 100% offline** — images never leave your computer  
**✅ Portable & self-containedd** — no installation, no registry entries, just a single .exe you can run from anywhere  
**✅ No plugins needed** — works out of the box, no extra downloads or setup  
**✅ Free for everyone** — including commercial use, licensed under GPL-3.0  
**✅ Open source** — auditable, no hidden telemetry, no ads, ever  
**✅ Modern UI** — dark and light theme, drag & drop, clean interface  
**✅ Popular Conversions Supported** — [browse all available formats](#supported-input-formats)

---

## Key Features

* **Batch Processing** — convert, resize, and optimize hundreds of images in a single operation
* **8 Output Formats** — export to AVIF, WEBP, JPEG, HEIC/HEIF, PNG, BMP, TIFF, and ICO
* **Multi-threaded Conversion** — converts multiple images simultaneously for fast batch operations
* **Advanced Image Resizer** — 5 resize modes: proportional scaling, smart crop, and custom dimensions
* **Color Profile Management** — ICC-based color space conversion via Pillow ImageCms for high color accuracy
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

| JPEG | PNG | WebP | AVIF | HEIC / HEIF | SVG | BMP | TIFF | GIF | ICO |
|:----:|:---:|:----:|:----:|:-----------:|:---:|:---:|:----:|:---:|:---:|
| `.jpg`<br>`.jpeg` | `.png` | `.webp` | `.avif` | `.heic`<br>`.heif` | `.svg` | `.bmp` | `.tiff`<br>`.tif` | `.gif` | `.ico` |

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

You can enable or disable settings persistence in the Settings window. When disabled, the application always starts with default values (note: the language preference is determined by the system language).

---

## FAQ

**Q: Which format should I choose for maximum compression?**
> Use **AVIF** — it's the most modern format available. It delivers the smallest file sizes while maintaining excellent visual quality. Ideal for web, storage optimization, or sharing. At a quality setting of 85%, the file size is often 4× smaller than the original with no visible difference to the eye.

**Q: Which format is best for web images?**
> **WEBP** is the go-to for general web use — it offers a great balance between file size and quality, and is widely supported by all modern browsers. If your target audience uses up-to-date browsers, **AVIF** is even better.

**Q: Which format should I use if I need transparency (alpha channel)?**
> Use **PNG** (lossless, supports full alpha) or **WEBP** (lossy with alpha support). Avoid **JPEG** and **BMP** — they don't support transparency. JPEG will auto-convert RGBA to RGB.

**Q: Can I convert SVG files?**
> Yes. SVG files are accepted as input and can be converted into raster formats such as PNG, JPEG, WEBP, AVIF, and others.

**Q: Does it upload my images anywhere?**
> No. Everything is processed **fully offline** on your local machine. Your files are never uploaded, shared, or sent anywhere.

**Q: What does the quality slider affect?**
> The quality setting applies to lossy formats: **JPEG**, **WEBP**, **AVIF**, and **HEIC**. Lossless formats (PNG, TIFF, BMP, ICO) ignore this setting and always output at full quality.

**Q: How do I compare the original and converted image?**
> After conversion, click the **Compare** button — it opens a side-by-side view so you can evaluate quality and file size.

---

## ❤️ Support the Project

If Formatix Image Converter saved you time or effort, a small donation to support further development is always appreciated!

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
