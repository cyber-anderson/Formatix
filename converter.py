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

"""Логика конвертации и обработки изображений.

Модуль самодостаточен — не импортирует ничего из главного файла приложения.
Здесь же определяется, какие форматы (AVIF/HEIC/SVG) реально доступны в
текущем окружении (в зависимости от установленных опциональных пакетов),
и собираются производные от этого константы FORMATS / IMG_EXTS.

Кэш конвертации (dict) и блокировка (threading.Lock) — состояние, которым
владеет главное окно приложения, поэтому convert_one() принимает их как
явные необязательные аргументы, а не хранит сама. Это же касается
render_filename_template()/sanitize_filename_part(): им передают снимок
пресета и токенов, а не читают состояние GUI напрямую — благодаря этому
их можно безопасно вызывать и из фонового потока конвертации, и из
GUI-потока (например, для предпросмотра имени файла в настройках).
"""

import os
import io
import re
import datetime
import contextlib
from PIL import Image, ImageCms

# ── доступность опциональных форматов ──────────────────────────────────────────
HEIF_AVAILABLE = False
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
    HEIF_AVAILABLE = True
except Exception:
    pass

AVIF_AVAILABLE = False
try:
    # Pillow >= 10 поддерживает AVIF нативно если установлен libavif.
    # pillow-avif-plugin расширяет поддержку для старых версий Pillow.
    try:
        import pillow_avif  # noqa: F401 - регистрирует кодек автоматически при импорте
    except ImportError:
        pass
    # Проверяем реальную возможность сохранения: создаём 1x1 AVIF в памяти
    _test = Image.new("RGB", (1, 1))
    _buf  = io.BytesIO()
    _test.save(_buf, "AVIF", quality=50)
    AVIF_AVAILABLE = True
    del _test, _buf
except Exception:
    pass

SVG_AVAILABLE = False
try:
    import resvg_py as _resvg_py
    SVG_AVAILABLE = True
except Exception:
    pass

FORMATS = (["AVIF"] if AVIF_AVAILABLE else []) + ["WEBP", "JPEG"] + (["HEIC"] if HEIF_AVAILABLE else []) + ["PNG", "BMP", "TIFF", "ICO"]
IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif", ".gif", ".ico"} | ({".avif"} if AVIF_AVAILABLE else set()) | ({".heic", ".heif"} if HEIF_AVAILABLE else set()) | ({".svg"} if SVG_AVAILABLE else set())


# ── информация о файлах и разрешении ────────────────────────────────────────────

def format_size(size_bytes):
    """Возвращает читаемый размер файла (KB / MB)."""
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

    except Exception:
        pass

    return None, None


def load_pil_for_display(path):
    """Загружает изображение для отображения в окне сравнения.

    Единая точка входа для CompareWindow._load_pil.  Поддерживает:
    - SVG через resvg_py (рендер до 2048 px по длинной стороне)
    - ICC-коррекцию растровых форматов (любой профиль -> sRGB)
    - CMYK -> RGB до ICC (ImageCms не принимает CMYK напрямую)
    - UTF-16 BOM, UTF-8 BOM и plain-UTF-8 для SVG

    Вынесена на уровень модуля, чтобы её мог переиспользовать любой
    компонент приложения без дублирования кода.
    """
    ext = os.path.splitext(path)[1].lower()
    fallback = Image.new("RGB", (4, 4), (30, 30, 46))

    # ── SVG: рендерим через resvg_py ─────────────────────────────────────────
    if ext == ".svg" and SVG_AVAILABLE:
        try:
            with open(path, "rb") as _fb:
                _raw = _fb.read()
            if _raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
                svg_str = _raw.decode("utf-16")
            elif _raw[:3] == b"\xef\xbb\xbf":
                svg_str = _raw[3:].decode("utf-8", errors="replace")
            else:
                svg_str = _raw.decode("utf-8", errors="replace")

            native_w, native_h = get_svg_resolution_pure(path)

            # Ограничиваем размер рендера: большего для предпросмотра не нужно,
            # а _recompute_fit потом сам масштабирует под холст через LANCZOS.
            MAX_SVG = 2048
            if native_w and native_h:
                long_side = max(native_w, native_h)
                if long_side > MAX_SVG:
                    k = MAX_SVG / long_side
                    render_w = max(1, int(native_w * k))
                    render_h = max(1, int(native_h * k))
                else:
                    render_w, render_h = native_w, native_h
                png_bytes = _resvg_py.svg_to_bytes(
                    svg_string=svg_str, width=render_w, height=render_h)
            else:
                # SVG без явных размеров: resvg сам сохранит пропорции по viewBox
                png_bytes = _resvg_py.svg_to_bytes(
                    svg_string=svg_str, width=MAX_SVG, height=None)

            img = Image.open(io.BytesIO(png_bytes))
            img.load()
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGBA")
            return img
        except Exception:
            return fallback

    # ── Растровые форматы ─────────────────────────────────────────────────────
    try:
        img = Image.open(path)
        img.load()

        # CMYK -> RGB до ICC-коррекции (ImageCms не принимает CMYK напрямую)
        if img.mode == "CMYK":
            img = img.convert("RGB")

        # ICC-коррекция: приводим к sRGB для корректного отображения на экране
        try:
            icc_profile = img.info.get("icc_profile")
            if icc_profile:
                src_profile = ImageCms.ImageCmsProfile(io.BytesIO(icc_profile))
                dst_profile = ImageCms.createProfile("sRGB")
                out_mode = "RGBA" if img.mode in ("RGBA", "PA", "LA") else "RGB"
                img = ImageCms.profileToProfile(
                    img, src_profile, dst_profile, outputMode=out_mode)
        except Exception:
            pass  # если ICC не распознан - показываем как есть

        # Нормализуем итоговый режим
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGBA" if "A" in img.mode else "RGB")

        return img
    except Exception:
        return fallback


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


# ── имена файлов ────────────────────────────────────────────────────────────────

_INVALID_FILENAME_CHARS = '<>:"/\\|?*'


def sanitize_filename_part(s):
    """Убирает символы, недопустимые в именах файлов Windows (и управляющие
    символы), из текста, который пользователь мог ввести в токен «Свой текст»."""
    return "".join(c for c in s if c not in _INVALID_FILENAME_CHARS and ord(c) >= 32)


def render_filename_template(base_name, index, preset, tokens):
    """Строит новое базовое имя файла (без расширения) по выбранному
    пресету или пользовательскому шаблону.

    base_name - исходное имя файла (без расширения); index - порядковый
    номер файла в батче, считая с 1 (используется токеном "Номер").
    preset/tokens передаются явным снимком (а не читаются из состояния GUI),
    чтобы функцию можно было безопасно вызывать как из GUI-потока
    (для предпросмотра), так и из фонового потока конвертации.
    """
    if preset == "original":
        result = base_name
    elif preset == "number":
        result = f"{base_name}_{index:03d}"
    elif preset == "date":
        result = f"{base_name}_{datetime.date.today().isoformat()}"
    elif preset == "custom":
        if not tokens:
            # Пустой шаблон - ведём себя как "оставить как есть", а не
            # выдаём файл вообще без имени.
            result = base_name
        else:
            parts = []
            for tok in tokens:
                kind = tok.get("type")
                if kind == "name":
                    parts.append(base_name)
                elif kind == "index":
                    parts.append(f"{index:03d}")
                elif kind == "date":
                    parts.append(datetime.date.today().isoformat())
                elif kind == "text":
                    parts.append(tok.get("value", ""))
            result = "".join(parts).strip()
    else:
        result = base_name

    result = sanitize_filename_part(result).strip()
    return result or base_name  # защита от пустого/полностью «съеденного» имени


def generate_unique_filename(out_dir, base_name, ext,
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


# ── собственно конвертация ──────────────────────────────────────────────────────

def find_quality_for_target_size(img, save_fmt, base_kw, target_bytes):
    """Бинарным поиском подбирает максимальное качество (10-100), при
    котором закодированный в память файл не превышает target_bytes.

    base_kw - уже собранные параметры сохранения (icc_profile для AVIF
    и т.д.), кроме "quality" - она подбирается здесь и переопределяется
    на каждой итерации. Кодирование идёт в BytesIO, не на диск - реальная
    запись на диск происходит один раз после подбора, в вызывающем коде.

    Если даже quality=10 даёт файл больше target_bytes (например,
    очень «шумное» изображение, которое физически не сжать сильнее без
    уменьшения разрешения) - возвращает 10 как лучший достижимый
    результат; итоговый файл в этом случае будет больше запрошенного
    лимита, но конвертация не прерывается.
    """
    lo, hi = 10, 100
    best_q = 10
    while lo <= hi:
        mid = (lo + hi) // 2
        buf = io.BytesIO()
        test_kw = dict(base_kw)
        test_kw["quality"] = mid
        try:
            img.save(buf, save_fmt, **test_kw)
        except Exception:
            # Это качество не удалось закодировать - считаем его
            # недостижимым и сужаем диапазон вниз.
            hi = mid - 1
            continue
        if buf.tell() <= target_bytes:
            best_q = mid
            lo = mid + 1
        else:
            hi = mid - 1
    return best_q


def convert_one(path, out_dir, fmt, out_name, quality,
                mode, target_w, target_h, current_config_str, resize_key=None,
                quality_mode="percent", target_bytes=None,
                cache=None, lock=None):
    """Конвертирует один файл. Вызывается из пула потоков.

    cache/lock - необязательные общий словарь и блокировка, которыми
    владеет вызывающий код (обычно главное окно приложения). Если cache
    не передан, кэширование результатов просто отключается - функцию
    можно вызывать и полностью автономно.
    """
    out_path  = os.path.join(out_dir, out_name)
    error_msg = None
    lock_ctx  = lock if lock is not None else contextlib.nullcontext()

    # Проверка кэша
    cached_entry = None
    if cache is not None:
        with lock_ctx:
            cached_entry = cache.get(path)

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
            # После рендера resize не нужен - resvg уже отрисовал нужный размер.
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

            # CMYK не поддерживается ImageCms напрямую - конвертируем заранее
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

            # Для SVG resize пропускаем - изображение уже отрендерено в нужный размер
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
                # Сначала конвертируем в RGBA, затем берём маску -
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
                    # LA, P, PA -> RGBA чтобы сохранить прозрачность если она есть
                    if img.mode in ("LA", "PA"):
                        img = img.convert("RGBA")
                    elif img.mode == "P" and "transparency" in img.info:
                        img = img.convert("RGBA")
                    else:
                        img = img.convert("RGB")
                # Встраиваем sRGB ICC-профиль - AVIF декодеры ожидают его явно
                srgb_profile = ImageCms.createProfile("sRGB")
                kw["icc_profile"] = ImageCms.ImageCmsProfile(srgb_profile).tobytes()

            tmp_path = out_path + ".tmp"
            save_fmt = "HEIF" if fmt == "HEIC" else fmt

            # Режим "целевой размер файла": подбираем максимальное
            # качество, укладывающееся в лимит, бинарным поиском.
            # Если лимит физически недостижим даже при quality=10 -
            # используем лучшее из достижимого (см. find_quality_for_target_size).
            if quality_mode == "size" and target_bytes and fmt in ("JPEG", "WEBP", "HEIC", "AVIF"):
                quality = find_quality_for_target_size(img, save_fmt, kw, target_bytes)
                kw["quality"] = quality

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

    # Запись в кэш только при успехе - неудачи не кэшируем,
    # чтобы следующий запуск пересчитал файл заново.
    if success and cache is not None:
        with lock_ctx:
            # LRU-ограничение: не более 500 записей за сессию
            if len(cache) >= 500:
                cache.pop(next(iter(cache)))
            cache[path] = (current_config_str, out_path, f_size, True, res_str)

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
