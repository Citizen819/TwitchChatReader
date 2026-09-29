# -*- coding: utf-8 -*-
"""
Twitch TTS Chat Bot — озвучка чата Twitch через edge-tts + GUI.
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
from collections import defaultdict, deque
import tkinter as tk
from tkinter import ttk, scrolledtext

import edge_tts


# ==================================================================
#                       КОНФИГ ПО УМОЛЧАНИЮ
# ==================================================================
DEFAULT_CONFIG = {
    "channel": "",
    "oauth_token": "",
    "bot_name": "tts_bot",

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

    # Голос (edge-tts)
    "voice_name": "ru-RU-DmitryNeural",
    "voice_rate": 0,
    "voice_volume": 0,
    "voice_pitch": 0,

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

    # ------------------ ОЗВУЧКА (edge-tts) ------------------
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
        """Воспроизводит MP3 через playsound3 (без открытия внешних плееров)."""
        try:
            from playsound3 import playsound
            playsound(path)
        except Exception as e:
            self.log(f"⚠️ Ошибка воспроизведения: {e}", "error")

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
                self.log(f"⚠️ Ошибка edge-tts: {e}", "error")

    # ------------------ РАБОТА СО СПИСКАМИ ------------------
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
            self.log(f"✅ Загружены списки: бан — {len(self.blacklist)}, "
                     f"белый — {len(self.whitelist)}", "info")
        except Exception as e:
            self.log(f"⚠️ Ошибка загрузки списков: {e}", "error")

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
            self.log(f"⚠️ Не удалось сохранить списки: {e}", "error")

    # ------------------ ФИЛЬТРЫ ------------------
    def is_bot(self, username):
        if not self.config.get("filter_bots", True):
            return False
        name = username.lower()
        return name in self.config.get("bot_names", []) or name.endswith("bot")

    def is_command(self, message):
        if not self.config.get("filter_commands", True):
            return False
        return message.strip().startswith(tuple(self.config.get("command_prefixes", ["!"])))

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
        display = tags.get("display-name", "кто-то")
        if not self.is_privileged(tags):
            self.log(f"⛔ [{display}] нет прав на управление ботом", "warn")
            return True

        parts = msg.split()
        if len(parts) < 2:
            return True
        action = parts[1].lower()
        target = parts[2].lstrip("@").lower() if len(parts) >= 3 else None

        if action == "ban" and target:
            if self.add_to_blacklist(target):
                self.log(f"🔨 [{display}] забанил: {target}", "info")
            else:
                self.log(f"ℹ️ [{display}] {target} уже в бане", "info")
        elif action == "unban" and target:
            if self.remove_from_blacklist(target):
                self.log(f"♻️ [{display}] разбанил: {target}", "info")
            else:
                self.log(f"ℹ️ [{display}] {target} не был в бане", "info")
        elif action == "allow" and target:
            if self.add_to_whitelist(target):
                self.log(f"✅ [{display}] в белый список: {target}", "info")
            else:
                self.log(f"ℹ️ [{display}] {target} уже в белом", "info")
        elif action == "deny" and target:
            if self.remove_from_whitelist(target):
                self.log(f"➖ [{display}] убрал из белого: {target}", "info")
            else:
                self.log(f"ℹ️ [{display}] {target} не в белом", "info")
        elif action == "list":
            b, w = self.get_lists()
            self.log(f"📋 Бан ({len(b)}): {', '.join(b) or '—'}", "info")
            self.log(f"📋 Белый ({len(w)}): {', '.join(w) or '—'}", "info")
        elif action == "save":
            self.save_lists()
            self.log(f"💾 [{display}] списки сохранены", "info")
        elif action == "reload":
            self.load_lists()
            self.log(f"🔄 [{display}] списки перечитаны", "info")
        elif action == "help":
            self.log(f"ℹ️ Команды: ban | unban | allow | deny | list | save | reload",
                     "info")
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
        token = self.config.get("oauth_token", "").strip()
        channel = self.config.get("channel", "").strip().lower()

        if not token or not channel:
            self.log("⚠️ Заполните OAuth-токен и имя канала", "error")
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
            self.log(f"⚠️ Не удалось подключиться: {e}", "error")
            return False

        try:
            self.sock.send(f"PASS {token}\n".encode("utf-8"))
            self.sock.send(f"NICK {self.config.get('bot_name', 'tts_bot')}\n".encode("utf-8"))
            self.sock.send("CAP REQ :twitch.tv/tags\n".encode("utf-8"))
            self.sock.send(f"JOIN #{channel}\n".encode("utf-8"))
        except Exception as e:
            self.log(f"⚠️ Ошибка отправки данных: {e}", "error")
            return False

        self.running = True
        self.tts_thread = threading.Thread(target=self.tts_worker, daemon=True)
        self.tts_thread.start()

        self.log(f"✅ Подключено к #{channel}", "success")

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
                self.log(f"⚠️ Соединение разорвано: {e}", "error")
        finally:
            self.running = False
            try:
                if self.sock:
                    self.sock.close()
            except Exception:
                pass
            self.speech_queue.put(None)
            self.log("🔌 Отключено от чата", "warn")

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
            if ok:
                self._bump_stat("__spoken__")
                self.log(f"🔊 [{display}]: {message}", "spoken")
                self.speech_queue.put(f"{display} пишет: {result}")
            else:
                self._bump_stat(result)
                self.log(f"🚫 [{display}] отфильтровано ({result}): {message}", "filtered")
        except Exception as e:
            self.log(f"⚠️ Ошибка обработки: {e}", "error")

    def disconnect(self):
        self.running = False
        try:
            if self.sock:
                self.sock.close()
        except Exception:
            pass
        self.log("🛑 Отключение...", "warn")

    def skip_current(self):
        while not self.speech_queue.empty():
            try:
                self.speech_queue.get_nowait()
            except queue.Empty:
                break
        self.log("⏭️ Очередь озвучки очищена", "warn")


# ==================================================================
#                        ГРАФИЧЕСКИЙ ИНТЕРФЕЙС
# ==================================================================
class TTSApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Twitch TTS Chat Bot (edge-tts)")
        self.root.geometry("1050x740")
        self.root.minsize(880, 620)

        self.config = self.load_config()
        self.bot = TTSChatBot(self.config, self.log)

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

        # Голос (edge-tts)
        self.config["voice_name"] = self.combo_voice.get().split(" ")[0]
        self.config["voice_rate"] = int(self.scale_rate.get())
        self.config["voice_volume"] = int(self.scale_volume.get())
        self.config["voice_pitch"] = int(self.scale_pitch.get())

        # Фильтры
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
            self.log(f"⚠️ Не удалось сохранить конфиг: {e}", "error")

    # ------------------ UI ------------------
    def _build_ui(self):
        top = ttk.LabelFrame(self.root, text="Подключение", padding=8)
        top.pack(fill="x", padx=8, pady=(8, 4))

        ttk.Label(top, text="Канал:").grid(row=0, column=0, sticky="w")
        self.entry_channel = ttk.Entry(top, width=20)
        self.entry_channel.grid(row=0, column=1, padx=(4, 12))
        self.entry_channel.insert(0, self.config.get("channel", ""))

        ttk.Label(top, text="OAuth-токен:").grid(row=0, column=2, sticky="w")
        self.entry_token = ttk.Entry(top, width=32, show="•")
        self.entry_token.grid(row=0, column=3, padx=(4, 4))
        self.entry_token.insert(0, self.config.get("oauth_token", ""))

        # Точечный биндинг Ctrl+V для поля токена (с return "break" — без дублей)
        self.entry_token.bind("<Control-v>", self._on_token_paste)
        self.entry_token.bind("<Control-V>", self._on_token_paste)

        self.var_show_token = tk.BooleanVar(value=False)
        ttk.Checkbutton(top, text="👁", variable=self.var_show_token,
                        command=self._toggle_token_visibility,
                        width=3).grid(row=0, column=4, padx=(0, 4))

        ttk.Button(top, text="📋 Вставить",
                   command=self._paste_token_from_clipboard,
                   width=12).grid(row=0, column=5, padx=(0, 8))

        self.btn_connect = ttk.Button(top, text="▶ Подключиться",
                                       command=self._toggle_connect)
        self.btn_connect.grid(row=0, column=6, padx=4)

        ttk.Button(top, text="⏭ Пропустить",
                   command=self._skip_current).grid(row=0, column=7, padx=4)

        self.lbl_status = ttk.Label(top, text="⚪ Отключено",
                                     foreground="gray", font=("", 10, "bold"))
        self.lbl_status.grid(row=0, column=8, padx=12)

        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=8, pady=4)

        # --- ЧАТ ---
        tab_chat = ttk.Frame(notebook)
        notebook.add(tab_chat, text="💬 Чат")

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
        ttk.Button(chat_btns, text="Очистить лог",
                   command=self._clear_log).pack(side="left", padx=2)
        ttk.Button(chat_btns, text="Сохранить лог",
                   command=self._save_log).pack(side="left", padx=2)

        # --- СПИСКИ ---
        tab_lists = ttk.Frame(notebook)
        notebook.add(tab_lists, text="📋 Списки")

        lists_frame = ttk.Frame(tab_lists)
        lists_frame.pack(fill="both", expand=True, padx=8, pady=8)

        black_frame = ttk.LabelFrame(lists_frame, text="🔨 Чёрный список (не озвучивать)",
                                      padding=8)
        black_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 4))

        self.listbox_black = tk.Listbox(black_frame, height=14)
        self.listbox_black.pack(fill="both", expand=True)

        b1 = ttk.Frame(black_frame)
        b1.pack(fill="x", pady=(6, 0))
        self.entry_black = ttk.Entry(b1)
        self.entry_black.pack(side="left", fill="x", expand=True)
        ttk.Button(b1, text="+ Добавить",
                   command=self._add_black).pack(side="left", padx=(4, 0))

        b2 = ttk.Frame(black_frame)
        b2.pack(fill="x", pady=(4, 0))
        ttk.Button(b2, text="− Удалить выбранного",
                   command=self._remove_black).pack(side="left")

        white_frame = ttk.LabelFrame(lists_frame, text="✅ Белый список (озвучивать всегда)",
                                      padding=8)
        white_frame.grid(row=0, column=1, sticky="nsew", padx=(4, 0))

        self.listbox_white = tk.Listbox(white_frame, height=14)
        self.listbox_white.pack(fill="both", expand=True)

        w1 = ttk.Frame(white_frame)
        w1.pack(fill="x", pady=(6, 0))
        self.entry_white = ttk.Entry(w1)
        self.entry_white.pack(side="left", fill="x", expand=True)
        ttk.Button(w1, text="+ Добавить",
                   command=self._add_white).pack(side="left", padx=(4, 0))

        w2 = ttk.Frame(white_frame)
        w2.pack(fill="x", pady=(4, 0))
        ttk.Button(w2, text="− Удалить выбранного",
                   command=self._remove_white).pack(side="left")

        lists_frame.columnconfigure(0, weight=1)
        lists_frame.columnconfigure(1, weight=1)
        lists_frame.rowconfigure(0, weight=1)

        bottom_lists = ttk.Frame(tab_lists)
        bottom_lists.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bottom_lists, text="💾 Сохранить в файл",
                   command=self._save_lists_manual).pack(side="left", padx=2)
        ttk.Button(bottom_lists, text="🔄 Перечитать из файла",
                   command=self._reload_lists).pack(side="left", padx=2)

        # --- ФИЛЬТРЫ ---
        tab_filters = ttk.Frame(notebook)
        notebook.add(tab_filters, text="⚙️ Фильтры")
        self._build_filters_tab(tab_filters)

        # --- ГОЛОС ---
        tab_voice = ttk.Frame(notebook)
        notebook.add(tab_voice, text="🔊 Голос")
        self._build_voice_tab(tab_voice)

        # --- СТАТИСТИКА ---
        tab_stats = ttk.Frame(notebook)
        notebook.add(tab_stats, text="📊 Статистика")

        self.stats_text = scrolledtext.ScrolledText(tab_stats, wrap="word",
                                                     font=("Consolas", 10),
                                                     state="disabled")
        self.stats_text.pack(fill="both", expand=True, padx=8, pady=8)
        ttk.Button(tab_stats, text="🔄 Обновить",
                   command=self._refresh_stats).pack(pady=(0, 8))

        bottom = ttk.Frame(self.root)
        bottom.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bottom, text="💾 Сохранить настройки",
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
            ("Фильтровать команды (начинающиеся с ! / .)", self.var_filter_commands),
            ("Фильтровать ботов (nightbot и все *bot)", self.var_filter_bots),
            ("Фильтровать ссылки", self.var_filter_links),
            ("Фильтровать КАПС", self.var_filter_caps),
            ("Фильтровать по длине", self.var_filter_length),
            ("Фильтровать эмодзи-спам", self.var_filter_emoji),
            ("Фильтровать повторы", self.var_filter_repeats),
            ("Фильтровать стоп-слова", self.var_filter_stopwords),
            ("Заменять мат на «бип» (иначе — пропуск)", self.var_censor),
            ("Разрешить управление из чата (!tts ban ...)", self.var_chat_commands),
        ]
        for text, var in rows:
            ttk.Checkbutton(inner, text=text, variable=var).pack(anchor="w", padx=8, pady=2)

        nums = ttk.LabelFrame(inner, text="Числовые параметры", padding=8)
        nums.pack(fill="x", padx=8, pady=8)

        ttk.Label(nums, text="Макс. длина:").grid(row=0, column=0, sticky="w")
        self.entry_max_len = ttk.Entry(nums, width=8)
        self.entry_max_len.grid(row=0, column=1, padx=4)
        self.entry_max_len.insert(0, str(self.config.get("max_length", 200)))

        ttk.Label(nums, text="Мин. длина:").grid(row=0, column=2, sticky="w", padx=(12, 0))
        self.entry_min_len = ttk.Entry(nums, width=8)
        self.entry_min_len.grid(row=0, column=3, padx=4)
        self.entry_min_len.insert(0, str(self.config.get("min_length", 2)))

        ttk.Label(nums, text="Порог капса (0–1):").grid(row=1, column=0, sticky="w")
        self.entry_caps = ttk.Entry(nums, width=8)
        self.entry_caps.grid(row=1, column=1, padx=4)
        self.entry_caps.insert(0, str(self.config.get("caps_threshold", 0.7)))

        ttk.Label(nums, text="Повторов подряд:").grid(row=1, column=2, sticky="w", padx=(12, 0))
        self.entry_repeat_count = ttk.Entry(nums, width=8)
        self.entry_repeat_count.grid(row=1, column=3, padx=4)
        self.entry_repeat_count.insert(0, str(self.config.get("repeat_max_count", 2)))

        ttk.Label(nums, text="Окно повторов (сек):").grid(row=2, column=0, sticky="w")
        self.entry_repeat_window = ttk.Entry(nums, width=8)
        self.entry_repeat_window.grid(row=2, column=1, padx=4)
        self.entry_repeat_window.insert(0, str(self.config.get("repeat_window", 60)))

        sw_frame = ttk.LabelFrame(inner, text="Стоп-слова (по одному в строке)",
                                   padding=8)
        sw_frame.pack(fill="both", expand=True, padx=8, pady=8)
        self.text_stopwords = scrolledtext.ScrolledText(sw_frame, height=8,
                                                          font=("Consolas", 10))
        self.text_stopwords.pack(fill="both", expand=True)
        self.text_stopwords.insert("1.0", "\n".join(self.config.get("stopwords", [])))

        bots_frame = ttk.LabelFrame(inner, text="Имена ботов (по одному в строке)",
                                     padding=8)
        bots_frame.pack(fill="both", expand=True, padx=8, pady=8)
        self.text_bots = scrolledtext.ScrolledText(bots_frame, height=8,
                                                     font=("Consolas", 10))
        self.text_bots.pack(fill="both", expand=True)
        self.text_bots.insert("1.0", "\n".join(self.config.get("bot_names", [])))

    def _build_voice_tab(self, parent):
        frame = ttk.Frame(parent, padding=16)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Голос (edge-tts):").grid(row=0, column=0, sticky="w", pady=4)
        self.combo_voice = ttk.Combobox(frame, state="readonly", width=60)

        voices = [
            "ru-RU-DmitryNeural (мужской)",
            "ru-RU-SvetlanaNeural (женский)",
        ]
        self.combo_voice["values"] = voices
        saved_voice = self.config.get("voice_name", "ru-RU-DmitryNeural")
        idx = 0
        for i, v in enumerate(voices):
            if v.startswith(saved_voice):
                idx = i
                break
        self.combo_voice.current(idx)
        self.combo_voice.grid(row=0, column=1, pady=4, sticky="ew")

        ttk.Label(frame, text="Скорость (-50 .. +100 %):").grid(row=1, column=0, sticky="w", pady=4)
        self.scale_rate = ttk.Scale(frame, from_=-50, to=100, orient="horizontal", length=400)
        self.scale_rate.set(self.config.get("voice_rate", 0))
        self.scale_rate.grid(row=1, column=1, pady=4, sticky="ew")
        self.lbl_rate = ttk.Label(frame, text=f"{int(self.scale_rate.get()):+d}%")
        self.lbl_rate.grid(row=1, column=2, padx=8)
        self.scale_rate.configure(
            command=lambda v: self.lbl_rate.config(text=f"{int(float(v)):+d}%"))

        ttk.Label(frame, text="Громкость (-50 .. +50 %):").grid(row=2, column=0, sticky="w", pady=4)
        self.scale_volume = ttk.Scale(frame, from_=-50, to=50, orient="horizontal", length=400)
        self.scale_volume.set(self.config.get("voice_volume", 0))
        self.scale_volume.grid(row=2, column=1, pady=4, sticky="ew")
        self.lbl_volume = ttk.Label(frame, text=f"{int(self.scale_volume.get()):+d}%")
        self.lbl_volume.grid(row=2, column=2, padx=8)
        self.scale_volume.configure(
            command=lambda v: self.lbl_volume.config(text=f"{int(float(v)):+d}%"))

        ttk.Label(frame, text="Тембр (-50 .. +50 Hz):").grid(row=3, column=0, sticky="w", pady=4)
        self.scale_pitch = ttk.Scale(frame, from_=-50, to=50, orient="horizontal", length=400)
        self.scale_pitch.set(self.config.get("voice_pitch", 0))
        self.scale_pitch.grid(row=3, column=1, pady=4, sticky="ew")
        self.lbl_pitch = ttk.Label(frame, text=f"{int(self.scale_pitch.get()):+d}Hz")
        self.lbl_pitch.grid(row=3, column=2, padx=8)
        self.scale_pitch.configure(
            command=lambda v: self.lbl_pitch.config(text=f"{int(float(v)):+d}Hz"))

        ttk.Button(frame, text="🔊 Тест голоса",
                   command=self._test_voice).grid(row=4, column=0, pady=20, sticky="w")

        ttk.Label(frame,
                  text="edge-tts требует подключения к интернету.\n"
                       "Изменения применятся при следующем сообщении.",
                  foreground="gray").grid(row=5, column=0, columnspan=3,
                                          sticky="w", pady=(12, 0))
        frame.columnconfigure(1, weight=1)

    # ------------------ РАБОТА С ТОКЕНОМ ------------------
    def _on_token_paste(self, event=None):
        """Обработчик Ctrl+V для поля токена. return 'break' — чтобы Tkinter
        не обработал событие повторно встроенным обработчиком."""
        self._paste_token_from_clipboard()
        return "break"

    def _toggle_token_visibility(self):
        self.entry_token.config(show="" if self.var_show_token.get() else "•")

    def _paste_token_from_clipboard(self):
        try:
            text = self.root.clipboard_get()
        except tk.TclError:
            self.log("⚠️ Буфер обмена пуст", "warn")
            return
        text = text.strip().replace("\r", "").replace("\n", "")
        if text.lower().startswith("oauth:"):
            text = text[6:]
        self.entry_token.delete(0, "end")
        self.entry_token.insert(0, text)
        self.log(f"📋 Токен вставлен ({len(text)} символов)", "info")

    # ------------------ ДЕЙСТВИЯ UI ------------------
    def _toggle_connect(self):
        if self.bot.running:
            self.bot.disconnect()
            self.btn_connect.config(text="▶ Подключиться")
            self.lbl_status.config(text="⚪ Отключено", foreground="gray")
        else:
            self.save_config()
            ok = self.bot.connect()
            if ok:
                self.btn_connect.config(text="⏹ Отключиться")
                self.lbl_status.config(text="🟢 Подключено", foreground="green")

    def _skip_current(self):
        self.bot.skip_current()

    def _add_black(self):
        name = self.entry_black.get().strip()
        if not name:
            return
        if self.bot.add_to_blacklist(name):
            self.log(f"🔨 Добавлен в бан: {name}", "info")
        self.entry_black.delete(0, "end")
        self._refresh_lists_display()

    def _remove_black(self):
        sel = self.listbox_black.curselection()
        if not sel:
            return
        name = self.listbox_black.get(sel[0])
        if self.bot.remove_from_blacklist(name):
            self.log(f"♻️ Убран из бана: {name}", "info")
        self._refresh_lists_display()

    def _add_white(self):
        name = self.entry_white.get().strip()
        if not name:
            return
        if self.bot.add_to_whitelist(name):
            self.log(f"✅ Добавлен в белый список: {name}", "info")
        self.entry_white.delete(0, "end")
        self._refresh_lists_display()

    def _remove_white(self):
        sel = self.listbox_white.curselection()
        if not sel:
            return
        name = self.listbox_white.get(sel[0])
        if self.bot.remove_from_whitelist(name):
            self.log(f"➖ Убран из белого списка: {name}", "info")
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
        self.log("💾 Списки сохранены в файл", "info")

    def _reload_lists(self):
        self.bot.load_lists()
        self._refresh_lists_display()
        self.log("🔄 Списки перечитаны из файла", "info")

    def _test_voice(self):
        self.save_config()
        try:
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                tmp_path = tmp.name
            asyncio.run(self.bot._synthesize(
                "Привет! Это тест голоса edge-tts.",
                tmp_path
            ))
            self.bot._play_file(tmp_path)
            self.root.after(8000, lambda: self._cleanup_temp(tmp_path))
        except Exception as e:
            self.log(f"⚠️ Ошибка теста: {e}", "error")

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
            self.log(f"💾 Лог сохранён: {path}", "info")
        except Exception as e:
            self.log(f"⚠️ Ошибка сохранения: {e}", "error")

    def _refresh_stats(self):
        stats = self.bot.get_stats()
        total = sum(v for k, v in stats.items() if not k.startswith("__"))
        spoken = stats.get("__spoken__", 0)
        commands = stats.get("__command__", 0)

        self.stats_text.config(state="normal")
        self.stats_text.delete("1.0", "end")

        self.stats_text.insert("end", "=" * 50 + "\n")
        self.stats_text.insert("end", "  СТАТИСТИКА ФИЛЬТРАЦИИ\n")
        self.stats_text.insert("end", "=" * 50 + "\n\n")
        self.stats_text.insert("end", f"🔊 Озвучено:            {spoken}\n")
        self.stats_text.insert("end", f"🎮 Команд управления:   {commands}\n")
        self.stats_text.insert("end", f"🚫 Отфильтровано всего: {total}\n\n")
        self.stats_text.insert("end", "─" * 50 + "\n")
        self.stats_text.insert("end", "Разбивка по причинам:\n\n")

        if total == 0:
            self.stats_text.insert("end", "  Пока ничего не отфильтровано.\n")
        else:
            labels = {
                "blacklist": "🔨 Чёрный список",
                "bot": "🤖 Бот",
                "command": "🎮 Команда",
                "link": "🔗 Ссылка",
                "length": "📏 Длина",
                "caps": "🔠 КАПС",
                "emoji": "😀 Эмодзи-спам",
                "repeat": "🔁 Повтор",
                "stopword": "🤬 Стоп-слово",
            }
            for key, count in sorted(stats.items(), key=lambda x: -x[1]):
                if key.startswith("__"):
                    continue
                label = labels.get(key, key)
                pct = (count / total * 100) if total else 0
                bar = "█" * int(pct / 4)
                self.stats_text.insert("end", f"  {label:<22} {count:>5}  ({pct:5.1f}%) {bar}\n")

        self.stats_text.config(state="disabled")

    def _save_all(self):
        self.save_config()
        self.bot.save_lists()
        self.log("💾 Все настройки сохранены", "info")

    def _on_close(self):
        try:
            self.save_config()
            self.bot.save_lists()
            if self.bot.running:
                self.bot.disconnect()
        except Exception:
            pass
        self.root.destroy()

    # ------------------ ЛОГ В UI ------------------
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