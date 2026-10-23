"""Who may use the web UI: one access token, browser sessions, one-time login codes and an optional PIN.

Only hashes are stored (HOME/auth.json). The access token is shown once, when it is created.
A file that is there but cannot be read fails closed: nobody gets in and nothing overwrites it but rotate_token().

    token = auth.ensure_token()      # plaintext on first run, None afterwards
    auth.check(token_or_session)     # True if it may use the API
    auth.set_pin("4821")             # optional second lock; "" removes it
    python -m sparx.auth set-pin | clear-pin | code | rotate-token
"""
import hashlib
import hmac
import json
import os
import secrets
import sys
import threading
import time

from . import config

PIN_ITERATIONS = 200_000
SESSION_SECONDS = 30 * 86400
CODE_SECONDS = 600
MAX_FAILS, FAIL_WINDOW = 5, 300      # failed sign-ins, and separately wrong PINs, per client before a lockout window
PIN_MAX_ALL, PIN_WINDOW_ALL = 20, 3600      # wrong PINs from all clients together: behind a proxy they share an address
PIN_ALL = "pin*"
RECOVER = "python -m sparx.auth rotate-token"

_lock = threading.RLock()
_fails: dict[str, list[float]] = {}  # "login:<client>", "pin:<client>" and PIN_ALL -> times of recent failures


class Damaged(Exception):
    """auth.json exists but cannot be read. It is left as it is; only rotate_token() replaces it."""

    def __init__(self):
        super().__init__(f"{config.path('auth.json')} is damaged, so nobody can sign in. To recover run: {RECOVER}\n"
                         "That makes a new access token, signs every browser out and removes the PIN (set it again).")


def _h(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", "replace")).hexdigest()


def _load() -> dict:
    """The stored state; empty on a first run (no file). Raises Damaged for a file that is there but unusable."""
    try:
        d = json.loads(config.path("auth.json").read_text(encoding="utf-8"))
    except FileNotFoundError:
        d = {}
    except (OSError, ValueError):
        raise Damaged() from None
    if not isinstance(d, dict) or not all(isinstance(d.setdefault(k, {}), dict) for k in ("sessions", "codes")):
        raise Damaged()
    return d


def _load_or_none() -> dict | None:
    try:
        return _load()
    except Damaged:
        return None


def damaged() -> bool:
    return _load_or_none() is None


def _save(d: dict):
    """Write to a temporary file and swap it in, so a crash or a reader mid-write never sees half a file."""
    now = time.time()
    for k in ("sessions", "codes"):
        d[k] = {h: v for h, v in d[k].items() if (v["exp"] if isinstance(v, dict) else v) > now}
    tmp = config.path("secrets", f"auth.json.{secrets.token_hex(6)}.tmp")       # secrets/: closed to every file tool
    try:
        with tmp.open("w", encoding="utf-8") as f:
            f.write(json.dumps(d, indent=1))
            f.flush()
            os.fsync(f.fileno())
        for attempt in range(10):
            try:
                os.replace(tmp, config.path("auth.json"))
                break
            except PermissionError:         # Windows: another thread or process has the file open for a moment
                if attempt == 9:
                    raise
                time.sleep(0.02)
    finally:
        tmp.unlink(missing_ok=True)


def _find(table: dict, value: str):
    """Constant-time lookup of sha256(value) among the keys of table (no early exit)."""
    want, hit = _h(value), None
    for h in table:
        if hmac.compare_digest(h, want):
            hit = h
    return hit


# ---- access token and sessions

def ensure_token() -> str | None:
    """Create the access token on first run and return it; None when one already exists (it cannot be recovered)."""
    with _lock:
        d = _load_or_none()
        if d is None or d.get("token"):
            return None
        return _new_token(d)


def rotate_token() -> str:
    """Replace the access token, sign every browser out and cancel unused login codes.

    The one call that replaces a damaged auth.json; the PIN in it cannot be read, so it is gone and must be set again."""
    with _lock:
        d = _load_or_none() or {}
        d["sessions"], d["codes"] = {}, {}
        return _new_token(d)


def _new_token(d: dict) -> str:
    token = secrets.token_urlsafe(32)
    d["token"] = _h(token)
    _save(d)
    return token


def _session(d: dict, value: str) -> dict | None:
    h = _find(d["sessions"], value) if value else None
    s = d["sessions"].get(h) if h else None
    return s if s and s["exp"] > time.time() else None


def _is_token(d: dict, value: str) -> bool:
    return bool(value and d.get("token")) and hmac.compare_digest(d["token"], _h(value))


def check(value: str) -> bool:
    """True if value is the access token or a live session."""
    d = _load_or_none()
    return d is not None and _is_token(d, value or "") | (_session(d, value or "") is not None)


def login_code() -> str:
    """A single-use code for a login link, valid for CODE_SECONDS."""
    with _lock:
        d = _load()
        code = secrets.token_urlsafe(18)
        d["codes"][_h(code)] = time.time() + CODE_SECONDS
        _save(d)
        return code


def login(value: str, client: str = "", *, codes_only: bool = False) -> str | None:
    """Exchange the access token or a one-time code for a new session. None (and a strike) if it is wrong.

    `codes_only` refuses the access token (it counts as a wrong value), for the GET link where a URL is logged."""
    with _lock:
        if throttled(client):
            return None
        d = _load_or_none()
        if d is None:
            return None
        code = _find(d["codes"], value) if value else None
        ok = (not codes_only and _is_token(d, value or "")) or bool(code and d["codes"][code] > time.time())
        if not ok:
            fail(client)
            return None
        if code:
            del d["codes"][code]
        session = secrets.token_urlsafe(32)
        d["sessions"][_h(session)] = {"exp": time.time() + SESSION_SECONDS, "unlocked": False}
        _save(d)
        _fails.pop(f"login:{client}", None)     # never the PIN strikes: the token holder is who the PIN keeps out
        return session


def logout(session: str):
    with _lock:
        d = _load_or_none()
        h = _find(d["sessions"], session or "") if d else None
        if h:
            del d["sessions"][h]
            _save(d)


# ---- failed-attempt throttling (in memory): sign-in per client; PIN per client and across all clients

def _count(key: str) -> int:
    """Failures still inside their window for key. Every entry whose window has passed is dropped on the way."""
    now = time.time()
    with _lock:
        for k in list(_fails):
            recent = [t for t in _fails[k] if t > now - (PIN_WINDOW_ALL if k == PIN_ALL else FAIL_WINDOW)]
            if recent:
                _fails[k] = recent
            else:
                del _fails[k]
        return len(_fails.get(key, ()))


def fail(client: str, kind: str = "login"):
    with _lock:
        _count("")
        _fails.setdefault(f"{kind}:{client}", []).append(time.time())
        if kind == "pin":
            _fails.setdefault(PIN_ALL, []).append(time.time())


def throttled(client: str) -> bool:
    """Too many failed sign-ins from this client."""
    return _count(f"login:{client}") >= MAX_FAILS


def pin_blocked(client: str) -> str:
    """Why this client may not try a PIN right now ("" when it may)."""
    with _lock:
        if _count(PIN_ALL) >= PIN_MAX_ALL:
            minutes = int((_fails[PIN_ALL][-PIN_MAX_ALL] + PIN_WINDOW_ALL - time.time()) // 60) + 1
            return (f"Too many wrong PINs ({PIN_MAX_ALL} within an hour, counting every device). "
                    f"PIN entry is locked for everyone for about {minutes} more minute(s).")
        if _count(f"pin:{client}") >= MAX_FAILS:
            return "Too many wrong PINs. Wait a few minutes."
        return ""


# ---- PIN

def _pin_hash(pin: str, salt: bytes, iterations: int) -> str:
    return hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), salt, iterations).hex()


def set_pin(pin: str):
    """Set the PIN (4+ characters), or remove it with "". Every session is locked again."""
    if pin and len(pin) < 4:
        raise ValueError("PIN must be at least 4 characters")
    with _lock:
        d = _load()         # Damaged: refused, and the message says how to recover
        if pin:
            salt = secrets.token_bytes(16)
            d["pin"] = {"salt": salt.hex(), "hash": _pin_hash(pin, salt, PIN_ITERATIONS), "iterations": PIN_ITERATIONS}
        else:
            d.pop("pin", None)
        for s in d["sessions"].values():
            s["unlocked"] = False
        _save(d)


def has_pin() -> bool:
    d = _load_or_none()
    return d is None or bool(d.get("pin"))      # unreadable: assume the lock is there


def pin_stamp() -> str:
    """Changes whenever the PIN is set, changed or removed (not secret: the salt)."""
    p = (_load_or_none() or {}).get("pin")
    return p["salt"] if p else ""


def check_pin(pin: str) -> bool:
    """Compare only. Anything that takes a PIN from outside goes through try_pin, which counts the failures."""
    p = (_load_or_none() or {}).get("pin")
    if not p or not pin:
        return False
    return hmac.compare_digest(p["hash"], _pin_hash(pin, bytes.fromhex(p["salt"]), p["iterations"]))


def try_pin(pin: str, client: str = "") -> bool:
    """One counted PIN attempt: refused while pin_blocked(client), a strike when wrong."""
    with _lock:
        if pin_blocked(client):
            return False
        if not check_pin(pin):
            fail(client, "pin")
            return False
        _fails.pop(f"pin:{client}", None)       # this client's strikes only; the all-clients count runs out by itself
        return True


def locked(value: str) -> bool:
    """True when a PIN is set and this session has not been unlocked with it (the bare token is always locked)."""
    d = _load_or_none()
    if d is None:
        return True
    if not d.get("pin"):
        return False
    s = _session(d, value or "")
    return not (s and s.get("unlocked"))


def unlock(session: str, pin: str, client: str = "") -> bool:
    with _lock:
        if not try_pin(pin, client):
            return False
        _set_unlocked(session, True)
        return True


def lock(session: str):
    with _lock:
        _set_unlocked(session, False)


def _set_unlocked(session: str, state: bool):
    d = _load_or_none()
    h = _find(d["sessions"], session or "") if d else None
    if h:
        d["sessions"][h]["unlocked"] = state
        _save(d)


def main(argv=None):
    import getpass
    cmd = (argv or sys.argv[1:] or ["help"])[0]
    if cmd == "set-pin":
        pin = getpass.getpass("New PIN (4+ characters): ")
        if pin != getpass.getpass("Again: "):
            sys.exit("The two entries differ; PIN unchanged.")
        try:
            set_pin(pin)
        except (ValueError, Damaged) as e:
            sys.exit(str(e))
        print("PIN set. Browsers must enter it to unlock Sparx." if pin else "PIN removed.")
    elif cmd in ("clear-pin", "code") and damaged():
        sys.exit(str(Damaged()))
    elif cmd == "clear-pin":
        set_pin("")
        print("PIN removed.")
    elif cmd == "code":
        print(f"/login?code={login_code()}   (append to the server address; single use, {CODE_SECONDS // 60} minutes)")
    elif cmd == "rotate-token":
        lost = damaged()
        print(f"New access token (shown once): {rotate_token()}\nEvery browser was signed out; unused login links "
              "no longer work." + ("\nThe damaged auth.json was replaced and any PIN went with it: run set-pin again."
                                   if lost else ""))
    else:
        print("usage: python -m sparx.auth set-pin | clear-pin | code | rotate-token")


if __name__ == "__main__":
    main()
