"""Web UI and API: chat over a WebSocket, dashboards, approvals, uploads. `sparx serve` runs it.

Security model: bound to 127.0.0.1 unless the user chooses otherwise; every /api call and the WebSocket need the
access token (Authorization: Bearer) or a session cookie obtained by logging in; an optional PIN locks sessions;
state-changing requests and the WebSocket must come from the page's own origin; the page may load only itself (CSP).
"""
import asyncio
import inspect
import json
import re
import socket
import sqlite3
import time
import traceback
import uuid
from contextlib import asynccontextmanager, suppress
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response

from . import __version__, auth, automation, config, db, jobs, llm, models, pending, security, tools, undo
from .assistant import Sparx, kv_get, kv_set

WEB = Path(__file__).parent / "web"
STATIC = {"app.js": "text/javascript", "orb.js": "text/javascript", "style.css": "text/css", "manifest.json": "application/manifest+json",
          "sw.js": "text/javascript", "icon.svg": "image/svg+xml"}
COOKIE = "sparx_session"
UNSAFE = {"POST", "PUT", "PATCH", "DELETE"}
PIN_FREE = {"/api/unlock", "/api/logout"}       # reachable while the session is PIN-locked
APPROVAL_TIMEOUT = 120.0                        # seconds the browser has to answer an approval; then it is a deny
JOB_INTERVAL = 20.0
MAX_MESSAGE = 20000

# settings the web UI may change. Everything else (limits, allowed_roots, integrations, server, always_on) is CLI-only.
SAFE_KEYS = {"name": 80, "user": 80, "address": 40, "language": 20, "personality": 500}
SAFE_GROUPS = ("proactive", "voice", "models")
GUARDED_GROUPS = ("permissions", "tool_permissions")     # need the PIN
POLICIES = ("allow", "ask", "deny")

# tables owned by other modules: name candidates per dashboard, read with SELECT * and rendered generically
TABLES = {"tasks": ("tasks",), "events": ("events", "calendar_events", "calendar"), "reminders": ("reminders",),
          "habits": ("habits",), "goals": ("goals",), "memories": ("memories", "memory"), "expenses": ("expenses",)}
_DONE_COLS = ("done", "completed", "complete", "finished", "fired", "sent", "dismissed", "archived", "cancelled")
_DONE_STATUS = ("done", "completed", "complete", "cancelled", "canceled", "closed", "archived", "sent", "fired")
_WHEN = re.compile(r"start|when|date|due|time|day|remind|(^|_)at$")

CONNS: set = set()      # live WebSocket connections


# ---- request helpers

def _bearer(conn) -> str:
    h = conn.headers.get("authorization", "")
    return h[7:].strip() if h[:7].lower() == "bearer " else ""


def _client(conn) -> str:
    return conn.client.host if conn.client else "unknown"


def _same_origin(conn) -> bool | None:
    """True/False when the browser sent an Origin header (does it match Host?), None when there is none."""
    origin = conn.headers.get("origin")
    if origin is None:
        return None
    return urlsplit(origin).netloc.lower() == conn.headers.get("host", "").lower() != ""


def _unlocked(conn, token: str) -> bool:
    if not auth.locked(token):
        return True
    pin = conn.headers.get("x-sparx-pin", "")       # API clients using the bare token send the PIN per request
    return bool(pin) and auth.try_pin(pin, _client(conn))      # the same counted attempt as /api/unlock


def _csp(host: str) -> str:
    ws = f" ws://{host} wss://{host}" if re.fullmatch(r"[A-Za-z0-9.\-:\[\]]+", host or "") else ""
    return ("default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data: blob:; font-src 'self'; "
            f"connect-src 'self'{ws}; media-src 'self' blob:; manifest-src 'self'; worker-src 'self'; object-src 'none'; "
            "base-uri 'none'; form-action 'self'; frame-ancestors 'none'")


def _guard(request: Request) -> JSONResponse | None:
    """Origin and authentication checks shared by every HTTP route. None means the request may proceed."""
    path = request.url.path
    bearer = _bearer(request)
    token = bearer or request.cookies.get(COOKIE, "")
    request.state.token = token
    if request.method in UNSAFE:
        same = _same_origin(request)
        cross_site = request.headers.get("sec-fetch-site", "same-origin") not in ("same-origin", "none")
        if same is False or cross_site or (same is None and not bearer and path != "/api/login"):
            return JSONResponse({"detail": "Cross-origin request refused."}, 403)
    if not path.startswith("/api/") or path == "/api/login":
        return None
    if not auth.check(token):
        return JSONResponse({"detail": "Not signed in."}, 401)
    if path not in PIN_FREE and not _unlocked(request, token):
        return JSONResponse({"detail": "Locked. Enter the PIN."}, 423)
    return None


async def _json(request: Request) -> dict:
    try:
        body = await request.json()
    except ValueError:
        body = None
    if not isinstance(body, dict):
        raise HTTPException(400, "Send a JSON object.")
    return body


# ---- data helpers

def _plain(v):
    if isinstance(v, (bytes, bytearray, memoryview)):
        return f"<{len(v)} bytes>"
    return v[:2000] + "…" if isinstance(v, str) and len(v) > 2000 else v


def rows(table: str, limit: int = 200) -> list[dict]:
    """Newest rows of a table another module owns; [] when it does not exist or cannot be read."""
    if not re.fullmatch(r"[A-Za-z_]\w*", table or ""):
        return []
    for order in (" ORDER BY rowid DESC", ""):
        try:
            return [{k: _plain(v) for k, v in r.items()}
                    for r in db.q(f'SELECT * FROM "{table}"{order} LIMIT ?', (int(limit),))]
        except sqlite3.Error:
            continue
    return []


def dash(kind: str, limit: int = 200) -> list[dict]:
    for table in TABLES.get(kind, ()):
        found = rows(table, limit)
        if found:
            return found
    return []


def _open(items: list[dict]) -> list[dict]:
    """Drop rows that look finished, whatever the owning module called that column."""
    def finished(r):
        return any(r.get(c) not in (None, 0, "", "0", False) for c in _DONE_COLS) or \
            str(r.get("status") or r.get("state") or "").lower() in _DONE_STATUS
    return [r for r in items if not finished(r)]


def _on_day(items: list[dict], day: str) -> list[dict]:
    def hit(r):
        return any(isinstance(v, str) and v.startswith(day) and _WHEN.search(k.lower())
                   and not k.lower().startswith(("created", "updated", "added")) for k, v in r.items())
    return [r for r in items if hit(r)]


def today() -> dict:
    day = datetime.now().date().isoformat()
    return {"date": day, "events": _on_day(dash("events"), day), "tasks": _open(dash("tasks"))[:30],
            "reminders": _open(dash("reminders"))[:30], "notifications": jobs.unread(10)}


def heartbeat() -> dict | None:
    """The background daemon's last sign of life, wherever it left one (a kv row or a small file under HOME)."""
    with suppress(sqlite3.Error):
        for r in db.q("SELECT k, v FROM kv WHERE k LIKE 'daemon%' OR k LIKE 'heartbeat%' LIMIT 5"):
            return {"source": r["k"], "value": r["v"][:200]}
    for name in ("daemon.json", "daemon.heartbeat", "heartbeat.json", "heartbeat", "daemon.pid"):
        f = config.path(name, mkdir=False)
        with suppress(OSError):
            return {"source": name, "value": f.read_text(encoding="utf-8", errors="replace")[:200],
                    "age_seconds": int(time.time() - f.stat().st_mtime)}
    return None


async def run_tool(name: str, args: dict, approve: bool = False) -> tuple[bool, object]:
    """Run a registered tool for the UI. With approve=True the user's click is the approval ('deny' policies still hold);
    without it nobody is asked, as in the daemon. Returns (ok, parsed JSON or text)."""
    async def yes(tool, a):
        return True
    ctx = tools.Context(session="web", agent="web-ui", approve=yes if approve else None, scope=kv_get("scope", "personal"))
    try:
        text = await tools.call(name, args, ctx)
    except security.Stopped as e:
        return False, f"Stopped: {e}"
    if text.startswith(("Error:", "Not done:")):
        return False, text
    try:
        return True, json.loads(text)
    except ValueError:
        return True, text


def _run_card(r: dict) -> dict:
    """One automation run for the HUD: automation.runs()'s summary without the step log. A waiting run also says what
    is pending and which later steps an approval lets through, because the click approves the rest of the run."""
    out = {"id": r["run_id"], **{k: r[k] for k in ("automation", "status", "trigger", "started", "finished")}}
    if r["status"] != "waiting_approval":
        return out
    out["pending"], out["then"] = r["pending"], []
    run = automation.get_run(r["run_id"])
    for n, s in enumerate(run["steps"][run["step"] + 1:], run["step"] + 2):
        t = tools.REGISTRY.get(s.get("tool") or "")
        if t and security.permission(t.risk, t.name) == "ask":
            args = json.dumps(security.redact(s.get("args") or {}), ensure_ascii=False, default=str)[:300]
            out["then"].append(f"step {n}: {t.name} [{t.risk}] {args}")
        elif s.get("prompt"):
            out["then"].append(f"step {n}: prompt: {str(s['prompt'])[:200]}")
    return out


def _denied_step(run_id: int) -> str:
    """Name of the tool a waiting run is paused on, if the user's permission settings forbid it; else ''."""
    run = automation.get_run(run_id)
    if not run or run["status"] != "waiting_approval" or run["step"] >= len(run["steps"]):
        return ""
    t = tools.REGISTRY.get(run["steps"][run["step"]].get("tool") or "")
    return t.name if t and security.permission(t.risk, t.name) == "deny" else ""


def _fit(name: str, **slots) -> dict:
    """Map our generic argument names onto whatever the tool calls them."""
    alias = {"id": ("id", "memory_id", "key"), "text": ("text", "content", "value", "fact", "memory"),
             "scope": ("scope",), "query": ("query", "q", "search"), "limit": ("limit",)}
    params = tools.REGISTRY[name].params
    out = {}
    for slot, value in slots.items():
        key = next((a for a in alias[slot] if a in params), None)
        if key and value not in (None, ""):
            is_int = params[key].get("type") == "integer" and str(value).lstrip("-").isdigit()
            out[key] = int(value) if is_int else value
    return out


def safe_filename(name: str) -> str:
    """A plain file name: no folders, no drive or stream separators, no control characters, no reserved names."""
    name = re.split(r"[\\/]", name or "")[-1]
    name = re.sub(r"[^\w.\- ]", "_", name).strip(" .")
    if re.fullmatch(r"(?i)(con|prn|aux|nul|com\d|lpt\d)", name.split(".")[0]):
        name = "_" + name
    if len(name) > 100:
        name = name[:80] + name[-20:]
    return name or "upload"


def _file_part(body: bytes, content_type: str) -> tuple[str, bytes] | None:
    """First file in a multipart/form-data body, as (filename, data)."""
    m = re.search(r'boundary="?([^";,]+)"?', content_type)
    if not m:
        return None
    for part in (b"\r\n" + body).split(b"\r\n--" + m.group(1).encode("latin-1"))[1:]:
        if part[:2] == b"--":
            break
        head, sep, data = part.partition(b"\r\n\r\n")
        name = re.search(r'filename="((?:[^"\\]|\\.)*)"', head.decode("utf-8", "replace"))
        if sep and name:
            return name.group(1), data
    return None


def _check_setting(key: str, value) -> bool:
    """Validate one dotted key/value from the web UI. True if it needs the PIN. Raises HTTPException if not allowed."""
    group, _, leaf = key.partition(".")
    if key in SAFE_KEYS:
        if not isinstance(value, str) or len(value) > SAFE_KEYS[key]:
            raise HTTPException(400, f"{key} must be text of at most {SAFE_KEYS[key]} characters.")
        return False
    if group in SAFE_GROUPS and re.fullmatch(r"\w{1,40}", leaf):
        default = config.DEFAULTS[group].get(leaf)
        if group == "models" and leaf not in config.DEFAULTS["models"]:
            raise HTTPException(403, f"'{key}' is not a model role.")
        ok = isinstance(value, type(default)) if default is not None else isinstance(value, (str, bool, int, float))
        if not ok or (isinstance(value, str) and len(value) > 120):
            raise HTTPException(400, f"{key} has the wrong type.")
        return False
    if group in GUARDED_GROUPS and re.fullmatch(r"[\w:.\-]{1,80}", leaf):
        if group == "permissions" and leaf not in security.RISKS:
            raise HTTPException(400, f"'{leaf}' is not a risk level.")
        if value not in POLICIES and not (group == "tool_permissions" and value == ""):
            raise HTTPException(400, f"{key} must be one of {', '.join(POLICIES)}.")
        return True
    raise HTTPException(403, f"'{key}' cannot be changed from the web UI. Use `sparx config {key} <value>` on the computer.")


def _nested(key: str, value) -> dict:
    out = cur = {}
    parts = key.split(".", 1)
    for p in parts[:-1]:
        cur[p] = {}
        cur = cur[p]
    cur[parts[-1]] = value
    return out


def broadcast(event: dict, skip=None):
    for c in list(CONNS):
        if c is not skip:
            c.send(event)


def conversation_markdown(found: list[dict]) -> str:
    """A stored conversation as a Markdown document: title, date, then each message under You / Sparx."""
    first = next((r["content"] for r in found if r["role"] == "user"), "")
    title = " ".join(first.split())[:80] or "Conversation"
    out = [f"# {title}", "", f"Date: {found[0]['ts'][:10]}  ", f"Messages: {len(found)}", ""]
    for r in found:
        who = "You" if r["role"] == "user" else "Sparx"
        out += [f"## {who} · {r['ts'].replace('T', ' ')}", "", r["content"].strip(), ""]
    return "\n".join(out)


@undo.handler("conversation_restore")
def _undo_conversation_delete(data):
    """Put a deleted conversation's rows back, with their old ids unless something has taken one since."""
    found = data["rows"]
    if not found:
        return
    known = {c["name"] for c in db.q("PRAGMA table_info(messages)")}
    ids = [r["id"] for r in found]
    taken = db.one(f"SELECT 1 AS x FROM messages WHERE id IN ({','.join('?' * len(ids))}) LIMIT 1", ids)
    cols = [c for c in found[0] if c in known and not (taken and c == "id")]
    db.many(f"INSERT INTO messages ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
            [tuple(r.get(c) for c in cols) for r in found])
    if not taken:           # rows given new ids are picked up by the incremental index fill
        from .tools import memory
        memory.reindex_messages(ids)
    summary = data.get("summary")
    if summary and not db.one("SELECT 1 AS x FROM conv_summary WHERE conversation = ?", (data["conversation"],)):
        db.x("INSERT INTO conv_summary (conversation, summary, upto_id, ts) VALUES (?,?,?,?)",
             (data["conversation"], summary["summary"], summary["upto_id"], db.now()))
    broadcast({"type": "refresh", "conversation": data["conversation"]})


# ---- chat connection

class Conn:
    """One browser tab: its own Sparx, one turn at a time, events queued so nothing is sent concurrently."""

    def __init__(self, ws: WebSocket):
        self.ws = ws
        self.loop = asyncio.get_running_loop()
        self.out: asyncio.Queue = asyncio.Queue()
        self.pending: dict[str, asyncio.Future] = {}
        self.turn: asyncio.Task | None = None
        self.bot = Sparx(approve=self.approve, emit=self.send)

    def send(self, event: dict):
        """Queue an event for the browser. Safe from any thread."""
        self.loop.call_soon_threadsafe(self.out.put_nowait, event)

    def on_notification(self, n: dict):
        self.send({"type": "notification", "notification": n})

    async def pump(self):
        while True:
            await self.ws.send_text(json.dumps(await self.out.get(), ensure_ascii=False, default=str))

    async def approve(self, tool, args) -> bool:
        aid, fut = uuid.uuid4().hex[:12], self.loop.create_future()
        self.pending[aid] = fut
        self.send({"type": "approval_request", "id": aid, "tool": tool.name, "risk": tool.risk,
                   "description": tool.description[:300], "args": security.redact(args), "timeout": APPROVAL_TIMEOUT})
        allow, reason = False, "timed out"
        try:
            allow = bool(await asyncio.wait_for(fut, APPROVAL_TIMEOUT))
            reason = "allowed" if allow else "denied"
        except asyncio.TimeoutError:
            pass
        finally:
            self.pending.pop(aid, None)
        self.send({"type": "approval_resolved", "id": aid, "allow": allow, "reason": reason})
        return allow

    async def run(self, text: str):
        bot = self.bot
        bot.conversation = kv_get("conversation") or bot.conversation     # the conversation and scope are shared
        bot.scope = kv_get("scope", bot.scope)                            # by every device, so re-read them
        self.send({"type": "turn_start", "conversation": bot.conversation, "text": text})
        try:
            answer = await bot.turn(text)
            self.send({"type": "assistant", "text": answer, "conversation": bot.conversation, "loaded": sorted(bot.active)})
            broadcast({"type": "refresh", "conversation": bot.conversation}, skip=self)
        except asyncio.CancelledError:
            self.send({"type": "cancelled"})
        except (Exception, SystemExit) as e:
            self.send({"type": "error", "text": f"{type(e).__name__}: {str(e)[:400]}"})

    def cancel(self):
        if self.turn and not self.turn.done():
            self.turn.cancel()
        for fut in self.pending.values():
            if not fut.done():
                fut.cancel()

    def handle(self, msg: dict):
        kind = msg.get("type")
        if kind == "user":
            text = str(msg.get("text") or "").strip()[:MAX_MESSAGE]
            if self.turn and not self.turn.done():
                self.send({"type": "error", "busy": True, "text": "Still working on the previous message. Stop it or wait."})
            elif text:
                self.turn = asyncio.create_task(self.run(text))
        elif kind == "approval":
            fut = self.pending.get(str(msg.get("id")))
            if fut and not fut.done():
                fut.set_result(msg.get("allow") is True)
        elif kind == "stop":
            security.request_stop("web UI")
            for c in list(CONNS):
                c.cancel()
            broadcast({"type": "stopped"})
        elif kind == "cancel":
            self.cancel()
        elif kind == "ping":
            self.send({"type": "pong"})


async def _chat(ws: WebSocket):
    bearer = _bearer(ws)
    token = bearer or ws.cookies.get(COOKIE, "")
    same = _same_origin(ws)
    if same is False or (same is None and not bearer):
        return await ws.close(4403)
    pin_then = auth.pin_stamp()     # a bearer connection has no session to lock again: it ends when the PIN changes
    if not auth.check(token) or not _unlocked(ws, token):
        return await ws.close(4401)
    await ws.accept()
    conn = Conn(ws)
    CONNS.add(conn)
    jobs.LISTENERS.append(conn.on_notification)
    pump = asyncio.create_task(conn.pump())
    conn.send({"type": "hello", "conversation": conn.bot.conversation, "scope": conn.bot.scope,
               "stop": security.stop_requested()})
    try:
        while True:
            raw = await ws.receive_text()
            if not auth.check(token) or (auth.pin_stamp() != pin_then if bearer else auth.locked(token)):
                await ws.close(4401)
                break
            try:
                msg = json.loads(raw)
            except ValueError:
                continue
            if isinstance(msg, dict):
                conn.handle(msg)
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        CONNS.discard(conn)
        with suppress(ValueError):
            jobs.LISTENERS.remove(conn.on_notification)
        conn.cancel()
        pump.cancel()


# ---- background jobs in this process

async def job_loop(interval: float | None = None):
    """Run the daemon's tick() here so reminders and briefings work with only `sparx serve` running."""
    try:
        from . import daemon
    except Exception:
        return
    tick = getattr(daemon, "tick", None)
    if not inspect.iscoroutinefunction(tick):
        return
    from . import joblock
    lock = joblock.JobLock("serve", log=lambda m: print(m, flush=True))   # one job loop per Sparx home
    iv = JOB_INTERVAL if interval is None else interval
    try:
        while True:
            if lock.hold(iv) and not security.stop_requested():
                try:
                    await tick()
                except Exception:
                    config.path("logs", "errors.log").open("a", encoding="utf-8").write(
                        f"--- server job tick {time.strftime('%Y-%m-%d %H:%M:%S')}\n{traceback.format_exc()}\n")
            await asyncio.sleep(iv)
    finally:
        lock.release()


# ---- the app

def create_app(run_jobs: bool | None = None) -> FastAPI:
    tools.load_all()
    auth.ensure_token()

    @asynccontextmanager
    async def lifespan(app):
        want = config.settings()["server"].get("run_jobs", True) if run_jobs is None else run_jobs
        task = asyncio.create_task(job_loop()) if want else None
        yield
        if task:
            task.cancel()
        with suppress(Exception):
            from . import plugins
            await asyncio.to_thread(plugins.close_all)

    app = FastAPI(title="Sparx", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)

    @app.middleware("http")
    async def guard(request: Request, call_next):
        resp = _guard(request) or await call_next(request)
        h = resp.headers
        h["Content-Security-Policy"] = _csp(request.headers.get("host", ""))
        h["X-Content-Type-Options"] = "nosniff"
        h["X-Frame-Options"] = "DENY"
        h["Referrer-Policy"] = "no-referrer"
        h["Cross-Origin-Opener-Policy"] = "same-origin"
        h["Cross-Origin-Resource-Policy"] = "same-origin"
        h["Permissions-Policy"] = "microphone=(self), camera=(), geolocation=(), payment=(), usb=()"
        h["Cache-Control"] = "no-store" if request.url.path.startswith(("/api/", "/login")) else "no-cache"
        return resp

    def _signed_in(request: Request, resp, session: str):
        resp.set_cookie(COOKIE, session, max_age=auth.SESSION_SECONDS, httponly=True, samesite="strict",
                        secure=request.url.scheme == "https", path="/")
        return resp

    # -- static shell (holds no data, so it is served without a session)

    @app.get("/")
    def index():
        return FileResponse(WEB / "index.html", media_type="text/html")

    @app.get("/login")
    def login_link(request: Request, code: str = ""):
        if auth.throttled(_client(request)):
            return JSONResponse({"detail": "Too many failed attempts. Wait a few minutes."}, 429)
        session = auth.login(code, _client(request), codes_only=True)
        if not session:
            return RedirectResponse("/#login-failed", 303)
        return _signed_in(request, RedirectResponse("/", 303), session)

    # -- sign-in

    @app.post("/api/login")
    async def login(request: Request):
        if auth.throttled(_client(request)):
            raise HTTPException(429, "Too many failed attempts. Wait a few minutes.")
        session = auth.login(str((await _json(request)).get("token") or "").strip(), _client(request))
        if not session:
            raise HTTPException(401, "That token or code is not valid.")
        return _signed_in(request, JSONResponse({"ok": True, "pin_required": auth.has_pin()}), session)

    @app.post("/api/logout")
    def logout(request: Request):
        auth.logout(request.state.token)
        resp = JSONResponse({"ok": True})
        resp.delete_cookie(COOKIE, path="/")
        return resp

    @app.post("/api/unlock")
    async def unlock(request: Request):
        blocked = auth.pin_blocked(_client(request))
        if blocked:
            raise HTTPException(429, blocked)
        if not auth.unlock(request.state.token, str((await _json(request)).get("pin") or ""), _client(request)):
            raise HTTPException(401, "Wrong PIN.")
        return {"ok": True}

    @app.post("/api/lock")
    def lock(request: Request):
        auth.lock(request.state.token)
        return {"ok": True}

    @app.post("/api/auth/code")
    def link_device():
        code = auth.login_code()
        return {"path": f"/login?code={code}", "expires_in": auth.CODE_SECONDS}

    # -- state

    @app.get("/api/state")
    def state():
        s = config.settings()
        loaded = set(s["always_on"]).union(*(c.bot.active for c in CONNS))
        try:
            model = llm.spec_for()
        except Exception as e:
            model = f"unavailable ({type(e).__name__})"
        return {"name": s["name"], "user": s["user"], "version": __version__, "model": model,
                "language": s["language"], "personality": s["personality"],
                "groups": [{"name": c, "about": tools.CATEGORIES.get(c, ""), "tools": len(ts), "loaded": c in loaded}
                           for c, ts in sorted(tools.by_category().items())],
                "loaded": sorted(loaded), "stop": security.stop_requested(), "daemon": heartbeat(),
                "conversation": kv_get("conversation"), "scope": kv_get("scope", "personal"),
                "unread": len(jobs.unread(200)), "pending": len(pending.rows("pending", 200)),
                "waiting_runs": db.one("SELECT COUNT(*) AS n FROM automation_runs WHERE status = 'waiting_approval'")["n"],
                "pin_set": auth.has_pin(), "load_errors": tools.LOAD_ERRORS}

    @app.get("/api/tools")
    def tool_list():
        return {c: {"about": tools.CATEGORIES.get(c, ""),
                    "tools": [{"name": t.name, "description": t.description, "risk": t.risk,
                               "policy": security.permission(t.risk, t.name)} for t in ts]}
                for c, ts in sorted(tools.by_category().items())}

    @app.get("/api/audit")
    def audit(limit: int = 100, tool: str = ""):
        return security.audit_log(max(1, min(limit, 500)), tool)

    @app.get("/api/notifications")
    def notifications(all: bool = False):
        if all:
            return db.q("SELECT * FROM notifications ORDER BY id DESC LIMIT 100")
        return jobs.unread(100)

    @app.post("/api/notifications/read")
    async def notifications_read(request: Request):
        ids = (await _json(request)).get("ids")
        jobs.mark_read([int(i) for i in ids] if isinstance(ids, list) and ids else None)
        return {"ok": True}

    @app.get("/api/undo")
    def undo_list():
        return undo.recent(50)

    @app.post("/api/undo")
    async def undo_run(request: Request):
        uid = (await _json(request)).get("id")
        try:
            return {"result": await asyncio.to_thread(undo.run, int(uid) if uid else None)}
        except Exception as e:
            raise HTTPException(400, f"Could not undo: {type(e).__name__}: {str(e)[:200]}")

    @app.get("/api/settings")
    def settings_get():
        s = config.settings()
        s["integrations"] = sorted(s["integrations"])      # names only; their details stay on the computer
        return {"settings": security.redact(s), "pin_set": auth.has_pin(),
                "editable": [*SAFE_KEYS, *(f"{g}.*" for g in SAFE_GROUPS)], "pin_required": [f"{g}.*" for g in GUARDED_GROUPS]}

    @app.get("/api/models")
    async def models_get(refresh: bool = False):
        return await asyncio.to_thread(models.available, refresh)

    @app.patch("/api/settings")
    async def settings_patch(request: Request):
        body = await _json(request)
        changes = body.get("changes")
        if not isinstance(changes, dict) or not changes:
            raise HTTPException(400, 'Send {"changes": {"dotted.key": value}}.')
        guarded = [k for k, v in changes.items() if _check_setting(str(k), v)]       # validates every key first
        if guarded:
            who = _client(request)
            if not auth.has_pin():
                raise HTTPException(403, "Permissions can only be changed here once a PIN is set. "
                                         "On the computer run: python -m sparx.auth set-pin")
            blocked = auth.pin_blocked(who)
            if blocked:
                raise HTTPException(429, blocked)
            if not auth.try_pin(str(body.get("pin") or ""), who):
                raise HTTPException(403, "Changing permissions needs the correct PIN.")
        for k, v in changes.items():
            config.save_settings(_nested(str(k), v))
        return {"ok": True, "changed": sorted(changes)}

    @app.post("/api/stop")
    def stop():
        security.request_stop("web UI")
        for c in list(CONNS):
            c.loop.call_soon_threadsafe(c.cancel)
        broadcast({"type": "stopped"})
        return {"stop": True}

    @app.post("/api/resume")
    def resume():
        security.clear_stop()
        broadcast({"type": "resumed"})
        return {"stop": False}

    @app.get("/api/usage")
    def usage():
        day = datetime.now().date().isoformat()
        return {"llm": llm.USAGE, "history": llm.usage_history(30),
                "tools_today": db.one("SELECT COUNT(*) AS calls, COALESCE(SUM(ok = 0), 0) AS errors, "
                                      "COALESCE(SUM(ms), 0) AS ms FROM audit WHERE ts >= ?", (day,)),
                "top_tools": db.q("SELECT tool, COUNT(*) AS calls, COALESCE(SUM(ok = 0), 0) AS errors FROM audit "
                                  "WHERE ts >= ? GROUP BY tool ORDER BY calls DESC LIMIT 10", (day,))}

    # -- actions a background job could not run because nobody was there to approve them

    @app.get("/api/pending")
    def pending_list():
        def known(r):
            t = tools.REGISTRY.get(r["tool"])
            return {**r, "risk": t.risk if t else "", "description": (t.description if t else "")[:300]}
        return {"pending": [known(r) for r in pending.rows("pending")],
                "recent": [r for r in pending.rows("", 200) if r["status"] != "pending"][:20]}

    async def _pending_do(tool_name: str, id: int):
        ok, out = await run_tool(tool_name, {"id": id}, approve=True)     # the click on the card is the approval
        if not ok:
            raise HTTPException(400, str(out))
        broadcast({"type": "refresh", "conversation": kv_get("conversation")})
        return {"ok": True, "result": out}

    @app.post("/api/pending/{id}/approve")
    async def pending_approve(id: int):
        return await _pending_do("pending_approve", id)

    @app.post("/api/pending/{id}/dismiss")
    async def pending_dismiss(id: int):
        return await _pending_do("pending_dismiss", id)

    # -- saved automations and their runs; a run that paused for an approval is continued or dropped here

    @app.get("/api/automations")
    def automations():
        return {"automations": automation.listing(), "runs": [_run_card(r) for r in automation.runs(limit=30)]}

    async def _automation_do(tool_name: str, args: dict):
        ok, out = await run_tool(tool_name, args, approve=True)     # the click on the card is the approval
        if not ok:
            raise HTTPException(400, str(out))
        broadcast({"type": "refresh", "conversation": kv_get("conversation")})
        return {"ok": True, "result": out}

    @app.post("/api/automations/runs/{id}/resume")
    async def automation_resume(id: int):
        denied = _denied_step(id)
        if denied:      # resuming would only fail the run; leave it waiting so it can continue once the setting changes
            raise HTTPException(400, f"Not done: '{denied}' is disabled by the user's permission settings, "
                                     f"so run {id} is still waiting.")
        done = await _automation_do("automation_resume", {"run_id": id})
        run = automation.get_run(id)
        if run["status"] in ("failed", "stopped"):
            last = run["log"][-1] if run["log"] else {}
            raise HTTPException(400, f"Not done: run {id} {run['status']} at step {last.get('step', '?')}: "
                                     f"{str(last.get('output', ''))[:300]}")
        return {**done, "status": run["status"]}

    @app.post("/api/automations/runs/{id}/cancel")
    async def automation_cancel(id: int):
        return await _automation_do("automation_cancel", {"run_id": id})

    @app.post("/api/automations/{ref}/enabled")
    async def automation_enabled(ref: str, request: Request):
        on = (await _json(request)).get("enabled")
        if not isinstance(on, bool):
            raise HTTPException(400, 'Send {"enabled": true} or {"enabled": false}.')
        return await _automation_do("automation_enable" if on else "automation_disable", {"name": ref})

    # -- conversations (stored on the server, so every device sees the same ones)

    @app.get("/api/conversations")
    def conversations():
        found = db.q("SELECT conversation AS id, MIN(ts) AS started, MAX(ts) AS updated, COUNT(*) AS messages, "
                     "(SELECT substr(content, 1, 80) FROM messages u WHERE u.conversation = m.conversation "
                     " AND u.role = 'user' ORDER BY u.id LIMIT 1) AS title "
                     "FROM messages m GROUP BY conversation ORDER BY MAX(id) DESC LIMIT 100")
        return {"current": kv_get("conversation"), "conversations": found}

    @app.get("/api/conversations/{cid}/messages")
    def messages(cid: str):
        return db.q("SELECT id, role, content, ts, scope FROM messages WHERE conversation = ? ORDER BY id DESC LIMIT 200",
                    (cid,))[::-1]

    @app.post("/api/conversations")
    def conversation_new():
        cid = datetime.now().strftime("%Y%m%d-%H%M%S")
        kv_set("conversation", cid)
        broadcast({"type": "refresh", "conversation": cid})
        return {"current": cid}

    @app.post("/api/conversations/{cid}/select")
    def conversation_select(cid: str):
        if not db.one("SELECT 1 AS x FROM messages WHERE conversation = ? LIMIT 1", (cid,)):
            raise HTTPException(404, "No such conversation.")
        kv_set("conversation", cid)
        broadcast({"type": "refresh", "conversation": cid})
        return {"current": cid}

    def _stored(cid: str) -> list[dict]:
        found = db.q("SELECT * FROM messages WHERE conversation = ? ORDER BY id", (cid,))
        if not found:
            raise HTTPException(404, "No such conversation.")
        return found

    @app.get("/api/conversations/{cid}/export")
    def conversation_export(cid: str, format: str = "md"):
        if format not in ("md", "json"):
            raise HTTPException(400, "format must be md or json.")
        found = _stored(cid)
        name = safe_filename(f"sparx-conversation-{re.sub(r'[^A-Za-z0-9._-]', '_', cid)}.{format}")
        if format == "json":
            body, kind = json.dumps(found, ensure_ascii=False, indent=2, default=str), "application/json"
        else:
            body, kind = conversation_markdown(found), "text/markdown; charset=utf-8"
        return Response(body, media_type=kind, headers={"Content-Disposition": f'attachment; filename="{name}"'})

    @app.delete("/api/conversations/{cid}")
    def conversation_delete(cid: str):
        found = _stored(cid)
        if any(c.turn and not c.turn.done() and c.bot.conversation == cid for c in list(CONNS)):
            raise HTTPException(409, "Sparx is still answering in that conversation. Stop it or wait, then delete.")
        removed = db.x("DELETE FROM messages WHERE conversation = ? AND id <= ?", (cid, found[-1]["id"]))
        from .tools import memory
        memory.unindex_messages([r["id"] for r in found])
        from . import compact  # noqa: F401  (creates the conv_summary table)
        summary = db.one("SELECT summary, upto_id FROM conv_summary WHERE conversation = ?", (cid,))
        db.x("DELETE FROM conv_summary WHERE conversation = ?", (cid,))
        uid = undo.record(tools.Context(session=cid, agent="web-ui"), "conversation_restore",
                          f"Deleted conversation {cid} ({removed} messages)",
                          {"conversation": cid, "rows": found, "summary": summary})
        current = kv_get("conversation")
        if current == cid:     # otherwise the next message would quietly re-create the deleted conversation
            current = datetime.now().strftime("%Y%m%d-%H%M%S")
            current += "-1" if current == cid else ""
            kv_set("conversation", current)
        broadcast({"type": "refresh", "conversation": current})
        return {"deleted": removed, "conversation": cid, "undo_id": uid, "current": current}

    @app.post("/api/scope")
    async def scope_set(request: Request):
        scope = str((await _json(request)).get("scope") or "").strip()
        if not re.fullmatch(r"[\w][\w \-]{0,39}", scope):
            raise HTTPException(400, "A scope is a short name: letters, digits, spaces, '-' or '_'.")
        kv_set("scope", scope)
        return {"scope": scope}

    @app.post("/api/upload")
    async def upload(request: Request):
        limit = int(float(config.settings()["server"].get("max_upload_mb", 25)) * 1024 * 1024)
        ctype = request.headers.get("content-type", "")
        if not ctype.lower().startswith("multipart/form-data"):
            raise HTTPException(415, "Send the file as multipart/form-data.")
        too_big = HTTPException(413, f"File too large (limit {limit // (1024 * 1024)} MB).")
        declared = request.headers.get("content-length", "")
        if declared.isdigit() and int(declared) > limit + 4096:
            raise too_big
        body = bytearray()
        async for chunk in request.stream():
            body += chunk
            if len(body) > limit + 4096:
                raise too_big
        part = _file_part(bytes(body), ctype)
        if not part:
            raise HTTPException(400, "No file in the upload.")
        if len(part[1]) > limit:
            raise too_big
        name = safe_filename(part[0])
        dest = config.path("uploads", f"{time.strftime('%Y%m%d-%H%M%S')}-{name}")
        for n in range(1, 100):
            if not dest.exists():
                break
            dest = dest.with_name(f"{time.strftime('%Y%m%d-%H%M%S')}-{n}-{name}")
        await asyncio.to_thread(dest.write_bytes, part[1])
        return {"path": str(dest), "name": name, "size": len(part[1])}

    # -- dashboards

    @app.get("/api/today")
    def today_view():
        return today()

    @app.get("/api/dash/{kind}")
    def dashboard(kind: str, open_only: bool = False):
        if kind not in TABLES:
            raise HTTPException(404, f"Unknown dashboard. Choose from {', '.join(TABLES)}.")
        found = dash(kind)
        return {"kind": kind, "rows": _open(found) if open_only else found}

    @app.get("/api/memory")
    async def memory_list(scope: str = "", q: str = ""):
        can = {"editable": "memory_update" in tools.REGISTRY, "deletable": "memory_forget" in tools.REGISTRY}
        if "memory_list" not in tools.REGISTRY:
            return {"items": dash("memories"), "source": "table", "editable": False, "deletable": False}
        ok, out = await run_tool("memory_list", _fit("memory_list", scope=scope, query=q, limit=200))
        if not ok:
            raise HTTPException(400, str(out))
        if isinstance(out, dict):
            out = next((v for v in out.values() if isinstance(v, list)), [out])
        if isinstance(out, list):
            return {"items": [i if isinstance(i, dict) else {"text": str(i)} for i in out], "source": "tool", **can}
        return {"items": [], "text": str(out), "source": "tool", **can}

    async def _memory_change(tool_name: str, **slots):
        if tool_name not in tools.REGISTRY:
            raise HTTPException(501, "The memory tools are not installed, so memories cannot be changed here.")
        ok, out = await run_tool(tool_name, _fit(tool_name, **slots), approve=True)
        if not ok:
            raise HTTPException(400, str(out))
        return {"ok": True, "result": out}

    @app.patch("/api/memory/{mid}")
    async def memory_update(mid: str, request: Request):
        text = str((await _json(request)).get("text") or "").strip()
        if not text:
            raise HTTPException(400, "Send the corrected text.")
        return await _memory_change("memory_update", id=mid, text=text)

    @app.delete("/api/memory/{mid}")
    async def memory_forget(mid: str):
        return await _memory_change("memory_forget", id=mid)

    # -- HUD: system vitals, protocols, greeting (tools owned by sparx/tools/sparx.py; all optional)

    @app.get("/api/vitals")
    async def vitals():
        if "sparx_vitals" not in tools.REGISTRY:
            return {"available": False}
        ok, out = await run_tool("sparx_vitals", {})
        if not ok or not isinstance(out, dict):
            return {"available": False, "error": str(out)[:300]}
        return {"available": True, **out}

    @app.get("/api/protocols")
    async def protocols():
        if "protocol_list" not in tools.REGISTRY:
            return {"available": False, "protocols": []}
        ok, out = await run_tool("protocol_list", {})
        if ok and isinstance(out, dict):
            out = next((v for v in out.values() if isinstance(v, list)), [])
        if not ok or not isinstance(out, list):
            return {"available": ok, "protocols": []}
        found = [{"name": str(p.get("name"))[:60], "description": str(p.get("description") or "")[:200]}
                 for p in out if isinstance(p, dict) and p.get("name")]
        return {"available": True, "protocols": found}

    @app.get("/api/greeting")
    async def greeting():
        try:
            from .tools import sparx
            text = sparx.greeting()
            if inspect.isawaitable(text):
                text = await text
            return {"greeting": str(text or "Online.")[:400]}
        except Exception:
            return {"greeting": "Online."}

    # -- chat

    @app.websocket("/ws")
    async def ws_chat(ws: WebSocket):
        await _chat(ws)

    @app.get("/{name}")
    def static(name: str):
        if name not in STATIC:
            raise HTTPException(404, "Not found.")
        return FileResponse(WEB / name, media_type=STATIC[name])

    return app


def _lan_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))      # no packet is sent; this only picks the outgoing interface
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def serve(host: str, port: int):
    import uvicorn
    if auth.damaged():               # fail closed: no new token, nothing written over the file
        raise SystemExit(str(auth.Damaged()))
    first = auth.ensure_token()      # plaintext only the first time; afterwards only its hash exists
    app = create_app()
    local = host in ("127.0.0.1", "localhost", "::1")
    shown = "localhost" if local else _lan_ip() if host in ("0.0.0.0", "::") else host
    print(f"{config.settings()['name']} web UI. Open this one-time link (valid {auth.CODE_SECONDS // 60} minutes):\n"
          f"  http://{shown}:{port}/login?code={auth.login_code()}")
    if first:
        print(f"Access token for API clients (shown only once, keep it private):\n  {first}")
    if not local:
        print("\nWARNING: Sparx is reachable from other devices on your network, over plain unencrypted HTTP.\n"
              "  Anyone on the same Wi-Fi can read the traffic, including your session cookie and what you say.\n"
              "  Use it only on a network you trust. Safer: keep the default 127.0.0.1 and reach it through\n"
              "  Tailscale (`tailscale serve`) or an HTTPS tunnel. HTTPS is also what phones need for the\n"
              "  microphone and for installing the app. Set a PIN with: python -m sparx.auth set-pin\n")
    uvicorn.run(app, host=host, port=port, log_level="warning")
