<h1 align="center">
<sub>
<img src="icon.ico" height="38" width="38" alt="Formatix Image Converter">
</sub>
Formatix Image Converter
</h1>

Formatix is a fast, lightweight batch image converter for Windows. Convert, resize and optimize AVIF, WEBP, JPEG, PNG, BMP, TIFF, ICO and HEIF/HEIC images in just a few clicks. It also supports SVG vector files as input, allowing them to be converted into raster formats such as PNG, JPEG, WEBP and more.

No file limits, no internet connection. 100% offline processing means your images are never uploaded, shared, or sent anywhere — everything stays on your computer.

https://github.com/user-attachments/assets/e02e780b-f78b-439b-9979-90f6eafb6b10

---

## Features

- **Batch conversion** — convert hundreds of images in a single operation
- **8 output formats** — AVIF, WEBP, JPEG, HEIC/HEIF, PNG, BMP, TIFF, ICO
- **Multi-threaded processing** — converts multiple images simultaneously for faster batch operations
- **5 resize modes** — proportional scaling, smart crop and custom dimensions
- **Color profile processing** — ICC-based color space conversion via Pillow ImageCms for high color accuracy.
- **Multi-size ICO generation** — automatically creates icon packs up to 256×256 px
- **Adjustable quality settings** — JPEG, WEBP, AVIF and HEIC
- **Drag & Drop support**
- **Conversion cache** — instantly skips files already converted with identical settings
- **Atomic file writes** — prevents partially written output files
- **Overwrite protection**
- **File size statistics**
- **5 interface languages** — English, Русский, Українська, Deutsch, 中文
- **Automatic language detection**
- **Remember settings between sessions**
- **Light/Dark theme supports** — switch between dark and light in Settings.

---

## Requirements

* **OS:** Windows (if you are using the pre-compiled `.exe` file)
* **Python:** 3.10+ *(only required if running from source)*
* **Dependencies:** `Pillow`, `pillow-heif`, `tkinterdnd2`, `resvg-py` *(only required if running from source)*

## Running

### Option 1 — Executable (Windows)
Download the latest `.exe` from [Releases](https://github.com/cyber-anderson/Formatix/releases) and run it directly. No Python required. No installation, no setup — just run.

### Option 2 — From source
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

`.jpg` `.jpeg` `.png` `.webp` `.bmp` `.tiff` `.tif` `.gif` `.ico` `.heic` `.heif` `.svg` `.avif`

---

## Output Formats

| Format | Type & Quality | Notes |
| :--- | :--- | :--- |
| **AVIF** | Lossy (Adjustable) | Next-generation format; offers superior compression with high quality |
| **WEBP** | Lossy (Adjustable) | Best size-to-quality ratio for web use |
| **JPEG** | Lossy (Adjustable) | Standard format; RGBA transparency auto-converted to RGB |
| **HEIC** | Lossy (Adjustable) | High Efficiency Image Format (HEIF/HEIC), commonly used by Apple devices |
| **PNG** | Lossless (Fixed) | Ideal for graphics requiring perfect clarity and alpha channel |
| **BMP** | Uncompressed (Fixed) | Raw bitmap files with no compression |
| **TIFF** | Lossless (Fixed) | High-fidelity format used for archival and printing |
| **ICO** | Lossless (Fixed) | Windows icon container (automatically generates sizes up to 256×256) |


---

## Settings

Settings are stored in `~/.formatix_image_converter_settings.json`.

You can enable or disable settings persistence in the Settings window — when disabled, the app always starts with default values (the language preference is always remembered regardless).

---

## ☕ Support the Author

If Formatix saved you time or effort, a small donation is always appreciated.

| Currency | Network | Address |
|----------|---------|---------|
| BTC | Bitcoin | `bc1q8ajkfe5zg26ugwthjlcjqtn06dveh3kehted90` |
| ETH / USDT / BNB | ERC-20 / BEP-20 | `0x08bDC7b9d6f400260973B73063Eb81c27A10f1e3` |
| USDT | TRC-20 | `TU2RZTdh8p2fEt2hnKrUTAZNj8trfW6hYE` |
| SOL | Solana | `4VAPnL62M7o8SwrYHhE8ZSpHqDM8qvkqCjL4EKaAFj58` |
| TON | Toncoin  | `UQBPQAbGEsyCGNEZAXZoUBOcaTYglXl9FAZSu-7gQdxE-k7O` |

---

## License

[GPL-3.0](https://github.com/cyber-anderson/Formatix?tab=GPL-3.0-1-ov-file#)
