# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [4.1.0] - 2026-09-29

### Added
- Initial release
- Twitch chat connection via IRC
- Text-to-speech using edge-tts (neural voices)
- Graphical interface (Tkinter)
- Filters: bots, commands, links, CAPS, emoji spam, repeats, profanity
- Blacklist and whitelist with persistent storage
- Chat commands (`!tts ban`, `!tts allow`, etc.)
- Voice tuning: speed, volume, pitch
- Filter statistics
- Support for Windows, macOS, Linux

### Fixed
- Duplicate paste on Ctrl+V in token field
- External player opening instead of silent playback

[1.0.0]: https://github.com/<citizen819>/<TwitchChatReader>/releases/tag/v4.1.0