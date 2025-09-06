# Contributing Guide

Thanks for considering contributing to **psutil-bridge**!  
This repo is meant to provide a clean backend API for system metrics, and we’d love help building a TUI or improving the core.

---

##  Development Setup
1. Fork and clone this repo.
2. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
````

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```
4. Run examples:

   ```bash
   python
   >>> from bridge import cpu_percent, diskusage
   >>> print(cpu_percent(percpu=True))
   >>> print(diskusage())
   ```

---

##  Contribution Areas

* **TUI Frontend**: using `textual`, `rich`, `urwid`, or `curses`
* **CLI Demo**: `python -m bridge` should print JSON outputs
* **Packaging**: publish on PyPI, pipx, Arch AUR, etc.
* **Core Improvements**: better formatting, error handling, or additional psutil features

---

##  Guidelines

* Keep code style consistent with existing files (no docstrings in Turkish, no excessive comments).
* Functions should return plain dicts/lists with human-readable formatting.
* Gracefully handle unsupported features (return `{ "supported": False }` instead of raising).
* Small, focused PRs are preferred over giant all-in-one changes.

---

##  Pull Request Process

1. Branch from `main`.
2. Make sure code runs with `python -m bridge` and doesn’t print side effects on import.
3. Run `black .` (or follow PEP8 style).
4. Open PR with a clear description of what’s added/changed.

---

##  License

By contributing, you agree that your code will be licensed under the project’s MIT License (see [LICENSE](./LICENSE)).
