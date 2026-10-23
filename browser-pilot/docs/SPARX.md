# Sparx user guide

## What Sparx is

Sparx is a personal AI assistant that runs on your own Windows PC. You talk to it in a terminal, in a browser (including from your phone), or by voice. It answers questions and carries out tasks by calling "tools": small functions for tasks, reminders, files, web search, email, smart-home devices and so on. A language model decides which tools to call. Sparx's code runs them, asks you before risky ones, and records what it did.

Sparx lives in the `sparx/` package of this repository and builds on `browserpilot/`, the older browser-automation library (`pilot`). Sparx reuses its model client and its provider list. Your data stays in one folder on your PC (see "Where your data lives"). Sparx sends text to whichever language model you choose, so with a hosted model your conversation leaves your machine. With a local Ollama model it does not.

Sparx is developed on Python 3.14 on Windows 11. `pyproject.toml` says `requires-python >=3.10`, but Windows is the only platform it is built for: desktop control, toast notifications and encrypted secret storage use Windows features.

## Install and first run

From the repository folder:

```
pip install -e .
```

This installs the `pilot` and `sparx` commands. Required packages are `playwright`, `openai`, `httpx`, `fastapi` and `uvicorn`. For running the tests, `pip install -e .[dev]` adds `pytest` and `pytest-asyncio`.

Then:

```
sparx doctor      # check home folder, model, tool groups and optional packages
sparx             # same as `sparx chat`
```

`sparx doctor` prints your home folder, the model Sparx will use, how many tools loaded and in how many groups, any tool module that failed to load (marked `BROKEN`), which providers have an API key set, an `ok` or `missing` line for each optional package, and whether the emergency stop is set. Run it first when something does not work.

In the chat, type `/help` to see the slash commands.

### Commands

| Command | What it does |
| --- | --- |
| `sparx` or `sparx chat` | Chat in the terminal. |
| `sparx ask TEXT...` | One question, one answer. `-y` / `--yes` approves every action without asking. |
| `sparx serve [--host H] [--port P]` | Web UI for this PC and your phone. Defaults come from the `server` setting. |
| `sparx voice` | Hands-free voice mode with a wake word. |
| `sparx daemon` | Background process for reminders, briefings, monitors and automations. |
| `sparx team GOAL...` | Run a goal through the multi-agent team. |
| `sparx tools` | List every tool with its group, risk level and description. |
| `sparx audit [-n N]` | Show the last N actions (default 30). |
| `sparx stop` / `sparx resume` | Set or clear the emergency stop. |
| `sparx config [KEY [VALUE]]` | Show settings (or one key), or set a dotted key. |
| `sparx doctor` | Check models, tools and optional dependencies. |
| `sparx backup` | Copy the database and `settings.json` into `backups/` now (checked, keeps the newest 7). |

Chat slash commands: `/tools`, `/load GROUP`, `/scope NAME`, `/model SPEC`, `/usage`, `/audit [N]`, `/undo`, `/stop`, `/resume`, `/new`, `/exit`.

- **Tool groups.** Sparx does not give the model every tool at once. A few groups are always loaded (the `always_on` setting; default `core`, `memory`, `productivity`, `sparx`), and the model can load others as needed. `/tools` shows each group, its tool count, and a `*` next to the groups loaded in this chat. `/load GROUP` loads one yourself.
- **Memory scopes.** `/scope NAME` switches the memory scope (`personal`, `work`, `study`, or a project name). `/new` starts a fresh conversation; stored memory is kept.
- **`/model SPEC`** writes `models.default` to your settings file, so the change persists across sessions.

## Where your data lives

Everything is under the Sparx home folder: `%USERPROFILE%\.sparx`, or the folder named by the environment variable `SPARX_HOME`. It contains, among other things:

- `settings.json`: your settings (only the keys you changed; defaults fill in the rest).
- `.env`: API keys and other secrets (see below).
- `auth.json`: hashed web access token, sessions and PIN. Only hashes are stored.
- the SQLite database (memory, tasks, audit log, undo log, notifications and so on),
- `logs/` (`daemon.log`, `errors.log`), `uploads/` (files sent from the web UI), `trash/` (the file tools move deleted files here instead of unlinking them),
- `backups/` (checked copies of the database and `settings.json`: one a day while the daemon or `sparx serve` runs, or on demand with `sparx backup` or `storage_backup`; `retention.backups` sets how many to keep, default 7, and 0 turns the daily copy off),
- `STOP` (the emergency-stop flag file) and `daemon.heartbeat` (written while the daemon runs).

Deleting a conversation also removes it from the search index and drops its summary. You can undo a delete for `retention.undo_days` days (default 30; `0` keeps undo entries for ever), after which nothing of it is kept except in backups.

### Backups

A daily job (and `sparx backup`, or the `storage_backup` tool, whenever you like) copies the database and `settings.json` into `backups/` under the Sparx home folder. Each copy is checked with SQLite's integrity check before it is kept, and only the newest `retention.backups` copies stay (default 7; `0` turns the daily job off). The files in `backups/` are full copies of your data, so the file, knowledge, audio and vision tools refuse to open them. There is deliberately no restore tool, because restoring replaces live data. To restore by hand: run `sparx stop`, stop `serve` and `daemon`, copy the backup over `sparx.db`, delete `sparx.db-wal` and `sparx.db-shm`, then start Sparx again.

### Secrets

Sparx reads credentials only from environment variables, never from `settings.json`. On start it also reads `%USERPROFILE%\.sparx\.env` (`KEY=value` lines; `#` comments allowed). The `browserpilot` library additionally loads `.env` in the current folder and `%USERPROFILE%\.browserpilot\.env`. A real environment variable always wins over a file. The file, knowledge, audio and coding tools never open Sparx's own `.env` and `auth.json`, the `secrets` folder, or other credential files (see "Other safeguards"), but the file is plain text, so protect your user account.

There is also an encrypted secret store (part of the plugins group) that uses Windows DPAPI. On other platforms it refuses to store anything rather than fall back to plain text.

## Choosing a model

Model names are `provider/model`. Supported providers (from `browserpilot/config.py`):

| Provider | Needs |
| --- | --- |
| `ollama` | Ollama running locally (default `http://localhost:11434/v1`, override with `OLLAMA_BASE_URL`). No key. |
| `lmstudio` | LM Studio server running locally (override with `LMSTUDIO_BASE_URL`). No key. You must give a model name. |
| `groq` | `GROQ_API_KEY` |
| `gemini` | `GEMINI_API_KEY` |
| `openai` | `OPENAI_API_KEY` |
| `anthropic` | `ANTHROPIC_API_KEY` |
| `cerebras` | `CEREBRAS_API_KEY` |
| `deepseek` | `DEEPSEEK_API_KEY` |
| `mistral`, `xai`, `together` | `MISTRAL_API_KEY`, `XAI_API_KEY`, `TOGETHER_API_KEY`. You must give a model name (`mistral/<model>`); there is no default. |
| `custom` | Any OpenAI-compatible server: set `BROWSERPILOT_BASE_URL` (and `BROWSERPILOT_API_KEY` if it needs one). You must give a model name. |

A bare provider name (`groq`, `gemini`, `ollama`, `openai`, `anthropic`, `cerebras`, `deepseek`) uses that provider's built-in default model.

How Sparx picks the default model, in order:

1. `models.default` in settings (set with `sparx config models.default groq`, or `/model groq` in chat),
2. else the `SPARX_MODEL` environment variable,
3. else `BROWSERPILOT_MODEL`, whose built-in default is `groq/openai/gpt-oss-120b`.

If the chosen provider needs an API key and none is set, Sparx falls back to `ollama/gpt-oss:latest`. So with no keys at all, Sparx tries local Ollama. Ollama must be running with that model pulled (`ollama pull gpt-oss`), or you must set `models.default` to a model you have.

**A free remote GPU (Kaggle).** `docs/kaggle_sparx_server.ipynb` runs Ollama on a free Kaggle GPU behind a token-protected Cloudflare tunnel. Run it (GPU T4 x2, Internet on), then put the `BROWSERPILOT_BASE_URL` and `BROWSERPILOT_API_KEY` lines it prints into `~/.sparx/.env`. Use it as a backup that takes over when the main model is busy or down: `sparx config models.fallbacks '["custom/qwen2.5:14b"]'`, or as the main model with a local one behind it. The tunnel URL changes every session and sessions end after a few hours, so update the two lines each time; with no URL set, the `custom` backup is skipped.

Other roles fall back to `models.default` when unset: `fast` (summaries, classification, extraction), `smart` (planning, verification) and `vision` (image understanding). `models.embed` names the embedding model used by knowledge search (see "Known limits").

Small local models (roughly 3B to 8B) are unreliable at tool calling. Use a 20B+ model or a hosted one for real work. For Ollama, a larger context window helps (set `OLLAMA_CONTEXT_LENGTH=32768` before `ollama serve`).

## The web UI: `sparx serve`

```
sparx serve
```

This starts a local web server (default `127.0.0.1:8765`; change it with the `server.host` and `server.port` settings or the `--host` and `--port` flags). It prints a one-time login link:

```
http://localhost:8765/login?code=...
```

Open that link in your browser to sign in. The code is single-use and expires after 10 minutes. The first time the server ever runs, it also prints an **access token** for API clients. It is shown once and only its hash is stored, so copy it then. A browser session lasts 30 days. The login link takes only one-time codes; the access token is for `POST /api/login` and the `Authorization: Bearer` header.

For another login link later, run `python -m sparx.auth code` and append the output to the server address. Other helpers:

```
python -m sparx.auth set-pin        # optional PIN (4+ characters) that locks each session
python -m sparx.auth clear-pin
python -m sparx.auth rotate-token   # new access token, signs every browser out
```

What the UI provides (from `sparx/server.py`): chat over a WebSocket with approval prompts, conversations stored on the server and shared across devices, dashboards for tasks, events, reminders, habits, goals, memories and expenses, a "today" view, notifications, the audit and undo lists, file upload (25 MB limit by default, `server.max_upload_mb`), and an emergency stop. An approval request in the browser counts as a denial if you do not answer within 120 seconds.

Two panels deal with work Sparx did in the background:

- **Approvals** lists the actions a background job was not allowed to run on its own (see "Background jobs"). Each card shows the tool, its risk level, its arguments, who asked and when it expires. **Run now** runs the action (the click is the approval, via `pending_approve`) and **Dismiss** drops it (`pending_dismiss`). A "Recently handled" list shows the last 20 that are no longer waiting.
- **Automations** has three lists. "Waiting for you" shows runs paused at a step that needs approval, with the step and the later steps that would also ask. **Approve and continue** (`automation_resume`) approves that step and the rest of that run, so the later steps do not ask again; **Cancel run** (`automation_cancel`) drops it. If your permission settings have since set the waiting step's tool to `deny`, the run is left waiting and the panel says why. Below that, every saved automation with its trigger, step count and next run, and an **Enable** / **Disable** button (`automation_enable`, `automation_disable`). Below that, recent runs (from the last 30) and their status.

An action that was blocked inside an automation run is approved from the Automations panel, not from Approvals. When a run pauses, the matching entry in Approvals is closed with a note pointing at the run, so there is one place to answer.

Security properties, as implemented: every API call and the WebSocket need the token or a session cookie; state-changing requests must come from the page's own origin; five failed logins or PIN tries from one address cause a five-minute lockout; responses carry a restrictive Content-Security-Policy.

Settings you can change from the web UI: `name`, `user`, `address`, `language`, `personality`, and the `proactive.*`, `voice.*` and `models.*` groups. Changing `permissions.*` or `tool_permissions.*` there requires a PIN to be set first. Everything else (`limits`, `allowed_roots`, `integrations`, `server`, `always_on`) can only be changed with `sparx config` on the computer.

### Reaching it from a phone

By default only this PC can connect. `sparx serve --host 0.0.0.0` makes it reachable on your network, but it is plain HTTP: anyone on the same Wi-Fi can read the traffic, including the session cookie. The server prints a warning saying so. The safer route it suggests is to keep `127.0.0.1` and reach it through Tailscale (`tailscale serve`) or an HTTPS tunnel. Phones need HTTPS for the microphone and for installing the page as an app. Set a PIN if you expose it at all.

While `sparx serve` runs, it also runs the background jobs in the same process (setting `server.run_jobs`, default on), so reminders and briefings work with only the server running.

## Background jobs: `sparx daemon`

```
sparx daemon
```

The daemon loads all tools and then, every 5 seconds, runs each job that is due. Tool modules register jobs with `@jobs.every(seconds, name)`. In the current code they include reminders (every 30 s), automations (20 s), folder watches (20 s), scheduled messages (60 s), medication reminders (60 s), web page monitors (5 min), bill reminders and spending-anomaly checks (hourly) and housekeeping (daily). The daemon prints the job names when it starts.

- Jobs produce notifications. The daemon prints each one and, on Windows, shows a balloon toast (turn that off with `sparx config proactive.toasts false`). Notifications are stored and also appear in the web UI.
- A job runs only if `proactive.enabled` is true and its own flag is not false. The flags in the defaults are `reminders`, `deadline_risk`, `follow_ups`, `routine_detection`, `monitors` and `anomalies`. A job without its own flag is controlled by a flag named after the job. `proactive.daily_briefing` is the time of the morning briefing (default `08:00`).
- **Nobody can approve for a background job.** Jobs run with no approver, so any tool whose policy is `ask` is not run, and the refusal goes in the audit log. Tools whose policy is `allow` do run. Plan automations accordingly. An automation can run at most once a minute and have at most 20 steps; one that starts more than `limits.automation_runs_per_hour` times in an hour (default 120, 0 for no cap) or whose last 5 automatic runs all failed is turned off with a notification, and `automation_enable` turns it back on. A recipe has at most one automatic run waiting for your approval at a time: later occurrences are skipped until you resume it, drop it with `automation_cancel`, or it expires after 24 hours. The events an `event:` trigger can match today are `sensor.<device>.<metric>` and `sensor_clear.<device>.<metric>`, published when a sensor rule is crossed or clears; `automation_events` lists recent ones.
- More automation rules. A recipe is not started by a notification its own run raised, and a `file:` recipe ignores file changes seen while one of its own runs was going (so it also ignores anyone else's change to that folder in that window). Recipes that start each other through notifications stop after 3 runs in a row, with one notice and nothing turned off. A recipe created by a background run is saved disabled, and a background run cannot enable one; you turn it on yourself. Values from a trigger or an earlier step (a notification's text, a file name) that read like an instruction to the model pause an unattended run before any step that is not read-only, and the run waits for you in the Automations panel. An action blocked inside an automation run is approved there, not in Approvals; approving a waiting run approves the rest of that run.
- A hung job is cut off after 10 minutes. A job that raises an error is logged to `logs/daemon.log` and the others still run. When the same job fails three times in a row you get one notification saying so, and the `job_status` tool shows each job's last run, last error and failure count.
- The daemon writes `daemon.heartbeat` on each pass, which the web UI uses to show whether it is alive. While the emergency stop is set, the daemon runs nothing and idles.

Sparx does not install itself as a service. To keep the daemon running after login you have to arrange that yourself, for example with a Task Scheduler entry that runs `sparx daemon`. If you run both `sparx serve` and `sparx daemon`, only one of them runs the jobs: they share a lock file (`jobs.lock` in the Sparx home), and the other process takes over if the owner exits or stops refreshing the lock for a couple of minutes. `sparx doctor` shows which process is running jobs.

## Permissions and safety

Every tool declares a **risk level**. Before a tool runs, Sparx looks up the policy for it: `allow`, `ask` or `deny`.

| Risk | Meaning | Default |
| --- | --- | --- |
| `read` | Look at data Sparx already has access to. | allow |
| `write` | Create or change Sparx's own data and files in its workspace. | allow |
| `exec` | Run commands or code. | ask |
| `control` | Drive the desktop, browser or devices. | ask |
| `delete` | Remove things. | ask |
| `send` | Email, messages, posts: anything that reaches other people. | ask |
| `spend` | Purchases, transfers, trades. | ask |

Policies:

- `allow`: runs without asking.
- `ask`: you are asked first. In the terminal you see the tool, its risk and its arguments (secrets masked) and type `y` to allow; anything else is a no. In the web UI you get an approval prompt. If there is nobody to ask (no terminal attached, a background job, an unanswered web prompt), the answer is no and the model is told not to retry.
- `deny`: never runs.

Change the default for a risk level, or override a single tool, with `sparx config`:

```
sparx config permissions.send deny
sparx config permissions.write ask
sparx config tool_permissions.email_send deny
```

A `tool_permissions.<tool name>` entry takes priority over the risk-level policy. Use `sparx tools` to see tool names and risk levels, and `sparx config permissions` to see the current policies. Tools in the `write` category can still matter (they include creating files and editing code in your workspace); if that worries you, set `permissions.write` to `ask`.

`sparx ask -y` approves everything that would be `ask`. It does not override `deny`.

### Other safeguards

- **Audit log.** Every tool call, including refused ones, is recorded with time, agent, tool, risk, arguments, success and a short result. Credential-looking values are masked before logging. View it with `sparx audit`, `/audit` in chat, or the web UI.
- **Undo.** Tools that make reversible changes record how to reverse them. `/undo` in chat (or the web UI) reverses the most recent action that has not been undone. Not everything is reversible: an action with no undo handler reports "Cannot undo" and does nothing. The file tools move deleted files to the `trash` folder instead of unlinking them.
- **Emergency stop.** `sparx stop`, `/stop`, or the stop button in the web UI creates the `STOP` file. Every agent halts at its next tool call and the daemon stops running jobs. `sparx resume` or `/resume` clears it.
- **Run limits.** Defaults per run: 14 model rounds, 40 tool calls, 900 seconds and 4 parallel agents (`limits.*`).
- **Untrusted text.** Tools that return text Sparx did not write (web pages, files, email, OCR and so on) have their output wrapped and marked as data, and a pattern scan adds a warning if the text looks like instructions to the model. This reduces prompt-injection risk. It does not remove it.
- **File access.** File tools work only inside your home folder, the Sparx home folder and the folders in the `allowed_roots` setting. They always refuse system folders, credential files and folders, browser profiles, other apps' AppData folders and Sparx's own `settings.json`. Top-level folders such as Documents cannot be moved, renamed or deleted.
- **Credential files.** One check (`security.secret_path`) is shared by the file, knowledge, audio and coding tools, and also covers email attachments, statement and receipt import, activity import and calendar import. It refuses: Sparx's own `.env`, `auth.json` and `secrets` folder; anything inside folders such as `.ssh`, `.gnupg`, `.aws`, `.kube` or `.docker`, or inside browser profiles; files with well-known names (`.env`, `.netrc`, `.npmrc`, `id_rsa`, `id_ed25519`, saved-login databases and similar); any `.env.<something>` file; and any file ending in `.env`, `.key`, `.pem`, `.pfx`, `.p12`, `.ppk`, `.kdbx`, `.jks` or `.keystore`. It ignores case, trailing dots and spaces and Windows `:stream` suffixes, and follows links. The one exception is the committed templates `.env.example`, `.env.sample` and `.env.template`. The `.key` rule also catches Keynote files. Folder operations skip such files and say how many they left out.
- **Spoken approval.** In voice mode, an action with risk `send`, `delete`, `spend` or `exec` is approved only if you say the word "confirm" (a plain "yes" is not enough, because anyone in the room can say "yes"). Other risks take "yes". Silence or anything else counts as no. `screen_explain`, `speaker_identify` and `speaker_enrol` are `control` tools, so they ask first like any other.
- **Team sub-agents.** In `sparx team` and `team_run`, a researcher gets only the read-only tools of the memory, web and knowledge groups. A verifier gets only read-only tools, and anything it tries that would need approval is refused (not queued). An executor gets only the tool groups its subtask needs, never `agents` or `core` (so it cannot call `load_tools`, `settings_set` or `pending_approve`). A team subtask cannot start another team run. Tool calls made by a sub-agent count against the same per-run budget as the agent that started it, so splitting work across agents does not raise the limit.

### Behaviour of specific tools

- **Messages.** `email_draft` stores a draft and gives a `confirm` fingerprint of it; `email_send` with a `draft_id` sends only if you pass that `confirm` value, so a draft edited after you approved it is not sent. The send tools need the real address, chat id or number, not a contact name: contact names must match exactly, and a send given a name is refused with the address to use instead. A scheduled message (`message_schedule`) is approved when you schedule it, but it is not sent if sending has been set to `deny` by the time it is due, and it stays unsent while the emergency stop is set. Its status shows how it ended: `sent`, `failed`, `missed` (the daemon was not running within the grace period, so it is not sent late), `blocked`, `partial` (a long Telegram message got only its first parts through), or `unknown` (the connection broke, or Sparx stopped, mid-send, so it may or may not have gone out). Nothing is retried, so nobody gets a message twice.
- **Smart home.** Locks, alarms and garage, door and gate covers are operated only with `home_security_set`, which always needs you present. The ordinary device tools refuse a scene, group or device that Home Assistant says would operate one. A sensor rule that has fired stays quiet for 10 minutes (a constant in `sparx/tools/home.py`, not a setting), so a reading that hovers at the threshold does not send a stream of alerts.
- **Web monitors.** Sparx keeps at most 50 monitors. After 3 failed checks in a row you get one notice that changes are not being seen; it is repeated only after a check has succeeded in between. A monitor sends at most 3 change notices a day; after that you get one "changes on every check" notice. Web fetches that Sparx guards (not the ones to local addresses when `integrations.allow_local_fetch` is on) connect only to the address that was just checked and ignore proxy environment variables, and they do not pass API keys to a different host after a redirect.
- **Health.** The daemon sends a "Missed reminder" notice for a medication dose that passed unconfirmed, and for an appointment that has passed. At most 3 missed-dose notices go out in one pass, with a summary of the rest, and none for times before the medication was added. `medication_add` takes an `until` date (the last day of a course); reminders stop after it.
- **Finance.** `expense_import` reads at most 20,000 rows and says when it stopped there (`truncated`). Rows that look like expenses you entered by hand (same merchant and amount) are listed as probable duplicates and not imported unless you pass `import_duplicates`. A price quote older than its limit is marked stale and the reply says so.
- **Learning.** Coding exercises run in a separate Python process with a time limit and a stripped environment. Inside that process a guard allows file access only in the exercise's own folder, blocks sockets and starting programs, and caps memory. This is a guard in the Python process, not an operating-system sandbox: treat it as a safety net against mistakes, not a way to run hostile code. The exercise's grade is worked out by Sparx's own process afterwards, so the exercise code cannot change its grade or read the answers.

## Tool groups

Sparx's tools are organised in groups. The list below reflects the code at the time of writing. The code is changing, so run `sparx tools` to see what your install has; it also lists any group that failed to load.

| Group | What it covers |
| --- | --- |
| `core` | Load tool groups, date and time, calculator, undo, settings, notifications. |
| `memory` | Long-term memory about you and your projects; search over past conversations. |
| `productivity` | Tasks, calendar, scheduling, reminders, notes and journal, goals, habits, focus and time tracking, shopping lists, travel plans, daily briefing. |
| `sparx` | System vitals, situation report, named protocols ("good morning", "focus", "good night"), device modes ("meeting mode", "night mode", "battery mode", "normal mode"), lock screen. |
| `proactive` | Briefings, deadline and goal warnings, follow-ups, routine suggestions, background research, weekly analytics, and switches for each. |
| `automation` | Recipes that run tool steps on a schedule, event, file change or on demand; run log, resume, undo. |
| `agents` | Multi-agent team for large goals: plan, parallel research and execution, verification, reusable workflows. |
| `files` | Find, read, write, move, rename, organise, convert, zip, back up and watch files and folders. |
| `documents` | Create Word, Excel, PowerPoint, PDF, Markdown and HTML files from structured content. |
| `knowledge` | Personal knowledge base over your documents: ingest, search, cited answers, summaries, flashcards and quizzes. |
| `graph` | Knowledge graph of people, projects, decisions and documents, and how they relate. |
| `web` | Web and news search, fetching pages, research with citations, arXiv, Wikipedia, GitHub, Hacker News, page-change watching, price comparison. |
| `browser` | Drive your own Chrome with autonomous agents (the `pilot` engine); saved browser workflows. |
| `system` | Open, close and switch apps, run shell commands and Python, screenshots, clipboard, system info, mouse and keyboard. |
| `pc` | This PC's settings: speaker and microphone volume, default audio device, brightness, Wi-Fi and Bluetooth, dark mode, wallpaper, power plan, sleep / restart / shutdown, media keys, opening a Settings page, settings suggestions. |
| `desktop` | Managing this PC: snap, tile, minimise and close windows, launch any Start-menu app, install / update / remove software with winget, startup apps, screen resolution, network details, paired Bluetooth devices, recycle bin. |
| `phone` | Your Android phone over ADB: settings (Wi-Fi, Bluetooth, brightness, volumes, do not disturb, dark mode, battery saver and more), apps, reading and tapping the screen, typing, notifications, calls, screenshots, file transfer, and a pilot for multi-step goals. |
| `vision` | Describe images, read text in pictures and documents, explain the screen, webcam, summarise videos. |
| `audio` | Speak aloud, listen, transcribe recordings and meetings, translate speech, detect loud sounds. |
| `comms` | Email, Telegram and WhatsApp messages, scheduled messages, contacts, drafts, meeting invites. |
| `home` | Smart home and devices: Home Assistant, ESP32 / Raspberry Pi devices over HTTP or MQTT, sensors, energy, scenes, locks and alarms (confirmed separately). |
| `coding` | Repo map, code search and edit, tests, lint, build, debugging, git and GitHub, code review. |
| `finance` | Expenses, budgets, statement import, subscriptions, savings goals, loan and SIP calculators, watchlist quotes. Its description says it never moves money. |
| `health` | Workouts, wearable imports, sleep and activity summaries, meals, hydration, medication and appointment reminders, opt-in mood journal. Local only, no diagnosis. |
| `learning` | Tutor and study tools: flashcards (spaced repetition), quizzes, study plans, mock interviews, coding exercises. |
| `creative` | Images, diagrams, narration audio, subtitles, scripts, written content, web pages, simple video edits. |
| `plugins` | Tools from MCP plugin servers; the encrypted secret store. |

## Controlling your PC and phone

**This PC.** Ask in plain words: "volume to 30", "mute the mic", "switch audio to my headphones", "brightness 40", "dark mode", "turn Bluetooth off", "put Chrome on the left and VS Code on the right", "install VLC", "stop Spotify starting with Windows", "shut down in ten minutes". Each change is read back from Windows, and the reply says what the value was before. Volume, brightness, theme, wallpaper, default audio device, resolution and startup switches can be reversed with "undo that". Settings Windows gives no way to change from outside (night light, do not disturb, default apps, privacy) are opened in the Settings app for you instead.

**Your phone (Android only).** One-time setup on the phone:

1. Settings > About phone > Software information, tap **Build number** seven times.
2. Settings > Developer options, turn on **USB debugging**.
3. Plug the phone into this PC and accept "Allow USB debugging".

Without a cable: Developer options > **Wireless debugging** > "Pair device with pairing code", then tell Sparx the pairing address, the six-digit code and the address on the Wireless debugging screen ("connect to my phone at 192.168.1.23:37115, pair at 192.168.1.23:40123 with code 123456"). Later you only need the first address; it changes when wireless debugging is switched off and on.

Sparx needs `adb`. It looks on `PATH`, in the Android SDK (`%LOCALAPPDATA%\Android\Sdk\platform-tools`) and at `integrations.phone.adb`. If you have none: `winget install Google.PlatformTools`.

Then: "what's my phone's battery", "turn on do not disturb on my phone", "phone brightness 30", "open Maps on my phone", "what's on my phone screen", "call +91...", "send this PDF to my phone", "get the last photo off my phone". For anything with no direct switch ("turn on the hotspot", "set an alarm for 6:30") Sparx uses `phone_task`, which reads the screen and taps through it one step at a time.

**Modes.** "Meeting mode" mutes the PC and turns on do not disturb on the phone; "night mode" dims and quietens both and switches them to dark; "battery mode" lowers brightness and turns on the phone's battery saver; "normal mode" undoes meeting and night mode. They are ordinary protocols: change them or add your own with `protocol_save`.

**Suggestions.** Sparx asks rather than guesses when a choice is yours (two apps with similar names, two matching audio devices). With the daemon running it also offers settings changes when they make sense - battery saver when the phone is low, dark mode late in the evening, lower volume at night - as a notification you answer yes or no to. Turn that off with `sparx config proactive.device_suggestions false`.

**How much it may do without asking.** By default every one of these changes asks first, because they are `control` actions. To let Sparx change settings and drive the PC and phone without a prompt each time:

```
sparx config permissions.control allow
```

Installing software and phone shell commands stay behind `exec`, calls behind `send`, and shutdown, uninstalling and emptying the recycle bin behind `delete`. You can also open up a single tool instead, for example `sparx config tool_permissions.phone_setting allow`.

## Configuration keys that matter

View settings with `sparx config` (everything) or `sparx config proactive` (one branch). Set one with `sparx config KEY VALUE`. The value is parsed as JSON when it can be, otherwise stored as text, so mind your shell's quoting for JSON values.

| Key | Default | Meaning |
| --- | --- | --- |
| `name` | `Sparx` | The assistant's name. |
| `user` | empty | Your name. |
| `language` | `en` | Reply language (voice uses it too). |
| `personality` | `sparx` | `sparx`, `casual`, `professional` or `technical`. |
| `address` | `sir` | How the sparx personality addresses you. |
| `models.default`, `.fast`, `.smart`, `.vision`, `.embed` | empty | Model per role; empty falls back to the default. |
| `permissions.<risk>` | see table above | `allow`, `ask` or `deny`. |
| `tool_permissions.<tool>` | none | Per-tool override. |
| `limits.max_rounds`, `.max_tool_calls`, `.max_seconds`, `.max_agents` | 14, 40, 900, 4 | Per-run budgets. |
| `always_on` | `core, memory, productivity, sparx` | Groups loaded at the start of every chat. |
| `proactive.*` | enabled; briefing `08:00`; flags true | Background behaviour (see the daemon section). `proactive.toasts` turns off Windows toasts. |
| `voice.wake_word`, `.voice`, `.stt_model`, `.speak_replies` | `hey sparx`, `en-IN-NeerjaNeural`, `base`, true | Voice settings. |
| `server.host`, `server.port` | `127.0.0.1`, `8765` | Web UI address. `server.run_jobs` (default true) and `server.max_upload_mb` (default 25) also exist. |
| `allowed_roots` | empty list | Extra folders the file tools may touch. |
| `integrations.*` | empty | Settings for email, Telegram, Home Assistant, MQTT, web search and so on. Passwords and tokens never go here; they go in `.env`. |

### Integration settings and secrets

| Integration | Settings | Secret (in `.env` or the environment) |
| --- | --- | --- |
| Email (IMAP/SMTP) | `integrations.email` with `imap_host`, `smtp_host`, `user`; optional `imap_port`, `smtp_port`, `address`, `from_name`, `sent_folder`, `save_sent` | `SPARX_EMAIL_PASSWORD` (an app password) |
| Telegram | `integrations.telegram.chat_id` | `SPARX_TELEGRAM_TOKEN` (bot token from @BotFather) |
| WhatsApp | `integrations.whatsapp.phone_number_id` (the sending number's id in Meta's WhatsApp Cloud API) | `SPARX_WHATSAPP_TOKEN` |
| Home Assistant | `integrations.home_assistant.url` | `SPARX_HA_TOKEN` (long-lived access token) |
| MQTT | `integrations.mqtt.host`; optional `port`, `username` | `SPARX_MQTT_PASSWORD` |
| Web search | `integrations.searxng_url` (self-hosted SearXNG) | `BRAVE_API_KEY` (alternative) |
| GitHub tools | none | `GITHUB_TOKEN` |
| Phone (Android) | optional `integrations.phone.adb` (path to adb) and `integrations.phone.serial` (which device; saved automatically the first time one connects) | none |
| Image generation | `integrations.sd_url` for local Stable Diffusion | `OPENAI_API_KEY` for OpenAI |

Example: `sparx config integrations.home_assistant.url http://homeassistant.local:8123`. When a tool lacks its configuration it returns an error naming exactly what is missing.

## Optional dependencies

The required packages are listed under "Install and first run". Everything below is optional. The matching tools say what to install when it is missing, and `sparx doctor` shows which are present.

| Package | Used for | Without it |
| --- | --- | --- |
| `python-docx`, `python-pptx`, `openpyxl` | Word, PowerPoint and Excel files | Those file types cannot be created. |
| `pypdf` | Reading PDFs | PDF reading is unavailable. |
| `fpdf2` | Writing PDFs | PDFs cannot be created. With the old `fpdf` 1.x installed instead, non-Latin text becomes "?" and tables are plain text; `sparx doctor` flags it. |
| `faster-whisper` | Local speech-to-text | Speech is sent to a hosted Whisper instead when `GROQ_API_KEY` or `OPENAI_API_KEY` is set. With neither, speech-to-text tools say it is not set up. |
| `edge-tts`, `pyttsx3` | Natural voices (needs internet) and an offline voice | `edge-tts` is tried first and `pyttsx3` is the fallback when it is missing or offline. With neither, speaking fails with a message saying so. |
| `sounddevice` | Microphone and speaker | No microphone or speaker access, so no voice mode; the tools say to install it. Transcribing and creating audio files still work. |
| `opencv-python` (`cv2`) | Webcam | No webcam tools. |
| `mss` | Screenshots | No screenshot tools. |
| `pyautogui` | Mouse and keyboard control | No desktop control. |
| `pytesseract` | OCR | No OCR from images. |
| `paho-mqtt` | MQTT devices | MQTT tools report that the package is missing. |
| `ffmpeg` (a program, not a Python package) | Audio and video conversion and edits | Some audio and video tools cannot work. |

## Screen pilot and Telegram remote control

`screen_pilot` (risk `control`) does a multi-step job on the PC by taking a screenshot, asking the vision model for one action (click, type, key, scroll), doing it and repeating, for up to 30 steps. Steps the model marks as sending, paying, deleting, installing or signing in are put to you for approval first. It is only as good as the vision model and has not been tried on a real screen.

`sparx telegram` lets you message Sparx from anywhere. Create a bot with @BotFather, put `SPARX_TELEGRAM_TOKEN` in `~/.sparx/.env`, message the bot, read your chat id with `telegram_updates`, then `sparx config integrations.telegram.chat_id <id>`. Remote control works only in a private chat with the bot: `integrations.telegram.chat_id` must be your own user id, and a group or channel id (one starting with `-`) makes `sparx telegram` refuse to start. Only messages and button taps sent by that user are obeyed. Actions that need approval arrive as Yes/No buttons (120 seconds); each request has its own one-time buttons, and a tap on an old or finished request is answered "This request has expired." and approves nothing. `/stop` and `/resume` set and clear the emergency stop. The bot token is masked in anything Sparx sends back. Telegram traffic is not end-to-end encrypted.

## Coding assistant and automation from scripts

**`sparx run "prompt"`** runs one turn without a person at the keyboard, for scripts and CI. `--output-format` is `text` (default), `json` or `stream-json`. The exit code is 0 when it finished, 1 on an error, and 2 when it finished but at least one action needed an approval that was not given. Nobody is there to ask, so approvals are denied unless you pass `--yes` (or `--permission-mode yes`). `--allowed-tools` and `--deny-tools` take comma-separated names or globs, `--max-turns` caps the model rounds, and `--continue` or `--resume ID` pick up an earlier conversation. `sparx sessions` lists the stored conversations.

**Permission modes.** The `permission_mode` setting is `default` (the per-risk policy above), `accept_edits` (file-editing tools run without asking), `plan` or `bypass` (ask nothing). `permission_rules` holds `allow`, `ask` and `deny` lists of tool names (globs allowed), optionally with a pattern for the tool's main argument, for example `shell_run(git status*)`. Deny beats ask beats allow. A mode or rule only moves a call between ask and allow, or refuses it: it never lifts a `deny` policy or a tool's own hard refusal (protected paths, catastrophic commands). "Always allow" in an approval prompt lasts until that chat ends.

**Plan mode.** In plan mode only `read` tools run and everything else is refused until you approve the plan. Set `plan_mode` to start every session that way. The check sits in the tool registry, so shell commands, plugins and sub-agents are covered too.

**Hooks.** The `hooks` setting runs your shell commands around tool calls: events `pre_tool`, `post_tool`, `session_start`, `stop`, `user_prompt`, `pre_compact`, `subagent_stop` and `notification`. A hook receives JSON on stdin (event, tool, redacted arguments, the result for `post_tool`, session). A `pre_tool` hook that exits 2 blocks the call and its error text goes to the model; a `user_prompt` hook that exits 2 stops the prompt. Any other non-zero exit is only a warning. Hooks are read only from `settings.json`: the model and the web UI cannot set them, and they run without your credentials in their environment.

**`/rewind [n]`** puts back the files changed in the last n chat turns. Only files named in the arguments of the file tools (`code_edit`, `code_write`, `code_multi_edit`, `notebook_edit`, `file_write`) are saved, files over 5 MB are not, a shell command's side effects are not tracked, and the conversation itself is not rewound.

**Input shortcuts** in chat: `@path` attaches a file's text (`@folder/` lists it), `!command` runs a shell command yourself and keeps the output in the conversation, and `#note` appends a bullet to the project's `SPARX.md`. Attached files obey the same protected-path rules as the file tools.

**Project instructions and extensions.** Sparx reads `SPARX.md`, `AGENTS.md` and `CLAUDE.md` from the project into its system prompt (`sparx init` writes a `SPARX.md`). Skills (`skills/<name>/SKILL.md`), commands (`commands/<name>.md`), custom agents (`agents/<name>.md`) and output styles (`output-styles/<name>.md`) are read from `~/.sparx` and the project's `.sparx` folder, and also from `~/.claude` and the project's `.claude` folder; the project wins over your home folder. They are guidance only: `allowed-tools` or `tools` can only narrow what a run may use and never add permissions. Choose an output style with `/output-style NAME`.

**Long conversations and loops.** Old messages are folded into a running summary instead of being cut off, and a failed summary falls back to plain truncation. The loop guard spots repeated, alternating or repeatedly failing tool calls and turns common errors into a recovery hint; its thresholds are `limits.loop_repeat_nudge` and `limits.loop_repeat_stop`, `limits.loop_fail_nudge` and `limits.loop_fail_stop`, and `limits.loop_alternate_nudge` and `limits.loop_alternate_stop`; `limits.loop_guard` turns it off.

**`sparx kaggle-sync`** keeps Sparx pointed at a model server running in a Kaggle notebook. The notebook writes its URL and token to a secret gist named by `SPARX_KAGGLE_GIST`; with `SPARX_KAGGLE_KERNEL` (user/slug) set, Sparx can also start the notebook with the `kaggle` program. It writes `BROWSERPILOT_BASE_URL` and `BROWSERPILOT_API_KEY` to `~/.sparx/.env`, only accepts an `https` URL (plain `http` only for localhost) and a token of ordinary characters, and leaves GitHub alone while the current server still answers. `--watch` keeps checking, `--now` starts a session and waits for it, and `--autostart on` or `off` adds or removes a hidden Windows start-up script. `sparx models` lists the models you can use: Ollama, hosted providers with a key, and the Kaggle notebook.

## Known limits

Read this before trusting Sparx with anything important.

- **Hardware and account integrations are untested against the real thing.** The microphone, camera, desktop control (mouse, keyboard, screenshots), email, Telegram, Home Assistant and MQTT code has only been tested against fakes. It has not been verified on real devices or real accounts. Expect bugs, try harmless actions first, and keep `ask` on for `send` and `control`.
- **The shell denylist is a seatbelt, not a security boundary.** `shell_run` refuses a short list of obviously catastrophic commands (formatting disks, disk-wiping tools, registry deletes, shutdown, recursive delete of a drive or home folder, encoded PowerShell blobs). Pattern matching on command text is easy to get around, and anything else runs with your user's permissions once you approve it. Read what you approve.
- **Knowledge search is keyword-only until an embedding model is available.** Documents are indexed with SQLite full-text search (BM25). Meaning-based search is added only when an embedding model is reachable through Ollama (default `nomic-embed-text`, installed with `ollama pull nomic-embed-text`, or the model named in `models.embed`). Without it, searches match words, not meaning, and the ingest result says embeddings are off.
- **Prompt injection is mitigated, not solved.** Marking untrusted text and scanning for obvious phrases helps, but a determined web page or email can still try to steer the model. Keep `send`, `control`, `delete` and `spend` on `ask` when Sparx reads content from the internet or from strangers.
- **Background jobs cannot ask you.** Anything set to `ask` does not run in the daemon. Device-control and send actions (risk `control` or `send`) are queued instead for `limits.pending_minutes` (default 60), and you can run or dismiss them from the Approvals panel in the web UI or by asking Sparx (`pending_list`, `pending_approve`). Locks, security devices and robots are never queued.
- **The approval prompt for a saved draft shows only the first 500 characters of the body.** It lists the recipients, cc, subject and attachment names in full. Read a long draft first (`email_drafts`) before you approve.
- **Address pinning depends on a private part of the HTTP library.** The guard that makes fetches connect only to the checked address replaces an internal part of `httpx` (tested with 0.28.1). A different `httpx` version could break it, and the web tests would be the place to notice.
- **The exercise runner is not a sandbox.** See "Behaviour of specific tools".
- **Automation chains stop after 3 runs in a row.** This covers runs started by notifications, events and file changes that the run before made. A change nobody's run could have made starts a chain at depth 0.
- **Phone control is untested on a real device.** The phone tools are tested against a simulated phone. Android versions and phone makers differ: some switches (mobile data, Bluetooth, battery saver while charging) are refused over ADB on some phones. Sparx reads every setting back and tells you when the phone kept the old value. iPhones are not supported. Screens that block capture (banking apps, the lock screen) cannot be read.
- **Model quality limits Sparx.** Small local models make mistakes with tool calls, and any model can be wrong. Check anything that matters.
- **Windows in practice.** Toast notifications, encrypted secrets and desktop control assume Windows.
- **Network exposure.** The web UI is plain HTTP. Do not expose it beyond a network you trust without HTTPS in front of it.
- **No service installer and no auto-update.** You start and keep `serve`, `daemon` and `voice` running yourself.
