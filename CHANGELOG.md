# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-03-07

### Added

- **MHDDoS-GUI Release**: Created a powerful dual-architecture GUI (Web Dashboard and Desktop App) for MHDDoS.
- **Frontend**: Designed a modern, glassmorphism UI using React/Vite aesthetics via Tailwind CSS. Added real-time log terminal, proxy selection file browser, responsive layouts, all 57 attack methods categorized, auto-saving memory, and a dynamic contextual UI (hides irrelevant inputs based on attack layer).
- **Backend**: Implemented FastAPI backend to manage subprocesses (`start.py`) and stream logs via WebSockets.
