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
from tkinter import ttk, filedialog, messagebox, simpledialog
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
import time
from PIL import Image, ImageTk

# Compare и FancySlider — в compare.py
from compare import Compare, FancySlider

# Локализация (языки, строки переводов, автоопределение языка системы)
from localization import LANGUAGES, STRINGS, detect_system_lang, APP_NAME

# Окна "Настройки" и "Донат" — в settings.py
from settings import open_settings_window, open_donate_window

# Проверка обновлений через GitHub Releases API — в update.py
from update import fetch_latest_release, is_newer

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

# Определение доступности форматов (HEIF/AVIF/SVG) и логика конвертации — в converter.py
from converter import (
    HEIF_AVAILABLE, AVIF_AVAILABLE, SVG_AVAILABLE, FORMATS, IMG_EXTS,
    format_size, get_file_size_str, get_svg_resolution_pure,
    load_pil_for_display, get_image_res_str,
    sanitize_filename_part, render_filename_template, generate_unique_filename,
    convert_one,
)

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


def detect_system_theme():
    r"""Определяет текущую тему оформления системы (светлая/тёмная).

    Порядок проверки:
    1. Windows — реестр AppsUseLightTheme (HKCU\...\Personalize)
    2. macOS — defaults read -g AppleInterfaceStyle
    3. Linux — надёжного универсального способа нет, по умолчанию "dark"

    Возвращает "dark" или "light".
    """
    if sys.platform == "win32":
        try:
            import winreg
            with winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize") as key:
                value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            # 1 — светлая тема приложений, 0 — тёмная
            return "light" if value == 1 else "dark"
        except Exception:
            pass

    elif sys.platform == "darwin":
        try:
            result = subprocess.run(
                ["defaults", "read", "-g", "AppleInterfaceStyle"],
                capture_output=True, text=True, timeout=2)
            # Ключ существует и равен "Dark" только в тёмном режиме;
            # в светлом режиме ключа нет вовсе (ненулевой returncode)
            if result.returncode == 0 and "dark" in result.stdout.lower():
                return "dark"
            return "light"
        except Exception:
            pass

    return "dark"


# ── палитра ───────────────────────────────────────────────────────────────────
# Тёмная тема — оригинальные цвета, без изменений
THEME_DARK = {
    "BG": "#0f0f1a", "BG2": "#181825", "BG3": "#1e1e2e", "CARD": "#232336",
    "ACCENT": "#c678dd", "ACCENT2": "#ff6b9d", "HEART_RED": "#ff3366",
    "GREEN": "#a8ff78", "FG": "#cdd6f4", "FG2": "#6c7086", "FG3": "#45475a",
    "BORDER": "#313244", "CARD_TINT": "#1c1530",
}

# Светлая тема — тот же оттенок акцента (фиолетово-розовый), но на светлом фоне
THEME_LIGHT = {
    "BG": "#fafafc", "BG2": "#f0f0f5", "BG3": "#e6e6ee", "CARD": "#ffffff",
    "ACCENT": "#9c4dcc", "ACCENT2": "#e0457f", "HEART_RED": "#e0304f",
    "GREEN": "#4a9a1f", "FG": "#1e1e2e", "FG2": "#5c5c70", "FG3": "#b8b8c8",
    "BORDER": "#d4d4dc", "CARD_TINT": "#f3e9fb",
}

THEMES = {"dark": THEME_DARK, "light": THEME_LIGHT}

# Тема читается из настроек до отрисовки UI — переключение требует перезапуска,
# так как сотни виджетов создаются один раз со значениями этих констант.
# При первом запуске (ключа "theme" в настройках ещё нет) определяем системную
# тему автоматически — по аналогии с detect_system_lang() для языка.
_settings_snapshot = load_settings()
if "theme" in _settings_snapshot:
    ACTIVE_THEME = _settings_snapshot["theme"]
else:
    ACTIVE_THEME = detect_system_theme()
if ACTIVE_THEME not in THEMES:
    ACTIVE_THEME = "dark"
_palette = THEMES[ACTIVE_THEME]

BG      = _palette["BG"]
BG2     = _palette["BG2"]
BG3     = _palette["BG3"]
CARD    = _palette["CARD"]
ACCENT  = _palette["ACCENT"]
ACCENT2 = _palette["ACCENT2"]
HEART_RED = _palette["HEART_RED"]
GREEN   = _palette["GREEN"]
FG      = _palette["FG"]
FG2     = _palette["FG2"]
FG3     = _palette["FG3"]
BORDER  = _palette["BORDER"]
CARD_TINT = _palette["CARD_TINT"]

VERSION  = "1.15.0"


def strip_v_prefix(version_str):
    """Убирает необязательный префикс v/V у номера версии (теги GitHub releases
    обычно вида "v1.18.0", а VERSION хранится без него) — чтобы v{old} → v{new}
    не задваивал "v" независимо от того, есть ли префикс в исходной строке."""
    return version_str.lstrip("vV") if version_str else version_str

# Не проверяем обновления чаще раза в сутки — незачем дёргать GitHub API
# на каждый запуск, а лимит анонимных запросов (60/час на IP) и без того
# спокойно выдерживает проверку раз в день на любое число пользователей.
UPDATE_CHECK_INTERVAL_SEC = 24 * 60 * 60

# Константы анимации сердечка
_HEART_BEAT1_MS   = 120
_HEART_BEAT2_MS   = 250
_HEART_BEAT3_MS   = 370
_HEART_MIN_IDLE   = 1800
_HEART_MAX_IDLE   = 2600


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


class SegmentedToggle(tk.Frame):
    """Компактный переключатель на 2 позиции — рисуется на Canvas.
    По умолчанию прямоугольный (radius=0); при radius>0 углы скругляются
    через сглаженный полигон (в tkinter нет нативной поддержки round-corner).
    Используется для переключения режима качества между "% качества" и
    "целевой размер файла".

    Не хранит состояние сам — целиком управляется извне через переданную
    tk.StringVar (variable): подписывается на её изменения через trace и
    перерисовывается, а по клику вызывает command(new_value), не трогая
    variable напрямую — актуальное значение всегда выставляет вызывающий код.
    Это исключает рассинхронизацию между «что нарисовано» и «что сохранено»,
    даже если variable меняется откуда-то ещё, а не только кликом.
    """

    def __init__(self, parent, options, variable, command=None,
                 width=76, height=20, font=("Segoe UI", 8, "bold"), radius=0):
        super().__init__(parent, bg=BG2)
        self._segments = list(options)   # [(value, label), (value, label)]
        self._variable = variable
        self._command  = command
        self._width    = width
        self._height   = height
        self._radius   = radius
        self._font     = font
        self._enabled  = True

        self.canvas = tk.Canvas(self, width=width, height=height,
                                bg=BG2, highlightthickness=0, cursor="hand2")
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self._on_click)
        self._variable.trace_add("write", lambda *a: self._redraw())
        self._redraw()

    def _round_rect(self, x1, y1, x2, y2, r, **kw):
        """Скруглённый прямоугольник через сглаженный полигон (smooth=True)."""
        r = max(0, r)
        pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
               x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
        return self.canvas.create_polygon(pts, smooth=True, **kw)

    def _draw_shape(self, x1, y1, x2, y2, **kw):
        """Прямоугольник (radius=0) или скруглённый прямоугольник (radius>0)."""
        if self._radius > 0:
            return self._round_rect(x1, y1, x2, y2, self._radius, **kw)
        return self.canvas.create_rectangle(x1, y1, x2, y2, **kw)

    def set_labels(self, options):
        """Обновляет подписи сегментов (для смены языка интерфейса),
        сохраняя привязанные к ним значения."""
        self._segments = list(options)
        self._redraw()

    def _active_index(self):
        cur = self._variable.get()
        for i, (val, _label) in enumerate(self._segments):
            if val == cur:
                return i
        return 0

    def _redraw(self):
        c = self.canvas
        c.delete("all")
        w, h = self._width, self._height

        # Рамка-«трек» на всю ширину
        self._draw_shape(1, 1, w - 1, h - 1, fill=BG3, outline=BORDER, width=1)

        n     = len(self._segments)
        seg_w = w / n
        idx   = self._active_index()

        # Заливка активного сегмента
        indicator_color = ACCENT if self._enabled else BG2
        self._draw_shape(idx * seg_w + 1, 1, (idx + 1) * seg_w - 1, h - 1,
                         fill=indicator_color, outline="")

        # Разделитель между сегментами
        for i in range(1, n):
            x = i * seg_w
            c.create_line(x, 1, x, h - 1, fill=BORDER)

        active_fg   = "#ffffff" if self._enabled else FG3
        inactive_fg = FG3
        for i, (_val, label) in enumerate(self._segments):
            cx = (i + 0.5) * seg_w
            c.create_text(cx, h / 2, text=label,
                          fill=(active_fg if i == idx else inactive_fg), font=self._font)

    def _on_click(self, event):
        if not self._enabled:
            return
        n     = len(self._segments)
        seg_w = self._width / n
        idx   = min(max(int(event.x // seg_w), 0), n - 1)
        new_val = self._segments[idx][0]
        if self._command:
            self._command(new_val)

    def set_enabled(self, enabled: bool):
        """Включает/выключает интерактивность и визуально приглушает виджет."""
        self._enabled = enabled
        self.canvas.config(cursor="hand2" if enabled else "arrow")
        self._redraw()


# ── ГЛАВНОЕ ОКНО ──────────────────────────────────────────────────────────────
BaseClass = TkinterDnD.Tk if HAS_DND else tk.Tk


class App(BaseClass):
    """Главное окно приложения Formatix Image Converter."""

    def __init__(self):
        super().__init__()

        # Мьютекс для защиты совместно используемых данных между потоками
        self._data_lock = threading.Lock()

        self._settings = load_settings()
        if "lang" in self._settings:
            self._lang = self._settings["lang"]
        else:
            self._lang = detect_system_lang()
        # Тема уже применена на уровне модуля (см. ACTIVE_THEME) до создания
        # окна — здесь просто запоминаем текущее значение для отображения в UI.
        self._theme = ACTIVE_THEME
        # Флаг "запоминать настройки" — хранится всегда, независимо от самого флага
        self._remember_settings = tk.BooleanVar(
            value=self._settings.get("remember_settings", True))
        # Автопроверка обновлений — как lang/theme, не зависит от remember_settings
        self._check_updates = tk.BooleanVar(
            value=self._settings.get("check_updates", True))
        self._last_update_check = self._settings.get("last_update_check", 0)
        self._update_available  = None  # (tag, url) после найденного обновления, иначе None
        self.VERSION = VERSION  # доступно settings.py без импорта из этого модуля

        self.title(APP_NAME)
        self.geometry("1150x720")
        self.minsize(1150, 640)
        self.configure(bg=BG)

        try:
            ico_path = resource_path("icon.ico")
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
            pass

        self._files           = []
        self._results         = []
        self._out_dir         = tk.StringVar(value="")
        self._running         = False
        self._stop_requested  = False
        self._compare_win     = None  # ссылка на открытое окно сравнения
        self._converted_cache = {}
        self._total_src_bytes = 0
        self._total_dst_bytes = 0
        self._gui_queue       = queue.Queue()
        # Кэш результатов get_svg_resolution_pure по пути файла: path → (w, h).
        # Без него _has_svg_without_size() заново читала бы с диска и парсила
        # КАЖДЫЙ SVG в списке при каждом _upd() (на каждый Add/Drop/смену
        # языка), даже если ни один из этих SVG не менялся — на больших
        # списках это ощутимо подвешивало UI. Сбрасывается в _clear().
        self._svg_size_cache  = {}
        # Увеличивается на каждый новый запуск конвертации и при «Очистить»
        # во время активной конвертации. Воркер штампует каждое сообщение в
        # очередь своим batch_id — _listen_queue игнорирует сообщения с
        # устаревшим batch_id, чтобы результаты «осиротевшего» (уже
        # очищенного пользователем) запуска не оживали в UI задним числом.
        self._batch_id        = 0

        # Шаблон имени выходного файла: preset — один из "original"/"number"/
        # "date"/"custom"; tokens — список токенов для пресета "custom", каждый
        # {"type": "name"|"index"|"date"|"text", "value": "..." (только для text)}.
        self._filename_preset = tk.StringVar(value="original")
        self._filename_tokens = []

        self._loading = True  # блокирует _save_settings во время инициализации
        self._style_ttk()
        self._build()
        self._bind_sort_commands()

        remember = self._settings.get("remember_settings", True)
        if remember:
            saved_fmt  = self._settings.get("fmt", "AVIF")
            saved_qual = self._settings.get("quality", 85)
            if saved_fmt in FORMATS:
                self._fmt.set(saved_fmt)
            self._qual.set(saved_qual)
            # Восстанавливаем режим качества (% / целевой размер файла)
            saved_qmode = self._settings.get("quality_mode", "percent")
            if saved_qmode in ("percent", "size"):
                self._quality_mode.set(saved_qmode)
            saved_target_val = self._settings.get("target_size_val", 500)
            if isinstance(saved_target_val, int) and saved_target_val > 0:
                self._target_size_val.set(str(saved_target_val))
            saved_target_unit = self._settings.get("target_size_unit", "KB")
            if saved_target_unit in ("KB", "MB"):
                self._target_size_unit.set(saved_target_unit)
            self._refresh_quality_mode_ui()
            # Восстанавливаем режим изменения разрешения
            saved_resize_key = self._settings.get("resize_mode_key", "no_change")
            saved_resize_loc = self._key_to_localized_mode(saved_resize_key)
            if saved_resize_loc in self._resize_modes_localized():
                self._resize_mode.set(saved_resize_loc)
                self._on_resize_mode_changed()
            # Восстанавливаем папку сохранения
            saved_out_dir = self._settings.get("out_dir", "")
            if saved_out_dir and os.path.isdir(saved_out_dir):
                self._out_dir.set(saved_out_dir)
                self._dir_lbl.config(fg=FG)
            # Восстанавливаем шаблон имени выходного файла
            saved_fn_preset = self._settings.get("filename_preset", "original")
            if saved_fn_preset in ("original", "number", "date", "custom"):
                self._filename_preset.set(saved_fn_preset)
            saved_fn_tokens = self._settings.get("filename_tokens", [])
            if isinstance(saved_fn_tokens, list):
                self._filename_tokens = [
                    t for t in saved_fn_tokens
                    if isinstance(t, dict) and t.get("type") in ("name", "index", "date", "text")
                ]

        self._loading = False  # восстановление завершено, теперь сохранять можно

        # Применяем состояние слайдера для любого восстановленного формата
        self.after(10, self._on_format_changed)

        self._status.set(self.t("ready"))
        self._listen_queue()
        self._heart_hovered = False
        self._animate_heart_pulse()

        if HAS_DND:
            self._reg_dnd_root()

        # Небольшая задержка, чтобы не конкурировать с отрисовкой стартового экрана
        self.after(1500, self._maybe_check_updates)

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
        try:
            self._settings["quality_mode"]    = self._quality_mode.get()
        except AttributeError:
            pass
        try:
            target_val = self._target_size_val.get()
            if target_val.isdigit():
                self._settings["target_size_val"] = int(target_val)
        except AttributeError:
            pass
        try:
            self._settings["target_size_unit"] = self._target_size_unit.get()
        except AttributeError:
            pass
        try:
            self._settings["filename_preset"] = self._filename_preset.get()
        except AttributeError:
            pass
        try:
            self._settings["filename_tokens"] = list(self._filename_tokens)
        except AttributeError:
            pass
        try:
            out_dir_val = self._out_dir.get()
            # Сохраняем только реальный путь, не плейсхолдер
            if out_dir_val and os.path.isdir(out_dir_val):
                self._settings["out_dir"] = out_dir_val
            else:
                self._settings["out_dir"] = ""
        except AttributeError:
            pass

        self._settings["lang"]              = self._lang
        self._settings["theme"]             = getattr(self, "_theme", "dark")
        self._settings["remember_settings"] = self._remember_settings.get()
        self._settings["check_updates"]     = self._check_updates.get()
        self._settings["last_update_check"] = self._last_update_check

        # На диск пишем всегда — но если remember выключен,
        # очищаем fmt/quality/resize/out_dir из того что запишем
        to_write = dict(self._settings)
        if not self._remember_settings.get():
            to_write.pop("fmt", None)
            to_write.pop("quality", None)
            to_write.pop("resize_mode_key", None)
            to_write.pop("out_dir", None)
            to_write.pop("filename_preset", None)
            to_write.pop("filename_tokens", None)
        save_settings(to_write)

    # ── проверка обновлений ──────────────────────────────────────────────────

    def _maybe_check_updates(self):
        """Запускает фоновую проверку обновлений, если это разрешено настройками
        и с прошлой проверки прошло не меньше UPDATE_CHECK_INTERVAL_SEC.

        Вызывается один раз при старте (см. конец __init__), полностью молча —
        ни отсутствие сети, ни отключённая настройка не показывают пользователю
        никаких сообщений об ошибке.
        """
        if not self._check_updates.get():
            return
        if time.time() - self._last_update_check < UPDATE_CHECK_INTERVAL_SEC:
            return
        threading.Thread(target=self._update_check_worker, daemon=True).start()

    def _update_check_worker(self):
        """Фоновый поток автопроверки: сетевой запрос не должен блокировать GUI."""
        result = fetch_latest_release()
        self._last_update_check = time.time()
        self.after(0, self._save_settings)
        if result:
            tag, url = result
            if is_newer(tag, VERSION):
                self.after(0, lambda: self._show_update_available(tag, url))

    def _check_updates_now(self, on_result):
        """Проверка обновлений по клику "Проверить сейчас" в настройках.

        В отличие от _maybe_check_updates, игнорирует интервал между проверками
        (это явное действие пользователя) и не зависит от значения _check_updates.
        on_result вызывается в GUI-потоке с одним из статусов:
        "update" (tag, url — версия и ссылка на релиз), "uptodate", "error".
        """
        def worker():
            result = fetch_latest_release()
            self._last_update_check = time.time()
            self.after(0, self._save_settings)
            if result is None:
                self.after(0, lambda: on_result("error"))
                return
            tag, url = result
            if is_newer(tag, VERSION):
                self.after(0, lambda: self._show_update_available(tag, url))
                self.after(0, lambda: on_result("update", tag, url))
            else:
                self.after(0, lambda: on_result("uptodate"))
        threading.Thread(target=worker, daemon=True).start()

    def _show_update_available(self, tag, url):
        """Подсвечивает версию в шапке окна найденным обновлением (GUI-поток)."""
        self._update_available = (tag, url)
        self._ver_lbl.config(text=self.t("update_ver_label").format(
            old=strip_v_prefix(VERSION), new=strip_v_prefix(tag)), fg=ACCENT2)
        for seq in ("<Button-1>", "<Enter>", "<Leave>"):
            self._ver_lbl.unbind(seq)
        self._ver_lbl.bind("<Button-1>", lambda e: webbrowser.open(url))
        self._ver_lbl.bind("<Enter>", lambda e: self._ver_lbl.config(fg=ACCENT))
        self._ver_lbl.bind("<Leave>", lambda e: self._ver_lbl.config(fg=ACCENT2))

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
        self._ver_lbl = _ver_lbl

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

        self._compare_btn = self._btn(br, self.t("compare_btn"), self._open_compare)
        self._compare_btn.pack(side="left", padx=(6, 0))

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
        self._fmt = tk.StringVar(value="AVIF")
        _fmt_cb = ttk.Combobox(_fmt_wf, textvariable=self._fmt, values=FORMATS,
                               width=7, state="readonly", font=("Segoe UI", 10))
        _fmt_cb.pack()
        _fmt_cb.bind("<<ComboboxSelected>>", self._on_format_changed)

        # КАЧЕСТВО (два режима: по проценту качества ИЛИ по целевому размеру файла)
        _qual_blk = tk.Frame(ctrl_row, bg=BG2)
        _qual_blk.pack(side="left", anchor="n", padx=(0, 16))

        _qual_lbl_row = tk.Frame(_qual_blk, bg=BG2)
        _qual_lbl_row.pack(anchor="w")
        self._quality_lbl = tk.Label(_qual_lbl_row, text=self.t("quality_lbl"),
                                     font=("Segoe UI", 10, "bold"), bg=BG2, fg=FG2)
        self._quality_lbl.pack(side="left")

        # Переключатель режима — прямоугольная кнопка-тумблер (SegmentedToggle)
        # сразу справа от заголовка блока: «КАЧЕСТВО [% | Размер]».
        self._quality_mode = tk.StringVar(value="percent")
        self._qmode_toggle = SegmentedToggle(
            _qual_lbl_row,
            options=[("percent", self.t("qmode_percent")), ("size", self.t("qmode_size"))],
            variable=self._quality_mode,
            command=self._set_quality_mode,
            width=94)   # было 76 (по умолчанию) — не хватало места под "Размер"
        self._qmode_toggle.pack(side="left", padx=(8, 0))

        _qual_wf = tk.Frame(_qual_blk, bg=BG2)
        _qual_wf.pack(anchor="w", pady=(4, 0))

        self._qual = tk.IntVar(value=85)
        self._qual.trace_add("write", lambda *a: self._save_settings())
        self._qual_slider = FancySlider(_qual_wf, from_=10, to=100, variable=self._qual, width=190,
                                        bg2=BG2, accent=ACCENT, bg3=BG3, fg3=FG3)
        self._qual_slider.pack()

        # Целевой размер: поле ввода числа + единицы (KB/MB). Скрыто, пока
        # активен режим "по проценту" — показывается через _refresh_quality_mode_ui.
        self._target_size_frame = tk.Frame(_qual_wf, bg=BG2)
        self._target_size_val = tk.StringVar(value="500")
        self._target_size_val.trace_add("write", self._on_target_size_write)
        self._e_target_size = tk.Entry(
            self._target_size_frame, textvariable=self._target_size_val,
            font=("Segoe UI", 10, "bold"), bg=ACCENT, fg="#fff", width=5,
            bd=0, justify="center", insertbackground="#fff")
        self._e_target_size.pack(side="left", ipady=1)
        self._e_target_size.bind("<Double-Button-1>", self._select_all_entry)
        self._e_target_size.bind("<Control-a>",       self._ctrl_a_entry)
        self._e_target_size.bind("<Control-A>",       self._ctrl_a_entry)

        self._target_size_unit = tk.StringVar(value="KB")
        self._target_size_unit.trace_add("write", lambda *a: self._save_settings())
        self._cb_target_unit = ttk.Combobox(
            self._target_size_frame, textvariable=self._target_size_unit,
            values=["KB", "MB"], width=4, state="readonly", font=("Segoe UI", 9))
        self._cb_target_unit.pack(side="left", padx=(4, 0))

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
        self._refresh_quality_mode_ui()

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
        self._cbtn.bind("<Enter>", self._on_cbtn_enter)
        self._cbtn.bind("<Leave>", self._on_cbtn_leave)

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

    def _reorder_paired_list(self, old_order, paired_list, paired_tree, heading_cols):
        """Применяет ту же перестановку строк к «парному» списку/дереву.

        self._files и self._results связаны по индексу: элемент i одного
        списка должен соответствовать элементу i другого (исходный файл и
        его результат конвертации). Если отсортировать только одну из двух
        таблиц по заголовку столбца, эта связь молча ломается — окно
        сравнения и переключение ◀/▶ в нём начнут показывать случайные
        пары. Чтобы этого не происходило, при сортировке одной таблицы мы
        синхронно переставляем строки второй той же самой перестановкой.

        old_order — список старых индексов в новом порядке: old_order[i] —
        индекс, который теперь оказался на позиции i.

        Если длины списков расходятся (например, конвертация ещё не
        запускалась, или файлы добавлялись уже после неё) — синхронизировать
        нечего, строгого 1:1 соответствия и так не было; в этом случае
        просто выходим, не трогая парный список.
        """
        if len(paired_list) != len(old_order):
            return

        new_paired = [paired_list[i] for i in old_order]
        paired_list[:] = new_paired

        children = paired_tree.get_children()
        if len(children) != len(old_order):
            return
        for new_pos, old_pos in enumerate(old_order):
            paired_tree.move(children[old_pos], "", new_pos)

        # Парное дерево было переставлено «вынужденно», а не по своему
        # столбцу — сбрасываем его собственный индикатор сортировки, чтобы
        # стрелка в заголовке не врала о реальном порядке строк.
        paired_tree._sort_state = {}
        for col, base_text in heading_cols.items():
            paired_tree.heading(col, text=base_text)

    def _bind_sort_commands(self):
        """Привязывает команды сортировки к заголовкам обоих деревьев.
        Вызывается после _build и после смены языка."""
        # ── Исходные файлы ────────────────────────────────────────────────────
        def _sort_src(col_id):
            if self._running:
                return  # не сортируем во время конвертации — индексы могут съехать
            asc = not self._tv_src._sort_state.get(col_id, True)
            self._tv_src._sort_state = {col_id: asc}

            # Собираем четвёрки (значение_для_сортировки, iid, путь, старый_индекс)
            rows = []
            for iid in self._tv_src.get_children():
                idx = self._tv_src.index(iid)
                val = self._tv_src.set(iid, col_id)
                path = self._files[idx] if idx < len(self._files) else ""
                rows.append((val, iid, path, idx))

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

            # Перемещаем строки в дереве и синхронизируем self._files,
            # запоминая перестановку (old_order) для парного списка результатов
            old_order = []
            new_files = []
            for i, (_, iid, path, old_idx) in enumerate(rows):
                self._tv_src.move(iid, "", i)
                new_files.append(path)
                old_order.append(old_idx)
            self._files[:] = new_files

            # Поддерживаем парность с self._results: переставляем результаты
            # той же перестановкой, чтобы self._files[i] и self._results[i]
            # по-прежнему относились к одному и тому же файлу.
            self._reorder_paired_list(old_order, self._results, self._tv_dst, {
                "status": self.t("col_status"), "name": self.t("col_filename"),
                "res":    self.t("col_res"),    "size": self.t("col_size"),
            })

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
                rows.append((val, iid, res_entry, tags, all_vals, idx))

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

            old_order = []
            new_results = []
            for i, (_, iid, res_entry, _, __, old_idx) in enumerate(rows):
                self._tv_dst.move(iid, "", i)
                new_results.append(res_entry)
                old_order.append(old_idx)
            self._results[:] = new_results

            # Поддерживаем парность с self._files той же перестановкой
            self._reorder_paired_list(old_order, self._files, self._tv_src, {
                "name": self.t("col_filename"),
                "res":  self.t("col_res"), "size": self.t("col_size"),
            })

            arrow = "▲" if asc else "▼"
            for c in ("status", "name", "res", "size"):
                base = {"status": self.t("col_status"),
                        "name":   self.t("col_filename"),
                        "res":    self.t("col_res"),
                        "size":   self.t("col_size")}[c]
                self._tv_dst.heading(c, text=base + (" " + arrow if c == col_id else ""))

        for c in ("status", "name", "res", "size"):
            self._tv_dst.heading(c, command=lambda col=c: _sort_dst(col))

    def _btn(self, p, text, cmd, accent=False, big=False, dim=False, light=False):
        """Создаёт стилизованную кнопку.

        light=True — текст берётся из FG (яркий, как основные подписи в
        интерфейсе) вместо приглушённого FG2. Используется там, где обычный
        FG2 плохо читается на нестандартном фоне (например, на карточке
        «Свой шаблон» в настройках).
        """
        bn  = ACCENT if accent else CARD
        fn  = "#fff"  if accent else (FG3 if dim else (FG if light else FG2))
        bh  = ACCENT2 if accent else BG3
        fnt = ("Segoe UI", 11, "bold") if big else ("Segoe UI", 10)
        px, py = (20, 9) if big else (11, 5)
        # На светлой теме не-accent кнопки при hover используют тёмный текст
        # (BG3 светло-серый, белый текст на нём нечитаем)
        fh = "#fff" if (accent or ACTIVE_THEME == "dark") else FG
        b = tk.Button(p, text=text, command=cmd, font=fnt, bg=bn, fg=fn,
                      activebackground=bh, activeforeground=fh,
                      relief="flat", bd=0, padx=px, pady=py, cursor="hand2")
        b.bind("<Enter>", lambda e, w=b, _fh=fh: w.config(bg=bh, fg=_fh) if w["state"] != "disabled" else None)
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

        if hasattr(self, "_qual_slider"):
            self._refresh_quality_mode_ui()

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

    # ── режим качества: "% качества" ⇄ "целевой размер файла" ──────────────────

    def _set_quality_mode(self, mode):
        """Переключает режим блока КАЧЕСТВО между ползунком % и целевым размером."""
        if self._quality_mode.get() == mode:
            return
        self._quality_mode.set(mode)
        self._refresh_quality_mode_ui()
        self._save_settings()

    def _refresh_quality_mode_ui(self):
        """Показывает нужный виджет (слайдер или поле размера) согласно
        активному режиму. Также блокирует переключатель и оба виджета,
        если для текущего формата параметр качества не применяется вовсе
        (PNG/BMP/TIFF/ICO)."""
        mode              = self._quality_mode.get()
        quality_matters   = self._fmt.get() in ("JPEG", "WEBP", "HEIC", "AVIF")

        if mode == "percent":
            self._target_size_frame.pack_forget()
            self._qual_slider.pack()
        else:
            self._qual_slider.pack_forget()
            self._target_size_frame.pack()

        self._qual_slider.set_enabled(quality_matters and mode == "percent")
        self._qmode_toggle.set_enabled(quality_matters)

        target_state = "normal" if quality_matters else "disabled"
        self._e_target_size.config(
            state=target_state,
            bg=ACCENT if quality_matters else BG3,
            fg="#fff" if quality_matters else FG3)
        self._cb_target_unit.config(state=("readonly" if quality_matters else "disabled"))

    def _on_target_size_write(self, *args):
        """Разрешает вводить только цифры и ограничивает разумным максимумом."""
        val = self._target_size_val.get()
        if val == "":
            return
        if not val.isdigit():
            cleaned = "".join(c for c in val if c.isdigit())
            self._target_size_val.set(cleaned)
            return
        n = int(val)
        if n > 999999:
            self._target_size_val.set("999999")
            return
        self._save_settings()

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
            self._save_settings()

    def _clear_dir(self):
        """Сбрасывает папку сохранения."""
        self._out_dir.set(self.t("folder_placeholder"))
        self._dir_lbl.config(fg=FG2)
        self._settings.pop("out_dir", None)
        self._save_settings()

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
        new_paths = []
        for p in self.tk.splitlist(e.data):
            p = p.strip()
            if p and p not in self._files:
                if os.path.splitext(p)[1].lower() in IMG_EXTS:
                    self._files.append(p)
                    new_paths.append(p)
                    try:
                        self._total_src_bytes += os.path.getsize(p)
                    except Exception:
                        pass
                    # Добавляем мгновенно с "..." — разрешение загрузится фоново
                    self._tv_src.insert("", "end", iid=p, values=(
                        os.path.basename(p), "...", get_file_size_str(p)))
        self._upd()
        if new_paths:
            threading.Thread(target=self._load_resolutions,
                             args=(new_paths,), daemon=True).start()

    # ── управление списком файлов ─────────────────────────────────────────────

    def _add(self):
        """Открывает диалог добавления файлов."""
        files = filedialog.askopenfilenames(
            filetypes=[("Images", "*.jpg *.jpeg *.png *.webp *.bmp *.tiff *.gif *.ico"
                        + (" *.avif" if AVIF_AVAILABLE else "")
                        + (" *.heic *.heif" if HEIF_AVAILABLE else "")
                        + (" *.svg" if SVG_AVAILABLE else "")),
                       ("All", "*.*")])
        new_paths = []
        for f in files:
            if f not in self._files:
                self._files.append(f)
                new_paths.append(f)
                try:
                    self._total_src_bytes += os.path.getsize(f)
                except Exception:
                    pass
                # Добавляем мгновенно с "..." — разрешение загрузится фоново
                self._tv_src.insert("", "end", iid=f, values=(
                    os.path.basename(f), "...", get_file_size_str(f)))
        self._upd()
        if new_paths:
            threading.Thread(target=self._load_resolutions,
                             args=(new_paths,), daemon=True).start()

    def _load_resolutions(self, paths):
        """Фоновый поток: загружает разрешения файлов и обновляет Treeview."""
        for path in paths:
            try:
                res = get_image_res_str(path)
            except Exception:
                res = "—"
            # Обновляем строку в Treeview через gui_queue чтобы не трогать UI из потока
            self._gui_queue.put({
                "action": "update_src_res",
                "iid":    path,
                "res":    res,
            })

    def _clear(self):
        """Очищает списки файлов и результатов.

        Если в этот момент идёт конвертация, физически прервать фоновый
        поток мгновенно нельзя — он продолжит работать до своей следующей
        проверки self._stop_requested. Поэтому помимо самой остановки мы
        увеличиваем self._batch_id: все сообщения, которые «осиротевший»
        воркер всё ещё отправит в self._gui_queue, окажутся подписаны
        старым batch_id и будут проигнорированы в _listen_queue — иначе
        строки результатов уже отменённой конвертации «оживали» бы в только
        что очищенном списке.
        """
        if self._running:
            self._stop_requested = True
            self._batch_id += 1
            self._running = False
            self._cbtn.config(state="normal", text=self.t("convert_btn"))
            self._open_dir_btn.config(fg=FG3)

        with self._data_lock:
            self._files.clear()
            self._converted_cache.clear()
        self._svg_size_cache.clear()
        self._results.clear()
        self._total_src_bytes = 0
        self._total_dst_bytes = 0
        for item in self._tv_src.get_children():
            self._tv_src.delete(item)
        for item in self._tv_dst.get_children():
            self._tv_dst.delete(item)
        self._prog["value"] = 0
        self._status.set(self.t("cleared"))
        self._status_err.set("")
        self._clbl.config(text="")
        self._upd()

    def _has_svg_without_size(self):
        """Проверяет, есть ли в списке SVG-файлы, у которых не удалось определить разрешение.

        Результат get_svg_resolution_pure кэшируется по пути файла
        (self._svg_size_cache), чтобы не перечитывать с диска и не
        парсить регуляркой ВСЕ SVG в списке при каждом вызове — раньше
        это происходило на каждый Add/Drop/смену языка и подвешивало UI
        пропорционально количеству SVG в списке.
        """
        if not SVG_AVAILABLE:
            return False
        for p in self._files:
            if os.path.splitext(p)[1].lower() == ".svg":
                if p in self._svg_size_cache:
                    w, h = self._svg_size_cache[p]
                else:
                    w, h = get_svg_resolution_pure(p)
                    self._svg_size_cache[p] = (w, h)
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
        elif self._lang == "de":
            # В немецком всего две формы: единственное и множественное число.
            s = "Datei" if n == 1 else "Dateien"
            self._clbl.config(text=f"{n} {s}")
        elif self._lang == "zh":
            # В китайском у существительных нет грамматического числа —
            # форма "个文件" не меняется в зависимости от количества.
            self._clbl.config(text=f"{n} 个文件")
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

        # Если уже найдено обновление, метка версии показывает не "vX.X.X",
        # а текст из update_ver_label — его тоже нужно перевести
        if self._update_available:
            tag, _url = self._update_available
            self._ver_lbl.config(text=self.t("update_ver_label").format(
                old=strip_v_prefix(VERSION), new=strip_v_prefix(tag)))

        self._add_btn.config(text=self.t("add"))
        self._clear_btn.config(text=self.t("clear"))

        self._compare_btn.config(text=self.t("compare_btn"))

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
        self._qmode_toggle.set_labels([
            ("percent", self.t("qmode_percent")), ("size", self.t("qmode_size"))])
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

        # Если открыто окно сравнения — обновляем язык в нём
        if self._compare_win is not None:
            try:
                if self._compare_win.winfo_exists():
                    self._compare_win.update_lang()
                else:
                    self._compare_win = None
            except Exception:
                self._compare_win = None

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

    def _open_compare(self):
        """Открывает окно сравнения с умной логикой выбора пары.

        1. Нет файлов совсем → сообщение "Файлы для сравнения отсутствуют"
        2. Файлы есть, ничего не выделено → открываем первую пару
        3. Выделен только исходный → берём результат с тем же индексом
        4. Выделен только результат → берём исходный с тем же индексом
        5. Выделены оба → используем оба как есть (даже если не пара)
        """
        # ── Пункт 1: нет файлов совсем ───────────────────────────────────────
        has_src = len(self._files) > 0
        # Есть ли хотя бы один успешный результат
        has_dst = any(ok and dst and os.path.exists(dst)
                      for dst, ok in self._results)
        if not has_src or not has_dst:
            messagebox.showinfo(APP_NAME, self.t("compare_no_files"))
            return

        sel_src = self._tv_src.selection()
        sel_dst = self._tv_dst.selection()

        # ── Определяем idx_src ───────────────────────────────────────────────
        if sel_src:
            idx_src = self._tv_src.index(sel_src[0])
        elif sel_dst:
            # Пункт 4: выделен результат — берём исходный с тем же индексом
            idx_src = self._tv_dst.index(sel_dst[0])
        else:
            # Пункт 2: ничего не выделено — первая пара
            idx_src = 0

        # ── Определяем idx_dst ───────────────────────────────────────────────
        # forced_dst_sel: True если пользователь явно выделил результат 
        # ИЛИ исходный файл (в обоих случаях ожидается конкретная пара)
        forced_dst_sel = bool(sel_dst) or bool(sel_src)
        if sel_dst:
            idx_dst = self._tv_dst.index(sel_dst[0])
        elif sel_src:
            # Пункт 3: выделен исходный — результат с тем же индексом
            idx_dst = self._tv_src.index(sel_src[0])
        else:
            # Пункт 2: ничего не выделено — первая пара
            idx_dst = 0

        def _nearest_valid_dst(start):
            for i in range(start, len(self._results)):
                dst, ok = self._results[i]
                if ok and dst and os.path.exists(dst):
                    return i, dst
            for i in range(0, start):
                dst, ok = self._results[i]
                if ok and dst and os.path.exists(dst):
                    return i, dst
            return None, None

        if idx_dst >= len(self._results):
            idx_dst = 0
        dst_path, ok = self._results[idx_dst]
        if not ok or not dst_path or not os.path.exists(dst_path):
            # Пользователь принудительно выбрал файл с ошибкой — сообщаем
            if forced_dst_sel:
                messagebox.showwarning(APP_NAME, self.t("compare_no_files"))
                return
            # Автоматический выбор — тихо ищем ближайший валидный
            idx_dst, dst_path = _nearest_valid_dst(idx_dst)
            if dst_path is None:
                messagebox.showinfo(APP_NAME, self.t("compare_no_files"))
                return
            # Синхронизируем индекс исходника с найденным рабочим результатом,
            # чтобы открылась правильная пара файлов
            idx_src = idx_dst

        # Проверяем исходный файл
        if idx_src >= len(self._files):
            idx_src = 0
        src_path = self._files[idx_src]
        if not os.path.exists(src_path):
            messagebox.showinfo(APP_NAME, self.t("compare_no_files"))
            return

        self._compare_win = Compare(self, src_path, dst_path,
                                          self.t("compare_title"), BG, BG2, BG3,
                                          FG, FG2, FG3, ACCENT, BORDER, CARD,
                                          index=idx_src)

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

    def _on_cbtn_enter(self, e=None):
        """При наведении: подсвечиваем кнопку + показываем 'Остановить' во время конвертации."""
        if self._cbtn["state"] != "disabled":
            self._cbtn.config(bg=ACCENT2, fg="#fff")
        if self._running and not self._stop_requested:
            self._cbtn.config(text=self.t("stop_btn"))

    def _on_cbtn_leave(self, e=None):
        """При уходе мыши: возвращаем обычный цвет + текст 'Обработка...'."""
        if self._cbtn["state"] != "disabled":
            self._cbtn.config(bg=ACCENT, fg="#fff")
        if self._running and not self._stop_requested:
            self._cbtn.config(text=self.t("processing_btn"))

    def _toggle_stop(self):
        """Устанавливает флаг остановки — воркер завершит текущие задачи и выйдет."""
        self._stop_requested = True
        self._cbtn.config(text=self.t("processing_btn"))  # убрать hover-текст

    def _start(self):
        """Валидирует параметры и запускает фоновый поток конвертации."""
        if self._running:
            self._toggle_stop()
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

        # Если активен режим "целевой размер файла" — валидируем и переводим в байты
        quality_mode = self._quality_mode.get()
        target_bytes = None
        if quality_mode == "size" and self._fmt.get() in ("JPEG", "WEBP", "HEIC", "AVIF"):
            try:
                target_size_num = int(self._target_size_val.get())
                if target_size_num <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror(APP_NAME, self.t("warn_bad_target_size"))
                return
            unit = self._target_size_unit.get()
            target_bytes = target_size_num * (1024 * 1024 if unit == "MB" else 1024)

        # Снимок шаблона имени файла — как и quality_mode/fmt выше, читаем из
        # GUI-переменных один раз здесь; дальше и проверка конфликтов, и сама
        # конвертация работают только с этим снимком, а не с self._filename_*.
        filename_preset = self._filename_preset.get()
        filename_tokens = [dict(t) for t in self._filename_tokens]

        out_dir = self._out_dir.get()
        if not out_dir or not os.path.isdir(out_dir):
            out_dir = filedialog.askdirectory(title=self.t("save_folder"))
            if not out_dir:
                return
            self._out_dir.set(out_dir)
            self._dir_lbl.config(fg=FG)
            self._save_settings()

        fmt_now            = self._fmt.get()
        ext_now            = ".jpg" if fmt_now == "JPEG" else f".{fmt_now.lower()}"
        if quality_mode == "size" and target_bytes:
            q_part = f"tgt:{target_bytes}"
        else:
            q_part = f"q:{self._qual.get()}"
        fn_part = f"fn:{filename_preset}:{filename_tokens}"
        current_config_str = (f"fmt:{fmt_now}|{q_part}|dir:{out_dir}"
                              f"|mode:{mode_key}|w:{target_w}|h:{target_h}|{fn_part}")

        # Проверяем конфликты по «чистому» имени (без суффикса _1, _2 и т.д.)
        # _generate_unique_filename здесь использовать нельзя — она сама
        # уходит от конфликта и диалог никогда не показывается.
        existing       = []
        seen_basenames = set()
        for i, p in enumerate(self._files, start=1):
            orig_base  = os.path.splitext(os.path.basename(p))[0]
            base_name  = render_filename_template(orig_base, i, filename_preset, filename_tokens)
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
        self._stop_requested = False
        self._cbtn.config(text=self.t("processing_btn"))
        self._prog["value"] = 0
        self.update_idletasks()

        # Делаем снимок списка файлов, чтобы фоновый поток работал
        # с неизменяемой копией и не было race condition.
        with self._data_lock:
            files_snapshot = list(self._files)

        # Новый batch_id «подписывает» все сообщения этого запуска — если
        # пользователь нажмёт «Очистить» во время конвертации, _clear()
        # увеличит batch_id и все дальнейшие сообщения этого воркера будут
        # проигнорированы как устаревшие (см. _listen_queue).
        self._batch_id += 1
        batch_id = self._batch_id

        threading.Thread(
            target=self._convert_worker,
            args=(files_snapshot, out_dir,
                  self._fmt.get(), self._qual.get(),
                  mode_key, target_w, target_h,
                  self._overwrite_confirmed, batch_id,
                  quality_mode, target_bytes,
                  filename_preset, filename_tokens),
            daemon=True).start()

    # ── очередь событий GUI ───────────────────────────────────────────────────

    def _listen_queue(self):
        """Опрашивает очередь от фонового потока и обновляет UI."""
        try:
            while True:
                task   = self._gui_queue.get_nowait()
                action = task.get("action")

                # insert_result/progress/finish помечены batch_id того запуска,
                # который их породил. Если пользователь успел нажать «Очистить»
                # во время конвертации, self._batch_id уже увеличен — значит
                # это сообщения «осиротевшего» воркера и их нужно отбросить,
                # иначе они задним числом оживят уже очищенные списки.
                if action in ("insert_result", "progress", "finish"):
                    if task.get("batch_id") != self._batch_id:
                        self._gui_queue.task_done()
                        continue

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

                elif action == "update_src_res":
                    # Обновляем разрешение в левой таблице после фоновой загрузки
                    iid = task["iid"]
                    try:
                        if self._tv_src.exists(iid):
                            vals = list(self._tv_src.item(iid, "values"))
                            vals[1] = task["res"]
                            self._tv_src.item(iid, values=vals)
                    except Exception:
                        pass

                elif action == "progress":
                    self._status.set(task["status"])
                    self._prog["value"] = task["prog_val"]

                elif action == "finish":
                    if task.get("stopped"):
                        self._status.set(f"■  {task['ok']}" + (f"  ✘ {task['err']}" if task["err"] else ""))
                        self._status_lbl.config(fg=FG2)
                    else:
                        self._status.set(f"✔ {task['ok']}")
                        self._status_lbl.config(fg=GREEN)
                    self._status_err.set(f"✘ {task['err']}" if task["err"] else "")
                    self._cbtn.config(state="normal", text=self.t("convert_btn"))
                    # Подсвечиваем кнопку «Открыть папку» как успешную только если
                    # хотя бы один файл реально сконвертировался — иначе кнопка
                    # выглядела зелёной (как при успехе) даже при 100% ошибок.
                    self._open_dir_btn.config(fg=GREEN if task["ok"] > 0 else FG3)
                    self._running = False
                    self._stop_requested = False

                self._gui_queue.task_done()
        except queue.Empty:
            pass
        self.after(100, self._listen_queue)

    # ── конвертация (фоновый поток) ───────────────────────────────────────────

    def _convert_worker(self, files_snapshot, out_dir, fmt, quality, mode_key,
                        target_w, target_h, allow_overwrite=False, batch_id=0,
                        quality_mode="percent", target_bytes=None,
                        filename_preset="original", filename_tokens=None):
        """Фоновый рабочий поток: конвертирует все файлы параллельно.

        batch_id штампуется на каждое сообщение в self._gui_queue — это
        позволяет _listen_queue отличить сообщения текущего запуска от
        сообщений уже отменённого пользователем через «Очистить» запуска.
        """
        # fmt, quality, mode_key переданы из GUI-потока как снимок значений —
        # не читаем self._fmt / self._qual / self._resize_mode из фонового потока.
        ext        = ".jpg" if fmt == "JPEG" else f".{fmt.lower()}"
        resize_key = mode_key  # уже языконезависимый ключ, декодирование не нужно
        total      = len(files_snapshot)
        filename_tokens = filename_tokens or []

        ok_cnt = err_cnt = 0
        done   = 0

        # Ключ кэша учитывает target_bytes (а не quality) в режиме "целевой
        # размер" — иначе кэш не заметит смену лимита. Шаблон имени файла
        # тоже входит в ключ: сам результат от него не зависит, но смена
        # шаблона должна приводить к перезаписи под новым именем, а не к
        # переиспользованию старого закэшированного out_path.
        if quality_mode == "size" and target_bytes:
            q_part = f"tgt:{target_bytes}"
        else:
            q_part = f"q:{quality}"
        fn_part = f"fn:{filename_preset}:{filename_tokens}"
        current_config_str = (f"fmt:{fmt}|{q_part}|dir:{out_dir}"
                              f"|mode:{mode_key}|w:{target_w}|h:{target_h}|{fn_part}")
        workers = min(os.cpu_count() or 4, 8)

        # Предварительное выделение уникальных имён на основе снимка списка.
        # Индекс (i) считается с 1 в порядке текущего списка — им пользуется
        # токен "Номер" в пользовательском шаблоне и пресет "Имя + номер".
        allocated_names = {}
        reserved_names  = set()
        for i, path in enumerate(files_snapshot, start=1):
            orig_base = os.path.splitext(os.path.basename(path))[0]
            base_name = render_filename_template(orig_base, i, filename_preset, filename_tokens)
            allocated_names[path] = generate_unique_filename(
                out_dir, base_name, ext, reserved_names,
                allow_overwrite=allow_overwrite)

        futures          = {}
        results_by_path  = {}
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for path in files_snapshot:
                out_name = allocated_names[path]
                f = pool.submit(convert_one, path, out_dir, fmt, out_name, quality,
                                mode_key, target_w, target_h, current_config_str, resize_key,
                                quality_mode, target_bytes,
                                cache=self._converted_cache, lock=self._data_lock)
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
                    "batch_id": batch_id,
                })
                # Проверяем флаг остановки после каждого завершённого файла
                if self._stop_requested:
                    # Отменяем ещё не запущенные задачи
                    for f in futures:
                        f.cancel()
                    break

        # Вставляем только завершённые результаты (при остановке — частичные)
        for path in files_snapshot:
            if path not in results_by_path:
                continue  # файл не был обработан — пропускаем
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
                "batch_id":   batch_id,
            })

        self._gui_queue.put({
            "action":  "finish",
            "status":  f"✔ {ok_cnt}" + (f"  ✘ {err_cnt}" if err_cnt else ""),
            "ok":      ok_cnt,
            "err":     err_cnt,
            "dir":     out_dir,
            "stopped": self._stop_requested,
            "batch_id": batch_id,
        })

    # ── окна настроек и доната ────────────────────────────────────────────────
    # Сами окна реализованы в settings.py; здесь — обёртки, собирающие
    # палитру текущей темы в словарь и передающие ссылку на себя (app).

    def _open_settings(self):
        """Открывает модальное окно настроек."""
        colors = {"BG": BG, "BG2": BG2, "BG3": BG3, "CARD": CARD,
                  "FG": FG, "FG2": FG2, "FG3": FG3,
                  "ACCENT": ACCENT, "ACCENT2": ACCENT2, "BORDER": BORDER,
                  "HEART_RED": HEART_RED, "CARD_TINT": CARD_TINT}
        open_settings_window(self, colors)

    def _donate(self):
        """Открывает окно с призывом поддержать проект."""
        colors = {"BG": BG, "BG2": BG2, "BG3": BG3, "CARD": CARD,
                  "FG": FG, "FG2": FG2, "FG3": FG3,
                  "ACCENT": ACCENT, "ACCENT2": ACCENT2, "BORDER": BORDER,
                  "HEART_RED": HEART_RED}
        open_donate_window(self, colors)

if __name__ == "__main__":
    App().mainloop()
