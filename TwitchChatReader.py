# -*- coding: utf-8 -*-
"""
TwitchChatReader — озвучка чата Twitch через edge-tts + GUI.
Developer: Dasti
Требования: pip install edge-tts playsound3
"""

import os
import sys
import re
import json
import time
import queue
import socket
import asyncio
import tempfile
import threading
import webbrowser
from collections import defaultdict, deque
import tkinter as tk
from tkinter import ttk, scrolledtext

import edge_tts


# ==================================================================
#                       ВЕРСИЯ И ССЫЛКИ
# ==================================================================
APP_NAME = "TwitchChatReader"
APP_VERSION = "4.1.3"
APP_AUTHOR = "Dasti"
REPO_URL = "https://github.com/Citizen819/TwitchChatReader"
DONATE_URLS = [
    ("donate.stream", "https://donate.stream/3Kster"),
    ("DonatePay", "https://donatepay.ru/don/1433265"),
]
SOCIAL_URLS = [
    ("Twitch",   "https://www.twitch.tv/tehnovlogg"),
    ("YouTube",  "https://www.youtube.com/@TeHnoVloGG"),
    ("TikTok",   "https://www.tiktok.com/@TeHnoVloGG"),
    ("Telegram", "https://t.me/TeHnoVloGG"),
]


# ==================================================================
#                       ЛОКАЛИЗАЦИЯ (RU / EN)
# ==================================================================
TRANSLATIONS = {
    "ru": {
        "app_title": "{name} — v{version} by {author}",
        "lang_label": "Язык:",
        "conn_frame": "Подключение",
        "channel": "Канал:",
        "token": "OAuth-токен:",
        "btn_connect": "▶ Подключиться",
        "btn_disconnect": "⏹ Отключиться",
        "btn_skip": "⏭ Пропустить",
        "btn_paste": "📋 Вставить",
        "status_off": "⚪ Отключено",
        "status_on": "🟢 Подключено",
        "tab_chat": "💬 Чат",
        "tab_lists": "📋 Списки",
        "tab_filters": "⚙️ Фильтры",
        "tab_voice": "🔊 Голос",
        "tab_stats": "📊 Статистика",
        "tab_update": "🔄 Обновление",
        "tab_donate": "💰 Донат",
        "tab_social": "🌐 Соцсети",
        "btn_clear_log": "Очистить лог",
        "btn_save_log": "Сохранить лог",
        "black_frame": "🔨 Чёрный список (не озвучивать)",
        "white_frame": "✅ Белый список (озвучивать всегда)",
        "btn_add": "+ Добавить",
        "btn_remove_selected": "− Удалить выбранного",
        "btn_save_file": "💾 Сохранить в файл",
        "btn_reload_file": "🔄 Перечитать из файла",
        "filter_commands": "Фильтровать команды (начинающиеся с ! / .)",
        "filter_bots": "Фильтровать ботов (nightbot и все *bot)",
        "filter_links": "Фильтровать ссылки",
        "filter_caps": "Фильтровать КАПС",
        "filter_length": "Фильтровать по длине",
        "filter_emoji": "Фильтровать эмодзи-спам",
        "filter_repeats": "Фильтровать повторы",
        "filter_stopwords": "Фильтровать стоп-слова",
        "censor_stopwords": "Заменять мат на «бип» (иначе — пропуск)",
        "allow_chat_commands": "Разрешить управление из чата (!tts ban ...)",
        "num_params": "Числовые параметры",
        "max_length": "Макс. длина:",
        "min_length": "Мин. длина:",
        "caps_threshold": "Порог капса (0–1):",
        "repeat_count": "Повторов подряд:",
        "repeat_window": "Окно повторов (сек):",
        "stopwords_frame": "Стоп-слова (по одному в строке)",
        "bots_frame": "Имена ботов (по одному в строке)",
        "voice_label": "Голос (edge-tts):",
        "voice_rate": "Скорость (-50 .. +100 %):",
        "voice_volume": "Громкость (-50 .. +50 %):",
        "voice_pitch": "Тембр (-50 .. +50 Hz):",
        "btn_test_voice": "🔊 Тест голоса",
        "voice_note": "edge-tts требует подключения к интернету.\n"
                      "Изменения применятся при следующем сообщении.",
        "fmt_frame": "Формат озвучки",
        "read_username": "Читать ник пользователя",
        "read_says_word": "Читать слово «пишет»",
        "template_label": "Шаблон фразы (плейсхолдеры {name} и {text}):",
        "template_preview": "Пример: {example}",
        "template_empty": "(пусто — озвучится только текст сообщения)",
        "template_error": "Ошибка в шаблоне",
        "stats_header": "СТАТИСТИКА ФИЛЬТРАЦИИ",
        "stats_spoken": "🔊 Озвучено:",
        "stats_commands": "🎮 Команд управления:",
        "stats_filtered": "🚫 Отфильтровано всего:",
        "stats_breakdown": "Разбивка по причинам:",
        "stats_empty": "Пока ничего не отфильтровано.",
        "stat_blacklist": "🔨 Чёрный список",
        "stat_bot": "🤖 Бот",
        "stat_command": "🎮 Команда",
        "stat_link": "🔗 Ссылка",
        "stat_length": "📏 Длина",
        "stat_caps": "🔠 КАПС",
        "stat_emoji": "😀 Эмодзи-спам",
        "stat_repeat": "🔁 Повтор",
        "stat_stopword": "🤬 Стоп-слово",
        "upd_title": "🔄 {name}",
        "upd_version": "Версия {version}",
        "upd_author": "Разработчик: {author}",
        "upd_links": "Ссылки",
        "upd_repo_label": "Репозиторий на GitHub:",
        "upd_btn_open": "🌐 Открыть на GitHub",
        "upd_btn_copy": "📋 Скопировать ссылку",
        "upd_notes": "Что нового",
        "upd_current": "Текущая версия: {version}",
        "upd_history": "История изменений:",
        "upd_hint": "Чтобы обновиться — скачайте свежий TwitchChatReader.py из репозитория\n"
                    "и замените старый файл. Настройки и списки сохранятся.",
        "don_title": "💰 Поддержать стримера",
        "don_subtitle": "Спасибо, что смотришь стрим! Любая поддержка "
                        "помогает развивать канал 💚",
        "don_btn_open": "🌐 Открыть {name}",
        "don_btn_copy": "📋 Скопировать ссылку",
        "don_note": "Обе площадки принимают карты РФ, ЮMoney и другие "
                    "способы оплаты.\nВыберите ту, что удобнее — ссылки "
                    "ведут на официальные страницы донатов.",
        "soc_title": "🌐 Соцсети стримера",
        "soc_subtitle": "Подписывайся, чтобы не пропустить новые стримы "
                        "и видео 🎬",
        "soc_btn_open": "🌐 Открыть {name}",
        "soc_btn_copy": "📋 Скопировать ссылку",
        "soc_note": "Кнопки открывают страницы в браузере по умолчанию.\n"
                    "Ссылку можно скопировать и поделиться с друзьями.",
        "btn_save_settings": "💾 Сохранить настройки",
        "log_copied": "📋 Ссылка скопирована: {url}",
        "log_opened": "🌐 Открыто: {name}",
        "log_open_error": "⚠️ Не удалось открыть браузер: {error}",
        "log_copy_error": "⚠️ Не удалось скопировать: {error}",
        "log_token_pasted": "📋 Токен вставлен ({n} символов)",
        "log_clipboard_empty": "⚠️ Буфер обмена пуст",
        "log_lists_saved": "💾 Списки сохранены в файл",
        "log_lists_reloaded": "🔄 Списки перечитаны из файла",
        "log_all_saved": "💾 Все настройки сохранены",
        "log_lang_changed": "🌍 Язык переключён на: {lang}",
        "log_lang_reload_hint": "ℹ️ Заголовки вкладок и окна обновлены. "
                                "Для остальных надписей перезапустите бота.",
        "log_filtered": "🚫 [{name}] отфильтровано ({reason}): {message}",
        "log_spoken": "🔊 [{name}]: {message}",
        "log_connected": "✅ Подключено к #{channel}",
        "log_disconnected": "🔌 Отключено от чата",
        "log_connecting": "🛑 Отключение...",
        "log_skip": "⏭️ Очередь озвучки очищена",
        "log_lists_loaded": "✅ Загружены списки: бан — {b}, белый — {w}",
        "log_lists_load_error": "⚠️ Ошибка загрузки списков: {error}",
        "log_lists_save_error": "⚠️ Не удалось сохранить списки: {error}",
        "log_config_save_error": "⚠️ Не удалось сохранить конфиг: {error}",
        "log_fill_fields": "⚠️ Заполните OAuth-токен и имя канала",
        "log_connect_error": "⚠️ Не удалось подключиться: {error}",
        "log_send_error": "⚠️ Ошибка отправки данных: {error}",
        "log_conn_lost": "⚠️ Соединение разорвано: {error}",
        "log_parse_error": "⚠️ Ошибка обработки: {error}",
        "log_tts_error": "⚠️ Ошибка edge-tts: {error}",
        "log_play_error": "⚠️ Ошибка воспроизведения: {error}",
        "log_test_error": "⚠️ Ошибка теста: {error}",
        "log_log_saved": "💾 Лог сохранён: {path}",
        "log_log_save_error": "⚠️ Ошибка сохранения: {error}",
        "log_perm_denied": "⛔ [{name}] нет прав на управление ботом",
        "log_cmd_ban": "🔨 [{name}] забанил: {target}",
        "log_cmd_ban_already": "ℹ️ [{name}] {target} уже в бане",
        "log_cmd_unban": "♻️ [{name}] разбанил: {target}",
        "log_cmd_unban_not": "ℹ️ [{name}] {target} не был в бане",
        "log_cmd_allow": "✅ [{name}] в белый список: {target}",
        "log_cmd_allow_already": "ℹ️ [{name}] {target} уже в белом",
        "log_cmd_deny": "➖ [{name}] убрал из белого: {target}",
        "log_cmd_deny_not": "ℹ️ [{name}] {target} не в белом",
        "log_cmd_save": "💾 [{name}] списки сохранены",
        "log_cmd_reload": "🔄 [{name}] списки перечитаны",
        "log_cmd_help": "ℹ️ Команды: ban | unban | allow | deny | list | save | reload",
        "log_added_black": "🔨 Добавлен в бан: {name}",
        "log_removed_black": "♻️ Убран из бана: {name}",
        "log_added_white": "✅ Добавлен в белый список: {name}",
        "log_removed_white": "➖ Убран из белого списка: {name}",
    },
    "en": {
        "app_title": "{name} — v{version} by {author}",
        "lang_label": "Language:",
        "conn_frame": "Connection",
        "channel": "Channel:",
        "token": "OAuth token:",
        "btn_connect": "▶ Connect",
        "btn_disconnect": "⏹ Disconnect",
        "btn_skip": "⏭ Skip",
        "btn_paste": "📋 Paste",
        "status_off": "⚪ Disconnected",
        "status_on": "🟢 Connected",
        "tab_chat": "💬 Chat",
        "tab_lists": "📋 Lists",
        "tab_filters": "⚙️ Filters",
        "tab_voice": "🔊 Voice",
        "tab_stats": "📊 Stats",
        "tab_update": "🔄 Update",
        "tab_donate": "💰 Donate",
        "tab_social": "🌐 Socials",
        "btn_clear_log": "Clear log",
        "btn_save_log": "Save log",
        "black_frame": "🔨 Blacklist (never read)",
        "white_frame": "✅ Whitelist (always read)",
        "btn_add": "+ Add",
        "btn_remove_selected": "− Remove selected",
        "btn_save_file": "💾 Save to file",
        "btn_reload_file": "🔄 Reload from file",
        "filter_commands": "Filter commands (starting with ! / .)",
        "filter_bots": "Filter bots (nightbot and all *bot)",
        "filter_links": "Filter links",
        "filter_caps": "Filter CAPS",
        "filter_length": "Filter by length",
        "filter_emoji": "Filter emoji spam",
        "filter_repeats": "Filter repeats",
        "filter_stopwords": "Filter stopwords",
        "censor_stopwords": "Replace profanity with \"beep\" (otherwise skip)",
        "allow_chat_commands": "Allow chat control (!tts ban ...)",
        "num_params": "Numeric parameters",
        "max_length": "Max length:",
        "min_length": "Min length:",
        "caps_threshold": "Caps threshold (0–1):",
        "repeat_count": "Repeats in a row:",
        "repeat_window": "Repeat window (sec):",
        "stopwords_frame": "Stopwords (one per line)",
        "bots_frame": "Bot names (one per line)",
        "voice_label": "Voice (edge-tts):",
        "voice_rate": "Rate (-50 .. +100 %):",
        "voice_volume": "Volume (-50 .. +50 %):",
        "voice_pitch": "Pitch (-50 .. +50 Hz):",
        "btn_test_voice": "🔊 Test voice",
        "voice_note": "edge-tts requires an internet connection.\n"
                      "Changes will apply to the next message.",
        "fmt_frame": "Speech format",
        "read_username": "Read username",
        "read_says_word": "Read the word \"says\"",
        "template_label": "Phrase template (placeholders {name} and {text}):",
        "template_preview": "Example: {example}",
        "template_empty": "(empty — only the message text will be read)",
        "template_error": "Template error",
        "stats_header": "FILTER STATISTICS",
        "stats_spoken": "🔊 Spoken:",
        "stats_commands": "🎮 Control commands:",
        "stats_filtered": "🚫 Filtered total:",
        "stats_breakdown": "Breakdown by reason:",
        "stats_empty": "Nothing has been filtered yet.",
        "stat_blacklist": "🔨 Blacklist",
        "stat_bot": "🤖 Bot",
        "stat_command": "🎮 Command",
        "stat_link": "🔗 Link",
        "stat_length": "📏 Length",
        "stat_caps": "🔠 CAPS",
        "stat_emoji": "😀 Emoji spam",
        "stat_repeat": "🔁 Repeat",
        "stat_stopword": "🤬 Stopword",
        "upd_title": "🔄 {name}",
        "upd_version": "Version {version}",
        "upd_author": "Developer: {author}",
        "upd_links": "Links",
        "upd_repo_label": "GitHub repository:",
        "upd_btn_open": "🌐 Open on GitHub",
        "upd_btn_copy": "📋 Copy link",
        "upd_notes": "What's new",
        "upd_current": "Current version: {version}",
        "upd_history": "Changelog:",
        "upd_hint": "To update — download the latest TwitchChatReader.py from the repo\n"
                    "and replace the old file. Settings and lists are preserved.",
        "don_title": "💰 Support the streamer",
        "don_subtitle": "Thanks for watching! Any support helps the channel grow 💚",
        "don_btn_open": "🌐 Open {name}",
        "don_btn_copy": "📋 Copy link",
        "don_note": "Both platforms accept RU cards, YooMoney, and other payment "
                    "methods.\nPick whichever is more convenient — links lead "
                    "to official donation pages.",
        "soc_title": "🌐 Streamer's socials",
        "soc_subtitle": "Follow to never miss new streams and videos 🎬",
        "soc_btn_open": "🌐 Open {name}",
        "soc_btn_copy": "📋 Copy link",
        "soc_note": "Buttons open pages in your default browser.\n"
                    "You can copy a link and share it with friends.",
        "btn_save_settings": "💾 Save settings",
        "log_copied": "📋 Link copied: {url}",
        "log_opened": "🌐 Opened: {name}",
        "log_open_error": "⚠️ Could not open browser: {error}",
        "log_copy_error": "⚠️ Could not copy: {error}",
        "log_token_pasted": "📋 Token pasted ({n} chars)",
        "log_clipboard_empty": "⚠️ Clipboard is empty",
        "log_lists_saved": "💾 Lists saved to file",
        "log_lists_reloaded": "🔄 Lists reloaded from file",
        "log_all_saved": "💾 All settings saved",
        "log_lang_changed": "🌍 Language switched to: {lang}",
        "log_lang_reload_hint": "ℹ️ Tab and window titles updated. "
                                "Restart the bot to apply to all labels.",
        "log_filtered": "🚫 [{name}] filtered ({reason}): {message}",
        "log_spoken": "🔊 [{name}]: {message}",
        "log_connected": "✅ Connected to #{channel}",
        "log_disconnected": "🔌 Disconnected from chat",
        "log_connecting": "🛑 Disconnecting...",
        "log_skip": "⏭️ Speech queue cleared",
        "log_lists_loaded": "✅ Lists loaded: black — {b}, white — {w}",
        "log_lists_load_error": "⚠️ Failed to load lists: {error}",
        "log_lists_save_error": "⚠️ Failed to save lists: {error}",
        "log_config_save_error": "⚠️ Failed to save config: {error}",
        "log_fill_fields": "⚠️ Fill in the OAuth token and channel name",
        "log_connect_error": "⚠️ Connection failed: {error}",
        "log_send_error": "⚠️ Send error: {error}",
        "log_conn_lost": "⚠️ Connection lost: {error}",
        "log_parse_error": "⚠️ Processing error: {error}",
        "log_tts_error": "⚠️ edge-tts error: {error}",
        "log_play_error": "⚠️ Playback error: {error}",
        "log_test_error": "⚠️ Test error: {error}",
        "log_log_saved": "💾 Log saved: {path}",
        "log_log_save_error": "⚠️ Save error: {error}",
        "log_perm_denied": "⛔ [{name}] no permission to control the bot",
        "log_cmd_ban": "🔨 [{name}] banned: {target}",
        "log_cmd_ban_already": "ℹ️ [{name}] {target} already banned",
        "log_cmd_unban": "♻️ [{name}] unbanned: {target}",
        "log_cmd_unban_not": "ℹ️ [{name}] {target} was not banned",
        "log_cmd_allow": "✅ [{name}] whitelisted: {target}",
        "log_cmd_allow_already": "ℹ️ [{name}] {target} already whitelisted",
        "log_cmd_deny": "➖ [{name}] removed from whitelist: {target}",
        "log_cmd_deny_not": "ℹ️ [{name}] {target} not whitelisted",
        "log_cmd_save": "💾 [{name}] lists saved",
        "log_cmd_reload": "🔄 [{name}] lists reloaded",
        "log_cmd_help": "ℹ️ Commands: ban | unban | allow | deny | list | save | reload",
        "log_added_black": "🔨 Added to ban: {name}",
        "log_removed_black": "♻️ Removed from ban: {name}",
        "log_added_white": "✅ Added to whitelist: {name}",
        "log_removed_white": "➖ Removed from whitelist: {name}",
    },
}


def tr(key, lang="ru", **kwargs):
    """Возвращает перевод по ключу."""
    table = TRANSLATIONS.get(lang, TRANSLATIONS["ru"])
    text = table.get(key, TRANSLATIONS["ru"].get(key, key))
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError):
            return text
    return text


# ==================================================================
#                       КОНФИГ ПО УМОЛЧАНИЮ
# ==================================================================
DEFAULT_CONFIG = {
    "channel": "",
    "oauth_token": "",
    "bot_name": "tts_bot",
    "language": "ru",

    # Фильтры
    "filter_commands": True,
    "command_prefixes": ["!", "/", "."],
    "filter_bots": True,
    "bot_names": [
        "nightbot", "moobot", "streamelements", "streamlabs",
        "fossabot", "wizebot", "sery_bot", "commanderroot",
        "soundalerts", "creatisbot", "kofistreambot", "logviewer",
        "buttsbot", "potatbotat", "pxls_enjoyer", "stay_hydrated_bot",
        "thepositivebot", "vjbot", "slanderbot", "aidenbot",
    ],
    "filter_links": True,
    "filter_caps": True,
    "caps_threshold": 0.7,
    "caps_min_length": 8,
    "filter_length": True,
    "max_length": 200,
    "min_length": 2,
    "filter_emoji_spam": True,
    "emoji_threshold": 0.5,
    "filter_repeats": True,
    "repeat_window": 60,
    "repeat_max_count": 2,
    "filter_stopwords": True,
    "stopwords": [
        "хуй", "пизда", "блядь", "бля", "ебать", "ебал", "ебаный",
        "сука", "мразь", "гандон", "долбоёб", "долбоеб", "мудак",
        "nigger", "faggot", "retard",
        "follow for follow", "f4f", "l2p", "get rekt",
    ],
    "censor_stopwords": True,

    # Списки
    "blacklist": [],
    "whitelist": [],
    "allow_chat_commands": True,
    "command_permission": ["broadcaster", "moderator"],

    # Голос
    "voice_name": "ru-RU-DmitryNeural",
    "voice_rate": 0,
    "voice_volume": 0,
    "voice_pitch": 0,

    # Формат озвучки
    "read_username": True,
    "read_says_word": True,
    "speech_template": "{name} пишет: {text}",

    # Файлы
    "lists_file": "tts_lists.json",
    "config_file": "tts_config.json",
}


LINK_PATTERN = re.compile(
    r"(https?://|www\.|\.com|\.ru|\.net|\.org|\.tv|\.gg|\.io)",
    re.IGNORECASE
)

EMOJI_PATTERN = re.compile(
    "["
    "\U0001F300-\U0001F5FF"
    "\U0001F600-\U0001F64F"
    "\U0001F680-\U0001F6FF"
    "\U0001F700-\U0001F77F"
    "\U0001F780-\U0001F7FF"
    "\U0001F800-\U0001F8FF"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FAFF"
    "\U00002600-\U000026FF"
    "\U00002700-\U000027BF"
    "\U0001F1E0-\U0001F1FF"
    "]+",
    flags=re.UNICODE
)


# ==================================================================
#                          ЯДРО БОТА
# ==================================================================
class TTSChatBot:
    def __init__(self, config, log_callback):
        self.config = config
        self.log = log_callback
        self.speech_queue = queue.Queue()
        self.running = False
        self.sock = None

        self.lists_lock = threading.Lock()
        self.blacklist = set(n.lower() for n in config.get("blacklist", []))
        self.whitelist = set(n.lower() for n in config.get("whitelist", []))

        self.user_message_history = defaultdict(lambda: deque(maxlen=10))
        self.history_lock = threading.Lock()

        self.stats = defaultdict(int)
        self.stats_lock = threading.Lock()

        self.tts_thread = None

    def _lang(self):
        return self.config.get("language", "ru")

    # ------------------ ОЗВУЧКА ------------------
    def _build_rate_str(self, value):
        return f"{value:+d}%"

    def _build_volume_str(self, value):
        return f"{value:+d}%"

    def _build_pitch_str(self, value):
        return f"{value:+d}Hz"

    async def _synthesize(self, text, output_file):
        communicate = edge_tts.Communicate(
            text,
            self.config.get("voice_name", "ru-RU-DmitryNeural"),
            rate=self._build_rate_str(self.config.get("voice_rate", 0)),
            volume=self._build_volume_str(self.config.get("voice_volume", 0)),
            pitch=self._build_pitch_str(self.config.get("voice_pitch", 0)),
        )
        await communicate.save(output_file)

    def _play_file(self, path):
        try:
            from playsound3 import playsound
            playsound(path)
        except Exception as e:
            self.log(tr("log_play_error", self._lang(), error=e), "error")

    def _build_phrase(self, name, text):
        read_name = self.config.get("read_username", True)
        read_says = self.config.get("read_says_word", True)
        template = self.config.get("speech_template", "{name} пишет: {text}")

        if "{text}" not in template:
            template = template + " {text}"

        if not read_name:
            template = template.replace("{name}", "")

        if not read_says:
            template = re.sub(r"\s*пишет\s*:?\s*", " ", template,
                              flags=re.IGNORECASE)
            template = re.sub(r"\s*говорит\s*:?\s*", " ", template,
                              flags=re.IGNORECASE)
            template = re.sub(r"\s*says\s*:?\s*", " ", template,
                              flags=re.IGNORECASE)

        try:
            phrase = template.format(name=name, text=text)
        except (KeyError, IndexError):
            phrase = f"{name}: {text}" if read_name else text

        phrase = re.sub(r"\s+", " ", phrase).strip()
        phrase = re.sub(r"^[:\s]+", "", phrase)
        phrase = re.sub(r"\s*:\s*$", "", phrase)

        return phrase or text

    def tts_worker(self):
        while self.running or not self.speech_queue.empty():
            try:
                text = self.speech_queue.get(timeout=0.5)
            except queue.Empty:
                continue
            if text is None:
                break

            try:
                clean = text.replace("!", "").replace("@", "").strip()
                if not clean:
                    continue

                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                    tmp_path = tmp.name

                try:
                    asyncio.run(self._synthesize(clean, tmp_path))
                    self._play_file(tmp_path)
                finally:
                    try:
                        if os.path.exists(tmp_path):
                            os.remove(tmp_path)
                    except Exception:
                        pass
            except Exception as e:
                self.log(tr("log_tts_error", self._lang(), error=e), "error")

    # ------------------ СПИСКИ ------------------
    def is_blacklisted(self, username):
        with self.lists_lock:
            return username.lower() in self.blacklist

    def is_whitelisted(self, username):
        with self.lists_lock:
            return username.lower() in self.whitelist

    def add_to_blacklist(self, username):
        name = username.lower().lstrip("@")
        with self.lists_lock:
            if name in self.blacklist:
                return False
            self.blacklist.add(name)
            self.whitelist.discard(name)
        self.save_lists()
        return True

    def remove_from_blacklist(self, username):
        name = username.lower().lstrip("@")
        with self.lists_lock:
            if name not in self.blacklist:
                return False
            self.blacklist.remove(name)
        self.save_lists()
        return True

    def add_to_whitelist(self, username):
        name = username.lower().lstrip("@")
        with self.lists_lock:
            if name in self.whitelist:
                return False
            self.whitelist.add(name)
            self.blacklist.discard(name)
        self.save_lists()
        return True

    def remove_from_whitelist(self, username):
        name = username.lower().lstrip("@")
        with self.lists_lock:
            if name not in self.whitelist:
                return False
            self.whitelist.remove(name)
        self.save_lists()
        return True

    def get_lists(self):
        with self.lists_lock:
            return sorted(self.blacklist), sorted(self.whitelist)

    def load_lists(self):
        path = self.config.get("lists_file", "tts_lists.json")
        if not os.path.exists(path):
            self.save_lists()
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            with self.lists_lock:
                file_black = set(n.lower() for n in data.get("blacklist", []))
                file_white = set(n.lower() for n in data.get("whitelist", []))
                self.blacklist |= file_black
                self.whitelist |= file_white
                self.whitelist -= self.blacklist
            self.log(tr("log_lists_loaded", self._lang(),
                        b=len(self.blacklist), w=len(self.whitelist)), "info")
        except Exception as e:
            self.log(tr("log_lists_load_error", self._lang(), error=e), "error")

    def save_lists(self):
        path = self.config.get("lists_file", "tts_lists.json")
        with self.lists_lock:
            data = {
                "blacklist": sorted(self.blacklist),
                "whitelist": sorted(self.whitelist),
                "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
        try:
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, path)
        except Exception as e:
            self.log(tr("log_lists_save_error", self._lang(), error=e), "error")

    # ------------------ ФИЛЬТРЫ ------------------
    def is_bot(self, username):
        if not self.config.get("filter_bots", True):
            return False
        name = username.lower()
        return name in self.config.get("bot_names", []) or name.endswith("bot")

    def is_command(self, message):
        if not self.config.get("filter_commands", True):
            return False
        return message.strip().startswith(
            tuple(self.config.get("command_prefixes", ["!"])))

    def has_link(self, message):
        if not self.config.get("filter_links", True):
            return False
        return bool(LINK_PATTERN.search(message))

    def is_caps_spam(self, message):
        if not self.config.get("filter_caps", True):
            return False
        letters = [c for c in message if c.isalpha()]
        min_len = self.config.get("caps_min_length", 8)
        if len(letters) < min_len:
            return False
        upper = sum(1 for c in letters if c.isupper())
        return (upper / len(letters)) > self.config.get("caps_threshold", 0.7)

    def is_bad_length(self, message):
        if not self.config.get("filter_length", True):
            return False
        s = message.strip()
        return (len(s) < self.config.get("min_length", 2) or
                len(s) > self.config.get("max_length", 200))

    def is_emoji_spam(self, message):
        if not self.config.get("filter_emoji_spam", True):
            return False
        if not message:
            return False
        emoji_chars = sum(len(m) for m in EMOJI_PATTERN.findall(message))
        return (emoji_chars / len(message)) > self.config.get("emoji_threshold", 0.5)

    def is_repeat(self, username, message):
        if not self.config.get("filter_repeats", True):
            return False
        now = time.time()
        window = self.config.get("repeat_window", 60)
        max_count = self.config.get("repeat_max_count", 2)
        normalized = message.strip().lower()
        with self.history_lock:
            history = self.user_message_history[username.lower()]
            while history and now - history[0][0] > window:
                history.popleft()
            count = sum(1 for _, msg in history if msg == normalized)
            history.append((now, normalized))
        return count >= max_count

    def contains_stopwords(self, message):
        if not self.config.get("filter_stopwords", True):
            return False
        lowered = message.lower()
        for word in self.config.get("stopwords", []):
            if re.search(rf"\b{re.escape(word)}\w*", lowered):
                return True
        return False

    def censor_message(self, message):
        result = message
        for word in self.config.get("stopwords", []):
            result = re.sub(rf"\b{re.escape(word)}\w*", "бип", result,
                            flags=re.IGNORECASE)
        return result

    def should_speak(self, username, message):
        name = username.lower()

        if self.is_blacklisted(name):
            return False, "blacklist"
        if self.is_bot(name):
            return False, "bot"
        if self.is_whitelisted(name):
            return True, message
        if self.is_command(message):
            return False, "command"
        if self.has_link(message):
            return False, "link"
        if self.is_bad_length(message):
            return False, "length"
        if self.is_caps_spam(message):
            return False, "caps"
        if self.is_emoji_spam(message):
            return False, "emoji"
        if self.is_repeat(username, message):
            return False, "repeat"
        if self.contains_stopwords(message):
            if self.config.get("censor_stopwords", True):
                message = self.censor_message(message)
            else:
                return False, "stopword"
        return True, message

    def _bump_stat(self, key):
        with self.stats_lock:
            self.stats[key] += 1

    def get_stats(self):
        with self.stats_lock:
            return dict(self.stats)

    # ------------------ УПРАВЛЕНИЕ ИЗ ЧАТА ------------------
    def is_privileged(self, tags):
        badges = tags.get("badges", "")
        allowed = self.config.get("command_permission", ["broadcaster", "moderator"])
        for badge in badges.split(","):
            if badge.split("/")[0] in allowed:
                return True
        return tags.get("login", "").lower() == self.config.get("channel", "").lower()

    def handle_control_command(self, message, tags):
        if not self.config.get("allow_chat_commands", True):
            return False
        msg = message.strip()
        if not msg.lower().startswith("!tts "):
            return False
        lang = self._lang()
        display = tags.get("display-name", "кто-то")
        if not self.is_privileged(tags):
            self.log(tr("log_perm_denied", lang, name=display), "warn")
            return True

        parts = msg.split()
        if len(parts) < 2:
            return True
        action = parts[1].lower()
        target = parts[2].lstrip("@").lower() if len(parts) >= 3 else None

        if action == "ban" and target:
            if self.add_to_blacklist(target):
                self.log(tr("log_cmd_ban", lang, name=display, target=target), "info")
            else:
                self.log(tr("log_cmd_ban_already", lang, name=display,
                            target=target), "info")
        elif action == "unban" and target:
            if self.remove_from_blacklist(target):
                self.log(tr("log_cmd_unban", lang, name=display, target=target), "info")
            else:
                self.log(tr("log_cmd_unban_not", lang, name=display,
                            target=target), "info")
        elif action == "allow" and target:
            if self.add_to_whitelist(target):
                self.log(tr("log_cmd_allow", lang, name=display, target=target), "info")
            else:
                self.log(tr("log_cmd_allow_already", lang, name=display,
                            target=target), "info")
        elif action == "deny" and target:
            if self.remove_from_whitelist(target):
                self.log(tr("log_cmd_deny", lang, name=display, target=target), "info")
            else:
                self.log(tr("log_cmd_deny_not", lang, name=display,
                            target=target), "info")
        elif action == "list":
            b, w = self.get_lists()
            self.log(f"📋 BAN ({len(b)}): {', '.join(b) or '—'}", "info")
            self.log(f"📋 WHITE ({len(w)}): {', '.join(w) or '—'}", "info")
        elif action == "save":
            self.save_lists()
            self.log(tr("log_cmd_save", lang, name=display), "info")
        elif action == "reload":
            self.load_lists()
            self.log(tr("log_cmd_reload", lang, name=display), "info")
        elif action == "help":
            self.log(tr("log_cmd_help", lang), "info")
        return True

    # ------------------ ПОДКЛЮЧЕНИЕ ------------------
    @staticmethod
    def parse_tags(line):
        tags = {}
        if line.startswith("@"):
            tag_str = line[1:].split(" ", 1)[0]
            for pair in tag_str.split(";"):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    tags[k] = v
        return tags

    def connect(self):
        lang = self._lang()
        token = self.config.get("oauth_token", "").strip()
        channel = self.config.get("channel", "").strip().lower()

        if not token or not channel:
            self.log(tr("log_fill_fields", lang), "error")
            return False

        if not token.startswith("oauth:"):
            token = "oauth:" + token

        self.load_lists()

        try:
            self.sock = socket.socket()
            self.sock.settimeout(10)
            self.sock.connect(("irc.chat.twitch.tv", 6667))
            self.sock.settimeout(None)
        except Exception as e:
            self.log(tr("log_connect_error", lang, error=e), "error")
            return False

        try:
            self.sock.send(f"PASS {token}\n".encode("utf-8"))
            self.sock.send(
                f"NICK {self.config.get('bot_name', 'tts_bot')}\n".encode("utf-8"))
            self.sock.send("CAP REQ :twitch.tv/tags\n".encode("utf-8"))
            self.sock.send(f"JOIN #{channel}\n".encode("utf-8"))
        except Exception as e:
            self.log(tr("log_send_error", lang, error=e), "error")
            return False

        self.running = True
        self.tts_thread = threading.Thread(target=self.tts_worker, daemon=True)
        self.tts_thread.start()

        self.log(tr("log_connected", lang, channel=channel), "success")

        recv_thread = threading.Thread(target=self._receive_loop, daemon=True)
        recv_thread.start()
        return True

    def _receive_loop(self):
        buffer = ""
        try:
            while self.running:
                try:
                    data = self.sock.recv(4096).decode("utf-8", errors="ignore")
                except socket.timeout:
                    continue
                except OSError:
                    break
                if not data:
                    break
                buffer += data
                while "\r\n" in buffer:
                    line, buffer = buffer.split("\r\n", 1)
                    self._process_line(line)
        except Exception as e:
            if self.running:
                self.log(tr("log_conn_lost", self._lang(), error=e), "error")
        finally:
            self.running = False
            try:
                if self.sock:
                    self.sock.close()
            except Exception:
                pass
            self.speech_queue.put(None)
            self.log(tr("log_disconnected", self._lang()), "warn")

    def _process_line(self, line):
        if line.startswith("PING"):
            try:
                self.sock.send("PONG :tmi.twitch.tv\n".encode("utf-8"))
            except Exception:
                pass
            return

        if "PRIVMSG" not in line:
            return

        try:
            tags = self.parse_tags(line)
            username = tags.get("login", "")
            display = tags.get("display-name", username) or username

            msg_part = line.split("PRIVMSG", 1)[1]
            if ":" not in msg_part:
                return
            message = msg_part.split(":", 1)[1]

            if self.handle_control_command(message, tags):
                self._bump_stat("__command__")
                return

            ok, result = self.should_speak(username, message)
            lang = self._lang()
            if ok:
                self._bump_stat("__spoken__")
                self.log(tr("log_spoken", lang, name=display, message=message),
                         "spoken")
                phrase = self._build_phrase(display, result)
                self.speech_queue.put(phrase)
            else:
                self._bump_stat(result)
                self.log(tr("log_filtered", lang, name=display,
                            reason=result, message=message), "filtered")
        except Exception as e:
            self.log(tr("log_parse_error", self._lang(), error=e), "error")

    def disconnect(self):
        self.running = False
        try:
            if self.sock:
                self.sock.close()
        except Exception:
            pass
        self.log(tr("log_connecting", self._lang()), "warn")

    def skip_current(self):
        while not self.speech_queue.empty():
            try:
                self.speech_queue.get_nowait()
            except queue.Empty:
                break
        self.log(tr("log_skip", self._lang()), "warn")


# ==================================================================
#                        ГРАФИЧЕСКИЙ ИНТЕРФЕЙС
# ==================================================================
class TTSApp:
    def __init__(self, root):
        self.root = root
        self.root.geometry("1100x820")
        self.root.minsize(900, 680)

        self.config = self.load_config()
        self.lang = self.config.get("language", "ru")

        self.root.title(tr("app_title", self.lang, name=APP_NAME,
                            version=APP_VERSION, author=APP_AUTHOR))

        self.bot = TTSChatBot(self.config, self.log)

        self.notebook = None
        self.tabs = {}

        self._build_ui()
        self._refresh_lists_display()
        self._refresh_stats()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------ КОНФИГ ------------------
    def load_config(self):
        path = DEFAULT_CONFIG["config_file"]
        cfg = dict(DEFAULT_CONFIG)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                cfg.update(saved)
            except Exception:
                pass
        return cfg

    def save_config(self):
        self.config["channel"] = self.entry_channel.get().strip().lower()
        self.config["oauth_token"] = self.entry_token.get().strip()
        self.config["language"] = self.lang

        self.config["voice_name"] = self.combo_voice.get().split(" ")[0]
        self.config["voice_rate"] = int(self.scale_rate.get())
        self.config["voice_volume"] = int(self.scale_volume.get())
        self.config["voice_pitch"] = int(self.scale_pitch.get())

        self.config["read_username"] = self.var_read_username.get()
        self.config["read_says_word"] = self.var_read_says.get()
        self.config["speech_template"] = (self.entry_template.get().strip()
                                          or "{name} пишет: {text}")

        self.config["filter_commands"] = self.var_filter_commands.get()
        self.config["filter_bots"] = self.var_filter_bots.get()
        self.config["filter_links"] = self.var_filter_links.get()
        self.config["filter_caps"] = self.var_filter_caps.get()
        self.config["filter_length"] = self.var_filter_length.get()
        self.config["filter_emoji_spam"] = self.var_filter_emoji.get()
        self.config["filter_repeats"] = self.var_filter_repeats.get()
        self.config["filter_stopwords"] = self.var_filter_stopwords.get()
        self.config["censor_stopwords"] = self.var_censor.get()
        self.config["allow_chat_commands"] = self.var_chat_commands.get()

        try:
            self.config["max_length"] = int(self.entry_max_len.get())
            self.config["min_length"] = int(self.entry_min_len.get())
            self.config["caps_threshold"] = float(self.entry_caps.get())
            self.config["repeat_max_count"] = int(self.entry_repeat_count.get())
            self.config["repeat_window"] = int(self.entry_repeat_window.get())
        except ValueError:
            pass

        self.config["stopwords"] = [
            w.strip() for w in self.text_stopwords.get("1.0", "end").splitlines()
            if w.strip()
        ]
        self.config["bot_names"] = [
            w.strip().lower() for w in self.text_bots.get("1.0", "end").splitlines()
            if w.strip()
        ]

        path = self.config["config_file"]
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.log(tr("log_config_save_error", self.lang, error=e), "error")

    # ------------------ UI ------------------
    def _build_ui(self):
        top = ttk.LabelFrame(self.root, text=tr("conn_frame", self.lang), padding=8)
        top.pack(fill="x", padx=8, pady=(8, 4))

        ttk.Label(top, text=tr("lang_label", self.lang)).grid(row=0, column=0, sticky="w")

        self.combo_lang = ttk.Combobox(top, state="readonly", width=5,
                                        values=["ru", "en"])
        self.combo_lang.set(self.lang)
        self.combo_lang.grid(row=0, column=1, padx=(4, 12))
        self.combo_lang.bind("<<ComboboxSelected>>", self._on_language_change)

        ttk.Label(top, text=tr("channel", self.lang)).grid(row=0, column=2, sticky="w")
        self.entry_channel = ttk.Entry(top, width=18)
        self.entry_channel.grid(row=0, column=3, padx=(4, 12))
        self.entry_channel.insert(0, self.config.get("channel", ""))

        ttk.Label(top, text=tr("token", self.lang)).grid(row=0, column=4, sticky="w")
        self.entry_token = ttk.Entry(top, width=28, show="•")
        self.entry_token.grid(row=0, column=5, padx=(4, 4))
        self.entry_token.insert(0, self.config.get("oauth_token", ""))

        self.entry_token.bind("<Control-v>", self._on_token_paste)
        self.entry_token.bind("<Control-V>", self._on_token_paste)

        self.var_show_token = tk.BooleanVar(value=False)
        ttk.Checkbutton(top, text="👁", variable=self.var_show_token,
                        command=self._toggle_token_visibility,
                        width=3).grid(row=0, column=6, padx=(0, 4))

        ttk.Button(top, text=tr("btn_paste", self.lang),
                   command=self._paste_token_from_clipboard,
                   width=11).grid(row=0, column=7, padx=(0, 8))

        self.btn_connect = ttk.Button(top, text=tr("btn_connect", self.lang),
                                       command=self._toggle_connect)
        self.btn_connect.grid(row=0, column=8, padx=4)

        ttk.Button(top, text=tr("btn_skip", self.lang),
                   command=self._skip_current).grid(row=0, column=9, padx=4)

        self.lbl_status = ttk.Label(top, text=tr("status_off", self.lang),
                                     foreground="gray", font=("", 10, "bold"))
        self.lbl_status.grid(row=0, column=10, padx=12)

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=8, pady=4)

        # --- ЧАТ ---
        tab_chat = ttk.Frame(self.notebook)
        self.notebook.add(tab_chat, text=tr("tab_chat", self.lang))
        self.tabs["tab_chat"] = tab_chat

        self.chat_log = scrolledtext.ScrolledText(tab_chat, wrap="word",
                                                    font=("Consolas", 10),
                                                    state="disabled")
        self.chat_log.pack(fill="both", expand=True, padx=4, pady=4)
        self.chat_log.tag_config("spoken", foreground="#1a7f37")
        self.chat_log.tag_config("filtered", foreground="#999999")
        self.chat_log.tag_config("info", foreground="#0958d9")
        self.chat_log.tag_config("warn", foreground="#b8860b")
        self.chat_log.tag_config("error", foreground="#c92a2a")
        self.chat_log.tag_config("success", foreground="#1a7f37",
                                  font=("Consolas", 10, "bold"))

        chat_btns = ttk.Frame(tab_chat)
        chat_btns.pack(fill="x", padx=4, pady=(0, 4))
        ttk.Button(chat_btns, text=tr("btn_clear_log", self.lang),
                   command=self._clear_log).pack(side="left", padx=2)
        ttk.Button(chat_btns, text=tr("btn_save_log", self.lang),
                   command=self._save_log).pack(side="left", padx=2)

        # --- СПИСКИ ---
        tab_lists = ttk.Frame(self.notebook)
        self.notebook.add(tab_lists, text=tr("tab_lists", self.lang))
        self.tabs["tab_lists"] = tab_lists

        lists_frame = ttk.Frame(tab_lists)
        lists_frame.pack(fill="both", expand=True, padx=8, pady=8)

        black_frame = ttk.LabelFrame(lists_frame,
                                      text=tr("black_frame", self.lang),
                                      padding=8)
        black_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 4))

        self.listbox_black = tk.Listbox(black_frame, height=14)
        self.listbox_black.pack(fill="both", expand=True)

        b1 = ttk.Frame(black_frame)
        b1.pack(fill="x", pady=(6, 0))
        self.entry_black = ttk.Entry(b1)
        self.entry_black.pack(side="left", fill="x", expand=True)
        ttk.Button(b1, text=tr("btn_add", self.lang),
                   command=self._add_black).pack(side="left", padx=(4, 0))

        b2 = ttk.Frame(black_frame)
        b2.pack(fill="x", pady=(4, 0))
        ttk.Button(b2, text=tr("btn_remove_selected", self.lang),
                   command=self._remove_black).pack(side="left")

        white_frame = ttk.LabelFrame(lists_frame,
                                      text=tr("white_frame", self.lang),
                                      padding=8)
        white_frame.grid(row=0, column=1, sticky="nsew", padx=(4, 0))

        self.listbox_white = tk.Listbox(white_frame, height=14)
        self.listbox_white.pack(fill="both", expand=True)

        w1 = ttk.Frame(white_frame)
        w1.pack(fill="x", pady=(6, 0))
        self.entry_white = ttk.Entry(w1)
        self.entry_white.pack(side="left", fill="x", expand=True)
        ttk.Button(w1, text=tr("btn_add", self.lang),
                   command=self._add_white).pack(side="left", padx=(4, 0))

        w2 = ttk.Frame(white_frame)
        w2.pack(fill="x", pady=(4, 0))
        ttk.Button(w2, text=tr("btn_remove_selected", self.lang),
                   command=self._remove_white).pack(side="left")

        lists_frame.columnconfigure(0, weight=1)
        lists_frame.columnconfigure(1, weight=1)
        lists_frame.rowconfigure(0, weight=1)

        bottom_lists = ttk.Frame(tab_lists)
        bottom_lists.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bottom_lists, text=tr("btn_save_file", self.lang),
                   command=self._save_lists_manual).pack(side="left", padx=2)
        ttk.Button(bottom_lists, text=tr("btn_reload_file", self.lang),
                   command=self._reload_lists).pack(side="left", padx=2)

        # --- ФИЛЬТРЫ ---
        tab_filters = ttk.Frame(self.notebook)
        self.notebook.add(tab_filters, text=tr("tab_filters", self.lang))
        self.tabs["tab_filters"] = tab_filters
        self._build_filters_tab(tab_filters)

        # --- ГОЛОС ---
        tab_voice = ttk.Frame(self.notebook)
        self.notebook.add(tab_voice, text=tr("tab_voice", self.lang))
        self.tabs["tab_voice"] = tab_voice
        self._build_voice_tab(tab_voice)

        # --- СТАТИСТИКА ---
        tab_stats = ttk.Frame(self.notebook)
        self.notebook.add(tab_stats, text=tr("tab_stats", self.lang))
        self.tabs["tab_stats"] = tab_stats

        self.stats_text = scrolledtext.ScrolledText(tab_stats, wrap="word",
                                                     font=("Consolas", 10),
                                                     state="disabled")
        self.stats_text.pack(fill="both", expand=True, padx=8, pady=8)
        ttk.Button(tab_stats, text="🔄",
                   command=self._refresh_stats).pack(pady=(0, 8))

        # --- ОБНОВЛЕНИЕ ---
        tab_update = ttk.Frame(self.notebook)
        self.notebook.add(tab_update, text=tr("tab_update", self.lang))
        self.tabs["tab_update"] = tab_update
        self._build_update_tab(tab_update)

        # --- ДОНАТ ---
        tab_donate = ttk.Frame(self.notebook)
        self.notebook.add(tab_donate, text=tr("tab_donate", self.lang))
        self.tabs["tab_donate"] = tab_donate
        self._build_donate_tab(tab_donate)

        # --- СОЦСЕТИ ---
        tab_social = ttk.Frame(self.notebook)
        self.notebook.add(tab_social, text=tr("tab_social", self.lang))
        self.tabs["tab_social"] = tab_social
        self._build_social_tab(tab_social)

        # --- НИЗ ---
        bottom = ttk.Frame(self.root)
        bottom.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bottom, text=tr("btn_save_settings", self.lang),
                   command=self._save_all).pack(side="right", padx=2)

    def _build_filters_tab(self, parent):
        canvas = tk.Canvas(parent, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        inner = ttk.Frame(canvas)
        inner.bind("<Configure>",
                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.var_filter_commands = tk.BooleanVar(value=self.config.get("filter_commands", True))
        self.var_filter_bots = tk.BooleanVar(value=self.config.get("filter_bots", True))
        self.var_filter_links = tk.BooleanVar(value=self.config.get("filter_links", True))
        self.var_filter_caps = tk.BooleanVar(value=self.config.get("filter_caps", True))
        self.var_filter_length = tk.BooleanVar(value=self.config.get("filter_length", True))
        self.var_filter_emoji = tk.BooleanVar(value=self.config.get("filter_emoji_spam", True))
        self.var_filter_repeats = tk.BooleanVar(value=self.config.get("filter_repeats", True))
        self.var_filter_stopwords = tk.BooleanVar(value=self.config.get("filter_stopwords", True))
        self.var_censor = tk.BooleanVar(value=self.config.get("censor_stopwords", True))
        self.var_chat_commands = tk.BooleanVar(value=self.config.get("allow_chat_commands", True))

        rows = [
            (tr("filter_commands", self.lang), self.var_filter_commands),
            (tr("filter_bots", self.lang), self.var_filter_bots),
            (tr("filter_links", self.lang), self.var_filter_links),
            (tr("filter_caps", self.lang), self.var_filter_caps),
            (tr("filter_length", self.lang), self.var_filter_length),
            (tr("filter_emoji", self.lang), self.var_filter_emoji),
            (tr("filter_repeats", self.lang), self.var_filter_repeats),
            (tr("filter_stopwords", self.lang), self.var_filter_stopwords),
            (tr("censor_stopwords", self.lang), self.var_censor),
            (tr("allow_chat_commands", self.lang), self.var_chat_commands),
        ]
        for text, var in rows:
            ttk.Checkbutton(inner, text=text, variable=var).pack(
                anchor="w", padx=8, pady=2)

        nums = ttk.LabelFrame(inner, text=tr("num_params", self.lang), padding=8)
        nums.pack(fill="x", padx=8, pady=8)

        ttk.Label(nums, text=tr("max_length", self.lang)).grid(row=0, column=0, sticky="w")
        self.entry_max_len = ttk.Entry(nums, width=8)
        self.entry_max_len.grid(row=0, column=1, padx=4)
        self.entry_max_len.insert(0, str(self.config.get("max_length", 200)))

        ttk.Label(nums, text=tr("min_length", self.lang)).grid(
            row=0, column=2, sticky="w", padx=(12, 0))
        self.entry_min_len = ttk.Entry(nums, width=8)
        self.entry_min_len.grid(row=0, column=3, padx=4)
        self.entry_min_len.insert(0, str(self.config.get("min_length", 2)))

        ttk.Label(nums, text=tr("caps_threshold", self.lang)).grid(
            row=1, column=0, sticky="w")
        self.entry_caps = ttk.Entry(nums, width=8)
        self.entry_caps.grid(row=1, column=1, padx=4)
        self.entry_caps.insert(0, str(self.config.get("caps_threshold", 0.7)))

        ttk.Label(nums, text=tr("repeat_count", self.lang)).grid(
            row=1, column=2, sticky="w", padx=(12, 0))
        self.entry_repeat_count = ttk.Entry(nums, width=8)
        self.entry_repeat_count.grid(row=1, column=3, padx=4)
        self.entry_repeat_count.insert(0, str(self.config.get("repeat_max_count", 2)))

        ttk.Label(nums, text=tr("repeat_window", self.lang)).grid(
            row=2, column=0, sticky="w")
        self.entry_repeat_window = ttk.Entry(nums, width=8)
        self.entry_repeat_window.grid(row=2, column=1, padx=4)
        self.entry_repeat_window.insert(0, str(self.config.get("repeat_window", 60)))

        sw_frame = ttk.LabelFrame(inner, text=tr("stopwords_frame", self.lang),
                                   padding=8)
        sw_frame.pack(fill="both", expand=True, padx=8, pady=8)
        self.text_stopwords = scrolledtext.ScrolledText(sw_frame, height=8,
                                                          font=("Consolas", 10))
        self.text_stopwords.pack(fill="both", expand=True)
        self.text_stopwords.insert("1.0", "\n".join(self.config.get("stopwords", [])))

        bots_frame = ttk.LabelFrame(inner, text=tr("bots_frame", self.lang),
                                     padding=8)
        bots_frame.pack(fill="both", expand=True, padx=8, pady=8)
        self.text_bots = scrolledtext.ScrolledText(bots_frame, height=8,
                                                     font=("Consolas", 10))
        self.text_bots.pack(fill="both", expand=True)
        self.text_bots.insert("1.0", "\n".join(self.config.get("bot_names", [])))

    def _build_voice_tab(self, parent):
        canvas = tk.Canvas(parent, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        frame = ttk.Frame(canvas)
        frame.bind("<Configure>",
                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        ttk.Label(frame, text=tr("voice_label", self.lang)).grid(
            row=0, column=0, sticky="w", pady=4, padx=(8, 0))
        self.combo_voice = ttk.Combobox(frame, state="readonly", width=50)

        voices = [
            "ru-RU-DmitryNeural (мужской / male)",
            "ru-RU-SvetlanaNeural (женский / female)",
        ]
        self.combo_voice["values"] = voices
        saved_voice = self.config.get("voice_name", "ru-RU-DmitryNeural")
        idx = 0
        for i, v in enumerate(voices):
            if v.startswith(saved_voice):
                idx = i
                break
        self.combo_voice.current(idx)
        self.combo_voice.grid(row=0, column=1, pady=4, sticky="ew", padx=(0, 8))

        ttk.Label(frame, text=tr("voice_rate", self.lang)).grid(
            row=1, column=0, sticky="w", pady=4, padx=(8, 0))
        self.scale_rate = ttk.Scale(frame, from_=-50, to=100,
                                     orient="horizontal", length=400)
        self.scale_rate.set(self.config.get("voice_rate", 0))
        self.scale_rate.grid(row=1, column=1, pady=4, sticky="ew")
        self.lbl_rate = ttk.Label(frame, text=f"{int(self.scale_rate.get()):+d}%")
        self.lbl_rate.grid(row=1, column=2, padx=8)
        self.scale_rate.configure(
            command=lambda v: self.lbl_rate.config(text=f"{int(float(v)):+d}%"))

        ttk.Label(frame, text=tr("voice_volume", self.lang)).grid(
            row=2, column=0, sticky="w", pady=4, padx=(8, 0))
        self.scale_volume = ttk.Scale(frame, from_=-50, to=50,
                                       orient="horizontal", length=400)
        self.scale_volume.set(self.config.get("voice_volume", 0))
        self.scale_volume.grid(row=2, column=1, pady=4, sticky="ew")
        self.lbl_volume = ttk.Label(frame, text=f"{int(self.scale_volume.get()):+d}%")
        self.lbl_volume.grid(row=2, column=2, padx=8)
        self.scale_volume.configure(
            command=lambda v: self.lbl_volume.config(text=f"{int(float(v)):+d}%"))

        ttk.Label(frame, text=tr("voice_pitch", self.lang)).grid(
            row=3, column=0, sticky="w", pady=4, padx=(8, 0))
        self.scale_pitch = ttk.Scale(frame, from_=-50, to=50,
                                      orient="horizontal", length=400)
        self.scale_pitch.set(self.config.get("voice_pitch", 0))
        self.scale_pitch.grid(row=3, column=1, pady=4, sticky="ew")
        self.lbl_pitch = ttk.Label(frame, text=f"{int(self.scale_pitch.get()):+d}Hz")
        self.lbl_pitch.grid(row=3, column=2, padx=8)
        self.scale_pitch.configure(
            command=lambda v: self.lbl_pitch.config(text=f"{int(float(v)):+d}Hz"))

        ttk.Button(frame, text=tr("btn_test_voice", self.lang),
                   command=self._test_voice).grid(
            row=4, column=0, pady=20, sticky="w", padx=(8, 0))

        fmt_frame = ttk.LabelFrame(frame, text=tr("fmt_frame", self.lang), padding=8)
        fmt_frame.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(8, 4), padx=8)

        self.var_read_username = tk.BooleanVar(
            value=self.config.get("read_username", True))
        self.var_read_says = tk.BooleanVar(
            value=self.config.get("read_says_word", True))

        ttk.Checkbutton(fmt_frame, text=tr("read_username", self.lang),
                        variable=self.var_read_username,
                        command=self._update_template_preview).pack(anchor="w", pady=2)

        ttk.Checkbutton(fmt_frame, text=tr("read_says_word", self.lang),
                        variable=self.var_read_says,
                        command=self._update_template_preview).pack(anchor="w", pady=2)

        ttk.Label(fmt_frame, text=tr("template_label", self.lang)).pack(
            anchor="w", pady=(8, 2))

        self.entry_template = ttk.Entry(fmt_frame, width=60)
        self.entry_template.pack(fill="x", pady=2)
        self.entry_template.insert(0, self.config.get("speech_template",
                                                       "{name} пишет: {text}"))

        self.lbl_template_preview = ttk.Label(fmt_frame, text="...",
                                               foreground="gray")
        self.lbl_template_preview.pack(anchor="w", pady=(4, 0))

        self.entry_template.bind("<KeyRelease>",
                                  lambda e: self._update_template_preview())

        ttk.Label(frame, text=tr("voice_note", self.lang), foreground="gray").grid(
            row=6, column=0, columnspan=3, sticky="w", pady=(12, 8), padx=8)
        frame.columnconfigure(1, weight=1)

        self._update_template_preview()

    def _build_update_tab(self, parent):
        frame = ttk.Frame(parent, padding=20)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text=tr("upd_title", self.lang, name=APP_NAME),
                  font=("", 16, "bold")).pack(anchor="w")
        ttk.Label(frame, text=tr("upd_version", self.lang, version=APP_VERSION),
                  foreground="gray").pack(anchor="w", pady=(2, 0))
        ttk.Label(frame, text=tr("upd_author", self.lang, author=APP_AUTHOR),
                  foreground="gray").pack(anchor="w", pady=(2, 16))

        info = ttk.LabelFrame(frame, text=tr("upd_links", self.lang), padding=12)
        info.pack(fill="x", pady=(0, 12))

        ttk.Label(info, text=tr("upd_repo_label", self.lang)).pack(anchor="w")
        ttk.Label(info, text=REPO_URL, foreground="#0958d9",
                  font=("", 10, "underline")).pack(anchor="w", pady=(2, 8))

        btns = ttk.Frame(frame)
        btns.pack(fill="x", pady=(0, 12))

        ttk.Button(btns, text=tr("upd_btn_open", self.lang),
                   command=lambda: self._open_url(REPO_URL, "GitHub")
                   ).pack(side="left", padx=(0, 8))
        ttk.Button(btns, text=tr("upd_btn_copy", self.lang),
                   command=lambda: self._copy_url(REPO_URL)
                   ).pack(side="left", padx=(0, 8))

        notes = ttk.LabelFrame(frame, text=tr("upd_notes", self.lang), padding=12)
        notes.pack(fill="both", expand=True)

        changelog = scrolledtext.ScrolledText(notes, wrap="word",
                                                font=("Consolas", 10), height=12)
        changelog.pack(fill="both", expand=True)

        changelog.insert("end", tr("upd_current", self.lang,
                                    version=APP_VERSION) + "\n\n")
        changelog.insert("end", tr("upd_history", self.lang) + "\n")
        changelog.insert("end", "─" * 50 + "\n\n")
        changelog.insert("end",
            "v4.1.3\n"
            f"  • Developer: {APP_AUTHOR}\n"
            "  • Language switcher (RU / EN)\n"
            "  • Update, Donate, Socials tabs\n"
            "  • Speech format settings (nickname, «says», custom template)\n\n"
            "v1.0.0\n"
            "  • Initial release\n"
            "  • Twitch chat via IRC, edge-tts, GUI, filters, lists, stats\n"
        )
        changelog.config(state="disabled")

        ttk.Label(frame, text=tr("upd_hint", self.lang),
                  foreground="gray", justify="left").pack(anchor="w", pady=(12, 0))

    def _build_donate_tab(self, parent):
        frame = ttk.Frame(parent, padding=20)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text=tr("don_title", self.lang),
                  font=("", 16, "bold")).pack(anchor="w")
        ttk.Label(frame, text=tr("don_subtitle", self.lang),
                  foreground="gray", wraplength=600,
                  justify="left").pack(anchor="w", pady=(4, 20))

        for name, url in DONATE_URLS:
            card = ttk.LabelFrame(frame, text=name, padding=12)
            card.pack(fill="x", pady=(0, 12))

            ttk.Label(card, text=url, foreground="#0958d9",
                      font=("", 10)).pack(anchor="w", pady=(0, 8))

            btns = ttk.Frame(card)
            btns.pack(fill="x")

            ttk.Button(btns, text=tr("don_btn_open", self.lang, name=name),
                       command=lambda u=url, n=name: self._open_url(u, n)
                       ).pack(side="left", padx=(0, 8))
            ttk.Button(btns, text=tr("don_btn_copy", self.lang),
                       command=lambda u=url: self._copy_url(u)
                       ).pack(side="left")

        ttk.Label(frame, text=tr("don_note", self.lang),
                  foreground="gray", justify="left",
                  wraplength=600).pack(anchor="w", pady=(20, 0))

    def _build_social_tab(self, parent):
        frame = ttk.Frame(parent, padding=20)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text=tr("soc_title", self.lang),
                  font=("", 16, "bold")).pack(anchor="w")
        ttk.Label(frame, text=tr("soc_subtitle", self.lang),
                  foreground="gray", wraplength=600,
                  justify="left").pack(anchor="w", pady=(4, 20))

        for name, url in SOCIAL_URLS:
            card = ttk.LabelFrame(frame, text=name, padding=12)
            card.pack(fill="x", pady=(0, 12))

            ttk.Label(card, text=url, foreground="#0958d9",
                      font=("", 10)).pack(anchor="w", pady=(0, 8))

            btns = ttk.Frame(card)
            btns.pack(fill="x")

            ttk.Button(btns, text=tr("soc_btn_open", self.lang, name=name),
                       command=lambda u=url, n=name: self._open_url(u, n)
                       ).pack(side="left", padx=(0, 8))
            ttk.Button(btns, text=tr("soc_btn_copy", self.lang),
                       command=lambda u=url: self._copy_url(u)
                       ).pack(side="left")

        ttk.Label(frame, text=tr("soc_note", self.lang),
                  foreground="gray", justify="left",
                  wraplength=600).pack(anchor="w", pady=(20, 0))

    # ------------------ ЯЗЫК ------------------
    def _on_language_change(self, event=None):
        new_lang = self.combo_lang.get()
        if new_lang == self.lang:
            return
        self.lang = new_lang
        self.config["language"] = new_lang
        self.bot.config = self.config
        self.save_config()

        for key, widget in self.tabs.items():
            try:
                self.notebook.tab(widget, text=tr(key, self.lang))
            except Exception:
                pass

        self.root.title(tr("app_title", self.lang, name=APP_NAME,
                            version=APP_VERSION, author=APP_AUTHOR))
        self.log(tr("log_lang_changed", self.lang, lang=self.lang.upper()), "info")
        self.log(tr("log_lang_reload_hint", self.lang), "info")

    # ------------------ ТОКЕН ------------------
    def _on_token_paste(self, event=None):
        self._paste_token_from_clipboard()
        return "break"

    def _toggle_token_visibility(self):
        self.entry_token.config(show="" if self.var_show_token.get() else "•")

    def _paste_token_from_clipboard(self):
        try:
            text = self.root.clipboard_get()
        except tk.TclError:
            self.log(tr("log_clipboard_empty", self.lang), "warn")
            return
        text = text.strip().replace("\r", "").replace("\n", "")
        if text.lower().startswith("oauth:"):
            text = text[6:]
        self.entry_token.delete(0, "end")
        self.entry_token.insert(0, text)
        self.log(tr("log_token_pasted", self.lang, n=len(text)), "info")

    # ------------------ ПРЕВЬЮ ШАБЛОНА ------------------
    def _update_template_preview(self):
        template = self.entry_template.get() or "{name} пишет: {text}"

        if not self.var_read_username.get():
            template = template.replace("{name}", "")
        if not self.var_read_says.get():
            template = re.sub(r"\s*пишет\s*:?\s*", " ", template,
                              flags=re.IGNORECASE)
            template = re.sub(r"\s*говорит\s*:?\s*", " ", template,
                              flags=re.IGNORECASE)
            template = re.sub(r"\s*says\s*:?\s*", " ", template,
                              flags=re.IGNORECASE)

        try:
            example = template.format(name="Vasya", text="привет всем")
        except (KeyError, IndexError):
            example = tr("template_error", self.lang)

        example = re.sub(r"\s+", " ", example).strip()
        example = re.sub(r"^[:\s]+", "", example)
        if not example:
            example = tr("template_empty", self.lang)

        self.lbl_template_preview.config(
            text=tr("template_preview", self.lang, example=example))

    # ------------------ URL ------------------
    def _open_url(self, url, name=""):
        try:
            webbrowser.open(url)
            self.log(tr("log_opened", self.lang, name=name or url), "info")
        except Exception as e:
            self.log(tr("log_open_error", self.lang, error=e), "error")

    def _copy_url(self, url):
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(url)
            self.log(tr("log_copied", self.lang, url=url), "info")
        except Exception as e:
            self.log(tr("log_copy_error", self.lang, error=e), "error")

    # ------------------ ДЕЙСТВИЯ UI ------------------
    def _toggle_connect(self):
        if self.bot.running:
            self.bot.disconnect()
            self.btn_connect.config(text=tr("btn_connect", self.lang))
            self.lbl_status.config(text=tr("status_off", self.lang),
                                    foreground="gray")
        else:
            self.save_config()
            self.bot.config = self.config
            ok = self.bot.connect()
            if ok:
                self.btn_connect.config(text=tr("btn_disconnect", self.lang))
                self.lbl_status.config(text=tr("status_on", self.lang),
                                        foreground="green")

    def _skip_current(self):
        self.bot.skip_current()

    def _add_black(self):
        name = self.entry_black.get().strip()
        if not name:
            return
        if self.bot.add_to_blacklist(name):
            self.log(tr("log_added_black", self.lang, name=name), "info")
        self.entry_black.delete(0, "end")
        self._refresh_lists_display()

    def _remove_black(self):
        sel = self.listbox_black.curselection()
        if not sel:
            return
        name = self.listbox_black.get(sel[0])
        if self.bot.remove_from_blacklist(name):
            self.log(tr("log_removed_black", self.lang, name=name), "info")
        self._refresh_lists_display()

    def _add_white(self):
        name = self.entry_white.get().strip()
        if not name:
            return
        if self.bot.add_to_whitelist(name):
            self.log(tr("log_added_white", self.lang, name=name), "info")
        self.entry_white.delete(0, "end")
        self._refresh_lists_display()

    def _remove_white(self):
        sel = self.listbox_white.curselection()
        if not sel:
            return
        name = self.listbox_white.get(sel[0])
        if self.bot.remove_from_whitelist(name):
            self.log(tr("log_removed_white", self.lang, name=name), "info")
        self._refresh_lists_display()

    def _refresh_lists_display(self):
        b, w = self.bot.get_lists()
        self.listbox_black.delete(0, "end")
        self.listbox_white.delete(0, "end")
        for n in b:
            self.listbox_black.insert("end", n)
        for n in w:
            self.listbox_white.insert("end", n)

    def _save_lists_manual(self):
        self.bot.save_lists()
        self.log(tr("log_lists_saved", self.lang), "info")

    def _reload_lists(self):
        self.bot.load_lists()
        self._refresh_lists_display()
        self.log(tr("log_lists_reloaded", self.lang), "info")

    def _test_voice(self):
        self.save_config()
        self.bot.config = self.config
        try:
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                tmp_path = tmp.name

            test_phrase = self.bot._build_phrase("Vasya", "privet vsem")
            asyncio.run(self.bot._synthesize(test_phrase, tmp_path))
            self.bot._play_file(tmp_path)
            self.root.after(8000, lambda: self._cleanup_temp(tmp_path))
        except Exception as e:
            self.log(tr("log_test_error", self.lang, error=e), "error")

    def _cleanup_temp(self, path):
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass

    def _clear_log(self):
        self.chat_log.config(state="normal")
        self.chat_log.delete("1.0", "end")
        self.chat_log.config(state="disabled")

    def _save_log(self):
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(defaultextension=".txt",
                                             filetypes=[("Text", "*.txt")])
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.chat_log.get("1.0", "end"))
            self.log(tr("log_log_saved", self.lang, path=path), "info")
        except Exception as e:
            self.log(tr("log_log_save_error", self.lang, error=e), "error")

    def _refresh_stats(self):
        stats = self.bot.get_stats()
        total = sum(v for k, v in stats.items() if not k.startswith("__"))
        spoken = stats.get("__spoken__", 0)
        commands = stats.get("__command__", 0)

        self.stats_text.config(state="normal")
        self.stats_text.delete("1.0", "end")

        self.stats_text.insert("end", "=" * 50 + "\n")
        self.stats_text.insert("end", tr("stats_header", self.lang) + "\n")
        self.stats_text.insert("end", "=" * 50 + "\n\n")
        self.stats_text.insert("end", f"{tr('stats_spoken', self.lang)} {spoken}\n")
        self.stats_text.insert("end", f"{tr('stats_commands', self.lang)} {commands}\n")
        self.stats_text.insert("end", f"{tr('stats_filtered', self.lang)} {total}\n\n")
        self.stats_text.insert("end", "─" * 50 + "\n")
        self.stats_text.insert("end", tr("stats_breakdown", self.lang) + "\n\n")

        if total == 0:
            self.stats_text.insert("end", f"  {tr('stats_empty', self.lang)}\n")
        else:
            labels = {
                "blacklist": tr("stat_blacklist", self.lang),
                "bot": tr("stat_bot", self.lang),
                "command": tr("stat_command", self.lang),
                "link": tr("stat_link", self.lang),
                "length": tr("stat_length", self.lang),
                "caps": tr("stat_caps", self.lang),
                "emoji": tr("stat_emoji", self.lang),
                "repeat": tr("stat_repeat", self.lang),
                "stopword": tr("stat_stopword", self.lang),
            }
            for key, count in sorted(stats.items(), key=lambda x: -x[1]):
                if key.startswith("__"):
                    continue
                label = labels.get(key, key)
                pct = (count / total * 100) if total else 0
                bar = "█" * int(pct / 4)
                self.stats_text.insert(
                    "end", f"  {label:<22} {count:>5}  ({pct:5.1f}%) {bar}\n")

        self.stats_text.config(state="disabled")

    def _save_all(self):
        self.save_config()
        self.bot.config = self.config
        self.bot.save_lists()
        self.log(tr("log_all_saved", self.lang), "info")

    def _on_close(self):
        try:
            self.save_config()
            self.bot.save_lists()
            if self.bot.running:
                self.bot.disconnect()
        except Exception:
            pass
        self.root.destroy()

    # ------------------ ЛОГ ------------------
    def log(self, text, tag="info"):
        self.root.after(0, self._log_ui, text, tag)

    def _log_ui(self, text, tag):
        timestamp = time.strftime("[%H:%M:%S] ")
        self.chat_log.config(state="normal")
        self.chat_log.insert("end", timestamp, "info")
        self.chat_log.insert("end", text + "\n", tag)
        self.chat_log.see("end")
        self.chat_log.config(state="disabled")


# ==================================================================
#                              ЗАПУСК
# ==================================================================
def main():
    root = tk.Tk()
    try:
        style = ttk.Style()
        if "vista" in style.theme_names():
            style.theme_use("vista")
        elif "clam" in style.theme_names():
            style.theme_use("clam")
    except Exception:
        pass

    app = TTSApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()