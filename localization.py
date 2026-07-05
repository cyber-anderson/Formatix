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

"""Локализация интерфейса: список языков, все строки переводов и
автоопределение языка системы.

Модуль полностью самодостаточен — использует только стандартную библиотеку
(os, sys, ctypes, locale, winreg) и не зависит от остального кода
приложения. Главный файл импортирует из него LANGUAGES, STRINGS и
detect_system_lang().
"""

import os
import sys
import ctypes
import locale

# Используется прямо здесь, в f-строках STRINGS (например, "donate_sub").
# Это единственный источник истины для имени приложения — главный файл
# импортирует APP_NAME отсюда же, а не определяет свою копию.
APP_NAME = "Formatix Image Converter"

LANGUAGES = {"en": "English", "ru": "Русский", "uk": "Українська", "de": "Deutsch", "zh": "中文"}

STRINGS = {
    "en": {
        "add": "+ Add", "clear": "✕ Clear",
        "src_panel": "📂  Source Files", "dst_panel": "✅  Result",
        "save_folder": "SAVE FOLDER", "folder_placeholder": "not selected — will be asked on convert",
        "pick_dir": "📁 Choose", "format_lbl": "FORMAT", "quality_lbl": "QUALITY",
        "resize_lbl": "CHANGING RESOLUTION", "progress_lbl": "PROGRESS",
        "filesize_lbl": "FILE SIZE", "was": "Was:", "became": "Became:",
        "convert_btn": "▶  Convert", "processing_btn": "▶  Processing...", "stop_btn": "■  Stop",
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
        "donate_title": "Support Development",
        "donate_sub": f"Thanks for using {APP_NAME}!",
        "donate_desc": "If the program saved your time, you can\nsupport its development:",
        "donate_copied": "Address copied!",
        "donate_btn": "Open page with wallets",
        "auto": "Auto",
        "cache_tag": " (cache)",
        "resize_custom": "Custom",
        "ico_too_large_title": "ICO size limit",
        "ico_too_large_msg": "ICO format does not support resolutions above 256×256.\nThe image will be resized to fit.",
        "ico_too_large_cancel": "Cancel",
        "ico_too_large_ok": "OK",
        "settings_remember": "Remember settings",
        "settings_theme": "Theme", "theme_dark": "Dark", "theme_light": "Light",
        "theme_restart_note": "Restart the app to apply the new theme.",
        "settings_check_updates": "Check for updates automatically",
        "update_check_now": "Check now", "update_checking": "Checking…",
        "update_up_to_date": "You have the latest version",
        "update_check_failed": "Could not check for updates",
        "update_ver_label": "update {version} is available",
        "svg_no_size_title": "SVG: size required",
        "svg_no_size_msg": "SVG files have no fixed resolution.\nPlease set width and height in “Custom” mode before converting.",
        "compare_btn": "🆚 Compare", "compare_title": "Comparison",
        "compare_no_files": "No files to compare",
        "qmode_percent": "%", "qmode_size": "Size",
        "warn_bad_target_size": "Please enter a valid target file size (greater than 0).",
        "settings_filename_lbl": "File name",
        "fn_preset_original": "Keep as is", "fn_preset_number": "Name + sequence number",
        "fn_preset_date": "Name + date", "fn_preset_custom": "Custom template…",
        "fn_add_name": "File name", "fn_add_index": "Number", "fn_add_date": "Date",
        "fn_add_text": "Custom text…", "fn_clear": "Clear", "fn_preview_lbl": "Preview:",
        "fn_custom_text_prompt": "Enter text to insert",
        "fn_empty_hint": "Click a button above to build a template",
    },
    "ru": {
        "add": "+ Добавить", "clear": "✕ Очистить",
        "src_panel": "📂  Исходные файлы", "dst_panel": "✅  Результат",
        "save_folder": "ПАПКА ДЛЯ СОХРАНЕНИЯ", "folder_placeholder": "не выбрана — будет запрошена при конвертации",
        "pick_dir": "📁 Выбрать", "format_lbl": "ФОРМАТ", "quality_lbl": "КАЧЕСТВО",
        "resize_lbl": "ИЗМЕНЕНИЕ РАЗРЕШЕНИЯ", "progress_lbl": "ПРОГРЕСС",
        "filesize_lbl": "РАЗМЕР ФАЙЛОВ", "was": "Было: ", "became": "Стало:",
        "convert_btn": "▶  Конвертировать", "processing_btn": "▶  Обработка...", "stop_btn": "■  Остановить",
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
        "donate_title": "Поддержать разработку",
        "donate_sub": f"Спасибо за использование {APP_NAME}!",
        "donate_desc": "Если программа сэкономила ваше время, вы можете\nподдержать её развитие:",
        "donate_copied": "Адрес успешно скопирован!",
        "donate_btn": "Открыть страницу с кошельками",
        "auto": "Авто",
        "cache_tag": " (кэш)",
        "resize_custom": "Пользовательский",
        "ico_too_large_title": "Ограничение ICO",
        "ico_too_large_msg": "Формат ICO не поддерживает разрешения больше 256×256.\nИзображение будет изменено по размеру.",
        "ico_too_large_cancel": "Отмена",
        "ico_too_large_ok": "ОК",
        "settings_remember": "Запоминать настройки",
        "settings_theme": "Тема", "theme_dark": "Тёмная", "theme_light": "Светлая",
        "theme_restart_note": "Перезапустите приложение, чтобы применить новую тему.",
        "settings_check_updates": "Проверять обновления автоматически",
        "update_check_now": "Проверить сейчас", "update_checking": "Проверяем…",
        "update_up_to_date": "У вас последняя версия",
        "update_check_failed": "Не удалось проверить обновления",
        "update_ver_label": "доступно обновление {version}",
        "svg_no_size_title": "SVG: требуется размер",
        "svg_no_size_msg": "SVG-файлы не имеют фиксированного разрешения.\nПожалуйста, задайте ширину и высоту в режиме «Пользовательский» перед конвертацией.",
        "compare_btn": "🆚 Сравнить", "compare_title": "Сравнение",
        "compare_no_files": "Файлы для сравнения отсутствуют",
        "qmode_percent": "%", "qmode_size": "Размер",
        "warn_bad_target_size": "Введите корректный целевой размер файла (больше 0).",
        "settings_filename_lbl": "Имя файла",
        "fn_preset_original": "Оставить как есть", "fn_preset_number": "Имя + номер по порядку",
        "fn_preset_date": "Имя + дата", "fn_preset_custom": "Свой шаблон…",
        "fn_add_name": "Имя файла", "fn_add_index": "Номер", "fn_add_date": "Дата",
        "fn_add_text": "Свой текст…", "fn_clear": "Очистить", "fn_preview_lbl": "Пример:",
        "fn_custom_text_prompt": "Введите текст для вставки",
        "fn_empty_hint": "Нажмите кнопку выше, чтобы собрать шаблон",
    },
    "uk": {
        "add": "+ Додати", "clear": "✕ Очистити",
        "src_panel": "📂  Вихідні файли", "dst_panel": "✅  Результат",
        "save_folder": "ПАПКА ДЛЯ ЗБЕРЕЖЕННЯ", "folder_placeholder": "не обрана — буде запитана при конвертації",
        "pick_dir": "📁 Обрати", "format_lbl": "ФОРМАТ", "quality_lbl": "ЯКІСТЬ",
        "resize_lbl": "ЗМІНА РОЗДІЛЬНОСТІ", "progress_lbl": "ПРОГРЕС",
        "filesize_lbl": "РОЗМІР ФАЙЛІВ", "was": "Було: ", "became": "Стало:",
        "convert_btn": "▶  Конвертувати", "processing_btn": "▶  Обробка...", "stop_btn": "■  Зупинити",
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
        "donate_title": "Підтримати розробку",
        "donate_sub": f"Дякую за використання {APP_NAME}!",
        "donate_desc": "Якщо програма заощадила ваш час, ви можете\nпідтримати її розвиток:",
        "donate_copied": "Адресу скопійовано!",
        "donate_btn": "Відкрити сторінку з гаманцями",
        "auto": "Авто",
        "cache_tag": " (кеш)",
        "resize_custom": "Користувацький",
        "ico_too_large_title": "Обмеження ICO",
        "ico_too_large_msg": "Формат ICO не підтримує роздільності більше 256×256.\nЗображення буде змінено за розміром.",
        "ico_too_large_cancel": "Скасувати",
        "ico_too_large_ok": "ОК",
        "settings_remember": "Запам'ятовувати налаштування",
        "settings_theme": "Тема", "theme_dark": "Темна", "theme_light": "Світла",
        "theme_restart_note": "Перезапустіть застосунок, щоб застосувати нову тему.",
        "settings_check_updates": "Перевіряти оновлення автоматично",
        "update_check_now": "Перевірити зараз", "update_checking": "Перевіряємо…",
        "update_up_to_date": "У вас остання версія",
        "update_check_failed": "Не вдалося перевірити оновлення",
        "update_ver_label": "доступне оновлення {version}",
        "svg_no_size_title": "SVG: потрібен розмір",
        "svg_no_size_msg": "SVG-файли не мають фіксованої роздільності.\nБудь ласка, задайте ширину і висоту в режимі «Користувацький» перед конвертацією.",
        "compare_btn": "🆚 Порівняти", "compare_title": "Порівняння",
        "compare_no_files": "Файли для порівняння відсутні",
        "qmode_percent": "%", "qmode_size": "Розмір",
        "warn_bad_target_size": "Введіть коректний цільовий розмір файлу (більше 0).",
        "settings_filename_lbl": "Ім'я файлу",
        "fn_preset_original": "Залишити як є", "fn_preset_number": "Ім'я + порядковий номер",
        "fn_preset_date": "Ім'я + дата", "fn_preset_custom": "Свій шаблон…",
        "fn_add_name": "Ім'я файлу", "fn_add_index": "Номер", "fn_add_date": "Дата",
        "fn_add_text": "Свій текст…", "fn_clear": "Очистити", "fn_preview_lbl": "Приклад:",
        "fn_custom_text_prompt": "Введіть текст для вставки",
        "fn_empty_hint": "Натисніть кнопку вище, щоб зібрати шаблон",
    },
    "de": {
        "add": "+ Hinzufügen", "clear": "✕ Leeren",
        "src_panel": "📂  Quelldateien", "dst_panel": "✅  Ergebnis",
        "save_folder": "SPEICHERORDNER", "folder_placeholder": "nicht ausgewählt — wird beim Konvertieren abgefragt",
        "pick_dir": "📁 Wählen", "format_lbl": "FORMAT", "quality_lbl": "QUALITÄT",
        "resize_lbl": "AUFLÖSUNGSÄNDERUNG", "progress_lbl": "FORTSCHRITT",
        "filesize_lbl": "DATEIGRÖSSE", "was": "War:  ", "became": "Jetzt:",
        "convert_btn": "▶  Konvertieren", "processing_btn": "▶  Verarbeitung...", "stop_btn": "■  Stopp",
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
        "donate_title": "Entwicklung unterstützen",
        "donate_sub": f"Danke für die Nutzung von {APP_NAME}!",
        "donate_desc": "Wenn das Programm Ihnen Zeit gespart hat, können Sie\ndessen Entwicklung unterstützen:",
        "donate_copied": "Adresse kopiert!",
        "donate_btn": "Seite mit Wallets öffnen",
        "auto": "Auto",
        "cache_tag": " (Cache)",
        "resize_custom": "Benutzerdefiniert",
        "ico_too_large_title": "ICO-Größenbeschränkung",
        "ico_too_large_msg": "Das ICO-Format unterstützt keine Auflösungen über 256×256.\nDas Bild wird entsprechend skaliert.",
        "ico_too_large_cancel": "Abbrechen",
        "ico_too_large_ok": "OK",
        "settings_remember": "Einstellungen speichern",
        "settings_theme": "Design", "theme_dark": "Dunkel", "theme_light": "Hell",
        "theme_restart_note": "Starten Sie die App neu, um das neue Design zu übernehmen.",
        "settings_check_updates": "Automatisch nach Updates suchen",
        "update_check_now": "Jetzt prüfen", "update_checking": "Wird geprüft…",
        "update_up_to_date": "Sie haben die neueste Version",
        "update_check_failed": "Update-Prüfung fehlgeschlagen",
        "update_ver_label": "update {version} verfügbar",
        "svg_no_size_title": "SVG: Größe erforderlich",
        "svg_no_size_msg": "SVG-Dateien haben keine feste Auflösung.\nBitte geben Sie Breite und Höhe im Modus „Benutzerdefiniert“ vor der Konvertierung ein.",
        "compare_btn": "🆚 Vergleichen", "compare_title": "Vergleich",
        "compare_no_files": "Keine Dateien zum Vergleich vorhanden",
        "qmode_percent": "%", "qmode_size": "Größe",
        "warn_bad_target_size": "Bitte eine gültige Zielgröße eingeben (größer als 0).",
        "settings_filename_lbl": "Dateiname",
        "fn_preset_original": "Unverändert lassen", "fn_preset_number": "Name + laufende Nummer",
        "fn_preset_date": "Name + Datum", "fn_preset_custom": "Eigene Vorlage…",
        "fn_add_name": "Dateiname", "fn_add_index": "Nummer", "fn_add_date": "Datum",
        "fn_add_text": "Eigener Text…", "fn_clear": "Leeren", "fn_preview_lbl": "Vorschau:",
        "fn_custom_text_prompt": "Einzufügenden Text eingeben",
        "fn_empty_hint": "Oben auf eine Schaltfläche klicken, um eine Vorlage zu erstellen",
    },
    "zh": {
        "add": "+ 添加", "clear": "✕ 清空",
        "src_panel": "📂  源文件", "dst_panel": "✅  结果",
        "save_folder": "保存文件夹", "folder_placeholder": "未选择 — 转换时将询问",
        "pick_dir": "📁 选择", "format_lbl": "格式", "quality_lbl": "质量",
        "resize_lbl": "更改分辨率", "progress_lbl": "进度",
        "filesize_lbl": "文件大小", "was": "之前:", "became": "之后:",
        "convert_btn": "▶  转换", "processing_btn": "▶  处理中...", "stop_btn": "■  停止",
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
        "donate_title": "支持开发",
        "donate_sub": f"感谢使用 {APP_NAME}！",
        "donate_desc": "如果该程序节省了您的时间，您可以\n支持它的开发：",
        "donate_copied": "地址已复制！",
        "donate_btn": "打开钱包页面",
        "auto": "自动",
        "cache_tag": " (缓存)",
        "resize_custom": "自定义",
        "ico_too_large_title": "ICO 尺寸限制",
        "ico_too_large_msg": "ICO 格式不支持超过 256×256 的分辨率。\n图像将被调整大小。",
        "ico_too_large_cancel": "取消",
        "ico_too_large_ok": "确定",
        "settings_remember": "记住设置",
        "settings_theme": "主题", "theme_dark": "深色", "theme_light": "浅色",
        "theme_restart_note": "重启应用以应用新主题。",
        "settings_check_updates": "自动检查更新",
        "update_check_now": "立即检查", "update_checking": "正在检查…",
        "update_up_to_date": "已是最新版本",
        "update_check_failed": "检查更新失败",
        "update_ver_label": "更新 {version} 可用",
        "svg_no_size_title": "SVG：需要指定尺寸",
        "svg_no_size_msg": "SVG 文件没有固定分辨率。\n请在「自定义」模式下设置宽度和高度后再进行转换。",
        "compare_btn": "🆚 对比", "compare_title": "对比",
        "compare_no_files": "没有可对比的文件",
        "qmode_percent": "%", "qmode_size": "大小",
        "warn_bad_target_size": "请输入有效的目标文件大小（大于 0）。",
        "settings_filename_lbl": "文件名",
        "fn_preset_original": "保持不变", "fn_preset_number": "文件名 + 序号",
        "fn_preset_date": "文件名 + 日期", "fn_preset_custom": "自定义模板…",
        "fn_add_name": "文件名", "fn_add_index": "序号", "fn_add_date": "日期",
        "fn_add_text": "自定义文本…", "fn_clear": "清空", "fn_preview_lbl": "预览：",
        "fn_custom_text_prompt": "输入要插入的文本",
        "fn_empty_hint": "点击上方按钮来构建模板",
    },
}


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
