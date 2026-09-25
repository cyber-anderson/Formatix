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

"""Проверка обновлений через GitHub Releases API.

Модуль самодостаточен — использует только стандартную библиотеку
(urllib, json) и не знает ничего про Tkinter или структуру главного
приложения. Сетевой вызов синхронный и блокирующий, поэтому вызывающий
код обязан запускать check_for_update() в фоновом потоке, а не в
GUI-потоке.

Приложение анонимно (без токена) обращается к публичному GitHub API —
лимит 60 запросов/час действует на IP-адрес, а не на репозиторий или
пользователя, так что даже при большом числе пользователей приложения
исчерпать его на практике нереально, особенно если проверять не чаще
раза в день (см. UPDATE_CHECK_INTERVAL_SEC и _should_check_now в
formatix.py).
"""

import json
import urllib.request
import urllib.error

GITHUB_REPO  = "cyber-anderson/Formatix"
API_URL      = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
RELEASES_URL = f"https://github.com/{GITHUB_REPO}/releases/latest"


def parse_version(version_str):
    """'v1.16.0' / '1.16.0' -> (1, 16, 0) для сравнения кортежами.

    Нечисловые хвосты внутри сегмента (например, '0-beta') обрезаются
    до первых цифр — этого достаточно для сравнения релизов проекта,
    полноценный semver-парсинг здесь избыточен.
    """
    version_str = version_str.strip().lstrip("vV")
    parts = []
    for chunk in version_str.split("."):
        digits = ""
        for ch in chunk:
            if not ch.isdigit():
                break
            digits += ch
        parts.append(int(digits) if digits else 0)
    return tuple(parts) if parts else (0,)


def is_newer(remote_version, current_version):
    """True, если remote_version строго новее current_version."""
    return parse_version(remote_version) > parse_version(current_version)


def fetch_latest_release(timeout=5):
    """Запрашивает последний релиз с GitHub.

    Возвращает (tag_name, html_url) или None при любой ошибке (нет сети,
    таймаут, лимит API, репозиторий недоступен и т.д.) — ошибки сети не
    должны быть заметны пользователю, поэтому все они гасятся молча.
    """
    req = urllib.request.Request(
        API_URL,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "Formatix-Update-Check",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        return None

    tag = data.get("tag_name") or ""
    url = data.get("html_url") or RELEASES_URL
    if not tag:
        return None
    return tag, url


def check_for_update(current_version, timeout=5):
    """Синхронная проверка обновления — вызывать из фонового потока.

    Возвращает (tag_name, url) новой версии, если она новее current_version,
    иначе None (в том числе при любой сетевой ошибке).
    """
    result = fetch_latest_release(timeout=timeout)
    if result is None:
        return None
    tag, url = result
    if is_newer(tag, current_version):
        return tag, url
    return None
