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

"""Окно сравнения изображений и вспомогательный виджет-слайдер.

Вынесено в отдельный модуль из основного файла приложения, так как это
самый большой по объёму код кусок интерфейса. Модуль полностью
самодостаточен: не импортирует ничего из главного файла приложения —
все цвета темы передаются явными аргументами при создании виджетов.
Это позволяет подключать его как обычный локальный модуль (PyInstaller
подхватит его автоматически по операторам import и соберёт в один exe).
"""

import tkinter as tk
from tkinter import ttk
import os
from PIL import Image, ImageTk

from converter import load_pil_for_display


class FancySlider(tk.Frame):
    """Ползунок качества с числовым полем ввода.

    Цвета темы передаются явными аргументами (bg2/accent/bg3/fg3), а не
    берутся из глобальных констант — модуль не зависит от главного файла.
    """

    def __init__(self, parent, from_=10, to=100, variable=None, width=180,
                 bg2="#181825", accent="#c678dd", bg3="#1e1e2e", fg3="#45475a",
                 **kw):
        kw.pop("bg", None)
        kw.pop("height", None)
        super().__init__(parent, bg=bg2)
        self._var   = variable or tk.IntVar(value=85)
        self.from_  = from_
        self.to     = to
        self._bg2    = bg2
        self._accent = accent
        self._bg3    = bg3
        self._fg3    = fg3

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
                              bg=self._accent, fg="#fff", width=4,
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
            self.entry.config(state="normal", bg=self._accent, fg="#fff",
                              font=("Segoe UI", 10, "bold"))
            self.entry_var.set(str(self._var.get()))
        else:
            self.scale.config(state="disabled")
            self.entry.config(state="disabled", bg=self._bg3, fg=self._fg3,
                              font=("Consolas", 10, "bold"))
            self.entry_var.set("—")


# ── ОКНО СРАВНЕНИЯ ────────────────────────────────────────────────────────────

# ── ОКНО СРАВНЕНИЯ ────────────────────────────────────────────────────────────

class CompareWindow(tk.Toplevel):
    """Полноэкранное окно сравнения исходного и результирующего изображений.

    Реализует слайдер-разделитель (split-view): пользователь тянет линию
    влево/вправо и видит левую часть (оригинал) и правую (результат).

    Также поддерживает увеличение (ползунок зума 100–400%) и панорамирование.

    Производительность: дорогой ресемплинг (LANCZOS) больших исходных
    изображений выполняется только при открытии окна, при изменении его
    размера и при изменении зума — результат кэшируется в self._src_fit /
    self._dst_fit. При перетаскивании разделителя или панорамировании
    выполняется только дешёвая операция обрезки (crop) уже готовых
    изображений, а объекты на холсте не удаляются и пересоздаются, а лишь
    двигаются/обновляются (coords / itemconfigure). Кроме того, частые
    события <B1-Motion> объединяются через after_idle в один кадр
    перерисовки, чтобы очередь событий не накапливалась и интерфейс не
    "отставал" от курсора.
    """

    _DIVIDER_W = 3   # ширина линии разделителя в пикселях
    _RESIZE_DEBOUNCE_MS = 80  # задержка пересчёта при изменении размера окна / зума
    _ZOOM_MIN_PCT = 100
    _ZOOM_MAX_PCT = 400
    _ZOOM_WHEEL_STEP_PCT = 10  # шаг изменения зума колесом мыши

    def __init__(self, master, src_path, dst_path, title,
                 bg, bg2, bg3, fg, fg2, fg3, accent, border, card, index=0):
        super().__init__(master)
        self.title(title)
        self.configure(bg=bg)
        
        # Разворачиваем окно (максимизируем), оставляя панель задач видимой
        try:
            self.state("zoomed")  # Стандартный способ для Windows
        except tk.TclError:
            self.attributes("-zoomed", True)  # Резервный вариант для Linux

        # Оставляем только закрытие окна по кнопке Escape
        self.bind("<Escape>", lambda e: self.destroy())
        # Переключение между файлами для сравнения — стрелками с клавиатуры
        self.bind("<Left>",  lambda e: self._navigate(-1))
        self.bind("<Right>", lambda e: self._navigate(1))

        self._bg = bg; self._bg2 = bg2; self._bg3 = bg3
        self._fg = fg; self._fg2 = fg2; self._fg3 = fg3
        self._accent = accent; self._border = border; self._card = card
        self._src_path = src_path
        self._dst_path = dst_path

        # Индекс текущей пары "файл / результат" в общих списках главного окна
        # (self.master._files / self.master._results) — используется для
        # переключения на предыдущий/следующий файл кнопками ◀ / ▶.
        self._pair_index = index

        # Имена файлов для подписей
        self._src_name = os.path.basename(src_path)
        self._dst_name = os.path.basename(dst_path)

        # Загружаем изображения
        self._src_pil = self._load_pil(src_path)
        self._dst_pil = self._load_pil(dst_path)

        # Позиция разделителя (0.0 – 1.0 от ширины холста)
        self._split = 0.5
        self._dragging_divider = False
        self._panning_lmb = False

        # Кэш изображений, уже подогнанных под текущий размер холста и зум.
        # Пересчитывается только в _recompute_fit() — НЕ на каждый кадр.
        # При зуме > 100% self._img_w/_img_h могут превышать размер холста —
        # видимая часть (viewport) вычисляется в _redraw() на основе текущего
        # панорамирования (self._pan_x/_pan_y).
        self._src_fit = None
        self._dst_fit = None
        self._img_w = 0
        self._img_h = 0
        self._canvas_w = 0
        self._canvas_h = 0
        # Кэш viewport-параметров последнего _redraw — нужен для корректного
        # хит-теста и зажима разделителя в границы картинки (_on_mouse_move,
        # _on_press, _update_split_from_x).
        self._off_x = 0   # отступ слева до начала картинки (letterbox)
        self._vw    = 0   # ширина видимой части картинки на холсте

        # Зум и панорамирование
        self._zoom = 1.0          # 1.0 = "по размеру окна", максимум — _ZOOM_MAX_PCT/100
        self._zoom_var = tk.IntVar(value=100) # Переменная для FancySlider
        self._zoom_var.trace_add("write", lambda *a: self._on_zoom_var_change())

        self._pan_x = 0.0
        self._pan_y = 0.0
        self._pan_last_x = 0
        self._pan_last_y = 0
        self._zoom_job = None

        # id объектов на холсте — создаются один раз, далее только двигаются
        self._left_item = None
        self._right_item = None
        self._divider_item = None
        self._handle_item = None
        self._handle_text_item = None
        self._lbl_before_bg = None
        self._lbl_before_text = None
        self._lbl_after_bg = None
        self._lbl_after_text = None

        # Ссылки на PhotoImage, чтобы избежать сборки мусора
        self._left_photo = None
        self._right_photo = None

        # Отложенный пересчёт при ресайзе + флаг "кадр уже запланирован"
        self._resize_job = None
        self._redraw_pending = False

        self._build_ui()
        self.after(50, self._recompute_fit_and_redraw)   # ждём финального размера окна

    # ── загрузка ──────────────────────────────────────────────────────────────

    def _load_pil(self, path):
        """Делегирует загрузку в модульную функцию load_pil_for_display.

        Вся логика (SVG, ICC, CMYK) живёт в одном месте и переиспользуется
        другими компонентами без дублирования кода.
        """
        return load_pil_for_display(path)

    # ── построение UI ─────────────────────────────────────────────────────────

    def _build_ui(self):
        # Нижняя панель с заголовком
        top = tk.Frame(self, bg=self._bg2, pady=6)
        tk.Frame(self, bg=self._border, height=1).pack(fill="x", side="bottom")
        top.pack(fill="x", side="bottom")

        self._title_lbl = tk.Label(top, text=f"{self._src_name}   ⇄   {self._dst_name}",
                 font=("Segoe UI", 11, "bold"),
                 bg=self._bg2, fg=self._fg)
        self._title_lbl.pack(side="left", padx=16)

        # Кнопки переключения на предыдущий / следующий файл сравнения —
        # по центру верхней панели.
        nav_frame = tk.Frame(top, bg=self._bg2)
        nav_frame.place(relx=0.5, rely=0.5, anchor="center")

        self._nav_prev_btn = tk.Label(nav_frame, text="◀", font=("Segoe UI", 12, "bold"),
                                      bg=self._bg2, fg=self._fg2, cursor="hand2", padx=10)
        self._nav_prev_btn.pack(side="left")
        self._nav_prev_btn.bind("<Button-1>", lambda e: self._navigate(-1))
        self._nav_prev_btn.bind("<Enter>", lambda e: self._on_nav_hover(self._nav_prev_btn, True))
        self._nav_prev_btn.bind("<Leave>", lambda e: self._on_nav_hover(self._nav_prev_btn, False))

        self._nav_counter_lbl = tk.Label(nav_frame, text="", font=("Segoe UI", 9),
                                         bg=self._bg2, fg=self._fg3, padx=8)
        self._nav_counter_lbl.pack(side="left")

        self._nav_next_btn = tk.Label(nav_frame, text="▶", font=("Segoe UI", 12, "bold"),
                                      bg=self._bg2, fg=self._fg2, cursor="hand2", padx=10)
        self._nav_next_btn.pack(side="left")
        self._nav_next_btn.bind("<Button-1>", lambda e: self._navigate(1))
        self._nav_next_btn.bind("<Enter>", lambda e: self._on_nav_hover(self._nav_next_btn, True))
        self._nav_next_btn.bind("<Leave>", lambda e: self._on_nav_hover(self._nav_next_btn, False))

        self._update_nav_buttons()

        # Ползунок зума (100% – 400%)
        zoom_frame = tk.Frame(top, bg=self._bg2)
        zoom_frame.pack(side="right", padx=(0, 18))

        tk.Label(zoom_frame, text="🔍", font=("Segoe UI", 10),
                 bg=self._bg2, fg=self._fg2).pack(side="left", padx=(0, 4))

        self._zoom_slider = FancySlider(
            zoom_frame, from_=self._ZOOM_MIN_PCT, to=self._ZOOM_MAX_PCT,
            variable=self._zoom_var, width=140,
            bg2=self._bg2, accent=self._accent, bg3=self._bg3, fg3=self._fg3
        )
        self._zoom_slider.pack(side="left")

        self._zoom_lbl = tk.Label(zoom_frame, text="100%", font=("Segoe UI", 9),
                                  bg=self._bg2, fg=self._fg2, width=4, anchor="w")
        self._zoom_lbl.pack(side="left", padx=(6, 0))


        # Основной холст
        self._canvas = tk.Canvas(self, bg=self._bg, highlightthickness=0,
                                 cursor="hand2")
        self._canvas.pack(fill="both", expand=True)

        self._canvas.bind("<Configure>",       self._on_resize)
        self._canvas.bind("<Motion>",          self._on_mouse_move) # Отслеживание движения мыши
        self._canvas.bind("<ButtonPress-1>",   self._on_press)
        self._canvas.bind("<B1-Motion>",       self._on_drag)
        self._canvas.bind("<ButtonRelease-1>", self._on_release)

        # Зум колесом мыши прямо на холсте (Windows/macOS: <MouseWheel>,
        # Linux: <Button-4>/<Button-5>)
        self._canvas.bind("<MouseWheel>", self._on_mousewheel_zoom)
        self._canvas.bind("<Button-4>",   lambda e: self._on_mousewheel_zoom(e, direction=1))
        self._canvas.bind("<Button-5>",   lambda e: self._on_mousewheel_zoom(e, direction=-1))

    # ── события ───────────────────────────────────────────────────────────────

    def _on_resize(self, e):
        # Debounce: при серии событий <Configure> (например, во время плавного
        # изменения размера окна) пересчитываем подогнанные изображения только
        # один раз — после того как пользователь перестал менять размер.
        if self._resize_job is not None:
            self.after_cancel(self._resize_job)
        self._resize_job = self.after(self._RESIZE_DEBOUNCE_MS,
                                       self._recompute_fit_and_redraw)

    def _on_mouse_move(self, e):
        # Если мы уже что-то тянем, курсор не меняем
        if self._dragging_divider or self._panning_lmb:
            return
        cw = self._canvas_w or self._canvas.winfo_width()
        # divider_x — реальное положение линии на холсте (зажатое в картинку)
        divider_x = max(self._off_x,
                        min(self._off_x + self._vw if self._vw else cw,
                            int(cw * self._split)))
        # Курсор-стрелки только если мышь над линией И внутри картинки
        img_left  = self._off_x
        img_right = self._off_x + self._vw if self._vw else cw
        if img_left <= e.x <= img_right and abs(e.x - divider_x) <= 15:
            self._canvas.config(cursor="sb_h_double_arrow")
        else:
            self._canvas.config(cursor="hand2")

    def _on_press(self, e):
        cw = self._canvas_w or self._canvas.winfo_width()
        divider_x = max(self._off_x,
                        min(self._off_x + self._vw if self._vw else cw,
                            int(cw * self._split)))
        img_left  = self._off_x
        img_right = self._off_x + self._vw if self._vw else cw
        # Захват разделителя — только если клик внутри картинки и рядом с линией
        if img_left <= e.x <= img_right and abs(e.x - divider_x) <= 15:
            self._dragging_divider = True
            self._canvas.config(cursor="sb_h_double_arrow")
        else:
            # Иначе начинаем панорамирование (тянем холст)
            self._panning_lmb = True
            self._pan_last_x = e.x
            self._pan_last_y = e.y
            self._canvas.config(cursor="fleur")

    def _on_drag(self, e):
        if self._dragging_divider:
            self._update_split_from_x(e.x)
        elif self._panning_lmb:
            dx = e.x - self._pan_last_x
            dy = e.y - self._pan_last_y
            self._pan_last_x = e.x
            self._pan_last_y = e.y
            self._pan_x -= dx
            self._pan_y -= dy
            self._request_redraw()

    def _on_release(self, e):
        self._dragging_divider = False
        self._panning_lmb = False
        self._on_mouse_move(e) # Обновляем курсор после отпускания

    def _update_split_from_x(self, x):
        cw = self._canvas_w or self._canvas.winfo_width()
        if cw <= 0:
            return
        # Зажимаем x в границы картинки — чтобы _split никогда не кодировал
        # позицию за пределами изображения (letterbox-отступы слева/справа).
        # _off_x и _vw актуальны с последнего _redraw; при первом вызове до
        # первого рендера оба равны 0 и зажатие работает как раньше.
        img_left  = self._off_x
        img_right = self._off_x + self._vw if self._vw else cw
        x_clamped = max(img_left, min(img_right, x))
        self._split = x_clamped / cw
        self._request_redraw()

    # ── переключение между файлами для сравнения ────────────────────────────

    def update_lang(self):
        """Обновляет все надписи окна сравнения при смене языка в App."""
        try:
            # Заголовок окна
            self.title(self.master.t("compare_title"))
            # Подпись с именами файлов не меняется — это имена файлов
            # Подписи BEFORE/AFTER на нижней полосе
            if hasattr(self, "_lbl_before"):
                was = self.master.t("was").replace(":", "").upper()
                self._lbl_before.config(text=f"◀  {was}")
            if hasattr(self, "_lbl_after"):
                became = self.master.t("became").replace(":", "").upper()
                self._lbl_after.config(text=f"{became}  ▶")
            # Перерисовываем canvas чтобы обновить надписи BEFORE/AFTER на изображении
            self._request_redraw()
        except Exception:
            pass

    def _find_pair(self, start_idx, direction):
        """Ищет соседний валидный индекс пары "файл / результат" в указанном
        направлении (-1 — назад, +1 — вперёд), начиная от start_idx (сам
        start_idx не проверяется). Валидной считается пара, где оба файла
        (исходный и результат) существуют, а конвертация была успешной —
        то есть та же логика, что и в App._open_compare().
        Возвращает (idx, src_path, dst_path) или None, если такой пары нет.
        """
        files = getattr(self.master, "_files", [])
        results = getattr(self.master, "_results", [])
        total = min(len(files), len(results))
        i = start_idx + direction
        while 0 <= i < total:
            src = files[i]
            try:
                dst, ok = results[i]
            except (TypeError, ValueError):
                i += direction
                continue
            if ok and dst and src and os.path.exists(dst) and os.path.exists(src):
                return i, src, dst
            i += direction
        return None

    def _navigate(self, direction):
        btn = self._nav_prev_btn if direction < 0 else self._nav_next_btn
        if not getattr(btn, "_enabled", True):
            return
        found = self._find_pair(self._pair_index, direction)
        if found is None:
            return
        idx, src_path, dst_path = found
        self._pair_index = idx
        self._load_pair(src_path, dst_path)

    def _load_pair(self, src_path, dst_path):
        """Загружает новую пару изображений в уже открытое окно сравнения,
        сохраняя текущий зум/панораму/позицию разделителя — удобно для
        быстрого просмотра одного и того же участка на разных файлах.
        """
        self._src_path = src_path
        self._dst_path = dst_path
        self._src_name = os.path.basename(src_path)
        self._dst_name = os.path.basename(dst_path)
        self._src_pil = self._load_pil(src_path)
        self._dst_pil = self._load_pil(dst_path)

        # Сбрасываем кэш подогнанных изображений — пересчитаем под новую пару
        self._src_fit = None
        self._dst_fit = None

        if hasattr(self, "_title_lbl"):
            self._title_lbl.config(text=f"{self._src_name}   ⇄   {self._dst_name}")

        self._update_nav_buttons()
        self._recompute_fit_and_redraw()

    def _update_nav_buttons(self):
        if not hasattr(self, "_nav_prev_btn"):
            return
        has_prev = self._find_pair(self._pair_index, -1) is not None
        has_next = self._find_pair(self._pair_index, 1) is not None
        self._set_nav_btn_state(self._nav_prev_btn, has_prev)
        self._set_nav_btn_state(self._nav_next_btn, has_next)

        files = getattr(self.master, "_files", [])
        results = getattr(self.master, "_results", [])
        total = min(len(files), len(results))
        if total and 0 <= self._pair_index < total:
            self._nav_counter_lbl.config(text=f"{self._pair_index + 1} / {total}")
        else:
            self._nav_counter_lbl.config(text="")

    def _set_nav_btn_state(self, btn, enabled):
        btn._enabled = enabled
        btn.config(fg=self._fg2 if enabled else self._bg3,
                   cursor="hand2" if enabled else "arrow")

    def _on_nav_hover(self, btn, hovering):
        if not getattr(btn, "_enabled", True):
            return
        btn.config(fg=self._fg if hovering else self._fg2)

    # ── зум ───────────────────────────────────────────────────────────────────

    def _on_zoom_var_change(self):
        try:
            pct = float(self._zoom_var.get())
        except (TypeError, ValueError, tk.TclError):
            pct = 100.0
            
        pct = max(self._ZOOM_MIN_PCT, min(self._ZOOM_MAX_PCT, pct))
        self._zoom = pct / 100.0
        if hasattr(self, "_zoom_lbl"):
            self._zoom_lbl.config(text=f"{int(round(pct))}%")

        # Отложенный пересчёт (debounce)
        if self._zoom_job is not None:
            self.after_cancel(self._zoom_job)
        self._zoom_job = self.after(self._RESIZE_DEBOUNCE_MS, self._recompute_fit_and_redraw)

    def _on_mousewheel_zoom(self, e, direction=None):
        if direction is None:
            direction = 1 if e.delta > 0 else -1
        current = self._zoom_var.get()
        new_pct = current + direction * self._ZOOM_WHEEL_STEP_PCT
        new_pct = max(self._ZOOM_MIN_PCT, min(self._ZOOM_MAX_PCT, new_pct))
        self._zoom_var.set(int(round(new_pct))) # Изменение переменной автоматически обновит FancySlider

    def _request_redraw(self):
        """Объединяет частые события движения мыши в один кадр перерисовки.

        Без этого каждое отдельное событие <B1-Motion> ставило бы в очередь
        собственный вызов _redraw(), и при быстром перетаскивании очередь
        событий Tk копится быстрее, чем успевает рисоваться холст — отсюда
        ощутимое "отставание" линии сравнения от курсора. after_idle
        гарантирует, что за один проход цикла обработки событий будет
        выполнена только одна (последняя по времени) перерисовка.
        """
        if self._redraw_pending:
            return
        self._redraw_pending = True
        self.after_idle(self._do_redraw)

    def _do_redraw(self):
        self._redraw_pending = False
        self._redraw()

    # ── пересчёт подогнанных изображений (дорогая операция) ─────────────────────

    def _recompute_fit_and_redraw(self):
        self._resize_job = None
        self._zoom_job = None
        self._recompute_fit()
        self._redraw()

    def _recompute_fit(self):
        """Масштабирует оригинальные изображения под текущий размер холста и зум.

        Выполняется только при открытии окна, при изменении размера окна и
        при изменении зума — НЕ при каждом движении мыши/панорамировании.
        Это самая дорогая операция (LANCZOS ресемплинг полноразмерных
        изображений), поэтому она кэшируется в self._src_fit/self._dst_fit.
        Short-circuit: если холст и зум не изменились — возвращаемся сразу.
        Сама позиция видимой области (off_x/off_y, панорамирование)
        вычисляется отдельно в _redraw() — она не требует пересчёта картинки.
        """
        c = self._canvas
        cw = c.winfo_width()
        ch = c.winfo_height()
        if cw < 2 or ch < 2:
            return

        iw, ih = self._src_pil.size
        base_scale = min(cw / iw, ch / ih) if iw and ih else 1
        scale = base_scale * self._zoom
        nw, nh = max(1, int(iw * scale)), max(1, int(ih * scale))

        # Пропускаем пересчёт если холст и целевой размер не изменились
        if (cw == self._canvas_w and ch == self._canvas_h
                and nw == self._img_w and nh == self._img_h
                and self._src_fit is not None):
            return

        self._canvas_w, self._canvas_h = cw, ch
        self._img_w, self._img_h = nw, nh

        self._src_fit = self._prepare_for_display(
            self._src_pil.resize((nw, nh), Image.Resampling.LANCZOS))
        self._dst_fit = self._prepare_for_display(
            self._dst_pil.resize((nw, nh), Image.Resampling.LANCZOS))

    def _prepare_for_display(self, img):
        """Конвертирует RGBA → RGB с фоном цвета холста для отображения.

        ImageTk.PhotoImage значительно быстрее работает с RGB, чем с RGBA —
        это критично, поскольку PhotoImage создаётся на каждый кадр движения
        слайдера. Цвет фона берётся через winfo_rgb(), что корректно работает
        как с hex (#1e1e2e), так и с именованными цветами Tk ("black", "gray10").
        """
        if img.mode != "RGBA":
            return img.convert("RGB") if img.mode != "RGB" else img
        try:
            # winfo_rgb возвращает (r, g, b) в диапазоне 0–65535
            r, g, b = self.winfo_rgb(self._bg)
            bg_color = (r >> 8, g >> 8, b >> 8)
        except Exception:
            bg_color = (30, 30, 46)
        bg = Image.new("RGB", img.size, bg_color)
        bg.paste(img, mask=img.split()[3])
        return bg

    # ── отрисовка (лёгкая операция — без ресемплинга) ────────────────────────────

    def _redraw(self):
        if self._src_fit is None or self._canvas_w < 2:
            self._recompute_fit()
            if self._src_fit is None:
                return

        cw, ch = self._canvas_w, self._canvas_h
        img_w, img_h = self._img_w, self._img_h

        # Видимая область (viewport) внутри (возможно увеличенного) изображения.
        # Если изображение меньше холста по какой-то оси — оно центрируется
        # (letterbox), как и раньше при зуме 100%. Если больше — заполняет
        # холст по этой оси целиком, и доступно панорамирование в её пределах.
        vw = min(cw, img_w)
        vh = min(ch, img_h)
        max_pan_x = max(0, img_w - vw)
        max_pan_y = max(0, img_h - vh)
        self._pan_x = max(0, min(max_pan_x, self._pan_x))
        self._pan_y = max(0, min(max_pan_y, self._pan_y))
        view_x, view_y = int(self._pan_x), int(self._pan_y)

        off_x = (cw - vw) // 2
        off_y = (ch - vh) // 2

        # Кэшируем для _on_mouse_move / _on_press / _update_split_from_x
        self._off_x = off_x
        self._vw    = vw

        split_x = int(cw * self._split)

        # Позиция разделителя зажата в границы картинки: линия никогда не
        # уходит в пустой letterbox-отступ слева/справа.
        divider_x = max(off_x, min(off_x + vw, split_x))

        # Только обрезка уже готовых изображений — никакого ресемплинга.
        # Это дешёвая операция даже для очень больших исходных фото, и не
        # зависит от того, насколько увеличено изображение, так как обрезаем
        # не весь увеличенный кадр, а только видимую (размером с холст) часть.
        left_px = max(0, min(vw, split_x - off_x))

        # Двойной буфер PhotoImage: держим ссылку на предыдущие объекты до тех
        # пор, пока не обновим Canvas — иначе Tk может обратиться к уже
        # удалённому PhotoImage и получить мерцание или падение.
        prev_left  = self._left_photo
        prev_right = self._right_photo

        if left_px > 0 and vh > 0:
            left_crop = self._src_fit.crop(
                (view_x, view_y, view_x + left_px, view_y + vh))
            self._left_photo = ImageTk.PhotoImage(left_crop)
        else:
            self._left_photo = None

        # right_px — ширина правой части: от split до правого края картинки.
        # Когда left_px == 0 (разделитель у левого края) правая часть
        # покрывает всю картинку целиком — картинка не исчезает.
        right_px = vw - left_px
        if right_px > 0 and vh > 0:
            right_crop = self._dst_fit.crop(
                (view_x + left_px, view_y, view_x + vw, view_y + vh))
            self._right_photo = ImageTk.PhotoImage(right_crop)
        else:
            self._right_photo = None

        self._draw_left(off_x, off_y)
        self._draw_right(off_x, off_y, left_px)
        self._draw_divider(divider_x, ch)
        self._draw_labels(off_x, off_y, vw)

        # После обновления Canvas старые PhotoImage можно отпустить
        del prev_left, prev_right

    def _draw_left(self, off_x, off_y):
        c = self._canvas
        if self._left_photo is None:
            # Убираем скрытие _left_item (state="hidden").
            # Из-за особенностей Tkinter скрытие нижнего слоя принудительно 
            # заливает область фоном, затирая правое изображение поверх него.
            # Так как правое изображение (с более высоким Z-index) при left_px == 0 
            # и так растянуто на всю ширину экрана, оно само идеально перекроет эту область.
            return
        
        if self._left_item is None:
            self._left_item = c.create_image(off_x, off_y, anchor="nw",
                                              image=self._left_photo)
        else:
            c.coords(self._left_item, off_x, off_y)
            c.itemconfigure(self._left_item, image=self._left_photo, state="normal")

    def _draw_right(self, off_x, off_y, left_px):
        c = self._canvas
        if self._right_photo is None:
            if self._right_item is not None:
                c.itemconfigure(self._right_item, state="hidden")
            return
        x = off_x + left_px
        if self._right_item is None:
            self._right_item = c.create_image(x, off_y, anchor="nw",
                                               image=self._right_photo)
        else:
            c.coords(self._right_item, x, off_y)
            c.itemconfigure(self._right_item, image=self._right_photo, state="normal")

    def _draw_divider(self, split_x, ch):
        c = self._canvas
        if self._divider_item is None:
            self._divider_item = c.create_line(split_x, 0, split_x, ch,
                                                fill=self._accent, width=self._DIVIDER_W)
        else:
            c.coords(self._divider_item, split_x, 0, split_x, ch)

    def _draw_labels(self, off_x, off_y, img_w):
        c = self._canvas
        pad = 12
        # label_y — независимая переменная, не перезаписывает параметр off_y
        label_y = self._canvas_h // 2 - pad - 8

        # Текст берётся из переводов на каждый кадр — при смене языка
        # надписи обновляются немедленно (fix: else-ветка тоже обновляет текст)
        was_txt    = self.master.t("was").replace(":", "").upper()
        became_txt = self.master.t("became").replace(":", "").upper()

        bx0, by0 = off_x + pad - 4,  label_y + pad - 2
        bx1, by1 = off_x + pad + 64, label_y + pad + 18
        tx,  ty  = off_x + pad + 30, label_y + pad + 8
        if self._lbl_before_bg is None:
            self._lbl_before_bg   = c.create_rectangle(bx0, by0, bx1, by1,
                                                        fill=self._bg2, outline="",
                                                        stipple="gray50")
            self._lbl_before_text = c.create_text(tx, ty, text=was_txt,
                                                   font=("Segoe UI", 9, "bold"),
                                                   fill=self._fg2, anchor="center")
        else:
            c.coords(self._lbl_before_bg,   bx0, by0, bx1, by1)
            c.coords(self._lbl_before_text, tx, ty)
            c.itemconfigure(self._lbl_before_text, text=was_txt)

        ax0, ay0 = off_x + img_w - pad - 68, label_y + pad - 2
        ax1, ay1 = off_x + img_w - pad + 4,  label_y + pad + 18
        atx, aty = off_x + img_w - pad - 32, label_y + pad + 8
        if self._lbl_after_bg is None:
            self._lbl_after_bg   = c.create_rectangle(ax0, ay0, ax1, ay1,
                                                       fill=self._bg2, outline="",
                                                       stipple="gray50")
            self._lbl_after_text = c.create_text(atx, aty, text=became_txt,
                                                  font=("Segoe UI", 9, "bold"),
                                                  fill=self._fg2, anchor="center")
        else:
            c.coords(self._lbl_after_bg,   ax0, ay0, ax1, ay1)
            c.coords(self._lbl_after_text, atx, aty)
            c.itemconfigure(self._lbl_after_text, text=became_txt)
