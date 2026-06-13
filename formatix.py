# Formatix Image Converter
# Copyright (C) 2026 cyber-anderson
# https://github.com/cyber-anderson/Formatix
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

import tkinter as tk
import locale
from tkinter import ttk, filedialog, messagebox
import threading
import webbrowser
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import sys
import queue
import random
import json
import ctypes
import subprocess
from PIL import Image
from PIL import ImageCms
import io

# Делаем приложение четким на экранах с масштабированием (High DPI)
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

HAS_DND = False
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    HAS_DND = True
except Exception:
    pass

HEIF_AVAILABLE = False
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
    HEIF_AVAILABLE = True
except Exception:
    pass

AVIF_AVAILABLE = False
try:
    # Pillow ≥ 10 поддерживает AVIF нативно если установлен libavif.
    # pillow-avif-plugin расширяет поддержку для старых версий Pillow.
    try:
        import pillow_avif  # noqa: F401 — регистрирует кодек автоматически при импорте
    except ImportError:
        pass
    # Проверяем реальную возможность сохранения: создаём 1×1 AVIF в памяти
    import io as _io
    _test = Image.new("RGB", (1, 1))
    _buf  = _io.BytesIO()
    _test.save(_buf, "AVIF", quality=50)
    AVIF_AVAILABLE = True
    del _test, _buf, _io
except Exception:
    pass

SVG_AVAILABLE = False
try:
    import resvg_py as _resvg_py
    SVG_AVAILABLE = True
except Exception:
    pass

# ── палитра ───────────────────────────────────────────────────────────────────
BG      = "#0f0f1a"
BG2     = "#181825"
BG3     = "#1e1e2e"
CARD    = "#232336"
ACCENT  = "#c678dd"
ACCENT2 = "#ff6b9d"
HEART_RED = "#ff3366"
GREEN   = "#a8ff78"
FG      = "#cdd6f4"
FG2     = "#6c7086"
FG3     = "#45475a"
BORDER  = "#313244"

APP_NAME = "Formatix Image Converter"
VERSION  = "1.11.0"

# Константы анимации сердечка
_HEART_BEAT1_MS   = 120
_HEART_BEAT2_MS   = 250
_HEART_BEAT3_MS   = 370
_HEART_MIN_IDLE   = 1800
_HEART_MAX_IDLE   = 2600

FORMATS = (["AVIF"] if AVIF_AVAILABLE else []) + ["WEBP", "JPEG"] + (["HEIC"] if HEIF_AVAILABLE else []) + ["PNG", "BMP", "TIFF", "ICO"]
IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif", ".gif", ".ico"} | ({".avif"} if AVIF_AVAILABLE else set()) | ({".heic", ".heif"} if HEIF_AVAILABLE else set()) | ({".svg"} if SVG_AVAILABLE else set())

# ── LOCALIZATION ───────────────────────────────────────────────────────────────
LANGUAGES = {"en": "English", "ru": "Русский", "uk": "Українська", "de": "Deutsch", "zh": "中文"}

STRINGS = {
    "en": {
        "add": "+ Add", "clear": "✕ Clear",
        "src_panel": "📂  Source Files", "dst_panel": "✅  Result",
        "save_folder": "SAVE FOLDER", "folder_placeholder": "not selected — will be asked on convert",
        "pick_dir": "📁 Choose", "format_lbl": "FORMAT", "quality_lbl": "QUALITY",
        "resize_lbl": "CHANGING RESOLUTION", "progress_lbl": "PROGRESS",
        "filesize_lbl": "FILE SIZE", "was": "Was:", "became": "Became:",
        "convert_btn": "▶  Convert", "processing_btn": "▶  Processing...",
        "col_filename": "File Name", "col_res": "Resolution", "col_size": "Size", "col_status": "Status",
        "drop_hint": "Drag images here\nor click to browse", "drop_release": "Release files here!",
        "ready": "Ready", "files_count": "Files: {n}",
        "cleared": "List cleared",
        "warn_no_files": "Add files first!",
        "warn_bad_size": "Please enter width and height values.",
        "overwrite_title": "Files exist",
        "overwrite_msg": "The following files already exist in the output folder:\n\n{names}\n\nReplace them?",
        "overwrite_more": "\n... and {n} more",
        "resize_no_change": "No changes",
        "resize_prop_w": "Proportional (by width)",
        "resize_prop_h": "Proportional (by height)",
        "resize_crop": "Smart Crop (Fill)",
        "settings_title": "Settings",
        "settings_lang": "Interface language",
        "settings_close": "Close",
        "donate_title": "Support the author",
        "donate_sub": f"Thanks for using {APP_NAME}!",
        "donate_desc": "If the app saved your time, you can support the\nauthor with crypto:",
        "donate_copied": "Address copied!",
        "donate_close": "Close",
        "donate_btn": "Open page with wallets",
        "auto": "Auto",
        "cache_tag": " (cache)",
        "resize_custom": "Custom",
        "ico_too_large_title": "ICO size limit",
        "ico_too_large_msg": "ICO format does not support resolutions above 256×256.\nThe image will be resized to fit.",
        "ico_too_large_cancel": "Cancel",
        "ico_too_large_ok": "OK",
        "settings_remember": "Remember settings",
        "svg_no_size_title": "SVG: size required",
        "svg_no_size_msg": "SVG files have no fixed resolution.\nPlease set width and height in “Custom” mode before converting.",
    },
    "ru": {
        "add": "+ Добавить", "clear": "✕ Очистить",
        "src_panel": "📂  Исходные файлы", "dst_panel": "✅  Результат",
        "save_folder": "ПАПКА ДЛЯ СОХРАНЕНИЯ", "folder_placeholder": "не выбрана — будет запрошена при конвертации",
        "pick_dir": "📁 Выбрать", "format_lbl": "ФОРМАТ", "quality_lbl": "КАЧЕСТВО",
        "resize_lbl": "ИЗМЕНЕНИЕ РАЗРЕШЕНИЯ", "progress_lbl": "ПРОГРЕСС",
        "filesize_lbl": "РАЗМЕР ФАЙЛОВ", "was": "Было: ", "became": "Стало:",
        "convert_btn": "▶  Конвертировать", "processing_btn": "▶  Обработка...",
        "col_filename": "Имя файла", "col_res": "Разрешение", "col_size": "Размер", "col_status": "Статус",
        "drop_hint": "Переместите изображения сюда\nили нажмите для обзора", "drop_release": "Отпустите файлы здесь!",
        "ready": "Готов к работе", "files_count": "Файлов: {n}",
        "cleared": "Список очищен",
        "warn_no_files": "Сначала добавьте файлы!",
        "warn_bad_size": "Пожалуйста, введите значения для ширины и высоты.",
        "overwrite_title": "Файлы существуют",
        "overwrite_msg": "Следующие файлы уже существуют в папке назначения:\n\n{names}\n\nЗаменить их?",
        "overwrite_more": "\n... и ещё {n} файл(ов)",
        "resize_no_change": "Без изменений",
        "resize_prop_w": "Пропорционально (по ширине)",
        "resize_prop_h": "Пропорционально (по высоте)",
        "resize_crop": "Умная обрезка (Заполнение)",
        "settings_title": "Настройки",
        "settings_lang": "Язык интерфейса",
        "settings_close": "Закрыть",
        "donate_title": "Поддержать автора",
        "donate_sub": f"Спасибо за использование {APP_NAME}!",
        "donate_desc": "Если программа сэкономила ваше время, вы можете\nподдержать автора криптой:",
        "donate_copied": "Адрес успешно скопирован!",
        "donate_close": "Закрыть",
        "donate_btn": "Открыть страницу с кошельками",
        "auto": "Авто",
        "cache_tag": " (кэш)",
        "resize_custom": "Пользовательский",
        "ico_too_large_title": "Ограничение ICO",
        "ico_too_large_msg": "Формат ICO не поддерживает разрешения больше 256×256.\nИзображение будет изменено по размеру.",
        "ico_too_large_cancel": "Отмена",
        "ico_too_large_ok": "ОК",
        "settings_remember": "Запоминать настройки",
        "svg_no_size_title": "SVG: требуется размер",
        "svg_no_size_msg": "SVG-файлы не имеют фиксированного разрешения.\nПожалуйста, задайте ширину и высоту в режиме «Пользовательский» перед конвертацией.",
    },
    "uk": {
        "add": "+ Додати", "clear": "✕ Очистити",
        "src_panel": "📂  Вихідні файли", "dst_panel": "✅  Результат",
        "save_folder": "ПАПКА ДЛЯ ЗБЕРЕЖЕННЯ", "folder_placeholder": "не обрана — буде запитана при конвертації",
        "pick_dir": "📁 Обрати", "format_lbl": "ФОРМАТ", "quality_lbl": "ЯКІСТЬ",
        "resize_lbl": "ЗМІНА РОЗДІЛЬНОСТІ", "progress_lbl": "ПРОГРЕС",
        "filesize_lbl": "РОЗМІР ФАЙЛІВ", "was": "Було: ", "became": "Стало:",
        "convert_btn": "▶  Конвертувати", "processing_btn": "▶  Обробка...",
        "col_filename": "Ім'я файлу", "col_res": "Роздільність", "col_size": "Розмір", "col_status": "Статус",
        "drop_hint": "Перетягніть зображення сюди\nабо натисніть для огляду", "drop_release": "Відпусти файли тут!",
        "ready": "Готовий до роботи",
        "files_count": "Файлів: {n}",
        "cleared": "Список очищено",
        "warn_no_files": "Спочатку додайте файли!",
        "warn_bad_size": "Будь ласка, введіть значення для ширини та висоти.",
        "overwrite_title": "Файли існують",
        "overwrite_msg": "Наступні файли вже існують у папці призначення:\n\n{names}\n\nЗамінити їх?",
        "overwrite_more": "\n... і ще {n} файл(ів)",
        "resize_no_change": "Без змін",
        "resize_prop_w": "Пропорційно (по ширині)",
        "resize_prop_h": "Пропорційно (по висоті)",
        "resize_crop": "Розумне кадрування (Заповнення)",
        "settings_title": "Налаштування",
        "settings_lang": "Мова інтерфейсу",
        "settings_close": "Закрити",
        "donate_title": "Підтримати автора",
        "donate_sub": f"Дякую за використання {APP_NAME}!",
        "donate_desc": "Якщо програма заощадила ваш час, ви можете\nпідтримати автора криптою:",
        "donate_copied": "Адресу скопійовано!",
        "donate_close": "Закрити",
        "donate_btn": "Відкрити сторінку з гаманцями",
        "auto": "Авто",
        "cache_tag": " (кеш)",
        "resize_custom": "Користувацький",
        "ico_too_large_title": "Обмеження ICO",
        "ico_too_large_msg": "Формат ICO не підтримує роздільності більше 256×256.\nЗображення буде змінено за розміром.",
        "ico_too_large_cancel": "Скасувати",
        "ico_too_large_ok": "ОК",
        "settings_remember": "Запам'ятовувати налаштування",
        "svg_no_size_title": "SVG: потрібен розмір",
        "svg_no_size_msg": "SVG-файли не мають фіксованої роздільності.\nБудь ласка, задайте ширину і висоту в режимі «Користувацький» перед конвертацією.",
    },
    "de": {
        "add": "+ Hinzufügen", "clear": "✕ Leeren",
        "src_panel": "📂  Quelldateien", "dst_panel": "✅  Ergebnis",
        "save_folder": "SPEICHERORDNER", "folder_placeholder": "nicht ausgewählt — wird beim Konvertieren abgefragt",
        "pick_dir": "📁 Wählen", "format_lbl": "FORMAT", "quality_lbl": "QUALITÄT",
        "resize_lbl": "AUFLÖSUNGSÄNDERUNG", "progress_lbl": "FORTSCHRITT",
        "filesize_lbl": "DATEIGRÖSSE", "was": "War:  ", "became": "Jetzt:",
        "convert_btn": "▶  Konvertieren", "processing_btn": "▶  Verarbeitung...",
        "col_filename": "Dateiname", "col_res": "Auflösung", "col_size": "Größe", "col_status": "Status",
        "drop_hint": "Ziehen Sie Bilder hierher\noder klicken Sie zum Durchsuchen", "drop_release": "Lassen Sie die Dateien hier los!",
        "ready": "Bereit", "files_count": "Dateien: {n}",
        "cleared": "Liste geleert",
        "warn_no_files": "Zuerst Dateien hinzufügen!",
        "warn_bad_size": "Bitte Werte für Breite und Höhe eingeben.",
        "overwrite_title": "Dateien vorhanden",
        "overwrite_msg": "Folgende Dateien existieren bereits im Zielordner:\n\n{names}\n\nErsetzen?",
        "overwrite_more": "\n... und {n} weitere",
        "resize_no_change": "Keine Änderung",
        "resize_prop_w": "Proportional (nach Breite)",
        "resize_prop_h": "Proportional (nach Höhe)",
        "resize_crop": "Intelligenter Zuschnitt (Füllen)",
        "settings_title": "Einstellungen",
        "settings_lang": "Oberflächensprache",
        "settings_close": "Schließen",
        "donate_title": "Autor unterstützen",
        "donate_sub": f"Danke für die Nutzung von {APP_NAME}!",
        "donate_desc": "Wenn die App Ihre Zeit gespart hat, können Sie den\nAutor mit Krypto unterstützen:",
        "donate_copied": "Adresse kopiert!",
        "donate_close": "Schließen",
        "donate_btn": "Seite mit Wallets öffnen",
        "auto": "Auto",
        "cache_tag": " (Cache)",
        "resize_custom": "Benutzerdefiniert",
        "ico_too_large_title": "ICO-Größenbeschränkung",
        "ico_too_large_msg": "Das ICO-Format unterstützt keine Auflösungen über 256×256.\nDas Bild wird entsprechend skaliert.",
        "ico_too_large_cancel": "Abbrechen",
        "ico_too_large_ok": "OK",
        "settings_remember": "Einstellungen speichern",
        "svg_no_size_title": "SVG: Größe erforderlich",
        "svg_no_size_msg": "SVG-Dateien haben keine feste Auflösung.\nBitte geben Sie Breite und Höhe im Modus „Benutzerdefiniert“ vor der Konvertierung ein.",
    },
    "zh": {
        "add": "+ 添加", "clear": "✕ 清空",
        "src_panel": "📂  源文件", "dst_panel": "✅  结果",
        "save_folder": "保存文件夹", "folder_placeholder": "未选择 — 转换时将询问",
        "pick_dir": "📁 选择", "format_lbl": "格式", "quality_lbl": "质量",
        "resize_lbl": "更改分辨率", "progress_lbl": "进度",
        "filesize_lbl": "文件大小", "was": "之前:", "became": "之后:",
        "convert_btn": "▶  转换", "processing_btn": "▶  处理中...",
        "col_filename": "文件名", "col_res": "分辨率", "col_size": "大小", "col_status": "状态",
        "drop_hint": "请拖拽图片到这里\n或点击浏览", "drop_release": "请在此释放文件！",
        "ready": "准备就绪", "files_count": "文件数: {n}",
        "cleared": "列表已清空",
        "warn_no_files": "请先添加文件！",
        "warn_bad_size": "请输入宽度和高度的值。",
        "overwrite_title": "文件已存在",
        "overwrite_msg": "以下文件在目标文件夹中已存在：\n\n{names}\n\n替换它们？",
        "overwrite_more": "\n... 还有 {n} 个",
        "resize_no_change": "不更改",
        "resize_prop_w": "等比例（按宽度）",
        "resize_prop_h": "等比例（按高度）",
        "resize_crop": "智能裁剪（填充）",
        "settings_title": "设置",
        "settings_lang": "界面语言",
        "settings_close": "关闭",
        "donate_title": "支持作者",
        "donate_sub": f"感谢使用 {APP_NAME}！",
        "donate_desc": "如果本应用节省了您的时间，您可以\n用加密货币支持作者:",
        "donate_copied": "地址已复制！",
        "donate_close": "关闭",
        "donate_btn": "打开钱包页面",
        "auto": "自动",
        "cache_tag": " (缓存)",
        "resize_custom": "自定义",
        "ico_too_large_title": "ICO 尺寸限制",
        "ico_too_large_msg": "ICO 格式不支持超过 256×256 的分辨率。\n图像将被调整大小。",
        "ico_too_large_cancel": "取消",
        "ico_too_large_ok": "确定",
        "settings_remember": "记住设置",
        "svg_no_size_title": "SVG：需要指定尺寸",
        "svg_no_size_msg": "SVG 文件没有固定分辨率。\n请在「自定义」模式下设置宽度和高度后再进行转换。",
    },
}

SETTINGS_FILE = os.path.join(os.path.expanduser("~"), ".formatix_image_converter_settings.json")


def load_settings():
    """Загружает настройки из JSON-файла в домашней директории."""
    try:
        with open(SETTINGS_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_settings(data):
    """Сохраняет настройки в JSON-файл."""
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def format_size(size_bytes):
    """Возвращает человекочитаемый размер файла (KB / MB)."""
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.2f} MB"


def get_file_size_str(path):
    """Возвращает размер файла на диске в виде строки."""
    try:
        return format_size(os.path.getsize(path))
    except Exception:
        return "?? KB"


def get_svg_resolution_pure(path):
    """Быстро и безопасно находит размеры SVG через регулярные выражения."""
    import re
    try:
        # Читаем только самое начало файла (этого хватит для тега <svg>)
        with open(path, "rb") as f:
            raw_bytes = f.read(8192)
        
        text = raw_bytes.decode("utf-8", errors="ignore").strip()
        
        # 1. Ищем тег <svg ...> целиком
        svg_tag_match = re.search(r"<svg([^>]+)>", text, re.IGNORECASE)
        if not svg_tag_match:
            return None, None
            
        svg_body = svg_tag_match.group(1)
        
        # 2. Пробуем вытащить явные width и height
        w_match = re.search(r'width=["\']\s*([\d.]+)(?:px|pt|em|cm|mm)?\s*["\']', svg_body)
        h_match = re.search(r'height=["\']\s*([\d.]+)(?:px|pt|em|cm|mm)?\s*["\']', svg_body)
        
        if w_match and h_match:
            return int(float(w_match.group(1))), int(float(h_match.group(1)))
            
        # 3. Если их нет, ищем viewBox="x y width height"
        vb_match = re.search(r'viewBox=["\']\s*(-?[\d.]+)\s+(-?[\d.]+)\s+([\d.]+)\s+([\d.]+)\s*["\']', svg_body)
        if vb_match:
            return int(float(vb_match.group(3))), int(float(vb_match.group(4)))
            
    except Exception as e:
        print(f"Formatix SVG parse error: {e}")
        
    return None, None


def get_image_res_str(path):
    """Возвращает разрешение изображения в виде строки 'WxH'."""
    ext = os.path.splitext(path)[1].lower()
    
    if ext == ".svg":
        w, h = get_svg_resolution_pure(path)
        if w and h:
            return f"{w}x{h}"
        return "SVG"  # Запасной вариант, если размеров внутри вообще нет
        
    try:
        with Image.open(path) as img:
            w, h = img.size
            return f"{w}x{h}"
    except Exception:
        return "??x??"

def resource_path(relative_path):
    """Получает абсолютный путь к ресурсам, работает для разработки и для PyInstaller."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def open_path(path):
    """Открывает файл или папку в файловом менеджере. Кроссплатформенно."""
    try:
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception:
        pass


def detect_system_lang():
    """Определяет язык интерфейса системы.

    Порядок проверки:
    1. Windows UI language через GetUserDefaultUILanguage (самый надёжный на Windows)
    2. Реестр Windows — текущий пользователь
    3. Unix-переменные окружения LANG / LANGUAGE / LC_ALL / LC_MESSAGES
    4. locale.getlocale() как последний запасной вариант
    """
    # Таблица: LCID / BCP-47 префикс → код приложения
    _LANG_MAP = {
        "ru": "ru", "uk": "uk", "de": "de",
        "zh": "zh", "be": "ru",
    }

    # ── 1. Windows: GetUserDefaultUILanguage ─────────────────────────────────
    if sys.platform == "win32":
        try:
            lcid = ctypes.windll.kernel32.GetUserDefaultUILanguage()
            # LCID: младший байт — основной язык, старший — диалект
            primary = lcid & 0x3FF
            # https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-lcid
            _LCID_PRIMARY = {
                0x19: "ru",  # Russian
                0x22: "uk",  # Ukrainian
                0x23: "be",  # Belarusian
                0x07: "de",  # German
                0x04: "zh",  # Chinese
            }
            if primary in _LCID_PRIMARY:
                return _LANG_MAP.get(_LCID_PRIMARY[primary], "en")
        except Exception:
            pass

        # ── 2. Windows: реестр ────────────────────────────────────────────────
        try:
            import winreg
            with winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Control Panel\International") as key:
                locale_val, _ = winreg.QueryValueEx(key, "LocaleName")
            # LocaleName вида "ru-RU", "uk-UA", "de-DE", "zh-CN"
            prefix = locale_val.lower().split("-")[0]
            if prefix in _LANG_MAP:
                return _LANG_MAP[prefix]
        except Exception:
            pass

    # ── 3. Unix: переменные окружения ─────────────────────────────────────────
    for env_var in ("LANG", "LANGUAGE", "LC_ALL", "LC_MESSAGES"):
        val = os.environ.get(env_var, "")
        if val:
            prefix = val.lower().split(".")[0].split("_")[0]
            if prefix in _LANG_MAP:
                return _LANG_MAP[prefix]
            if val.lower().startswith("zh"):
                return "zh"

    # ── 4. locale.getlocale() ─────────────────────────────────────────────────
    try:
        val = locale.getlocale()[0] or ""
        prefix = val.lower().split("_")[0]
        if prefix in _LANG_MAP:
            return _LANG_MAP[prefix]
    except Exception:
        pass

    return "en"


# ── КАСТОМНЫЙ СКРОЛЛБАР С АВТОСКРЫТИЕМ (ВЕРТИКАЛЬНЫЙ) ──────────────────────────
class CustomScrollbar(tk.Canvas):
    """Тонкий скроллбар, который автоматически скрывается, когда весь контент помещается."""

    def __init__(self, parent, target_treeview, **kwargs):
        super().__init__(parent, bg=CARD, bd=0, highlightthickness=0,
                         width=6, cursor="hand2", **kwargs)
        self.target = target_treeview
        self.thumb = self.create_rectangle(0, 0, 6, 0, fill=FG3, outline="")

        self.target.config(yscrollcommand=self.set_scroll)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<Button-1>", self._on_drag)
        self.bind("<Enter>", lambda e: self.itemconfig(self.thumb, fill=ACCENT))
        self.bind("<Leave>", lambda e: self.itemconfig(self.thumb, fill=FG3))
        self.is_gridded = False

    def set_scroll(self, first, last):
        """Обновляет положение бегунка и показывает/скрывает скроллбар."""
        first, last = float(first), float(last)
        if first <= 0.0 and last >= 1.0:
            if self.is_gridded:
                self.grid_forget()
                self.is_gridded = False
        else:
            if not self.is_gridded:
                self.grid(row=0, column=1, sticky="ns", padx=(2, 4), pady=6)
                self.is_gridded = True
                self.update_idletasks()

        h = self.winfo_height()
        if h > 1:
            y1 = int(first * h)
            y2 = int(last * h)
            self.coords(self.thumb, 0, y1, 6, y2)

    def _on_drag(self, event):
        """Прокручивает список при перетаскивании бегунка."""
        h = self.winfo_height()
        if h > 0:
            pos = event.y / h
            self.target.yview_moveto(pos)


# ── СЛАЙДЕР КАЧЕСТВА ──────────────────────────────────────────────────────────
class FancySlider(tk.Frame):
    """Ползунок качества с числовым полем ввода."""

    def __init__(self, parent, from_=10, to=100, variable=None, width=180, **kw):
        kw.pop("bg", None)
        kw.pop("height", None)
        super().__init__(parent, bg=BG2)
        self._var   = variable or tk.IntVar(value=85)
        self.from_  = from_
        self.to     = to

        # Стиль конфигурируется один раз снаружи (_style_ttk в App)
        self.scale = ttk.Scale(self, from_=from_, to=to, orient="horizontal",
                               variable=self._var, style="FS.Horizontal.TScale",
                               length=width - 50, command=self._on_scale_move)
        self.scale.pack(side="left", padx=(0, 6))

        # При клике на сам слайдер принудительно забираем фокус у поля ввода, 
        # чтобы разблокировать обновление текста во время перетаскивания.
        self.scale.bind("<Button-1>", lambda e: self.scale.focus_set())

        self.entry_var = tk.StringVar(value=str(self._var.get()))
        self.entry = tk.Entry(self, textvariable=self.entry_var,
                              font=("Segoe UI", 10, "bold"),
                              bg=ACCENT, fg="#fff", width=4,
                              bd=0, justify="center", insertbackground="#fff")
        self.entry.pack(side="left", ipady=1)

        self.entry_var.trace_add("write", self._on_entry_write)
        self._var.trace_add("write", self._on_var_update)

    def _on_scale_move(self, v):
        rounded = round(float(v))
        if self._var.get() != rounded:
            self._var.set(rounded)

    def _on_var_update(self, *args):
        # Обновляем поле ввода только если пользователь прямо сейчас не вводит в него текст
        if self.focus_get() != self.entry:
            self.entry_var.set(str(self._var.get()))
        # Если фокус в поле, обновляем ползунок (чтобы клавиатура работала)
    def _on_entry_write(self, *args):
        if self.focus_get() != self.entry:
            return
        val_str = self.entry_var.get()
        if not val_str.isdigit():
            if val_str == "":
                self._var.set(self.from_)
            return
        val = int(val_str)
        # Ограничиваем диапазон и корректируем поле если вышло за границы
        if val > self.to:
            # Откладываем обновление entry_var через after чтобы избежать
            # рекурсии внутри trace_add("write")
            self._var.set(self.to)
            self.entry.after(0, lambda: self.entry_var.set(str(self.to)))
            return
        if val < self.from_ and len(val_str) >= len(str(self.from_)):
            # Корректируем только если введено достаточно цифр (не в процессе набора)
            self._var.set(self.from_)
            self.entry.after(0, lambda: self.entry_var.set(str(self.from_)))
            return
        self._var.set(val)

    def set_enabled(self, enabled: bool):
        """Включает или отключает слайдер визуально."""
        if enabled:
            self.scale.config(state="normal")
            self.entry.config(state="normal", bg=ACCENT, fg="#fff",
                              font=("Segoe UI", 10, "bold"))
            self.entry_var.set(str(self._var.get()))
        else:
            self.scale.config(state="disabled")
            self.entry.config(state="disabled", bg=BG3, fg=FG3,
                              font=("Consolas", 10, "bold"))
            self.entry_var.set("—")


# ── ГЛАВНОЕ ОКНО ──────────────────────────────────────────────────────────────
BaseClass = TkinterDnD.Tk if HAS_DND else tk.Tk


class App(BaseClass):
    """Главное окно приложения Formatix."""

    def __init__(self):
        super().__init__()

        # Мьютекс для защиты совместно используемых данных между потоками
        self._data_lock = threading.Lock()

        self._settings = load_settings()
        if "lang" in self._settings:
            self._lang = self._settings["lang"]
        else:
            self._lang = detect_system_lang()
        # Флаг "запоминать настройки" — хранится всегда, независимо от самого флага
        self._remember_settings = tk.BooleanVar(
            value=self._settings.get("remember_settings", True))

        self.title(APP_NAME)
        self.geometry("1150x720")
        self.minsize(1150, 640)
        self.configure(bg=BG)

        try:
            ico_path = resource_path("icon.ico")
            from PIL import ImageTk
            with Image.open(ico_path) as ico:
                icons = []
                for size in (16, 24, 32, 48, 64, 128, 256):
                    try:
                        frame = ico.copy()
                        frame.thumbnail((size, size), Image.Resampling.LANCZOS)
                        icons.append(ImageTk.PhotoImage(frame))
                    except Exception:
                        pass
                if icons:
                    self.iconphoto(True, *icons)
                    self._icon_refs = icons  # защита от сборщика мусора
        except Exception as e:
            print("Ошибка загрузки иконки главного окна:", e)

        self._files           = []
        self._results         = []
        self._out_dir         = tk.StringVar(value="")
        self._running         = False
        self._converted_cache = {}
        self._total_src_bytes = 0
        self._total_dst_bytes = 0
        self._gui_queue       = queue.Queue()

        self._loading = True  # блокирует _save_settings во время инициализации
        self._style_ttk()
        self._build()
        self._bind_sort_commands()

        remember = self._settings.get("remember_settings", True)
        if remember:
            saved_fmt  = self._settings.get("fmt", "WEBP")
            saved_qual = self._settings.get("quality", 85)
            if saved_fmt in FORMATS:
                self._fmt.set(saved_fmt)
            self._qual.set(saved_qual)
            # Восстанавливаем режим изменения разрешения
            saved_resize_key = self._settings.get("resize_mode_key", "no_change")
            saved_resize_loc = self._key_to_localized_mode(saved_resize_key)
            if saved_resize_loc in self._resize_modes_localized():
                self._resize_mode.set(saved_resize_loc)
                self._on_resize_mode_changed()

        self._loading = False  # восстановление завершено, теперь сохранять можно

        # Применяем состояние слайдера для любого восстановленного формата
        self.after(10, self._on_format_changed)

        self._status.set(self.t("ready"))
        self._listen_queue()
        self._heart_hovered = False
        self._animate_heart_pulse()

        if HAS_DND:
            self._reg_dnd_root()

    # ── локализация ───────────────────────────────────────────────────────────

    def t(self, key):
        """Возвращает локализованную строку по ключу."""
        return STRINGS.get(self._lang, STRINGS["en"]).get(key, STRINGS["en"].get(key, key))

    def _resize_modes_localized(self):
        """Возвращает список режимов изменения размера на текущем языке."""
        s = STRINGS.get(self._lang, STRINGS["en"])
        return [s["resize_no_change"], s["resize_prop_w"], s["resize_prop_h"],
                s["resize_crop"], s["resize_custom"]]

    def _current_resize_mode_key(self):
        """Возвращает ключ текущего режима (независимый от языка)."""
        mode = self._resize_mode.get()
        for lang_code in STRINGS:
            s = STRINGS[lang_code]
            mapping = [
                ("no_change",   s.get("resize_no_change", "")),
                ("prop_width",  s.get("resize_prop_w", "")),
                ("prop_height", s.get("resize_prop_h", "")),
                ("smart_crop",  s.get("resize_crop", "")),
                ("custom",      s.get("resize_custom", "")),
            ]
            for key, loc in mapping:
                if mode == loc:
                    return key
        return "no_change"

    def _key_to_localized_mode(self, key):
        """Переводит ключ режима в локализованную строку."""
        key_map = {
            "no_change":   "resize_no_change",
            "prop_width":  "resize_prop_w",
            "prop_height": "resize_prop_h",
            "smart_crop":  "resize_crop",
            "custom":      "resize_custom",
        }
        str_key = key_map.get(key, "resize_no_change")
        return self.t(str_key)

    def _save_settings(self):
        """Обновляет self._settings и пишет на диск.

        Во время загрузки (_loading=True) ничего не делает — иначе trace-колбэки
        от set() перезатрут только что восстановленные значения.
        lang и remember_settings сохраняются всегда.
        fmt/quality/resize_mode_key обновляются в памяти всегда (чтобы при
        включении галочки сразу записались актуальные значения), но в файл
        попадают только когда remember включён.
        """
        if getattr(self, "_loading", True):
            return
        # Всегда актуализируем в памяти — независимо от галочки
        try:
            self._settings["fmt"]             = self._fmt.get()
        except AttributeError:
            pass
        try:
            self._settings["quality"]         = self._qual.get()
        except AttributeError:
            pass
        try:
            self._settings["resize_mode_key"] = self._current_resize_mode_key()
        except AttributeError:
            pass

        self._settings["lang"]              = self._lang
        self._settings["remember_settings"] = self._remember_settings.get()

        # На диск пишем всегда — но если remember выключен,
        # очищаем fmt/quality/resize из того что запишем, чтобы при следующем
        # запуске они не подхватились
        to_write = dict(self._settings)
        if not self._remember_settings.get():
            to_write.pop("fmt", None)
            to_write.pop("quality", None)
            to_write.pop("resize_mode_key", None)
        save_settings(to_write)

    # ── стили ─────────────────────────────────────────────────────────────────

    def _style_ttk(self):
        """Настраивает стили ttk для тёмной темы."""
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure("TCombobox",
                    fieldbackground=CARD, background=CARD,
                    foreground=FG, arrowcolor=ACCENT,
                    selectbackground=BG3, selectforeground=FG,
                    bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER)
        s.map("TCombobox", fieldbackground=[("readonly", CARD)],
              foreground=[("readonly", FG)])
        s.configure("P.Horizontal.TProgressbar",
                    troughcolor=BG3, background=ACCENT,
                    bordercolor=BG2, lightcolor=ACCENT, darkcolor=ACCENT)
        # Стиль слайдера — конфигурируем один раз здесь
        s.configure("FS.Horizontal.TScale", troughcolor=BG3,
                    background=BG2, sliderlength=26, sliderrelief="flat")
        s.map("FS.Horizontal.TScale",
              background=[("active", ACCENT2), ("", ACCENT)])
        s.configure("Treeview",
                    background=CARD, fieldbackground=CARD, foreground=FG,
                    rowheight=24, bd=0, borderwidth=0, relief="flat",
                    highlightthickness=0, font=("Segoe UI", 10))
        s.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
        s.configure("Treeview.Heading",
                    background=BG3, foreground=FG, bordercolor=BORDER,
                    font=("Segoe UI", 10, "bold"), relief="flat")
        s.map("Treeview.Heading", background=[("active", BG2)], foreground=[("active", ACCENT)])
        s.map("Treeview", background=[("selected", ACCENT)], foreground=[("selected", "#fff")])

    # ── построение интерфейса ─────────────────────────────────────────────────

    def _reg_dnd_root(self):
        """Регистрирует корневое окно как цель для drag-and-drop."""
        self.drop_target_register(DND_FILES)
        self.dnd_bind("<<Drop>>", self._drop)

    def _build(self):
        """Строит весь интерфейс главного окна."""
        hdr = tk.Frame(self, bg=BG2, height=56)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        lf = tk.Frame(hdr, bg=BG2)
        lf.pack(side="left", padx=20, fill="y")
        tk.Label(lf, text="⬡", font=("Segoe UI", 20), bg=BG2, fg=ACCENT).pack(side="left", anchor="center")
        tk.Label(lf, text=f" {APP_NAME}", font=("Segoe UI", 14, "bold"), bg=BG2, fg=FG).pack(side="left", anchor="center")
        _ver_lbl = tk.Label(lf, text=f"  v{VERSION}", font=("Segoe UI", 10),
                             bg=BG2, fg=FG2, cursor="hand2")
        _ver_lbl.pack(side="left", anchor="center")
        _ver_lbl.bind("<Button-1>", lambda e: webbrowser.open(
            "https://github.com/cyber-anderson/Formatix/releases"))
        _ver_lbl.bind("<Enter>", lambda e: _ver_lbl.config(fg=FG))
        _ver_lbl.bind("<Leave>", lambda e: _ver_lbl.config(fg=FG2))

        self._heart_container = tk.Frame(hdr, bg=BG2, width=45, height=56)
        self._heart_container.pack(side="right", padx=(0, 20))
        self._heart_container.pack_propagate(False)

        self._hbtn = tk.Label(self._heart_container, text="♥", font=("Segoe UI", 16),
                              bg=BG2, fg=FG3, cursor="hand2")
        self._hbtn.place(relx=0.5, rely=0.5, anchor="center")
        self._hbtn.bind("<Enter>",    lambda e: self._on_heart_hover(True))
        self._hbtn.bind("<Leave>",    lambda e: self._on_heart_hover(False))
        self._hbtn.bind("<Button-1>", lambda e: self._donate())

        self._settings_btn = tk.Label(hdr, text=self.t("settings_title"),
                                      font=("Segoe UI", 10, "bold"), bg=BG2, fg=FG2, cursor="hand2")
        self._settings_btn.pack(side="right", padx=(0, 8), anchor="center")
        self._settings_btn.bind("<Button-1>", lambda e: self._open_settings())
        self._settings_btn.bind("<Enter>", lambda e: self._settings_btn.config(fg=ACCENT))
        self._settings_btn.bind("<Leave>", lambda e: self._settings_btn.config(fg=FG2))

        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")

        main = tk.Frame(self, bg=BG)
        main.pack(fill="both", expand=True, padx=16, pady=12)

        br = tk.Frame(main, bg=BG)
        br.pack(fill="x", pady=(0, 8))

        self._add_btn   = self._btn(br, self.t("add"), self._add, accent=True)
        self._add_btn.pack(side="left", padx=(0, 6))
        self._clear_btn = self._btn(br, self.t("clear"), self._clear)
        self._clear_btn.pack(side="left")

        self._clbl = tk.Label(br, text="", font=("Segoe UI", 10), bg=BG, fg=FG2)
        self._clbl.pack(side="left", padx=10)

        paned = tk.Frame(main, bg=BG)
        paned.pack(fill="both", expand=True)
        paned.columnconfigure(0, weight=1)
        paned.columnconfigure(1, weight=1)
        paned.rowconfigure(0, weight=1)

        self._lb_src_card, self._tv_src, self._src_panel_lbl = self._make_tree(
            paned, self.t("src_panel"), 0, is_result=False)
        self._tv_src.bind("<Double-Button-1>", lambda e: self._open_item(self._tv_src, self._files)
                          if self._tv_src.identify_region(e.x, e.y) != "heading" else None)

        # DnD-виджеты создаются только при наличии библиотеки
        self._dz_hint = self._dz_ico = self._dz_lbl = None
        if HAS_DND:
            for w in (self._lb_src_card, self._tv_src):
                w.drop_target_register(DND_FILES)
                w.dnd_bind("<<DragEnter>>", lambda e: self._dz_hover(True))
                w.dnd_bind("<<DragLeave>>", lambda e: self._dz_hover(False))
                w.dnd_bind("<<Drop>>", self._drop)

            self._dz_hint = tk.Frame(self._tv_src._inner_frame, bg=CARD, cursor="hand2")
            self._dz_hint.place(relx=0.5, rely=0.45, anchor="center")

            self._dz_ico = tk.Label(self._dz_hint, text="⬇", font=("Segoe UI", 22),
                                    bg=CARD, fg=FG3, cursor="hand2")
            self._dz_ico.pack()
            self._dz_lbl = tk.Label(self._dz_hint, text=self.t("drop_hint"),
                                    font=("Segoe UI", 10), bg=CARD, fg=FG2,
                                    justify="center", cursor="hand2")
            self._dz_lbl.pack(pady=(4, 0))

            for w in (self._dz_hint, self._dz_ico, self._dz_lbl):
                w.bind("<Button-1>", lambda e: self._add() if not self._files else None)
            # Для самого дерева — открываем проводник только если клик НЕ по заголовку
            def _src_click_dnd(e, t=self._tv_src):
                if t.identify_region(e.x, e.y) != "heading" and not self._files:
                    self._add()
            self._tv_src.bind("<Button-1>", _src_click_dnd)
        else:
            # Без DnD привязываем клик напрямую к дереву
            def _src_click_nodnd(e, t=self._tv_src):
                if t.identify_region(e.x, e.y) != "heading" and not self._files:
                    self._add()
            self._tv_src.bind("<Button-1>", _src_click_nodnd)

        self._lb_dst_card, self._tv_dst, self._dst_panel_lbl = self._make_tree(
            paned, self.t("dst_panel"), 1, is_result=True)
        self._tv_dst.bind("<Double-Button-1>", lambda e: self._open_result()
                          if self._tv_dst.identify_region(e.x, e.y) != "heading" else None)
        if HAS_DND:
            self._tv_dst.drop_target_register(DND_FILES)
            self._tv_dst.dnd_bind("<<Drop>>", self._drop)

        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")
        bot = tk.Frame(self, bg=BG2, padx=16, pady=6)
        bot.pack(fill="x", side="bottom")

        folder_row = tk.Frame(bot, bg=BG2)
        folder_row.pack(fill="x", pady=(0, 10))
        self._save_folder_lbl = tk.Label(folder_row, text=self.t("save_folder"),
                                         font=("Segoe UI", 10, "bold"), bg=BG2, fg=FG2)
        self._save_folder_lbl.pack(side="left")

        dir_frame = tk.Frame(folder_row, bg=CARD,
                             highlightthickness=1, highlightbackground=BORDER, highlightcolor=BORDER)
        dir_frame.pack(side="left", fill="x", expand=True, padx=(8, 6))
        self._dir_lbl = tk.Label(dir_frame, textvariable=self._out_dir,
                                 font=("Segoe UI", 10), bg=CARD, fg=FG2, anchor="w", padx=8, pady=4)
        self._dir_lbl.pack(fill="x")
        self._out_dir.set(self.t("folder_placeholder"))

        self._pick_dir_btn  = self._btn(folder_row, self.t("pick_dir"), self._pick_dir)
        self._pick_dir_btn.pack(side="left")
        self._clear_dir_btn = self._btn(folder_row, "✕", self._clear_dir, dim=True)
        self._clear_dir_btn.pack(side="left", padx=(4, 0))
        self._open_dir_btn = self._btn(
            folder_row,
            "📂",
            self._open_out_dir,
            dim=True
        )
        self._open_dir_btn.pack(side="left", padx=(8, 0))

        # Изначально неактивна
        self._open_dir_btn.configure(fg=FG3)

        # Вся нижняя панель управления — один горизонтальный ряд через pack
        # Каждый блок: лейбл сверху + виджет снизу. Выравнивание — anchor="n"
        ctrl_row = tk.Frame(bot, bg=BG2)
        ctrl_row.pack(fill="x")

        def _ctrl_block(parent, label_text):
            """Создаёт блок: фрейм с лейблом сверху, возвращает (block, widget_frame)."""
            blk = tk.Frame(parent, bg=BG2)
            blk.pack(side="left", anchor="n", padx=(0, 16))
            lbl = tk.Label(blk, text=label_text,
                           font=("Segoe UI", 10, "bold"), bg=BG2, fg=FG2)
            lbl.pack(anchor="w")
            wf = tk.Frame(blk, bg=BG2)
            wf.pack(anchor="w", pady=(2, 0))
            return blk, lbl, wf

        # ФОРМАТ
        _fmt_blk, self._format_lbl, _fmt_wf = _ctrl_block(ctrl_row, self.t("format_lbl"))
        self._fmt = tk.StringVar(value="WEBP")
        _fmt_cb = ttk.Combobox(_fmt_wf, textvariable=self._fmt, values=FORMATS,
                               width=7, state="readonly", font=("Segoe UI", 10))
        _fmt_cb.pack()
        _fmt_cb.bind("<<ComboboxSelected>>", self._on_format_changed)

        # КАЧЕСТВО
        _qual_blk, self._quality_lbl, _qual_wf = _ctrl_block(ctrl_row, self.t("quality_lbl"))
        self._qual = tk.IntVar(value=85)
        self._qual.trace_add("write", lambda *a: self._save_settings())
        self._qual_slider = FancySlider(_qual_wf, from_=10, to=100, variable=self._qual, width=155)
        self._qual_slider.pack()

        # ИЗМЕНЕНИЕ РАЗРЕШЕНИЯ
        _res_blk, self._resize_lbl, _res_wf = _ctrl_block(ctrl_row, self.t("resize_lbl"))
        _res_blk.pack_configure(padx=(0, 12))
        self._resize_mode = tk.StringVar(value=self._resize_modes_localized()[0])
        self._cb_res = ttk.Combobox(_res_wf, textvariable=self._resize_mode,
                                    values=self._resize_modes_localized(),
                                    width=32, state="readonly", font=("Segoe UI", 10))
        self._cb_res.pack()
        self._cb_res.bind("<<ComboboxSelected>>", self._on_resize_mode_changed)

        # ПОЛЯ РАЗМЕРА (без лейбла — прячем через пустой лейбл той же высоты)
        _sz_blk = tk.Frame(ctrl_row, bg=BG2)
        _sz_blk.pack(side="left", anchor="n", padx=(0, 16))
        tk.Label(_sz_blk, text=" ", font=("Segoe UI", 10, "bold"),
                 bg=BG2, fg=BG2).pack(anchor="w")
        self._size_inputs_frame = tk.Frame(_sz_blk, bg=BG2)
        self._size_inputs_frame.pack(anchor="w", pady=(2, 0))

        self._w_val = tk.StringVar(value="")
        self._e_width = tk.Entry(
            self._size_inputs_frame, textvariable=self._w_val,
            bg=CARD, fg=FG2, state="disabled",
            font=("Consolas", 10, "bold"), width=5, bd=0, justify="center",
            highlightthickness=1, highlightbackground=BORDER, highlightcolor=BORDER,
            insertbackground="white", insertwidth=1)
        self._e_width.pack(side="left", ipady=2)

        self._lbl_x = tk.Label(self._size_inputs_frame, text="×",
                               font=("Segoe UI", 10), bg=BG2, fg=FG3)
        self._lbl_x.pack(side="left", padx=4)

        self._h_val = tk.StringVar(value="")
        self._e_height = tk.Entry(
            self._size_inputs_frame, textvariable=self._h_val,
            bg=CARD, fg=FG2, state="disabled",
            font=("Consolas", 10, "bold"), width=5, bd=0, justify="center",
            highlightthickness=1, highlightbackground=BORDER, highlightcolor=BORDER,
            insertbackground="white", insertwidth=1)
        self._e_height.pack(side="left", ipady=2)

        for entry in (self._e_width, self._e_height):
            entry.bind("<FocusIn>",         self._on_size_focus_in)
            entry.bind("<FocusOut>",        self._on_size_focus_out)
            entry.bind("<Button-1>",        self._on_size_click)
            entry.bind("<Double-Button-1>", self._select_all_entry)
            entry.bind("<Control-a>",       self._ctrl_a_entry)
            entry.bind("<Control-A>",       self._ctrl_a_entry)

        self._w_val.trace_add("write", self._limit_ico_size)
        self._h_val.trace_add("write", self._limit_ico_size)
        self._w_val.trace_add("write", self._limit_size_max)
        self._h_val.trace_add("write", self._limit_size_max)

        self._on_resize_mode_changed()

        # ПРОГРЕСС — блок растягивается, прогрессбар и виджет-фрейм тоже
        _pf_blk, self._progress_lbl, _pf_wf = _ctrl_block(ctrl_row, self.t("progress_lbl"))
        _pf_blk.pack_configure(side="left", fill="x", expand=True, padx=(0, 16), anchor="n")
        _pf_wf.pack_configure(fill="x")   # виджет-фрейм растягивается вместе с блоком
        self._prog = ttk.Progressbar(_pf_wf, style="P.Horizontal.TProgressbar", mode="determinate")
        self._prog.pack(fill="x")
        self._status     = tk.StringVar(value="")
        self._status_err = tk.StringVar(value="")
        status_row = tk.Frame(_pf_wf, bg=BG2)
        status_row.pack(anchor="w", fill="x", pady=(2, 0))
        self._status_lbl = tk.Label(status_row, textvariable=self._status,
                                    font=("Segoe UI", 10), bg=BG2, fg=FG2, anchor="w")
        self._status_lbl.pack(side="left")
        self._status_err_lbl = tk.Label(status_row, textvariable=self._status_err,
                                        font=("Segoe UI", 10), bg=BG2, fg=ACCENT2, anchor="w")
        self._status_err_lbl.pack(side="left", padx=(6, 0))

        # КНОПКА КОНВЕРТАЦИИ — на уровне лейблов (верхний ряд блока)
        _cbtn_blk = tk.Frame(ctrl_row, bg=BG2)
        _cbtn_blk.pack(side="left", anchor="n", padx=(0, 16))
        self._cbtn = self._btn(_cbtn_blk, self.t("convert_btn"), self._start, accent=True, big=True)
        self._cbtn.config(width=16)
        self._cbtn.pack(anchor="w", pady=(7, 0))

        # РАЗМЕР ФАЙЛОВ
        _sz_blk2, self._filesize_lbl, _sz_wf2 = _ctrl_block(ctrl_row, self.t("filesize_lbl"))
        _sz_blk2.pack_configure(padx=0)
        self._stats_frame = _sz_wf2
        self._lbl_size_src = tk.Label(self._stats_frame,
                                      text=f"{self.t('was')}  0.0 KB",
                                      font=("Consolas", 10), bg=BG2, fg=FG2, anchor="w")
        self._lbl_size_src.pack(anchor="w")
        self._lbl_size_dst = tk.Label(self._stats_frame,
                                      text=f"{self.t('became')} 0.0 KB",
                                      font=("Consolas", 10, "bold"), bg=BG2, fg=FG3, anchor="w")
        self._lbl_size_dst.pack(anchor="w")

    def _make_tree(self, parent, title, col, is_result=False):
        """Создаёт панель с деревом (список файлов или результатов)."""
        card = tk.Frame(parent, bg=CARD,
                        highlightthickness=1, highlightbackground=BORDER, highlightcolor=BORDER)
        card.grid(row=0, column=col, sticky="nsew",
                  padx=(0, 6) if col == 0 else (6, 0))

        hdr = tk.Frame(card, bg=BG3, pady=6)
        hdr.pack(fill="x")

        lbl = tk.Label(hdr, text=title, font=("Segoe UI", 10, "bold"), bg=BG3, fg=FG, padx=10)
        lbl.pack(side="left")

        inner = tk.Frame(card, bg=CARD)
        inner.pack(fill="both", expand=True)
        inner.columnconfigure(0, weight=1)
        inner.rowconfigure(0, weight=1)

        if is_result:
            cols = ("status", "name", "res", "size")
            tree = ttk.Treeview(inner, columns=cols, show="headings", style="Treeview")
            tree.heading("status", text=self.t("col_status"), anchor="center")
            tree.heading("name",   text=self.t("col_filename"), anchor="w")
            tree.heading("res",    text=self.t("col_res"), anchor="center")
            tree.heading("size",   text=self.t("col_size"), anchor="center")
            tree.column("status", width=70,  minwidth=70,  stretch=False, anchor="center")
            tree.column("name",   width=150, minwidth=100, stretch=True,  anchor="w")
            tree.column("res",    width=105, minwidth=105, stretch=False, anchor="center")
            tree.column("size",   width=105, minwidth=105, stretch=False, anchor="center")
            def _block_status_resize(e, t=tree):
                if t.identify_region(e.x, e.y) == "separator":
                    col_id = t.identify_column(e.x)
                    if col_id in ("#1",):  # только правая граница status
                        return "break"
            tree.bind("<Button-1>", _block_status_resize)
        else:
            cols = ("name", "res", "size")
            tree = ttk.Treeview(inner, columns=cols, show="headings", style="Treeview")
            tree.heading("name", text=self.t("col_filename"), anchor="w")
            tree.heading("res",  text=self.t("col_res"), anchor="center")
            tree.heading("size", text=self.t("col_size"), anchor="center")
            tree.column("name", width=200, minwidth=120, stretch=True,  anchor="w")
            tree.column("res",  width=105, minwidth=105, stretch=False, anchor="center")
            tree.column("size", width=90,  minwidth=90,  stretch=False, anchor="center")

        tree.grid(row=0, column=0, sticky="nsew", padx=(6, 2), pady=6)
        # Сохраняем ссылку на внутренний фрейм через отдельный атрибут экземпляра,
        # чтобы не делать monkey-patch стандартного виджета.
        tree._inner_frame = inner  # noqa: используется в _build для DnD-подсказки

        # Состояние сортировки: {col_id: bool} — True = ascending
        tree._sort_state = {}

        CustomScrollbar(inner, tree)

        tree.tag_configure("ok",   foreground=GREEN)
        tree.tag_configure("fail", foreground=ACCENT2)
        tree.bind("<MouseWheel>",
                  lambda e: tree.yview_scroll(int(-1 * (e.delta / 120)), "units"))
        return card, tree, lbl

    def _bind_sort_commands(self):
        """Привязывает команды сортировки к заголовкам обоих деревьев.
        Вызывается после _build и после смены языка."""
        # ── Исходные файлы ────────────────────────────────────────────────────
        def _sort_src(col_id):
            asc = not self._tv_src._sort_state.get(col_id, True)
            self._tv_src._sort_state = {col_id: asc}

            # Собираем пары (значение_для_сортировки, iid, путь_к_файлу)
            rows = []
            for iid in self._tv_src.get_children():
                idx = self._tv_src.index(iid)
                val = self._tv_src.set(iid, col_id)
                path = self._files[idx] if idx < len(self._files) else ""
                rows.append((val, iid, path))

            def _sort_key(item):
                v = item[0]
                if col_id == "size":
                    # Преобразуем "1.2 MB" / "345.6 KB" в байты для корректной сортировки
                    try:
                        num, unit = v.split()
                        num = float(num)
                        if "MB" in unit:
                            return num * 1024 * 1024
                        return num * 1024
                    except Exception:
                        return 0
                elif col_id == "res":
                    # "1920x1080" → (1920, 1080)
                    try:
                        w, h = v.lower().split("x")
                        return (int(w), int(h))
                    except Exception:
                        return (0, 0)
                return v.lower()

            rows.sort(key=_sort_key, reverse=not asc)

            # Перемещаем строки в дереве и синхронизируем self._files
            new_files = []
            for i, (_, iid, path) in enumerate(rows):
                self._tv_src.move(iid, "", i)
                new_files.append(path)
            self._files[:] = new_files

            # Обновляем индикатор сортировки в заголовке
            arrow = "▲" if asc else "▼"
            for c in ("name", "res", "size"):
                base = {"name": self.t("col_filename"),
                        "res":  self.t("col_res"),
                        "size": self.t("col_size")}[c]
                self._tv_src.heading(c, text=base + (" " + arrow if c == col_id else ""))

        for c in ("name", "res", "size"):
            self._tv_src.heading(c, command=lambda col=c: _sort_src(col))

        # ── Результат ────────────────────────────────────────────────────────
        def _sort_dst(col_id):
            if self._running:
                return  # не сортируем пока идёт конвертация — индексы могут съехать
            asc = not self._tv_dst._sort_state.get(col_id, True)
            self._tv_dst._sort_state = {col_id: asc}

            rows = []
            for iid in self._tv_dst.get_children():
                idx = self._tv_dst.index(iid)
                val = self._tv_dst.set(iid, col_id)
                res_entry = self._results[idx] if idx < len(self._results) else (None, False)
                tags = self._tv_dst.item(iid, "tags")
                all_vals = self._tv_dst.item(iid, "values")
                rows.append((val, iid, res_entry, tags, all_vals))

            def _sort_key(item):
                v = item[0]
                if col_id == "size":
                    try:
                        # Убираем суффикс кэша если есть
                        v2 = v.split()[0:2]
                        num, unit = float(v2[0]), v2[1]
                        if "MB" in unit:
                            return num * 1024 * 1024
                        return num * 1024
                    except Exception:
                        return 0
                elif col_id == "res":
                    try:
                        w, h = v.lower().split("x")
                        return (int(w), int(h))
                    except Exception:
                        return (0, 0)
                elif col_id == "status":
                    return v
                return v.lower()

            rows.sort(key=_sort_key, reverse=not asc)

            new_results = []
            for i, (_, iid, res_entry, _, __) in enumerate(rows):
                self._tv_dst.move(iid, "", i)
                new_results.append(res_entry)
            self._results[:] = new_results

            arrow = "▲" if asc else "▼"
            for c in ("status", "name", "res", "size"):
                base = {"status": self.t("col_status"),
                        "name":   self.t("col_filename"),
                        "res":    self.t("col_res"),
                        "size":   self.t("col_size")}[c]
                self._tv_dst.heading(c, text=base + (" " + arrow if c == col_id else ""))

        for c in ("status", "name", "res", "size"):
            self._tv_dst.heading(c, command=lambda col=c: _sort_dst(col))

    def _btn(self, p, text, cmd, accent=False, big=False, dim=False):
        """Создаёт стилизованную кнопку."""
        bn  = ACCENT if accent else CARD
        fn  = "#fff"  if accent else (FG3 if dim else FG2)
        bh  = ACCENT2 if accent else BG3
        fnt = ("Segoe UI", 11, "bold") if big else ("Segoe UI", 10)
        px, py = (20, 9) if big else (11, 5)
        b = tk.Button(p, text=text, command=cmd, font=fnt, bg=bn, fg=fn,
                      activebackground=bh, activeforeground="#fff",
                      relief="flat", bd=0, padx=px, pady=py, cursor="hand2")
        b.bind("<Enter>", lambda e, w=b: w.config(bg=bh, fg="#fff") if w["state"] != "disabled" else None)
        b.bind("<Leave>", lambda e, w=b: w.config(bg=bn, fg=fn)  if w["state"] != "disabled" else None)
        return b

    # ── логика изменения размера ───────────────────────────────────────────────

    def _is_auto_or_dash(self, val):
        """Проверяет, является ли значение прочерком или «Авто» на любом языке."""
        if val == "—":
            return True
        return any(val == STRINGS[lc].get("auto", "") for lc in STRINGS)

    def _on_resize_mode_changed(self, event=None):
        """Обновляет состояние полей ввода размера при смене режима."""
        key = self._current_resize_mode_key()

        # Если пользователь вручную выбрал режим, а у нас есть SVG без размеров — откатить
        if event is not None and key not in ("smart_crop", "custom"):
            if self._has_svg_without_size():
                messagebox.showerror(self.t("svg_no_size_title"), self.t("svg_no_size_msg"))
                self._resize_mode.set(self._key_to_localized_mode("custom"))
                key = "custom"

        if not hasattr(self, "_last_width"):
            self._last_width  = ""
        if not hasattr(self, "_last_height"):
            self._last_height = ""

        if key == "no_change":
            self._last_width  = self._w_val.get() if self._w_val.get().isdigit() else self._last_width
            self._last_height = self._h_val.get() if self._h_val.get().isdigit() else self._last_height
            self._w_val.set("—")
            self._h_val.set("—")
            self._e_width.config(state="disabled",  fg=FG2, highlightbackground=BORDER)
            self._e_height.config(state="disabled", fg=FG2, highlightbackground=BORDER)

        elif key == "prop_width":
            if self._is_auto_or_dash(self._w_val.get()):
                self._w_val.set(self._last_width)
            self._last_height = self._h_val.get() if self._h_val.get().isdigit() else self._last_height
            self._h_val.set(self.t("auto"))
            self._e_width.config(state="normal",    fg=FG,  highlightbackground=ACCENT)
            self._e_height.config(state="disabled", fg=FG2, highlightbackground=BORDER)

        elif key == "prop_height":
            if self._is_auto_or_dash(self._h_val.get()):
                self._h_val.set(self._last_height)
            self._last_width = self._w_val.get() if self._w_val.get().isdigit() else self._last_width
            self._w_val.set(self.t("auto"))
            self._e_width.config(state="disabled", fg=FG2, highlightbackground=BORDER)
            self._e_height.config(state="normal",  fg=FG,  highlightbackground=ACCENT)

        elif key == "smart_crop":
            if self._is_auto_or_dash(self._w_val.get()):
                self._w_val.set(self._last_width)
            if self._is_auto_or_dash(self._h_val.get()):
                self._h_val.set(self._last_height)
            self._e_width.config(state="normal",  fg=FG, highlightbackground=ACCENT, highlightcolor=ACCENT)
            self._e_height.config(state="normal", fg=FG, highlightbackground=ACCENT, highlightcolor=ACCENT)

        else:  # custom
            if self._is_auto_or_dash(self._w_val.get()):
                self._w_val.set(self._last_width)
            if self._is_auto_or_dash(self._h_val.get()):
                self._h_val.set(self._last_height)
            self._e_width.config(state="normal",  fg=FG, highlightbackground=ACCENT, highlightcolor=ACCENT)
            self._e_height.config(state="normal", fg=FG, highlightbackground=ACCENT, highlightcolor=ACCENT)

        self._save_settings()

    def _on_format_changed(self, event=None):
        """Обрабатывает смену формата вывода."""
        fmt     = self._fmt.get()
        prev    = getattr(self, "_prev_fmt", None)

        quality_matters = fmt in ("JPEG", "WEBP", "HEIC", "AVIF")
        if hasattr(self, "_qual_slider"):
            self._qual_slider.set_enabled(quality_matters)

        if fmt == "ICO":
            current_key = self._current_resize_mode_key()
            if current_key not in ("smart_crop", "custom"):
                self._resize_mode.set(self._key_to_localized_mode("smart_crop"))
            self._w_val.set("256")
            self._h_val.set("256")
            self._on_resize_mode_changed()
        elif prev == "ICO":
            # Переключились с ICO — сбрасываем поля чтобы размеры ICO
            # не перетекали в другой формат
            self._last_width  = ""
            self._last_height = ""
            self._w_val.set("")
            self._h_val.set("")
            self._on_resize_mode_changed()

        self._prev_fmt = fmt
        self._save_settings()

    def _limit_ico_size(self, *args):
        """Ограничивает размер ICO максимум 256 пикселей."""
        if not hasattr(self, "_fmt") or self._fmt.get() != "ICO":
            return
        for var in (self._w_val, self._h_val):
            value = var.get()
            if value.isdigit():
                n = min(int(value), 256)
                if str(n) != value:
                    var.set(str(n))

    def _limit_size_max(self, *args):
        """Ограничивает размер изображения максимум 16000 пикселей."""
        for var in (self._w_val, self._h_val):
            value = var.get()
            if value.isdigit():
                n = min(int(value), 16000)
                if str(n) != value:
                    var.set(str(n))

    def _on_size_focus_in(self, event):
        event.widget.config(highlightbackground=ACCENT, highlightcolor=ACCENT)

    def _on_size_focus_out(self, event):
        """При потере фокуса возвращаем цвет рамки согласно текущему режиму.

        В двухполевых режимах (smart_crop, custom) поле которое теряет фокус
        гасится до BORDER только если фокус уходит в другое поле ввода размера
        (пользователь переключился между полями). Если фокус уходит куда-то ещё
        (кнопка, combobox и т.д.) — оба поля остаются ACCENT.
        """
        key      = self._current_resize_mode_key()
        w        = event.widget
        focus_to = self.focus_get()

        if key in ("smart_crop", "custom"):
            # Фокус ушёл в другое поле размера — гасим текущее, второе уже
            # подсветится через _on_size_click / _on_size_focus_in
            other = self._e_height if w is self._e_width else self._e_width
            if focus_to is other:
                w.config(highlightbackground=BORDER, highlightcolor=BORDER)
            else:
                # Фокус ушёл куда-то ещё — оба поля остаются активными
                w.config(highlightbackground=ACCENT, highlightcolor=ACCENT)
        elif key == "prop_width" and w is self._e_width:
            w.config(highlightbackground=ACCENT, highlightcolor=ACCENT)
        elif key == "prop_height" and w is self._e_height:
            w.config(highlightbackground=ACCENT, highlightcolor=ACCENT)
        else:
            w.config(highlightbackground=BORDER, highlightcolor=BORDER)

    def _on_size_click(self, event):
        """Гарантирует, что при клике поле сразу получает фокус и окрашивается рамка."""
        w = event.widget
        if w.cget("state") != "disabled":
            w.focus_set()
            w.config(highlightbackground=ACCENT, highlightcolor=ACCENT)
            other = self._e_height if w is self._e_width else self._e_width
            if other.cget("state") != "disabled":
                other.config(highlightbackground=BORDER, highlightcolor=BORDER)

    def _select_all_entry(self, event):
        event.widget.select_range(0, "end")
        event.widget.icursor("end")
        return "break"

    def _ctrl_a_entry(self, event):
        event.widget.select_range(0, "end")
        return "break"

    # ── анимация сердечка ─────────────────────────────────────────────────────

    def _animate_heart_pulse(self):
        """Запускает анимацию пульсации иконки доната."""
        if self._heart_hovered:
            self.after(1000, self._animate_heart_pulse)
            return
        self._hbtn.config(font=("Segoe UI", 20, "bold"), fg=HEART_RED)
        self.after(_HEART_BEAT1_MS,
                   lambda: self._hbtn.config(font=("Segoe UI", 16), fg=FG3)
                   if not self._heart_hovered else None)
        self.after(_HEART_BEAT2_MS,
                   lambda: self._hbtn.config(font=("Segoe UI", 19, "bold"), fg=ACCENT2)
                   if not self._heart_hovered else None)
        self.after(_HEART_BEAT3_MS,
                   lambda: self._hbtn.config(font=("Segoe UI", 16), fg=FG3)
                   if not self._heart_hovered else None)
        self.after(random.randint(_HEART_MIN_IDLE, _HEART_MAX_IDLE), self._animate_heart_pulse)

    def _on_heart_hover(self, is_enter):
        self._heart_hovered = is_enter
        if is_enter:
            self._hbtn.config(fg=HEART_RED, font=("Segoe UI", 21, "bold"))
        else:
            self._hbtn.config(fg=FG3, font=("Segoe UI", 16))

    # ── управление папкой вывода ──────────────────────────────────────────────

    def _pick_dir(self):
        """Открывает диалог выбора папки сохранения."""
        d = filedialog.askdirectory(title=self.t("save_folder"))
        if d:
            self._out_dir.set(d)
            self._dir_lbl.config(fg=FG)

    def _clear_dir(self):
        """Сбрасывает папку сохранения."""
        self._out_dir.set(self.t("folder_placeholder"))
        self._dir_lbl.config(fg=FG2)

    # ── drag-and-drop ─────────────────────────────────────────────────────────

    def _dz_hover(self, on):
        """Подсвечивает зону drop при наведении файлов."""
        self._lb_src_card.config(highlightbackground=ACCENT if on else BORDER)
        if self._dz_ico:
            self._dz_ico.config(fg=ACCENT if on else FG3)
        if self._dz_lbl:
            self._dz_lbl.config(
                text=self.t("drop_release") if on else self.t("drop_hint"),
                fg=ACCENT if on else FG2)

    def _drop(self, e):
        """Обрабатывает сброс файлов из файлового менеджера."""
        self._dz_hover(False)
        for p in self.tk.splitlist(e.data):
            p = p.strip()
            if p and p not in self._files:
                if os.path.splitext(p)[1].lower() in IMG_EXTS:
                    self._files.append(p)
                    try:
                        self._total_src_bytes += os.path.getsize(p)
                    except Exception:
                        pass
                    self._tv_src.insert("", "end", values=(
                        os.path.basename(p), get_image_res_str(p), get_file_size_str(p)))
        self._upd()

    # ── управление списком файлов ─────────────────────────────────────────────

    def _add(self):
        """Открывает диалог добавления файлов."""
        files = filedialog.askopenfilenames(
            filetypes=[("Images", "*.jpg *.jpeg *.png *.webp *.bmp *.tiff *.gif *.ico"
                        + (" *.avif" if AVIF_AVAILABLE else "")
                        + (" *.heic *.heif" if HEIF_AVAILABLE else "")
                        + (" *.svg" if SVG_AVAILABLE else "")),
                       ("All", "*.*")])
        for f in files:
            if f not in self._files:
                self._files.append(f)
                try:
                    self._total_src_bytes += os.path.getsize(f)
                except Exception:
                    pass
                self._tv_src.insert("", "end", values=(
                    os.path.basename(f), get_image_res_str(f), get_file_size_str(f)))
        self._upd()

    def _clear(self):
        """Очищает списки файлов и результатов."""
        with self._data_lock:
            self._files.clear()
            self._converted_cache.clear()
        self._results.clear()
        self._total_src_bytes = 0
        self._total_dst_bytes = 0
        for item in self._tv_src.get_children():
            self._tv_src.delete(item)
        for item in self._tv_dst.get_children():
            self._tv_dst.delete(item)
        self._prog["value"] = 0
        self._status.set(self.t("cleared"))
        self._clbl.config(text="")
        self._upd()

    def _has_svg_without_size(self):
        """Проверяет, есть ли в списке SVG-файлы, у которых не удалось определить разрешение."""
        if not SVG_AVAILABLE:
            return False
        for p in self._files:
            if os.path.splitext(p)[1].lower() == ".svg":
                w, h = get_svg_resolution_pure(p)
                if not w or not h:
                    return True # Нашли проблемный файл
        return False

    def _upd(self):
        """Обновляет счётчик файлов и метку drop-зоны."""
        n = len(self._files)
        if self._dz_hint is not None:
            if n > 0:
                self._dz_hint.place_forget()
            else:
                self._dz_hint.place(relx=0.5, rely=0.45, anchor="center")
                if self._dz_ico:
                    self._dz_ico.config(fg=FG3)
                if self._dz_lbl:
                    self._dz_lbl.config(text=self.t("drop_hint"), fg=FG2)

        if self._lang == "ru":
            s = ("файл"   if n % 10 == 1 and n % 100 != 11 else
                 "файла"  if 2 <= n % 10 <= 4 and not (11 <= n % 100 <= 14) else "файлов")
            self._clbl.config(text=f"{n} {s}")
        elif self._lang == "uk":
            s = ("файл"   if n % 10 == 1 and n % 100 != 11 else
                 "файли"  if 2 <= n % 10 <= 4 and not (11 <= n % 100 <= 14) else "файлів")
            self._clbl.config(text=f"{n} {s}")
        else:
            self._clbl.config(text=f"{n} {'file' if n == 1 else 'files'}")

        if not self._running:
            self._status.set(self.t("files_count").format(n=n))
        self._lbl_size_src.config(
            text=f"{self.t('was')}  {format_size(self._total_src_bytes)}", fg=FG)
        if self._total_dst_bytes > 0:
            self._lbl_size_dst.config(
                text=f"{self.t('became')} {format_size(self._total_dst_bytes)}", fg=GREEN)
        else:
            self._lbl_size_dst.config(text=f"{self.t('became')} 0.0 KB", fg=FG3)

        # Если в списке есть SVG-файлы БЕЗ размера — автоматически переключаем на Custom
        if self._has_svg_without_size():
            if self._current_resize_mode_key() not in ("smart_crop", "custom"):
                self._resize_mode.set(self._key_to_localized_mode("custom"))
                self._on_resize_mode_changed()

        # Отложенное обновление скроллбара, чтобы Treeview успел отрисовать новые строки
        self.after(50, self._refresh_scrollbars)



    def _refresh_scrollbars(self):
        """Принудительно запрашивает обновление области прокрутки для показа скроллбара."""
        try:
            self._tv_src.yview_moveto(self._tv_src.yview()[0])
            self._tv_dst.yview_moveto(self._tv_dst.yview()[0])
        except Exception:
            pass

    # ── обновление строк интерфейса ───────────────────────────────────────────

    def _update_ui_strings(self):
        """Перерисовывает все надписи интерфейса при смене языка."""
        self.title(APP_NAME)
        self._add_btn.config(text=self.t("add"))
        self._clear_btn.config(text=self.t("clear"))

        self._src_panel_lbl.config(text=self.t("src_panel"))
        self._dst_panel_lbl.config(text=self.t("dst_panel"))

        self._tv_src.heading("name", text=self.t("col_filename"))
        self._tv_src.heading("res",  text=self.t("col_res"))
        self._tv_src.heading("size", text=self.t("col_size"))

        self._tv_dst.heading("status", text=self.t("col_status"))
        self._tv_dst.heading("name",   text=self.t("col_filename"))
        self._tv_dst.heading("res",    text=self.t("col_res"))
        self._tv_dst.heading("size",   text=self.t("col_size"))

        # Переподключаем команды сортировки с обновлёнными строками заголовков
        self._tv_src._sort_state = {}
        self._tv_dst._sort_state = {}
        self._bind_sort_commands()

        if not self._files and self._dz_lbl:
            self._dz_lbl.config(text=self.t("drop_hint"))

        self._save_folder_lbl.config(text=self.t("save_folder"))
        self._pick_dir_btn.config(text=self.t("pick_dir"))

        current_dir    = self._out_dir.get()
        is_placeholder = any(current_dir == STRINGS[lang]["folder_placeholder"] for lang in STRINGS)
        if is_placeholder or current_dir == "":
            self._out_dir.set(self.t("folder_placeholder"))

        self._format_lbl.config(text=self.t("format_lbl"))
        self._quality_lbl.config(text=self.t("quality_lbl"))
        self._resize_lbl.config(text=self.t("resize_lbl"))
        self._progress_lbl.config(text=self.t("progress_lbl"))
        self._filesize_lbl.config(text=self.t("filesize_lbl"))
        self._settings_btn.config(text=self.t("settings_title"))

        # Сохраняем текущий режим по языконезависимому ключу
        current_key = self._current_resize_mode_key()
        self._cb_res.config(values=self._resize_modes_localized())
        self._resize_mode.set(self._key_to_localized_mode(current_key))

        for val_var in (self._w_val, self._h_val):
            cur = val_var.get()
            if any(cur == STRINGS[lc].get("auto", "") for lc in STRINGS):
                val_var.set(self.t("auto"))

        if not self._running:
            self._cbtn.config(text=self.t("convert_btn"))
        else:
            self._cbtn.config(text=self.t("processing_btn"))

        self._upd()

    # ── открытие файлов ───────────────────────────────────────────────────────

    def _open_item(self, tree, path_list):
        """Открывает выбранный исходный файл двойным кликом."""
        sel = tree.selection()
        if not sel:
            return
        idx = tree.index(sel[0])
        if idx < len(path_list):
            path = path_list[idx]
            if os.path.exists(path):
                open_path(path)

    def _open_result(self):
        """Открывает выбранный результирующий файл двойным кликом."""
        sel = self._tv_dst.selection()
        if not sel:
            return
        idx = self._tv_dst.index(sel[0])
        if idx < len(self._results):
            path, ok = self._results[idx]
            if ok and os.path.exists(path):
                open_path(path)

    def _open_out_dir(self):
        """Открывает папку с результатами."""
        d = self._out_dir.get()
        if d and os.path.isdir(d):
            open_path(d)

    # ── запуск конвертации ────────────────────────────────────────────────────

    def _start(self):
        """Валидирует параметры и запускает фоновый поток конвертации."""
        if self._running:
            return
        if not self._files:
            messagebox.showwarning(APP_NAME, self.t("warn_no_files"))
            return

        mode     = self._resize_mode.get()
        mode_key = self._current_resize_mode_key()
        target_w = target_h = 0
        try:
            if mode_key in ("prop_width", "smart_crop", "custom"):
                target_w = int(self._w_val.get())
                if target_w <= 0:
                    raise ValueError
            if mode_key in ("prop_height", "smart_crop", "custom"):
                target_h = int(self._h_val.get())
                if target_h <= 0:
                    raise ValueError
        except ValueError:
            messagebox.showerror(APP_NAME, self.t("warn_bad_size"))
            return

        # Если есть SVG без встроенного разрешения — запрещаем конвертацию без явных размеров
        if mode_key not in ("smart_crop", "custom"):
            if self._has_svg_without_size():
                messagebox.showerror(APP_NAME, self.t("svg_no_size_msg"),
                                     title=self.t("svg_no_size_title"))
                return

        if self._fmt.get() == "ICO":
            target_w = min(target_w, 256) if target_w else 256
            target_h = min(target_h, 256) if target_h else 256
            #"Без изменений" + ICO — предупреждение если хотя бы один файл > 256
            if mode_key == "no_change":
                has_large = False
                for p in self._files:
                    try:
                        with Image.open(p) as _chk:
                            if _chk.size[0] > 256 or _chk.size[1] > 256:
                                has_large = True
                                break
                    except Exception:
                        pass
                if has_large:
                    answer = messagebox.askokcancel(
                        self.t("ico_too_large_title"),
                        self.t("ico_too_large_msg"),
                        icon="warning")
                    if not answer:
                        return

        out_dir = self._out_dir.get()
        if not out_dir or not os.path.isdir(out_dir):
            out_dir = filedialog.askdirectory(title=self.t("save_folder"))
            if not out_dir:
                return
            self._out_dir.set(out_dir)
            self._dir_lbl.config(fg=FG)

        fmt_now            = self._fmt.get()
        ext_now            = ".jpg" if fmt_now == "JPEG" else f".{fmt_now.lower()}"
        current_config_str = (f"fmt:{fmt_now}|q:{self._qual.get()}|dir:{out_dir}"
                              f"|mode:{mode_key}|w:{target_w}|h:{target_h}")

        # Проверяем конфликты по «чистому» имени (без суффикса _1, _2 и т.д.)
        # _generate_unique_filename здесь использовать нельзя — она сама
        # уходит от конфликта и диалог никогда не показывается.
        existing       = []
        seen_basenames = set()
        for p in self._files:
            base_name  = os.path.splitext(os.path.basename(p))[0]
            plain_name = f"{base_name}{ext_now}"
            out_path   = os.path.join(out_dir, plain_name)
            if plain_name.lower() in seen_basenames:
                continue
            seen_basenames.add(plain_name.lower())
            if not os.path.exists(out_path):
                continue
            existing.append(plain_name)

        self._overwrite_confirmed = False
        if existing:
            names_preview = "\n".join(existing[:5])
            if len(existing) > 5:
                names_preview += self.t("overwrite_more").format(n=len(existing) - 5)
            answer = messagebox.askyesno(
                APP_NAME,
                self.t("overwrite_msg").format(names=names_preview),
                icon="warning")
            if not answer:
                return
            self._overwrite_confirmed = True

        self._results.clear()
        self._total_dst_bytes = 0
        for item in self._tv_dst.get_children():
            self._tv_dst.delete(item)
        self._lbl_size_dst.config(text=f"{self.t('became')} ...", fg=ACCENT)
        self._status_lbl.config(fg=FG2)
        self._status_err.set("")
        self._open_dir_btn.config(fg=FG3)
        self._running = True
        self._cbtn.config(text=self.t("processing_btn"))
        self._prog["value"] = 0
        self.update_idletasks()

        # Делаем снимок списка файлов, чтобы фоновый поток работал
        # с неизменяемой копией и не было race condition.
        with self._data_lock:
            files_snapshot = list(self._files)

        threading.Thread(
            target=self._convert_worker,
            args=(files_snapshot, out_dir,
                  self._fmt.get(), self._qual.get(),
                  mode_key, target_w, target_h,
                  self._overwrite_confirmed),
            daemon=True).start()

    # ── очередь событий GUI ───────────────────────────────────────────────────

    def _listen_queue(self):
        """Опрашивает очередь от фонового потока и обновляет UI."""
        try:
            while True:
                task   = self._gui_queue.get_nowait()
                action = task.get("action")

                if action == "insert_result":
                    tag          = "ok" if task["success"] else "fail"
                    cache_tag    = self.t("cache_tag")
                    display_size = f"{task['size_str']}{cache_tag if task['cached'] else ''}"
                    self._tv_dst.insert("", "end", values=(
                        task["status_icon"],
                        task["out_name"],
                        task["res_str"],
                        display_size,
                    ), tags=(tag,))
                    self._results.append((task["out_path"], task["success"]))
                    self._total_dst_bytes += task["size_bytes"]
                    self._lbl_size_dst.config(
                        text=f"{self.t('became')} {format_size(self._total_dst_bytes)}", fg=GREEN)

                elif action == "progress":
                    self._status.set(task["status"])
                    self._prog["value"] = task["prog_val"]

                elif action == "finish":
                    self._status.set(f"✔ {task['ok']}")
                    self._status_lbl.config(fg=GREEN)
                    self._status_err.set(f"✘ {task['err']}" if task["err"] else "")
                    self._cbtn.config(state="normal", text=self.t("convert_btn"))
                    self._open_dir_btn.config(fg=GREEN)
                    self._running = False

                self._gui_queue.task_done()
        except queue.Empty:
            pass
        self.after(100, self._listen_queue)

    # ── конвертация (фоновый поток) ───────────────────────────────────────────

    def _convert_one(self, path, out_dir, fmt, out_name, quality,
                     mode, target_w, target_h, current_config_str, resize_key=None):
        """Конвертирует один файл. Вызывается из пула потоков."""
        out_path  = os.path.join(out_dir, out_name)
        error_msg = None

        # Проверка кэша (чтение _converted_cache защищено вызывающим кодом)
        with self._data_lock:
            cached_entry = self._converted_cache.get(path)

        if cached_entry:
            cached_config, cached_out_path, cached_size, cached_success, cached_res_str = cached_entry
            # Используем кэш только при success=True и наличии файла на диске
            if (cached_success and cached_config == current_config_str
                    and os.path.exists(cached_out_path)):
                return {
                    "path": path, "out_name": out_name, "out_path": cached_out_path,
                    "success": True, "cached": True,
                    "f_size": cached_size, "res_str": cached_res_str,
                    "size_str": format_size(cached_size),
                }

        success  = False
        f_size   = 0
        res_str  = "??x??"
        size_str = "0 KB"
        try:
            # ── SVG: рендерим через resvg_py в PNG-байты, затем открываем как обычное изображение
            is_svg = os.path.splitext(path)[1].lower() == ".svg"
            if is_svg and SVG_AVAILABLE:
                # Читаем байты и определяем кодировку: поддерживаем UTF-16 и UTF-8 BOM
                with open(path, "rb") as _fb:
                    _raw = _fb.read()
                if _raw.startswith(b"\xff\xfe") or _raw.startswith(b"\xfe\xff"):
                    svg_str = _raw.decode("utf-16")
                elif _raw.startswith(b"\xef\xbb\xbf"):
                    svg_str = _raw[3:].decode("utf-8", errors="replace")
                else:
                    svg_str = _raw.decode("utf-8", errors="replace")
                # Определяем размер рендера из параметров задачи
                if resize_key in ("smart_crop", "custom"):
                    render_w, render_h = target_w, target_h
                elif resize_key == "prop_width":
                    render_w, render_h = target_w, 0
                elif resize_key == "prop_height":
                    render_w, render_h = 0, target_h
                else:
                    # Для режима "Без изменений" вытаскиваем оригинальные пиксели из SVG
                    orig_w, orig_h = get_svg_resolution_pure(path)
                    render_w, render_h = orig_w or 0, orig_h or 0
                png_bytes = _resvg_py.svg_to_bytes(
                    svg_string=svg_str,
                    width=render_w if render_w else None,
                    height=render_h if render_h else None,
                )
                img = Image.open(io.BytesIO(png_bytes)).copy()
                # Принудительно переводим в RGBA чтобы не потерять прозрачность SVG
                if img.mode not in ("RGBA", "RGB"):
                    img = img.convert("RGBA")
                orig_w, orig_h = img.size
                # После рендера resize не нужен — resvg уже отрисовал нужный размер.
                # Для smart_crop делаем кроп если соотношение не совпало.
                if resize_key == "smart_crop" and (orig_w, orig_h) != (target_w, target_h):
                    scale = max(target_w / orig_w, target_h / orig_h)
                    inter_w = max(1, round(orig_w * scale))
                    inter_h = max(1, round(orig_h * scale))
                    img = img.resize((inter_w, inter_h), Image.Resampling.LANCZOS)
                    left = (inter_w - target_w) // 2
                    top  = (inter_h - target_h) // 2
                    img  = img.crop((left, top, left + target_w, top + target_h))
                # Для режима "Пользовательский" принудительно растягиваем/сплющиваем
                # картинку до точных цифр, игнорируя сохранение пропорций.
                elif resize_key == "custom" and (orig_w, orig_h) != (target_w, target_h):
                    img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
            else:
                img = Image.open(path)
                img.load()  # полностью читаем чтобы можно было закрыть файл

            with img:
                if not is_svg:
                    orig_w, orig_h = img.size  # берём ДО ICC (только для растровых)

                # CMYK не поддерживается ImageCms напрямую — конвертируем заранее
                if img.mode == "CMYK":
                    img = img.convert("RGB")

                try:
                    icc_profile = img.info.get("icc_profile")
                    if icc_profile:
                        src_profile = ImageCms.ImageCmsProfile(io.BytesIO(icc_profile))
                        dst_profile = ImageCms.createProfile("sRGB")
                        # Сохраняем альфа если он есть
                        out_mode = "RGBA" if img.mode in ("RGBA", "PA", "LA") else "RGB"
                        img = ImageCms.profileToProfile(
                            img, src_profile, dst_profile, outputMode=out_mode
                        )
                except Exception:
                    pass

                # Для SVG resize пропускаем — изображение уже отрендерено в нужный размер
                # Используем resize_key (языконезависимый) вместо rm[N]
                if not is_svg:
                    if resize_key == "prop_width":
                        new_w = target_w
                        new_h = max(1, round(orig_h * (target_w / orig_w)))
                        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                    elif resize_key == "prop_height":
                        new_h = target_h
                        new_w = max(1, round(orig_w * (target_h / orig_h)))
                        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                    elif resize_key == "smart_crop":
                        scale = max(target_w / orig_w, target_h / orig_h)
                        inter_w = max(1, round(orig_w * scale))
                        inter_h = max(1, round(orig_h * scale))
                        img = img.resize((inter_w, inter_h), Image.Resampling.LANCZOS)
                        left = (inter_w - target_w) // 2
                        top = (inter_h - target_h) // 2
                        img = img.crop((left, top, left + target_w, top + target_h))
                    elif resize_key == "custom":
                        img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)

                if fmt == "JPEG" and img.mode in ("RGBA", "P", "PA", "LA"):
                    # Сначала конвертируем в RGBA, затем берём маску —
                    # в палитровом режиме "P" split()[3] не альфа-канал
                    rgba   = img.convert("RGBA")
                    bg_img = Image.new("RGB", rgba.size, (255, 255, 255))
                    bg_img.paste(rgba, mask=rgba.split()[3])
                    img = bg_img

                kw = {"quality": quality} if fmt in ("JPEG", "WEBP", "HEIC", "AVIF") else {}

                if fmt == "ICO":
                    if img.mode not in ("RGBA", "RGB"):
                        img = img.convert("RGBA")
                    std_sizes = [16, 24, 32, 48, 64, 128, 256]
                    if resize_key == "no_change":
                        all_sizes = [s for s in sorted(set(std_sizes + [img.size[0]])) if s <= 256]
                        kw["sizes"] = [(s, s) for s in all_sizes]
                    else:
                        max_side = min(max(img.size), 256)
                        ico_sizes = [s for s in std_sizes if s < max_side]
                        ico_sizes.append(max_side)
                        kw["sizes"] = sorted([(s, s) for s in set(ico_sizes)])

                # AVIF: гарантируем совместимый цветовой режим и передаём ICC-профиль
                if fmt == "AVIF":
                    if img.mode not in ("RGB", "RGBA"):
                        # LA, P, PA → RGBA чтобы сохранить прозрачность если она есть
                        if img.mode in ("LA", "PA"):
                            img = img.convert("RGBA")
                        elif img.mode == "P" and "transparency" in img.info:
                            img = img.convert("RGBA")
                        else:
                            img = img.convert("RGB")
                    # Встраиваем sRGB ICC-профиль — AVIF декодеры ожидают его явно
                    srgb_profile = ImageCms.createProfile("sRGB")
                    kw["icc_profile"] = ImageCms.ImageCmsProfile(srgb_profile).tobytes()

                tmp_path = out_path + ".tmp"
                save_fmt = "HEIF" if fmt == "HEIC" else fmt
                try:
                    img.save(tmp_path, save_fmt, **kw)
                    if os.path.exists(out_path):
                        os.remove(out_path)
                    os.replace(tmp_path, out_path)
                except Exception:
                    # Удаляем незавершённый временный файл при любой ошибке записи
                    try:
                        if os.path.exists(tmp_path):
                            os.remove(tmp_path)
                    except OSError:
                        pass
                    raise
                # Для ICO показываем реальный максимальный размер внутри файла
                if fmt == "ICO":
                    try:
                        with Image.open(out_path) as ico_check:
                            max_s = max(ico_check.size)
                            res_str = f"{max_s}x{max_s} (ICO)"
                    except Exception:
                        res_str = f"{img.size[0]}x{img.size[1]} (ICO)"
                else:
                    res_str = f"{img.size[0]}x{img.size[1]}"

            success  = True
            f_size   = os.path.getsize(out_path)
            size_str = format_size(f_size)
        except Exception as ex:
            # Сохраняем текст ошибки отдельно, out_path остаётся валидным путём
            error_msg = str(ex)

        # Запись в кэш только при успехе — неудачи не кэшируем,
        # чтобы следующий запуск пересчитал файл заново.
        if success:
            with self._data_lock:
                # LRU-ограничение: не более 500 записей за сессию
                if len(self._converted_cache) >= 500:
                    self._converted_cache.pop(next(iter(self._converted_cache)))
                self._converted_cache[path] = (
                    current_config_str, out_path, f_size, True, res_str)

        return {
            "path":      path,
            "out_name":  out_name,
            "out_path":  out_path,       # всегда путь, никогда не строка ошибки
            "error_msg": error_msg,      # ошибка хранится отдельно
            "success":   success,
            "cached":    False,
            "f_size":    f_size,
            "res_str":   res_str,
            "size_str":  size_str,
        }

    def _generate_unique_filename(self, out_dir, base_name, ext,
                                   reserved_names=None, allow_overwrite=False):
        """Генерирует уникальное имя файла, не конфликтующее ни с диском, ни с батчем.

        allow_overwrite=True: файлы на диске не считаются конфликтом (пользователь
        уже согласился на замену), суффикс _1/_2 добавляется только при коллизии
        внутри текущего батча.
        """
        if reserved_names is None:
            reserved_names = set()
        counter = 0
        while True:
            filename   = f"{base_name}{ext}" if counter == 0 else f"{base_name}_{counter}{ext}"
            lower_name = filename.lower()
            on_disk    = os.path.exists(os.path.join(out_dir, filename))
            # При allow_overwrite файл на диске не блокирует имя
            disk_conflict = on_disk and not allow_overwrite
            if lower_name not in reserved_names and not disk_conflict:
                reserved_names.add(lower_name)
                return filename
            counter += 1

    def _convert_worker(self, files_snapshot, out_dir, fmt, quality, mode_key,
                        target_w, target_h, allow_overwrite=False):
        """Фоновый рабочий поток: конвертирует все файлы параллельно."""
        # fmt, quality, mode_key переданы из GUI-потока как снимок значений —
        # не читаем self._fmt / self._qual / self._resize_mode из фонового потока.
        ext        = ".jpg" if fmt == "JPEG" else f".{fmt.lower()}"
        resize_key = mode_key  # уже языконезависимый ключ, декодирование не нужно
        total      = len(files_snapshot)

        ok_cnt = err_cnt = 0
        done   = 0

        current_config_str = (f"fmt:{fmt}|q:{quality}|dir:{out_dir}"
                              f"|mode:{mode_key}|w:{target_w}|h:{target_h}")
        workers = min(os.cpu_count() or 4, 8)

        # Предварительное выделение уникальных имён на основе снимка списка
        allocated_names = {}
        reserved_names  = set()
        for path in files_snapshot:
            base_name = os.path.splitext(os.path.basename(path))[0]
            allocated_names[path] = self._generate_unique_filename(
                out_dir, base_name, ext, reserved_names,
                allow_overwrite=allow_overwrite)

        futures          = {}
        results_by_path  = {}
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for path in files_snapshot:
                out_name = allocated_names[path]
                # Для SVG добавляем пометку в статус — рендер может занять время
                bname_submit = os.path.basename(path)
                if os.path.splitext(path)[1].lower() == ".svg" and SVG_AVAILABLE:
                    self._gui_queue.put({
                        "action":   "progress",
                        "status":   f"SVG → {bname_submit[:16]}",
                        "prog_val": self._gui_queue.qsize(),  # приблизительно
                    })
                f = pool.submit(self._convert_one, path, out_dir, fmt, out_name, quality,
                                mode_key, target_w, target_h, current_config_str, resize_key)
                futures[f] = path

            for future in as_completed(futures):
                res   = future.result()
                path  = futures[future]
                bname = os.path.basename(path)
                done += 1
                results_by_path[path] = res
                self._gui_queue.put({
                    "action":   "progress",
                    "status":   f"{done}/{total}  {bname[:12]}",
                    "prog_val": round(done / total * 100),
                })

        # Вставляем результаты в порядке исходного списка файлов
        for path in files_snapshot:
            res = results_by_path[path]
            if res["success"]:
                ok_cnt += 1
            else:
                err_cnt += 1
            self._gui_queue.put({
                "action":     "insert_result",
                "status_icon": "✔" if res["success"] else "✘",
                "out_name":   res["out_name"],
                "res_str":    res["res_str"],
                "size_str":   res["size_str"],
                "cached":     res["cached"],
                "out_path":   res["out_path"],
                "success":    res["success"],
                "size_bytes": res["f_size"],
            })

        self._gui_queue.put({
            "action": "finish",
            "status": f"✔ {ok_cnt}" + (f"  ✘ {err_cnt}" if err_cnt else ""),
            "ok":     ok_cnt,
            "err":    err_cnt,
            "dir":    out_dir,
        })

    # ── окна настроек и доната ────────────────────────────────────────────────

    def _open_settings(self):
        """Открывает модальное окно настроек."""
        win = tk.Toplevel(self)
        win.title(self.t("settings_title"))
        win.resizable(False, False)
        win.configure(bg=BG)
        win.transient(self)
        win.grab_set()

        try:
            win.iconbitmap(resource_path("icon.ico"))
        except Exception:
            pass

        ww, wh = 300, 185
        win.update_idletasks()
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
        win.geometry(f"{ww}x{wh}+{(sw - ww) // 2}+{(sh - wh) // 2}")

        settings_title_lbl = tk.Label(win, text=self.t("settings_title"),
                                      font=("Segoe UI", 12, "bold"), bg=BG, fg=FG)
        settings_title_lbl.pack(pady=(18, 12))

        row = tk.Frame(win, bg=BG)
        row.pack(padx=24, fill="x")

        lang_lbl = tk.Label(row, text=self.t("settings_lang"),
                            font=("Segoe UI", 10), bg=BG, fg=FG2)
        lang_lbl.pack(side="left")

        lang_names = list(LANGUAGES.values())
        cb = ttk.Combobox(row, values=lang_names, width=14,
                          state="readonly", font=("Segoe UI", 10))
        cb.set(LANGUAGES[self._lang])
        cb.pack(side="right")

        # Чекбокс "Запоминать настройки"
        remember_row = tk.Frame(win, bg=BG, cursor="hand2")
        remember_row.pack(padx=24, fill="x", pady=(12, 0))

        remember_lbl = tk.Label(remember_row, text=self.t("settings_remember"),
                                font=("Segoe UI", 10), bg=BG, fg=FG2, cursor="hand2")
        remember_lbl.pack(side="left")

        BOX = 16
        chk_canvas = tk.Canvas(remember_row, width=BOX, height=BOX,
                               bg=BG, bd=0, highlightthickness=0, cursor="hand2")
        chk_canvas.pack(side="left", padx=(8, 0))

        def _draw_checkbox():
            chk_canvas.delete("all")
            checked = self._remember_settings.get()
            chk_canvas.create_rectangle(1, 1, BOX-1, BOX-1,
                                        outline=ACCENT if checked else FG3,
                                        fill=ACCENT if checked else BG, width=1)
            if checked:
                chk_canvas.create_line(3, 8, 6, 12, fill="#fff", width=2)
                chk_canvas.create_line(6, 12, 13, 4, fill="#fff", width=2)

        def _toggle_checkbox(e=None):
            self._remember_settings.set(not self._remember_settings.get())
            _draw_checkbox()
            self._save_settings()

        _draw_checkbox()

        for w in (remember_row, remember_lbl, chk_canvas):
            w.bind("<Button-1>", _toggle_checkbox)

        def on_lang_select(e):
            selected_name = cb.get()
            for code, name in LANGUAGES.items():
                if name == selected_name:
                    self._lang = code
                    self._save_settings()
                    self._update_ui_strings()
                    win.title(self.t("settings_title"))
                    settings_title_lbl.config(text=self.t("settings_title"))
                    lang_lbl.config(text=self.t("settings_lang"))
                    remember_lbl.config(text=self.t("settings_remember"))
                    cl.config(text=self.t("settings_close"))
                    break

        cb.bind("<<ComboboxSelected>>", on_lang_select)

        cl = tk.Label(win, text=self.t("settings_close"),
                      font=("Segoe UI", 10), bg=BG, fg=FG2, cursor="hand2")
        cl.pack(pady=(20, 0))
        cl.bind("<Button-1>", lambda e: win.destroy())
        cl.bind("<Enter>",    lambda e: cl.config(fg=FG))
        cl.bind("<Leave>",    lambda e: cl.config(fg=FG2))

    def _donate(self):
        win = tk.Toplevel(self)
        win.title(self.t("donate_title"))
        # Уменьшаем высоту окна, так как полей с кошельками больше нет
        win.geometry("500x300")
        win.configure(bg=BG)
        win.transient(self)
        win.grab_set()

        win.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 500) // 2
        y = self.winfo_y() + (self.winfo_height() - 300) // 2
        win.geometry(f"+{x}+{y}")
        
        tk.Label(win, text="♥", font=("Segoe UI", 28), bg=BG, fg=HEART_RED).pack(pady=(16, 2))
        tk.Label(win, text=self.t("donate_sub"),
                 font=("Segoe UI", 12, "bold"), bg=BG, fg=FG).pack()
 
        tk.Label(win, text=self.t("donate_desc"), font=("Segoe UI", 10),
                 bg=BG, fg=FG, justify="center").pack(pady=15)

        def _open_wallets():
            webbrowser.open("https://github.com/cyber-anderson/Formatix#-support-the-author")
            win.destroy()  # Окно закроется после открытия браузера (можно убрать, если не нужно)

        # Новая кнопка в стиле кнопки "Конвертировать" (как в _btn)
        btn = tk.Button(win, text=self.t("donate_btn"),
                        font=("Segoe UI", 11, "bold"),
                        bg=ACCENT, fg="#fff", activebackground=ACCENT2,
                        activeforeground="#fff", relief="flat", padx=20, pady=9,
                        command=_open_wallets, cursor="hand2")
        
        # Эффекты наведения для кнопки как в остальном интерфейсе
        btn.bind("<Enter>", lambda e, w=btn: w.config(bg=ACCENT2, fg="#fff"))
        btn.bind("<Leave>", lambda e, w=btn: w.config(bg=ACCENT, fg="#fff"))
        btn.pack(pady=10)

        cl = tk.Label(win, text=self.t("donate_close"),
                      font=("Segoe UI", 10), bg=BG, fg=FG2, cursor="hand2")
        cl.pack(pady=(15, 10))
        cl.bind("<Button-1>", lambda e: win.destroy())
        cl.bind("<Enter>",    lambda e: cl.config(fg=FG))
        cl.bind("<Leave>",    lambda e: cl.config(fg=FG2))

if __name__ == "__main__":
    App().mainloop()
