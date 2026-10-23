# Building a Sparx module

Sparx is a personal AI assistant. The core is done and tested; every capability is a *tool* in `sparx/tools/<module>.py`.
Read these first (they are short): `sparx/tools/__init__.py`, `sparx/tools/core.py`, `sparx/db.py`, `sparx/config.py`,
`sparx/security.py`, `sparx/jobs.py`, `sparx/undo.py`, `sparx/llm.py`, `sparx/agent.py`, `tests/conftest.py`, `tests/test_core.py`.

## Rules

1. **Only touch the files you were assigned.** Other agents are writing other files in this folder right now.
   Never edit core files (`sparx/*.py` listed above, `sparx/tools/__init__.py`, `sparx/tools/core.py`, `tests/conftest.py`,
   `pyproject.toml`). If the core lacks something, work around it in your own module and say so in your final report.
2. **Tools**: register with `@tool(...)` and declare your group once with `category(name, description)`.
   First parameter is `ctx`. Return str / dict / list. Raise `ToolError("...")` for expected failures.
   Names are `snake_case`, prefixed by domain (`task_add`, `email_send`). Descriptions are written for an LLM:
   one or two sentences saying what it does and when to use it. Keep parameter lists small.
3. **Risk** (`risk=`) decides whether the user is asked first. Be honest: `read`, `write` (Sparx's own data / its
   workspace), `exec` (run code or commands), `control` (desktop, browser, devices), `delete`, `send` (reaches other
   people), `spend` (money). Anything irreversible or outward-facing must be `delete`/`send`/`spend`/`control`/`exec`.
   Never ask the user yourself and never bypass the registry: the registry handles approval.
4. **Untrusted text**: `untrusted=True` on any tool returning text Sparx did not write (web, files, email, OCR,
   transcripts, device payloads).
5. **Storage**: SQLite through `sparx.db` (`db.schema(...)` at import, `db.q/one/x/many`, timestamps via `db.now()`).
   Files go under `config.path("<area>", ...)`. Never `from sparx.config import HOME`; tests repoint it.
   Secrets only via `config.secret("ENV_NAME")`; integration settings via `config.settings()["integrations"]`.
6. **Deleting**: move to `config.path("trash", ...)` instead of unlinking, and `undo.record(...)` anything reversible.
7. **Dependencies**: stdlib and what is installed first (httpx, fastapi, uvicorn, websockets, pydantic, openai,
   playwright, pypdf, pillow, numpy, chromadb, edge-tts, pyttsx3, pyautogui, cv2, sounddevice, rich, pytest,
   pytest-asyncio). Anything else is **optional**: import it inside the function and raise
   `ToolError("Install X to use this: pip install X")` when missing. Never import optional packages at module top level.
   Python is 3.14 on Windows 11; many packages have no wheel yet, so do not `pip install` heavy/native packages.
   Small pure-Python packages may be installed if a test truly needs them; list them in your final report.
8. **LLM calls inside tools**: `await llm.complete(system, user, role="fast")` / `llm.complete_json(...)` /
   `llm.get(role).chat(...)`. Always call through the `sparx.llm` module (`from sparx import llm`), so tests can fake it.
9. **Background work**: `@jobs.every(seconds, "name", flag="<proactive setting>")` and `jobs.notify(title, body, kind, why)`.
10. **Honesty**: no stubs that pretend. If a feature needs an account, device or library that is absent, the tool
    must say exactly what is missing and how to set it up. Do not fabricate data.
11. **Tests**: write `tests/test_<yourarea>.py` using the fixtures in `tests/conftest.py` (`ctx`, `fake_llm`,
    `run_tool`; the `home` fixture is automatic). No network, no real LLM, no real mic/camera/desktop in tests.
    Run only your own file: `python -m pytest tests/test_<yourarea>.py -q`. They must pass before you finish.
    On a machine short of memory, run the whole suite with `python tests/run_by_file.py --out <scratch dir>` instead of
    one process; its `results.json` and per-file logs are the evidence to quote in the run log.
    Also run `python -c "from sparx import tools; tools.load_all(); print(tools.LOAD_ERRORS)"` and make sure your
    module is not in the errors. Tests that launch a real browser carry `pytest.mark.browser`.
    `python -m pytest tests -m "not browser" -q` is the quick run; the full `python -m pytest tests -q` is still
    required before finishing any change to `sparx/web/*` or `sparx/server.py`.
12. Code style: match the core. Compact, typed where it helps, short docstrings, no boilerplate, no dead code.
    Aim for real, working behaviour over breadth of half-working features.

## Final report (your last message)

Plain text, under 250 words: tools added (names only), anything that needs setup (env vars, settings keys, optional
packages), anything from your assignment you did NOT build and why, and test result (N passed).
