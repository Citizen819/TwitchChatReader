# Twitch TTS Chat Bot

Озвучивает чат Twitch нейросетевыми голосами Microsoft Edge. Есть графический интерфейс, фильтры, чёрный и белый списки, статистика.

## Требования

- Python 3.10 или новее
- Интернет
- Windows / macOS / Linux

## Установка

1. Установите Python 3.10+ с https://www.python.org/downloads/
   - На Windows поставьте галочку **«Add Python to PATH»**.

2. Откройте терминал и установите зависимости:

pip install edge-tts playsound3


3. Получите OAuth-токен:
- Откройте https://twitchtokengenerator.com/
- Войдите, выберите **Custom Scope**, отметьте `chat:read`
- Нажмите **Generate Token** и скопируйте **Access Token**

4. Запустите бота:


python tts_chat.py


5. В окне:
- Введите имя канала (в нижнем регистре, без `#`)
- Вставьте токен (кнопка 📋 или Ctrl+V)
- Нажмите **▶ Подключиться**

## Команды в чате

Доступны только стримеру и модераторам:

| Команда | Описание |
|---|---|
| `!tts ban <user>` | Замьютить юзера |
| `!tts unban <user>` | Вернуть озвучку |
| `!tts allow <user>` | Озвучивать всегда |
| `!tts deny <user>` | Убрать из белого списка |
| `!tts list` | Показать оба списка |
| `!tts help` | Справка |

## Файлы

- `tts_config.json` — настройки (не выкладывайте, там ваш токен)
- `tts_lists.json` — чёрный и белый списки

## Решение проблем

**`ModuleNotFoundError: No module named 'edge_tts'`**

python -m pip install edge-tts


**`ModuleNotFoundError: No module named 'playsound3'`**


python -m pip install playsound3


**Нет звука на Linux**

Установите проигрыватель MP3:


sudo apt install mpv



**`pip install edge-tts` падает с «Could not find a version»**

Слишком старый Python. edge-tts требует Python 3.7+. Обновите до 3.10 или новее.

## Лицензия

MIT

