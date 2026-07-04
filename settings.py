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

"""Диалоговые окна «Настройки» и «Донат».

В отличие от compare_window.py и converter.py, эти окна очень плотно
завязаны на состояние главного окна приложения (язык, тема, сохранённые
настройки, шаблон имени файла и т.д.) — здесь нет смысла притворяться,
что модуль полностью независим. Вместо этого используется тот же приём,
что и раньше для CompareWindow: главное окно (App) передаётся явным
аргументом `app`, а palette цветов текущей темы — словарём `colors`,
вместо чтения глобальных констант напрямую. Это позволяет модулю не
зависеть от имени/структуры главного файла и не создавать циклический
импорт.

Ожидаемые ключи `colors`:
    BG, BG2, BG3, CARD, FG, FG2, FG3, ACCENT, ACCENT2, BORDER, HEART_RED,
    CARD_TINT (акцентно-тонированный фон для карточки «Свой шаблон»)

Ожидаемые атрибуты/методы `app` (главного окна):
    app.t(key)                  — перевод строки
    app._lang, app._theme       — текущий язык/тема
    app._save_settings()        — сохранение настроек на диск
    app._update_ui_strings()    — обновление текстов главного окна при смене языка
    app._remember_settings      — tk.BooleanVar
    app._filename_preset        — tk.StringVar (пресет имени файла)
    app._filename_tokens        — список токенов пользовательского шаблона
    app._btn(parent, text, cmd, dim=False) — фабрика стилизованных кнопок
"""

import tkinter as tk
from tkinter import ttk, simpledialog
import os
import sys
import webbrowser

from localization import LANGUAGES
from converter import render_filename_template, sanitize_filename_part


def resource_path(relative_path):
    """Получает абсолютный путь к ресурсам, работает для разработки и для PyInstaller.

    Небольшое дублирование с одноимённой функцией в главном файле — она
    слишком мала и слишком общая (просто обёртка над sys._MEIPASS), чтобы
    заводить ради неё ещё один модуль или тянуть сюда зависимость от
    имени главного файла.
    """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def open_settings_window(app, colors):
    """Открывает модальное окно настроек.

    app — экземпляр главного окна (App): нужен для доступа к языку, теме,
    сохранённым настройкам и методам-хелперам (app.t(), app._btn(), ...).
    colors — словарь текущей палитры темы (BG, FG, ACCENT и т.д.).
    """
    BG, BG2, BG3, CARD = colors["BG"], colors["BG2"], colors["BG3"], colors["CARD"]
    FG, FG2, FG3 = colors["FG"], colors["FG2"], colors["FG3"]
    ACCENT, ACCENT2, BORDER = colors["ACCENT"], colors["ACCENT2"], colors["BORDER"]
    CARD_TINT = colors["CARD_TINT"]

    win = tk.Toplevel(app)
    win.withdraw()   # скрываем, пока не соберём содержимое и не посчитаем реальный размер
    win.title(app.t("settings_title"))
    win.resizable(False, False)
    win.configure(bg=BG)
    win.transient(app)
    win.grab_set()

    try:
        win.iconbitmap(resource_path("icon.ico"))
    except Exception:
        pass

    ww = 360

    def _fit_window():
        """Пересчитывает высоту окна под текущее содержимое, сохраняя позицию."""
        win.update_idletasks()
        req_h = win.winfo_reqheight()
        win.geometry(f"{ww}x{req_h}+{win.winfo_x()}+{win.winfo_y()}")

    settings_title_lbl = tk.Label(win, text=app.t("settings_title"),
                                  font=("Segoe UI", 12, "bold"), bg=BG, fg=FG)
    settings_title_lbl.pack(pady=(18, 12))

    row = tk.Frame(win, bg=BG)
    row.pack(padx=24, fill="x")

    lang_lbl = tk.Label(row, text=app.t("settings_lang"),
                        font=("Segoe UI", 10), bg=BG, fg=FG2)
    lang_lbl.pack(side="left")

    lang_names = list(LANGUAGES.values())
    cb = ttk.Combobox(row, values=lang_names, width=14,
                      state="readonly", font=("Segoe UI", 10))
    cb.set(LANGUAGES[app._lang])
    cb.pack(side="right")

    # Выбор темы
    theme_row = tk.Frame(win, bg=BG)
    theme_row.pack(padx=24, fill="x", pady=(10, 0))

    theme_lbl = tk.Label(theme_row, text=app.t("settings_theme"),
                         font=("Segoe UI", 10), bg=BG, fg=FG2)
    theme_lbl.pack(side="left")

    theme_names = [app.t("theme_dark"), app.t("theme_light")]
    theme_keys  = ["dark", "light"]
    theme_cb = ttk.Combobox(theme_row, values=theme_names, width=14,
                            state="readonly", font=("Segoe UI", 10))
    theme_cb.set(app.t("theme_dark") if app._theme == "dark" else app.t("theme_light"))
    theme_cb.pack(side="right")

    # Уведомление о необходимости перезапуска — появляется только когда нужно
    restart_note = tk.Label(win, text="",
                            font=("Segoe UI", 8), bg=BG, fg=ACCENT2,
                            wraplength=260, justify="center")
    # .pack()/.pack_forget() управляются в _show_restart_note()

    def _show_restart_note(show):
        if show:
            restart_note.pack(fill="x", padx=24, pady=(6, 0), before=fn_sep)
        else:
            restart_note.pack_forget()
        _fit_window()

    def on_theme_select(e):
        selected_name = theme_cb.get()
        idx = theme_names.index(selected_name)
        new_theme = theme_keys[idx]
        if new_theme != app._theme:
            app._theme = new_theme
            app._save_settings()
            restart_note.config(text=app.t("theme_restart_note"))
            _show_restart_note(True)
        else:
            restart_note.config(text="")
            _show_restart_note(False)

    theme_cb.bind("<<ComboboxSelected>>", on_theme_select)

    # Чекбокс "Запоминать настройки"
    remember_row = tk.Frame(win, bg=BG, cursor="hand2")
    remember_row.pack(padx=24, fill="x", pady=(12, 0))

    remember_lbl = tk.Label(remember_row, text=app.t("settings_remember"),
                            font=("Segoe UI", 10), bg=BG, fg=FG2, cursor="hand2")
    remember_lbl.pack(side="left")

    BOX = 16
    chk_canvas = tk.Canvas(remember_row, width=BOX, height=BOX,
                           bg=BG, bd=0, highlightthickness=0, cursor="hand2")
    chk_canvas.pack(side="left", padx=(8, 0))

    def _draw_checkbox():
        chk_canvas.delete("all")
        checked = app._remember_settings.get()
        chk_canvas.create_rectangle(1, 1, BOX-1, BOX-1,
                                    outline=ACCENT if checked else FG3,
                                    fill=ACCENT if checked else BG, width=1)
        if checked:
            chk_canvas.create_line(3, 8, 6, 12, fill="#fff", width=2)
            chk_canvas.create_line(6, 12, 13, 4, fill="#fff", width=2)

    def _toggle_checkbox(e=None):
        app._remember_settings.set(not app._remember_settings.get())
        _draw_checkbox()
        app._save_settings()

    _draw_checkbox()

    for w in (remember_row, remember_lbl, chk_canvas):
        w.bind("<Button-1>", _toggle_checkbox)

    def on_lang_select(e):
        selected_name = cb.get()
        for code, name in LANGUAGES.items():
            if name == selected_name:
                app._lang = code
                app._save_settings()
                app._update_ui_strings()
                win.title(app.t("settings_title"))
                settings_title_lbl.config(text=app.t("settings_title"))
                lang_lbl.config(text=app.t("settings_lang"))
                remember_lbl.config(text=app.t("settings_remember"))
                theme_lbl.config(text=app.t("settings_theme"))
                theme_names_new = [app.t("theme_dark"), app.t("theme_light")]
                theme_cb.config(values=theme_names_new)
                theme_cb.set(theme_names_new[0] if app._theme == "dark" else theme_names_new[1])
                theme_names[:] = theme_names_new

                fn_title.config(text=app.t("settings_filename_lbl"))
                fn_preset_cb.config(values=[app.t(f"fn_preset_{pk}") for pk in PRESET_KEYS])
                fn_preset_cb.current(PRESET_KEYS.index(app._filename_preset.get()))
                builder_head_lbl.config(text=app.t("fn_preset_custom"))
                btn_name.config(text=app.t("fn_add_name"))
                btn_index.config(text=app.t("fn_add_index"))
                btn_date.config(text=app.t("fn_add_date"))
                btn_text.config(text=app.t("fn_add_text"))
                btn_clear.config(text=app.t("fn_clear"))
                preview_caption.config(text=app.t("fn_preview_lbl"))
                _render_chips()
                _update_preview()

                if restart_note.cget("text") != "":
                    restart_note.config(text=app.t("theme_restart_note"))
                    _fit_window()
                break

    cb.bind("<<ComboboxSelected>>", on_lang_select)

    # ── ИМЯ ФАЙЛА ────────────────────────────────────────────────────────
    fn_sep = tk.Frame(win, bg=BORDER, height=1)
    fn_sep.pack(fill="x", padx=24, pady=(14, 10))

    fn_title = tk.Label(win, text=app.t("settings_filename_lbl"),
                        font=("Segoe UI", 10, "bold"), bg=BG, fg=FG2)
    fn_title.pack(padx=24, anchor="w")

    fn_preset_row = tk.Frame(win, bg=BG)
    fn_preset_row.pack(padx=24, fill="x", pady=(6, 0))

    PRESET_KEYS = ["original", "number", "date", "custom"]

    fn_preset_cb = ttk.Combobox(fn_preset_row, state="readonly",
                                font=("Segoe UI", 9))
    fn_preset_cb.pack(fill="x")

    # ── Карточка "Свой шаблон" (появляется только при этом пресете) ───────
    # Фон CARD_TINT (акцентно-тонированный, не нейтрально-серый) выбран
    # специально, чтобы белые (CARD) кнопки токенов не сливались с карточкой.
    builder_card = tk.Frame(win, bg=CARD_TINT, highlightthickness=1,
                            highlightbackground=BORDER, highlightcolor=BORDER)
    # .pack() вызывается динамически в _refresh_builder_state()

    builder_head = tk.Frame(builder_card, bg=CARD_TINT)
    builder_head.pack(fill="x", padx=10, pady=(9, 0))
    builder_head_lbl = tk.Label(builder_head, text=app.t("fn_preset_custom"),
                                font=("Segoe UI", 9, "bold"), bg=CARD_TINT, fg=ACCENT)
    builder_head_lbl.pack(side="left")

    builder_frame = tk.Frame(builder_card, bg=CARD_TINT)
    builder_frame.pack(fill="x", padx=10, pady=(6, 10))

    btn_row1 = tk.Frame(builder_frame, bg=CARD_TINT)
    btn_row1.pack(fill="x")
    btn_name  = app._btn(btn_row1, app.t("fn_add_name"),  lambda: _add_token("name"), light=True)
    btn_index = app._btn(btn_row1, app.t("fn_add_index"), lambda: _add_token("index"), light=True)
    btn_date  = app._btn(btn_row1, app.t("fn_add_date"),  lambda: _add_token("date"), light=True)
    for b in (btn_name, btn_index, btn_date):
        b.pack(side="left", padx=(0, 4))

    btn_row2 = tk.Frame(builder_frame, bg=CARD_TINT)
    btn_row2.pack(fill="x", pady=(4, 0))
    btn_text  = app._btn(btn_row2, app.t("fn_add_text"), lambda: _add_token("text"), light=True)
    btn_clear = app._btn(btn_row2, app.t("fn_clear"), lambda: _clear_tokens(), dim=True)
    btn_text.pack(side="left", padx=(0, 4))
    btn_clear.pack(side="left")

    chips_container = tk.Frame(builder_frame, bg=CARD, height=30)
    chips_container.pack(fill="x", pady=(8, 0))
    chips_container.pack_propagate(False)
    chips_inner = tk.Frame(chips_container, bg=CARD)
    chips_inner.pack(anchor="w", padx=6, pady=4)

    # ── Предпросмотр ────────────────────────────────────────────────────
    preview_row = tk.Frame(win, bg=BG)
    preview_row.pack(padx=24, fill="x", pady=(10, 18))
    preview_caption = tk.Label(preview_row, text=app.t("fn_preview_lbl"),
                               font=("Segoe UI", 8), bg=BG, fg=FG3)
    preview_caption.pack(side="left")
    preview_val = tk.Label(preview_row, text="", font=("Consolas", 9, "bold"),
                           bg=BG, fg=FG)
    preview_val.pack(side="left", padx=(6, 0))

    _EXAMPLE_BASE = "photo"
    _EXAMPLE_EXT  = ".jpg"

    def _update_preview():
        k = app._filename_preset.get()
        ex_name = render_filename_template(
            _EXAMPLE_BASE, 1, k, app._filename_tokens) + _EXAMPLE_EXT
        preview_val.config(text=ex_name)

    def _render_chips():
        for w in chips_inner.winfo_children():
            w.destroy()
        if not app._filename_tokens:
            tk.Label(chips_inner, text=app.t("fn_empty_hint"),
                    font=("Segoe UI", 8), bg=CARD, fg=FG3).pack(side="left")
            return
        chip_style = {
            "name":  (ACCENT, "#ffffff", lambda tok: app.t("fn_add_name")),
            "index": (ACCENT2, "#ffffff", lambda tok: app.t("fn_add_index")),
            "date":  (BG2, FG2, lambda tok: app.t("fn_add_date")),
            "text":  (BG3, FG2, lambda tok: tok.get("value", "")),
        }
        for idx, tok in enumerate(app._filename_tokens):
            bg_c, fg_c, text_fn = chip_style.get(tok.get("type"), (BG3, FG2, lambda t: "?"))
            chip = tk.Label(chips_inner, text=f"{text_fn(tok)} ✕",
                            font=("Segoe UI", 8, "bold"), bg=bg_c, fg=fg_c,
                            padx=6, pady=2, cursor="hand2")
            chip.pack(side="left", padx=(0, 4))
            chip.bind("<Button-1>", lambda e, i=idx: _remove_token(i))

    def _refresh_builder_state():
        is_custom = (app._filename_preset.get() == "custom")
        if is_custom:
            builder_card.pack(padx=24, fill="x", pady=(10, 0), before=preview_row)
        else:
            builder_card.pack_forget()
        _fit_window()

    def _select_preset(key):
        app._filename_preset.set(key)
        idx = PRESET_KEYS.index(key)
        if fn_preset_cb.current() != idx:
            fn_preset_cb.current(idx)
        _refresh_builder_state()
        _update_preview()
        app._save_settings()

    def _on_preset_select(e=None):
        idx = fn_preset_cb.current()
        if 0 <= idx < len(PRESET_KEYS):
            _select_preset(PRESET_KEYS[idx])

    fn_preset_cb.bind("<<ComboboxSelected>>", _on_preset_select)

    def _add_token(kind):
        if app._filename_preset.get() != "custom":
            return
        if kind == "text":
            val = simpledialog.askstring(
                app.t("settings_filename_lbl"), app.t("fn_custom_text_prompt"), parent=win)
            if not val:
                return
            val = sanitize_filename_part(val)
            if not val:
                return
            app._filename_tokens.append({"type": "text", "value": val})
        else:
            app._filename_tokens.append({"type": kind})
        _render_chips()
        _update_preview()
        app._save_settings()

    def _remove_token(idx):
        if 0 <= idx < len(app._filename_tokens):
            del app._filename_tokens[idx]
            _render_chips()
            _update_preview()
            app._save_settings()

    def _clear_tokens():
        if app._filename_preset.get() != "custom":
            return
        app._filename_tokens.clear()
        _render_chips()
        _update_preview()
        app._save_settings()

    # Начальная отрисовка секции под уже восстановленные настройки
    fn_preset_cb.config(values=[app.t(f"fn_preset_{k}") for k in PRESET_KEYS])
    cur_key = app._filename_preset.get()
    if cur_key not in PRESET_KEYS:
        cur_key = "original"
    fn_preset_cb.current(PRESET_KEYS.index(cur_key))
    _render_chips()
    _refresh_builder_state()
    _update_preview()

    # Показываем окно только теперь, когда всё содержимое собрано —
    # чтобы сразу выставить размер под реальный контент, без лишних пустот
    win.update_idletasks()
    req_h = win.winfo_reqheight()
    x = app.winfo_x() + (app.winfo_width() - ww) // 2
    y = app.winfo_y() + (app.winfo_height() - req_h) // 2
    win.geometry(f"{ww}x{req_h}+{x}+{y}")
    win.deiconify()


def open_donate_window(app, colors):
    """Открывает окно с призывом поддержать проект.

    app — экземпляр главного окна (App). colors — словарь палитры темы.
    """
    BG, FG, FG2 = colors["BG"], colors["FG"], colors["FG2"]
    ACCENT, ACCENT2 = colors["ACCENT"], colors["ACCENT2"]
    HEART_RED = colors["HEART_RED"]

    win = tk.Toplevel(app)
    win.title(app.t("donate_title"))
    # Уменьшаем высоту окна, так как полей с кошельками больше нет
    win.geometry("500x300")
    win.configure(bg=BG)
    win.transient(app)
    win.grab_set()

    win.update_idletasks()
    x = app.winfo_x() + (app.winfo_width() - 500) // 2
    y = app.winfo_y() + (app.winfo_height() - 300) // 2
    win.geometry(f"+{x}+{y}")

    tk.Label(win, text="♥", font=("Segoe UI", 28), bg=BG, fg=HEART_RED).pack(pady=(16, 2))
    tk.Label(win, text=app.t("donate_sub"),
             font=("Segoe UI", 12, "bold"), bg=BG, fg=FG).pack()

    tk.Label(win, text=app.t("donate_desc"), font=("Segoe UI", 10),
             bg=BG, fg=FG, justify="center").pack(pady=15)

    def _open_wallets():
        webbrowser.open("https://github.com/cyber-anderson/Formatix#%EF%B8%8F-support-the-project")
        win.destroy()  # Окно закроется после открытия браузера (можно убрать, если не нужно)

    # Новая кнопка в стиле кнопки "Конвертировать" (как в _btn)
    btn = tk.Button(win, text=app.t("donate_btn"),
                    font=("Segoe UI", 11, "bold"),
                    bg=ACCENT, fg="#fff", activebackground=ACCENT2,
                    activeforeground="#fff", relief="flat", padx=20, pady=9,
                    command=_open_wallets, cursor="hand2")

    # Эффекты наведения для кнопки как в остальном интерфейсе
    btn.bind("<Enter>", lambda e, w=btn: w.config(bg=ACCENT2, fg="#fff"))
    btn.bind("<Leave>", lambda e, w=btn: w.config(bg=ACCENT, fg="#fff"))
    btn.pack(pady=(10, 24))

