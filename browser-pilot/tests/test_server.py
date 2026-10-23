import asyncio
import json
import sys
import types

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from sparx import auth, automation, config, db, jobs, llm, pending, security, server, tools
from sparx.tools import Tool, tool

ORIGIN = {"Origin": "http://testserver"}


@tool("t_srv_send", "send something", {"to": {"type": "string"}, "password": {"type": "string"}}, ["to"],
      category="testing_srv", risk="send")
async def _send(ctx, to, password=""):
    return f"sent to {to}"


@tool("t_srv_wait", "wait a long time", category="testing_srv")
async def _wait(ctx):
    await asyncio.sleep(30)


@pytest.fixture
def token():
    auth._fails.clear()
    return auth.ensure_token()


@pytest.fixture
def anon(token):
    """A browser that has not signed in."""
    return TestClient(server.create_app(run_jobs=False), headers=ORIGIN)


@pytest.fixture
def client(anon, token):
    assert anon.post("/api/login", json={"token": token}).status_code == 200
    return anon


def fake_tool(monkeypatch, name, fn, risk="read"):
    monkeypatch.setitem(tools.REGISTRY, name, Tool(name, name, {"id": {"type": "integer"}, "text": {"type": "string"}},
                                                   [], "fake", risk, False, 10, fn))


def until(ws, kind):
    """Read events until one of the given type arrives; returns (that event, everything read)."""
    seen = []
    while True:
        seen.append(ws.receive_json())
        if seen[-1]["type"] == kind:
            return seen[-1], seen
        assert seen[-1]["type"] not in ("assistant", "error", "cancelled"), f"turn ended before '{kind}': {seen}"


# ---- auth

def test_api_needs_auth(anon):
    for path in ("/api/state", "/api/audit", "/api/settings", "/api/vitals", "/api/conversations"):
        assert anon.get(path).status_code == 401
    assert anon.post("/api/stop").status_code == 401 and not security.stop_requested()
    assert anon.get("/api/state", headers={"Authorization": "Bearer wrong"}).status_code == 401
    with pytest.raises(WebSocketDisconnect):
        with anon.websocket_connect("/ws"):
            pass


def test_static_shell_and_security_headers(anon):
    r = anon.get("/")
    assert r.status_code == 200 and "<html" in r.text.lower()
    csp = r.headers["content-security-policy"]
    assert "default-src 'self'" in csp and "script-src 'self';" in csp and "unsafe" not in csp
    assert r.headers["x-frame-options"] == "DENY" and r.headers["x-content-type-options"] == "nosniff"
    for name in server.STATIC:
        assert anon.get(f"/{name}").status_code == 200, name
    assert anon.get("/auth.json").status_code == 404 and anon.get("/..%2fserver.py").status_code == 404


def test_bearer_token_and_token_is_stored_hashed(anon, token):
    assert anon.get("/api/state", headers={"Authorization": f"Bearer {token}"}).json()["name"] == "Sparx"
    assert token not in config.path("auth.json").read_text() and auth.ensure_token() is None


def test_login_flow_cookie_and_logout(anon, token):
    assert anon.post("/api/login", json={"token": "nope"}).status_code == 401
    r = anon.post("/api/login", json={"token": token})
    cookie = r.headers["set-cookie"].lower()
    assert r.status_code == 200 and "httponly" in cookie and "samesite=strict" in cookie
    assert anon.get("/api/state").status_code == 200
    assert anon.post("/api/logout").status_code == 200
    assert anon.get("/api/state").status_code == 401


def test_one_time_login_link(anon, client):
    path = client.post("/api/auth/code").json()["path"]
    phone = TestClient(client.app, headers=ORIGIN)
    r = phone.get(path, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/" and phone.get("/api/state").status_code == 200
    again = TestClient(client.app).get(path, follow_redirects=False)        # the code is spent
    assert again.headers["location"] == "/#login-failed" and "set-cookie" not in again.headers


def test_failed_logins_are_rate_limited(anon, token):
    for _ in range(auth.MAX_FAILS):
        assert anon.post("/api/login", json={"token": "guess"}).status_code == 401
    assert anon.post("/api/login", json={"token": token}).status_code == 429


def test_pin_lock(client, token):
    auth.set_pin("4821")
    assert client.get("/api/state").status_code == 423
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws"):
            pass
    assert client.post("/api/unlock", json={"pin": "0000"}).status_code == 401
    assert client.post("/api/unlock", json={"pin": "4821"}).status_code == 200
    assert client.get("/api/state").json()["pin_set"] is True
    bare = TestClient(client.app, headers={"Authorization": f"Bearer {token}"})
    assert bare.get("/api/state").status_code == 423
    assert bare.get("/api/state", headers={"X-Sparx-Pin": "4821"}).status_code == 200
    assert "4821" not in config.path("auth.json").read_text()
    with pytest.raises(ValueError):
        auth.set_pin("12")


def test_pin_guesses_are_limited_however_they_arrive(client, token):
    auth.set_pin("4821")
    bare = TestClient(client.app, headers={"Authorization": f"Bearer {token}", **ORIGIN})
    for i in range(auth.MAX_FAILS):                         # a token holder alternating guesses with fresh sign-ins
        guess = {"X-Sparx-Pin": f"000{i}"} if i % 2 else None
        r = bare.get("/api/state", headers=guess) if guess else client.post("/api/unlock", json={"pin": f"000{i}"})
        assert r.status_code == (423 if guess else 401), i
        assert bare.post("/api/login", json={"token": token}).status_code == 200
    assert bare.get("/api/state", headers={"X-Sparx-Pin": "4821"}).status_code == 423        # the header shares the count
    r = client.post("/api/unlock", json={"pin": "4821"})
    assert r.status_code == 429 and "wrong PINs" in r.json()["detail"]
    r = client.patch("/api/settings", json={"changes": {"permissions.send": "allow"}, "pin": "4821"})
    assert r.status_code in (423, 429) and config.settings()["permissions"]["send"] == "ask"
    with pytest.raises(WebSocketDisconnect):
        with bare.websocket_connect("/ws", headers={"X-Sparx-Pin": "4821"}):
            pass
    assert client.get("/api/state").status_code == 423


def test_pin_entry_locks_for_everyone_after_enough_failures(client, token):
    auth.set_pin("4821")
    for i in range(auth.PIN_MAX_ALL):
        assert not auth.try_pin("0000", f"10.0.0.{i}")      # twenty other addresses, one wrong guess each
    r = client.post("/api/unlock", json={"pin": "4821"})
    assert r.status_code == 429 and "minute" in r.json()["detail"] and client.get("/api/state").status_code == 423


def test_guarded_settings_pin_guesses_share_the_pin_limit(client):
    auth.set_pin("4821")
    assert client.post("/api/unlock", json={"pin": "4821"}).status_code == 200
    change = {"changes": {"permissions.send": "allow"}}
    for i in range(auth.MAX_FAILS):
        assert client.patch("/api/settings", json={**change, "pin": f"000{i}"}).status_code == 403
    assert client.patch("/api/settings", json={**change, "pin": "4821"}).status_code == 429
    assert config.settings()["permissions"]["send"] == "ask"


def test_damaged_auth_file_locks_the_server_and_is_left_alone(client, token, capsys):
    auth.set_pin("4821")
    assert client.post("/api/unlock", json={"pin": "4821"}).status_code == 200
    f = config.path("auth.json")
    broken = f.read_text(encoding="utf-8")[:40]
    f.write_text(broken, encoding="utf-8")
    assert client.get("/api/state").status_code == 401
    assert client.get("/api/state", headers={"Authorization": f"Bearer {token}"}).status_code == 401
    assert client.post("/api/login", json={"token": token}).status_code == 401
    assert client.post("/api/unlock", json={"pin": "4821"}).status_code == 401
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws"):
            pass
    again = TestClient(server.create_app(run_jobs=False), headers=ORIGIN)       # a restart issues no new token either
    assert again.post("/api/login", json={"token": token}).status_code == 401
    with pytest.raises(SystemExit) as stop:                 # `sparx serve` refuses to start and names the way out
        server.serve("127.0.0.1", 0)
    assert "python -m sparx.auth rotate-token" in str(stop.value)
    assert f.read_text(encoding="utf-8") == broken


def test_login_link_drops_the_code_and_is_not_cached(anon, client):
    code = client.post("/api/auth/code").json()["path"]
    for path, where in ((code, "/"), ("/login?code=wrong", "/#login-failed")):
        r = TestClient(client.app, headers=ORIGIN).get(path, follow_redirects=False)
        assert r.status_code == 303 and r.headers["location"] == where      # the code leaves the address bar
        assert r.headers["cache-control"] == "no-store" and r.headers["referrer-policy"] == "no-referrer"
        assert "code" not in r.text
    r = TestClient(client.app, headers=ORIGIN).get(client.post("/api/auth/code").json()["path"], follow_redirects=False)
    cookie = r.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=strict" in cookie and "path=/" in cookie


def test_rotating_the_token_cancels_printed_login_links(client, token):
    path = client.post("/api/auth/code").json()["path"]
    fresh = auth.rotate_token()
    r = TestClient(client.app, headers=ORIGIN).get(path, follow_redirects=False)
    assert r.headers["location"] == "/#login-failed" and "set-cookie" not in r.headers
    assert client.get("/api/state").status_code == 401
    assert client.get("/api/state", headers={"Authorization": f"Bearer {fresh}"}).status_code == 200


@pytest.mark.parametrize("how", ["cookie, PIN set", "cookie, token rotated", "bearer, PIN set", "bearer, PIN changed",
                                 "bearer, token rotated"])
def test_open_websocket_is_closed_on_its_next_message_after_a_lockdown(client, token, how):
    who, what = how.split(", ")
    headers = {}
    if what == "PIN changed":
        auth.set_pin("1111")
        assert client.post("/api/unlock", json={"pin": "1111"}).status_code == 200
        headers = {"X-Sparx-Pin": "1111"}
    if who == "bearer":
        client = TestClient(client.app, headers={"Authorization": f"Bearer {token}", **ORIGIN})
    with client.websocket_connect("/ws", headers=headers) as ws:
        assert ws.receive_json()["type"] == "hello"
        ws.send_json({"type": "ping"})
        assert ws.receive_json()["type"] == "pong"
        auth.rotate_token() if what == "token rotated" else auth.set_pin("4821")
        ws.send_json({"type": "ping"})
        with pytest.raises(WebSocketDisconnect) as closed:
            ws.receive_json()
        assert closed.value.code == 4401


def test_origin_check(client, token):
    evil = {"Origin": "http://evil.example"}
    assert client.post("/api/stop", headers=evil).status_code == 403
    assert client.post("/api/stop", headers={"Origin": "null"}).status_code == 403
    assert client.post("/api/stop", headers={"Sec-Fetch-Site": "cross-site"}).status_code == 403
    assert not security.stop_requested()
    no_origin = TestClient(client.app, cookies=dict(client.cookies))
    assert no_origin.get("/api/state").status_code == 200           # reads are fine
    assert no_origin.post("/api/stop").status_code == 403           # a cookie alone cannot change state
    assert no_origin.post("/api/stop", headers={"Authorization": f"Bearer {token}"}).status_code == 200
    security.clear_stop()
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws", headers=evil):
            pass


# ---- REST

def test_state_tools_audit_usage(client):
    s = client.get("/api/state").json()
    assert s["stop"] is False and "core" in s["loaded"] and any(g["name"] == "plugins" for g in s["groups"])
    assert "plugin_list" in [t["name"] for t in client.get("/api/tools").json()["plugins"]["tools"]]
    security.audit("s", "sparx", "t_echo", "read", {"password": "x"}, True, "ok", 3)
    a = client.get("/api/audit").json()
    assert a[0]["tool"] == "t_echo" and "***" in a[0]["args"]
    u = client.get("/api/usage").json()
    assert u["tools_today"]["calls"] == 1 and "calls" in u["llm"]
    assert u["history"]["rows"] == [] and u["history"]["totals"]["calls"] == 0
    llm.record_usage("a/m1", 10, 5, 100)
    u = client.get("/api/usage").json()
    assert u["history"]["totals"]["calls"] == 1 and [r["model"] for r in u["history"]["rows"]] == ["a/m1"]
    assert {"llm", "tools_today", "top_tools"} <= set(u)                    # the older keys are still there


def test_stop_and_resume(client):
    assert client.post("/api/stop").json() == {"stop": True}
    assert security.stop_requested() and client.get("/api/state").json()["stop"] is True
    assert client.post("/api/resume").json() == {"stop": False}
    assert not security.stop_requested()


def test_settings_allow_list(client):
    shown = client.get("/api/settings").json()
    assert shown["settings"]["permissions"]["send"] == "ask" and shown["pin_set"] is False

    def patch(changes, **extra):
        return client.patch("/api/settings", json={"changes": changes, **extra})
    assert patch({"personality": "technical", "proactive.reminders": False, "language": "kn"}).status_code == 200
    s = config.settings()
    assert (s["personality"], s["proactive"]["reminders"], s["language"]) == ("technical", False, "kn")
    assert s["proactive"]["deadline_risk"] is True
    for bad in ({"limits.max_tool_calls": 9999}, {"allowed_roots": ["C:/"]}, {"integrations.mcp_servers": {}},
                {"server.host": "0.0.0.0"}, {"always_on": []}, {"name": "ok", "limits.max_seconds": 1}):
        assert patch(bad).status_code == 403, bad
    assert patch({"proactive.reminders": "yes"}).status_code == 400
    assert patch({"name": {"nested": 1}}).status_code == 400
    assert config.settings()["name"] == "Sparx" and config.settings()["limits"]["max_tool_calls"] == 40


def test_permissions_need_the_pin(client):
    change = {"permissions.send": "allow"}
    assert client.patch("/api/settings", json={"changes": change}).status_code == 403        # no PIN set at all
    auth.set_pin("4821")
    client.post("/api/unlock", json={"pin": "4821"})
    assert client.patch("/api/settings", json={"changes": change}).status_code == 403
    assert client.patch("/api/settings", json={"changes": change, "pin": "1111"}).status_code == 403
    assert config.settings()["permissions"]["send"] == "ask"
    assert client.patch("/api/settings", json={"changes": {"permissions.send": "sure"}, "pin": "4821"}).status_code == 400
    assert client.patch("/api/settings", json={"changes": change, "pin": "4821"}).status_code == 200
    assert config.settings()["permissions"]["send"] == "allow"


def test_upload_sanitised_and_size_limited(client):
    r = client.post("/api/upload", files={"file": ("../../evil dir/re:port?.txt", b"hello\r\n--x\x00\xff world")})
    saved = r.json()
    path = config.path("uploads", "x").parent
    assert r.status_code == 200 and saved["size"] == 18
    assert saved["name"] == "re_port_.txt" and saved["path"].startswith(str(path))
    assert open(saved["path"], "rb").read() == b"hello\r\n--x\x00\xff world"
    assert client.post("/api/upload", content=b"raw").status_code == 415
    config.set_key("server.max_upload_mb", 0.001)
    assert client.post("/api/upload", files={"file": ("big.bin", b"x" * 20000)}).status_code == 413
    assert len(list(path.iterdir())) == 1


def test_safe_filename():
    f = server.safe_filename
    assert f("C:\\Users\\me\\..\\secret.txt") == "secret.txt" and f("../../etc/passwd") == "passwd"
    assert f("") == "upload" and f("...") == "upload" and f("con.txt") == "_con.txt" and f("a\x00b\n.py") == "a_b_.py"
    assert f("file.txt:stream") == "file.txt_stream" and len(f("x" * 500 + ".pdf")) == 100 and f(".env") == "env"


def test_dashboard_tolerates_missing_and_unknown_tables(client, monkeypatch):
    assert server.rows("zz_missing") == [] and server.rows("bad name; DROP TABLE audit") == []
    db.x("CREATE TABLE zz_things (id INTEGER PRIMARY KEY, title TEXT, done INTEGER, due TEXT, blob BLOB)")
    day = db.now()[:10]
    db.many("INSERT INTO zz_things (title, done, due, blob) VALUES (?,?,?,?)",
            [("old", 1, "2001-01-01", b"\x00\x01"), ("new", 0, f"{day}T09:00:00", None)])
    assert [r["title"] for r in server.rows("zz_things")] == ["new", "old"]
    assert server.rows("zz_things")[1]["blob"] == "<2 bytes>"
    monkeypatch.setitem(server.TABLES, "tasks", ("zz_missing", "zz_things"))
    monkeypatch.setitem(server.TABLES, "events", ("zz_things",))
    monkeypatch.setitem(server.TABLES, "reminders", ("zz_missing",))
    assert len(client.get("/api/dash/tasks").json()["rows"]) == 2
    assert [r["title"] for r in client.get("/api/dash/tasks?open_only=true").json()["rows"]] == ["new"]
    assert client.get("/api/dash/reminders").json()["rows"] == [] and client.get("/api/dash/nope").status_code == 404
    t = client.get("/api/today").json()
    assert [r["title"] for r in t["events"]] == ["new"] and [r["title"] for r in t["tasks"]] == ["new"]
    assert t["reminders"] == []


def test_notifications_and_undo(client):
    jobs.notify("Stretch", "You have been sitting for 2 hours", kind="health", why="No break since 10:00")
    n = client.get("/api/notifications").json()
    assert n[0]["why"] == "No break since 10:00" and client.get("/api/state").json()["unread"] == 1
    assert client.post("/api/notifications/read", json={"ids": [n[0]["id"]]}).status_code == 200
    assert client.get("/api/notifications").json() == [] and len(client.get("/api/notifications?all=true").json()) == 1
    assert client.get("/api/undo").json() == []
    assert client.post("/api/undo", json={}).json() == {"result": "Nothing to undo."}


def test_memory_endpoints_go_through_tools(client, monkeypatch):
    calls = []
    fake_tool(monkeypatch, "memory_list", lambda ctx, **a: [{"id": 7, "text": "likes tea"}])
    fake_tool(monkeypatch, "memory_update", lambda ctx, id, text: calls.append(("update", id, text)) or {"id": id}, "write")
    fake_tool(monkeypatch, "memory_forget", lambda ctx, id: calls.append(("forget", id)) or {"forgotten": id}, "delete")
    m = client.get("/api/memory").json()
    assert m["items"] == [{"id": 7, "text": "likes tea"}] and m["editable"] and m["deletable"]
    assert client.patch("/api/memory/7", json={"text": "likes coffee"}).status_code == 200
    assert client.delete("/api/memory/7").status_code == 200           # the click is the approval for a 'delete' tool
    assert calls == [("update", 7, "likes coffee"), ("forget", 7)]
    assert [a["tool"] for a in security.audit_log()][:2] == ["memory_forget", "memory_update"]
    config.set_key("tool_permissions.memory_forget", "deny")
    assert client.delete("/api/memory/7").status_code == 400 and len(calls) == 2
    monkeypatch.delitem(tools.REGISTRY, "memory_forget")
    assert client.delete("/api/memory/7").status_code == 501


# ---- HUD endpoints

def test_vitals_protocols_greeting_present(client, monkeypatch):
    fake_tool(monkeypatch, "sparx_vitals", lambda ctx: {"cpu_percent": 12.5, "battery": None})
    fake_tool(monkeypatch, "protocol_list", lambda ctx: [{"name": "house party", "description": "Lights and music"},
                                                         {"description": "nameless"}, "junk"])
    monkeypatch.setattr(tools, "sparx", types.SimpleNamespace(greeting=lambda: "Good evening, sir."), raising=False)
    assert client.get("/api/vitals").json() == {"available": True, "cpu_percent": 12.5, "battery": None}
    assert client.get("/api/protocols").json() == {
        "available": True, "protocols": [{"name": "house party", "description": "Lights and music"}]}
    assert client.get("/api/greeting").json() == {"greeting": "Good evening, sir."}


def test_vitals_protocols_greeting_absent(client, monkeypatch):
    def boom():
        raise RuntimeError("no greeting today")
    monkeypatch.delitem(tools.REGISTRY, "sparx_vitals", raising=False)
    monkeypatch.delitem(tools.REGISTRY, "protocol_list", raising=False)
    monkeypatch.setattr(tools, "sparx", types.SimpleNamespace(greeting=boom), raising=False)
    assert client.get("/api/vitals").json() == {"available": False}
    assert client.get("/api/protocols").json() == {"available": False, "protocols": []}
    assert client.get("/api/greeting").json() == {"greeting": "Online."}
    fake_tool(monkeypatch, "sparx_vitals", lambda ctx: 1 / 0)
    assert client.get("/api/vitals").json()["available"] is False


# ---- conversation export and delete

def _talk(cid, *turns):
    db.many("INSERT INTO messages (conversation, role, content, ts, scope) VALUES (?,?,?,?,?)",
            [(cid, role, text, f"2026-03-0{n + 1}T09:0{n}:00", "personal")
             for n, (role, text) in enumerate(p for q, a in turns for p in (("user", q), ("assistant", a)))])


def test_conversation_export_markdown_and_json(client, token):
    _talk("c-one", ("plan my day\nplease", "Here is **the plan**."), ("thanks", "Any time."))
    _talk("c-two", ("other chat", "Other answer."))
    r = client.get("/api/conversations/c-one/export?format=md")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/markdown")
    assert r.headers["content-disposition"] == 'attachment; filename="sparx-conversation-c-one.md"'
    md = r.text
    assert md.startswith("# plan my day please\n") and "Date: 2026-03-01" in md
    assert "## You · 2026-03-01 09:00:00\n\nplan my day\nplease\n" in md
    assert "## Sparx · 2026-03-02 09:01:00\n\nHere is **the plan**.\n" in md
    assert md.index("thanks") < md.index("Any time.") and "Other answer" not in md
    assert client.get("/api/conversations/c-one/export").text == md                    # Markdown is the default
    r = client.get("/api/conversations/c-one/export?format=json")
    stored = db.q("SELECT * FROM messages WHERE conversation = 'c-one' ORDER BY id")
    assert r.headers["content-type"] == "application/json" and r.json() == stored and len(stored) == 4
    assert r.headers["content-disposition"] == 'attachment; filename="sparx-conversation-c-one.json"'
    bare = TestClient(client.app, headers={"Authorization": f"Bearer {token}"})
    assert bare.get("/api/conversations/c-one/export?format=json").json() == stored
    assert client.get("/api/conversations/c-one/export?format=pdf").status_code == 400
    assert client.get("/api/conversations/nope/export").status_code == 404
    db.x("INSERT INTO messages (conversation, role, content, ts) VALUES (?,?,?,?)", ('a/b"\r\nX: y', "user", "hi", db.now()))
    odd = client.get("/api/conversations/a%2Fb%22%0D%0AX%3A%20y/export")
    assert odd.headers.get("content-disposition", "") in ("", 'attachment; filename="sparx-conversation-a_b___X__y.md"')
    assert "x" not in odd.headers                                                      # no header smuggled in via the id


def test_conversation_delete_only_that_one_and_undo(client):
    _talk("c-one", ("first", "one"), ("second", "two"))
    _talk("c-two", ("keep me", "kept"))
    before = db.q("SELECT * FROM messages ORDER BY id")
    r = client.delete("/api/conversations/c-one")
    assert r.status_code == 200 and r.json()["deleted"] == 4 and r.json()["conversation"] == "c-one"
    assert [m["conversation"] for m in db.q("SELECT conversation FROM messages")] == ["c-two", "c-two"]
    assert [c["id"] for c in client.get("/api/conversations").json()["conversations"]] == ["c-two"]
    assert client.delete("/api/conversations/c-one").status_code == 404
    assert client.delete("/api/conversations/nope").status_code == 404
    log = client.get("/api/undo").json()
    assert len(log) == 1 and log[0]["kind"] == "conversation_restore" and "c-one" in log[0]["description"]
    assert client.post("/api/undo", json={"id": r.json()["undo_id"]}).json()["result"].startswith("Undone: Deleted conversation")
    assert db.q("SELECT * FROM messages ORDER BY id") == before
    assert client.post("/api/undo", json={"id": log[0]["id"]}).json()["result"].startswith("Already undone")
    assert len(db.q("SELECT id FROM messages")) == 6


def test_conversation_undo_when_ids_were_reused(client):
    _talk("c-one", ("first", "one"))
    assert client.delete("/api/conversations/c-one").json()["deleted"] == 2
    _talk("c-two", ("newer", "chat"))                       # SQLite hands the freed ids to these rows
    assert client.post("/api/undo", json={}).json()["result"].startswith("Undone")
    assert [(m["conversation"], m["content"]) for m in db.q("SELECT * FROM messages ORDER BY id")] == [
        ("c-two", "newer"), ("c-two", "chat"), ("c-one", "first"), ("c-one", "one")]


def test_conversation_export_and_delete_need_auth(anon, token):
    _talk("c-one", ("secret", "answer"))
    assert anon.get("/api/conversations/c-one/export").status_code == 401
    assert anon.get("/api/conversations/c-one/export", headers={"Authorization": "Bearer wrong"}).status_code == 401
    assert anon.delete("/api/conversations/c-one").status_code == 401
    assert anon.post("/api/login", json={"token": token}).status_code == 200
    assert anon.delete("/api/conversations/c-one", headers={"Origin": "http://evil.example"}).status_code == 403
    assert len(db.q("SELECT id FROM messages")) == 2 and db.q("SELECT id FROM undo_log") == []


def test_conversation_delete_refused_while_a_turn_runs(client, fake_llm):
    fake_llm.script = [("t_srv_wait", {})]
    with client.websocket_connect("/ws") as ws:
        hello = ws.receive_json()
        _talk(hello["conversation"], ("earlier", "reply"))
        ws.send_json({"type": "user", "text": "wait"})
        until(ws, "tool_start")
        r = client.delete(f"/api/conversations/{hello['conversation']}")
        assert r.status_code == 409 and "still answering" in r.json()["detail"]
        ws.send_json({"type": "cancel"})
        until(ws, "cancelled")
        assert client.delete(f"/api/conversations/{hello['conversation']}").json()["deleted"] >= 2
    assert db.q("SELECT id FROM messages") == []


def test_deleting_the_current_conversation_starts_a_fresh_one(client, fake_llm):
    fake_llm.script = ["first answer", "second answer"]
    with client.websocket_connect("/ws") as ws:
        old = ws.receive_json()["conversation"]
        ws.send_json({"type": "user", "text": "hello"})
        until(ws, "assistant")
        _talk("c-other", ("side chat", "side answer"))
        assert client.delete("/api/conversations/c-other").json()["current"] == old     # not current: nothing moves
        gone = client.delete(f"/api/conversations/{old}").json()
        new = gone["current"]
        assert new != old and client.get("/api/conversations").json()["current"] == new
        assert client.get(f"/api/conversations/{new}/messages").json() == []
        ws.send_json({"type": "user", "text": "again"})
        reply, _ = until(ws, "assistant")
        assert reply["conversation"] == new
    stored = lambda: [(m["conversation"], m["content"]) for m in db.q("SELECT * FROM messages ORDER BY id")]
    assert stored() == [(new, "again"), (new, "second answer")]
    assert client.post("/api/undo", json={"id": gone["undo_id"]}).json()["result"].startswith("Undone")
    assert sorted(stored()) == sorted([(old, "hello"), (old, "first answer"), (new, "again"), (new, "second answer")])
    assert client.get("/api/conversations").json()["current"] == new                    # the restored one is not made current


# ---- pending actions

def _queued(to="a@b.c"):
    return pending.queue(tools.REGISTRY["t_srv_send"], {"to": to}, "daemon")


def test_pending_actions_list_approve_and_dismiss(client):
    first, second = _queued(), _queued("c@d.e")
    listed = client.get("/api/pending").json()
    assert [p["id"] for p in listed["pending"]] == [second, first] and listed["recent"] == []
    assert listed["pending"][1]["risk"] == "send" and listed["pending"][1]["description"] == "send something"
    assert listed["pending"][1]["args"] == {"to": "a@b.c"} and listed["pending"][1]["agent"] == "daemon"
    assert client.get("/api/state").json()["pending"] == 2

    r = client.post(f"/api/pending/{first}/approve", headers=ORIGIN)
    assert r.status_code == 200 and r.json()["ok"] and "sent to a@b.c" in r.json()["result"]
    assert security.audit_log(tool="t_srv_send")[0]["ok"] == 1
    r = client.post(f"/api/pending/{second}/dismiss", headers=ORIGIN)
    assert r.status_code == 200 and "dismissed" in r.json()["result"]
    listed = client.get("/api/pending").json()
    assert listed["pending"] == [] and [(p["id"], p["status"]) for p in listed["recent"]] == [(second, "dismissed"), (first, "done")]
    assert client.get("/api/state").json()["pending"] == 0
    assert len(security.audit_log(tool="t_srv_send")) == 1                      # the dismissed one never ran


def test_pending_actions_refusals(client):
    assert client.post("/api/pending/999/approve", headers=ORIGIN).status_code == 400
    assert client.post("/api/pending/999/dismiss", headers=ORIGIN).status_code == 400

    stale = _queued()
    db.x("UPDATE pending_actions SET expires = '2020-01-01T00:00:00' WHERE id = ?", (stale,))
    r = client.post(f"/api/pending/{stale}/approve", headers=ORIGIN)
    assert r.status_code == 400 and "expired" in r.json()["detail"]

    held = _queued("x@y.z")
    config.set_key("tool_permissions.t_srv_send", "deny")
    r = client.post(f"/api/pending/{held}/approve", headers=ORIGIN)
    assert r.status_code == 400 and "disabled by the user's permission settings" in r.json()["detail"]
    assert [p["id"] for p in client.get("/api/pending").json()["pending"]] == [held]      # still waiting
    assert security.audit_log(tool="t_srv_send")[0]["ok"] == 0


def test_pending_actions_need_auth(anon):
    held = _queued()
    assert anon.get("/api/pending").status_code == 401
    assert anon.post(f"/api/pending/{held}/approve").status_code == 401
    assert anon.post(f"/api/pending/{held}/dismiss").status_code == 401
    assert pending.get(held)["status"] == "pending"


# ---- automations

def _recipe(name="mailer", *to):
    """A recipe that sends to each address, and one automatic run of it, which waits at the first send."""
    automation.create(name, "daily 08:00", [{"tool": "t_srv_send", "args": {"to": t}} for t in to or ("a@b.c",)])
    ctx = tools.Context(agent="automation", approve=None)
    ctx.data["automated"] = True
    run = asyncio.run(automation.start(automation.get(name), ctx, trigger="schedule daily 08:00"))
    assert run["status"] == "waiting_approval" and security.audit_log(tool="t_srv_send") == []
    return run["run_id"]


def _sends():
    return [a["ok"] for a in security.audit_log(tool="t_srv_send")]


def test_automations_list_state_and_resume(client):
    assert client.get("/api/automations").json() == {"automations": [], "runs": []}
    assert client.get("/api/state").json()["waiting_runs"] == 0
    run = _recipe("mailer", "a@b.c", "c@d.e")
    d = client.get("/api/automations").json()
    (a,), (r,) = d["automations"], d["runs"]
    assert (a["name"], a["enabled"], len(a["steps"]), a["trigger"]["spec"]) == ("mailer", True, 2, "daily 08:00")
    assert "next_run" in a
    assert set(r) == {"id", "automation", "status", "trigger", "started", "finished", "pending", "then"}
    assert (r["id"], r["automation"], r["status"], r["trigger"]) == (run, "mailer", "waiting_approval", "schedule daily 08:00")
    assert r["pending"].startswith("step 1: t_srv_send [send]") and "a@b.c" in r["pending"] and r["finished"] is None
    assert len(r["then"]) == 1 and r["then"][0].startswith("step 2: t_srv_send [send]") and "c@d.e" in r["then"][0]
    assert client.get("/api/state").json()["waiting_runs"] == 1

    done = client.post(f"/api/automations/runs/{run}/resume", headers=ORIGIN)
    assert done.status_code == 200 and done.json()["ok"] and done.json()["status"] == "done"
    assert _sends() == [1, 1] and automation.get_run(run)["status"] == "done"
    (r,) = client.get("/api/automations").json()["runs"]
    assert r["status"] == "done" and r["finished"] and "pending" not in r and "log" not in r
    assert client.get("/api/state").json()["waiting_runs"] == 0
    assert security.audit_log(tool="automation_resume")[0]["ok"] == 1                 # the click is on record
    assert client.post(f"/api/automations/runs/{run}/resume", headers=ORIGIN).status_code == 400     # nothing left to resume
    assert _sends() == [1, 1]


def test_automations_cancel_and_enable_disable(client):
    run = _recipe()
    r = client.post(f"/api/automations/runs/{run}/cancel", headers=ORIGIN)
    assert r.status_code == 200 and automation.get_run(run)["status"] == "cancelled" and _sends() == []
    assert client.get("/api/state").json()["waiting_runs"] == 0
    assert client.post(f"/api/automations/runs/{run}/cancel", headers=ORIGIN).status_code == 400

    def switch(ref, body):
        return client.post(f"/api/automations/{ref}/enabled", json=body)
    assert switch("mailer", {"enabled": False}).status_code == 200
    assert client.get("/api/automations").json()["automations"][0]["enabled"] is False
    assert switch(automation.get("mailer")["id"], {"enabled": True}).json()["result"]["enabled"] is True      # by id too
    assert client.get("/api/automations").json()["automations"][0]["enabled"] is True
    assert [a["tool"] for a in security.audit_log()][:3] == ["automation_enable", "automation_disable", "automation_cancel"]
    for bad in ({}, {"enabled": "yes"}, {"enabled": 1}):
        assert switch("mailer", bad).status_code == 400, bad
    assert automation.get("mailer")["enabled"] == 1


def test_automations_refusals(client):
    for path in ("runs/999/resume", "runs/999/cancel"):
        r = client.post(f"/api/automations/{path}", headers=ORIGIN)
        assert r.status_code == 400 and "no automation run 999" in r.json()["detail"], path
    r = client.post("/api/automations/nope/enabled", json={"enabled": True})
    assert r.status_code == 400 and "no automation 'nope'" in r.json()["detail"]

    run = _recipe()
    config.set_key("tool_permissions.t_srv_send", "deny")
    r = client.post(f"/api/automations/runs/{run}/resume", headers=ORIGIN)
    assert r.status_code == 400 and "disabled by the user's permission settings" in r.json()["detail"]
    assert _sends() == [] and automation.get_run(run)["status"] == "waiting_approval"      # nothing ran; still waiting
    config.set_key("tool_permissions.t_srv_send", "")
    assert client.post(f"/api/automations/runs/{run}/resume", headers=ORIGIN).status_code == 200 and _sends() == [1]


def test_automations_a_run_that_fails_after_the_click_is_an_error(client):
    run = _recipe("mailer", "a@b.c", "c@d.e")
    steps = automation.get_run(run)["steps"]
    steps[1]["tool"] = "t_srv_gone"                 # the second step's tool has been uninstalled since the run began
    db.x("UPDATE automation_runs SET steps = ? WHERE id = ?", (json.dumps(steps), run))
    r = client.post(f"/api/automations/runs/{run}/resume", headers=ORIGIN)
    assert r.status_code == 400 and "failed at step 2" in r.json()["detail"] and "t_srv_gone" in r.json()["detail"]
    assert _sends() == [1] and automation.get_run(run)["status"] == "failed"


def test_automations_need_auth(anon):
    run = _recipe()
    assert anon.get("/api/automations").status_code == 401
    assert anon.post(f"/api/automations/runs/{run}/resume").status_code == 401
    assert anon.post(f"/api/automations/runs/{run}/cancel").status_code == 401
    assert anon.post("/api/automations/mailer/enabled", json={"enabled": False}).status_code == 401
    assert automation.get_run(run)["status"] == "waiting_approval" and automation.get("mailer")["enabled"] == 1
    assert _sends() == []


# ---- chat

def test_chat_roundtrip_and_conversations(client, fake_llm):
    fake_llm.script = [("calculate", {"expression": "6*7"}), "It is **42**."]
    with client.websocket_connect("/ws") as ws:
        hello = ws.receive_json()
        assert hello["type"] == "hello" and hello["stop"] is False
        ws.send_json({"type": "user", "text": "what is 6*7?"})
        reply, seen = until(ws, "assistant")
        kinds = [e["type"] for e in seen]
        assert kinds == ["turn_start", "tool_start", "tool_end", "assistant"]
        assert reply["text"] == "It is **42**." and seen[1]["tool"] == "calculate"
        jobs.notify("Ping", "body", why="because")
        note, _ = until(ws, "notification")
        assert note["notification"]["why"] == "because"
    convs = client.get("/api/conversations").json()
    assert convs["current"] == reply["conversation"] and convs["conversations"][0]["title"] == "what is 6*7?"
    msgs = client.get(f"/api/conversations/{reply['conversation']}/messages").json()
    assert [m["role"] for m in msgs] == ["user", "assistant"]
    new = client.post("/api/conversations").json()["current"]
    assert client.get("/api/state").json()["conversation"] == new
    assert client.post(f"/api/conversations/{reply['conversation']}/select").status_code == 200
    assert client.post("/api/conversations/nope/select").status_code == 404
    assert client.post("/api/scope", json={"scope": "work"}).json() == {"scope": "work"}
    assert client.post("/api/scope", json={"scope": "../x"}).status_code == 400
    assert not server.CONNS and not jobs.LISTENERS


def test_chat_approval_allowed(client, fake_llm):
    fake_llm.script = [("t_srv_send", {"to": "a@b.c", "password": "hunter2"}), "Sent."]
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "user", "text": "send it"})
        req, _ = until(ws, "approval_request")
        assert (req["tool"], req["risk"]) == ("t_srv_send", "send")
        assert req["args"] == {"to": "a@b.c", "password": "***"}
        ws.send_json({"type": "approval", "id": req["id"], "allow": True})
        reply, seen = until(ws, "assistant")
    assert reply["text"] == "Sent." and "tool_start" in [e["type"] for e in seen]
    assert fake_llm.seen[1][-1]["content"].startswith("sent to a@b.c")     # a first call into an unloaded group adds a "loaded now" note


def test_chat_approval_denied_and_timeout(client, fake_llm, monkeypatch):
    fake_llm.script = [("t_srv_send", {"to": "a@b.c"}), "Not sent.", ("t_srv_send", {"to": "a@b.c"}), "Still not sent."]
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "user", "text": "send it"})
        req, _ = until(ws, "approval_request")
        ws.send_json({"type": "approval", "id": "wrong-id", "allow": True})      # only the matching id counts
        ws.send_json({"type": "approval", "id": req["id"], "allow": False})
        reply, seen = until(ws, "assistant")
        assert reply["text"] == "Not sent." and "tool_start" not in [e["type"] for e in seen]
        assert "declined" in fake_llm.seen[1][-1]["content"]

        monkeypatch.setattr(server, "APPROVAL_TIMEOUT", 0.2)
        ws.send_json({"type": "user", "text": "try again"})
        resolved, _ = until(ws, "approval_resolved")
        assert resolved == {"type": "approval_resolved", "id": resolved["id"], "allow": False, "reason": "timed out"}
        until(ws, "assistant")
    assert [a["summary"] for a in security.audit_log(tool="t_srv_send")] == ["not approved", "not approved"]


def test_chat_one_turn_at_a_time_cancel_and_stop(client, fake_llm):
    fake_llm.script = [("t_srv_wait", {}), ("t_srv_wait", {})]      # a cancelled turn never asks the model again
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "user", "text": "wait"})
        until(ws, "tool_start")
        ws.send_json({"type": "user", "text": "second"})
        err, _ = until(ws, "error")
        assert "previous message" in err["text"]
        ws.send_json({"type": "cancel"})
        until(ws, "cancelled")
        assert not security.stop_requested()

        ws.send_json({"type": "user", "text": "wait again"})
        until(ws, "tool_start")
        ws.send_json({"type": "stop"})
        _, seen = until(ws, "cancelled")
        assert "stopped" in [e["type"] for e in seen] and security.stop_requested()
        fake_llm.script = ["unused"]
        ws.send_json({"type": "user", "text": "hello?"})
        reply, _ = until(ws, "assistant")
        assert reply["text"].startswith("Stopped")
    assert client.get("/api/conversations").json()["conversations"][0]["messages"] == 6      # cancelled turns stay in history


def test_chat_reports_model_errors(client, monkeypatch):
    from sparx import llm

    def broken(role="default"):
        raise SystemExit("No API key for groq")
    monkeypatch.setattr(llm, "get", broken)
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "user", "text": "hi"})
        err, _ = until(ws, "error")
    assert "No API key" in err["text"]


async def test_job_loop_ticks_daemon_and_tolerates_absence(monkeypatch):
    ticks = []

    async def tick():
        ticks.append(1)
        if len(ticks) == 1:
            raise RuntimeError("one bad tick must not end the loop")
    monkeypatch.setitem(sys.modules, "sparx.daemon", types.SimpleNamespace(tick=tick))
    import sparx
    monkeypatch.setattr(sparx, "daemon", sys.modules["sparx.daemon"], raising=False)
    task = asyncio.create_task(server.job_loop(0.01))
    await asyncio.sleep(0.2)
    task.cancel()
    assert len(ticks) >= 2
    monkeypatch.setattr(sparx, "daemon", types.SimpleNamespace(), raising=False)
    await asyncio.wait_for(server.job_loop(0.01), 1)        # no tick(): returns at once


def test_deleting_a_conversation_removes_its_search_index_and_summary_and_undo_restores_them(client):
    from sparx import compact  # noqa: F401
    from sparx.tools import memory
    _talk("c-gone", ("the zanzibarium plan", "noted"))
    memory.conversation_search(tools.Context(session="t"), "zanzibarium")        # fills the index
    db.x("INSERT INTO conv_summary (conversation, summary, upto_id, ts) VALUES (?,?,?,?)", ("c-gone", "about zanzibarium", 1, db.now()))
    count = lambda: db.one("SELECT COUNT(*) AS n FROM messages_fts WHERE messages_fts MATCH '\"zanzibarium\"'")["n"]
    assert count() == 1
    uid = client.delete("/api/conversations/c-gone").json()["undo_id"]
    assert count() == 0 and db.one("SELECT 1 AS x FROM conv_summary WHERE conversation = 'c-gone'") is None
    assert client.post("/api/undo", json={"id": uid}).json()["result"].startswith("Undone")
    assert count() == 1 and db.one("SELECT summary FROM conv_summary WHERE conversation = 'c-gone'")["summary"] == "about zanzibarium"


def test_an_undo_entry_from_before_summaries_still_restores(client):
    from sparx import undo
    _talk("c-old", ("hello", "hi"))
    rows = db.q("SELECT * FROM messages WHERE conversation = 'c-old'")
    db.x("DELETE FROM messages WHERE conversation = 'c-old'")
    uid = undo.record(tools.Context(session="c-old"), "conversation_restore", "Deleted conversation c-old", {"conversation": "c-old", "rows": rows})
    assert client.post("/api/undo", json={"id": uid}).json()["result"].startswith("Undone")
    assert len(db.q("SELECT id FROM messages WHERE conversation = 'c-old'")) == 2


@pytest.mark.parametrize("param", ["token", "code"])
def test_login_link_refuses_the_access_token(anon, token, param):
    r = anon.get(f"/login?{param}={token}", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/#login-failed" and "set-cookie" not in r.headers
    assert anon.get("/api/state").status_code == 401


def test_login_link_token_attempts_are_throttled_and_the_api_still_takes_the_token(anon, token):
    for _ in range(5):
        anon.get(f"/login?token={token}", follow_redirects=False)
    assert anon.get(f"/login?token={token}", follow_redirects=False).status_code == 429
    auth._fails.clear()
    assert anon.post("/api/login", json={"token": token}).status_code == 200
