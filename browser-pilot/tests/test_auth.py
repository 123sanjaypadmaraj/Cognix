"""sparx.auth called directly: PIN guess limits, a damaged auth.json, token rotation."""
import types

import pytest

from sparx import auth, config


@pytest.fixture(autouse=True)
def fresh(monkeypatch):
    monkeypatch.setattr(auth, "PIN_ITERATIONS", 1000)       # keeps the many PIN checks here fast
    auth._fails.clear()
    yield
    auth._fails.clear()


@pytest.fixture
def clock(monkeypatch):
    """auth's own clock, movable: clock.now += seconds."""
    c = types.SimpleNamespace(now=auth.time.time())
    monkeypatch.setattr(auth, "time", types.SimpleNamespace(time=lambda: c.now, sleep=lambda s: None))
    return c


def _secured(pin="4821"):
    token = auth.ensure_token()
    auth.set_pin(pin)
    return token


# ---- PIN guesses

def test_signing_in_again_does_not_reset_pin_strikes():
    token = _secured()
    for i in range(auth.MAX_FAILS):                         # the token holder's trick: guess, sign in again, guess
        session = auth.login(token, "lan")
        assert session and not auth.unlock(session, f"000{i}", "lan")
    session = auth.login(token, "lan")                      # signing in is still allowed: separate counters
    assert session and auth.pin_blocked("lan")
    assert not auth.unlock(session, "4821", "lan") and auth.locked(session)     # even the right PIN, while locked out
    assert not auth.try_pin("4821", "lan")
    assert not auth.pin_blocked("elsewhere")
    assert auth.unlock(auth.login(token, "elsewhere"), "4821", "elsewhere")


def test_wrong_tokens_and_wrong_pins_are_counted_apart():
    token = _secured()
    for _ in range(auth.MAX_FAILS):
        assert auth.login("guess", "lan") is None
    assert auth.throttled("lan") and auth.login(token, "lan") is None
    assert not auth.pin_blocked("lan") and auth.try_pin("4821", "lan")          # sign-in strikes are not PIN strikes


def test_a_correct_pin_clears_only_that_clients_strikes():
    _secured()
    for _ in range(auth.MAX_FAILS - 1):
        assert not auth.try_pin("0000", "lan")
    assert auth.try_pin("4821", "lan")
    for _ in range(auth.MAX_FAILS - 1):
        assert not auth.try_pin("0000", "lan")
    assert not auth.pin_blocked("lan")
    assert len(auth._fails[auth.PIN_ALL]) == 2 * (auth.MAX_FAILS - 1)           # the all-clients count is never cleared


def test_pin_failures_across_all_clients_lock_pin_entry_for_the_hour(clock):
    token = _secured()
    for i in range(auth.PIN_MAX_ALL):                       # behind a tunnel or proxy the address proves nothing
        assert not auth.pin_blocked(f"client{i}")
        assert not auth.try_pin("0000", f"client{i}")
    why = auth.pin_blocked("never-seen")
    assert "hour" in why or "minute" in why
    session = auth.login(token, "never-seen")
    assert session and not auth.unlock(session, "4821", "never-seen") and not auth.try_pin("4821", "never-seen")
    clock.now += auth.FAIL_WINDOW + 1                       # the per-client window passing does not lift it
    assert auth.pin_blocked("never-seen")
    clock.now += auth.PIN_WINDOW_ALL
    assert not auth.pin_blocked("never-seen") and auth.unlock(session, "4821", "never-seen")


def test_old_strikes_are_dropped_so_the_table_cannot_grow(clock):
    _secured()
    for i in range(8):
        auth.login("guess", f"a{i}")
        auth.try_pin("0000", f"a{i}")
    assert len(auth._fails) == 17                           # 8 sign-in, 8 PIN, the all-clients list
    clock.now += auth.FAIL_WINDOW + 1
    auth.login("guess", "new")
    assert set(auth._fails) == {"login:new", auth.PIN_ALL}
    clock.now += auth.PIN_WINDOW_ALL + 1
    assert not auth.throttled("a0") and not auth.pin_blocked("a0") and not auth._fails


# ---- a damaged auth.json

@pytest.mark.parametrize("cut", ["half", "empty", "not json", "wrong shape"])
def test_damaged_auth_file_fails_closed_and_is_not_overwritten(cut):
    token = _secured()
    session = auth.login(token, "lan")
    assert auth.unlock(session, "4821", "lan") and not auth.locked(session) and not auth.damaged()
    f = config.path("auth.json")
    whole = f.read_text(encoding="utf-8")
    broken = {"half": whole[:len(whole) // 2], "empty": "", "not json": "\x00\x00\x00", "wrong shape": "[1, 2]"}[cut]
    f.write_text(broken, encoding="utf-8")

    assert auth.damaged()
    assert not auth.check(token) and not auth.check(session)
    assert auth.locked(session) and auth.locked(token) and auth.has_pin()       # never "no PIN is set"
    assert not auth.check_pin("4821") and not auth.try_pin("4821", "lan") and not auth.unlock(session, "4821", "lan")
    assert auth.login(token, "lan") is None
    assert auth.ensure_token() is None                      # no fresh token for whoever asks first
    for refused in (auth.login_code, lambda: auth.set_pin("9999"), lambda: auth.set_pin("")):
        with pytest.raises(auth.Damaged, match="rotate-token"):
            refused()
    auth.logout(session)
    auth.lock(session)
    assert f.read_text(encoding="utf-8") == broken

    fresh_token = auth.rotate_token()                       # the one way out
    assert not auth.damaged() and auth.check(fresh_token) and not auth.check(token) and not auth.check(session)


def test_missing_auth_file_is_still_a_first_run():
    assert not auth.damaged() and not auth.has_pin() and not auth.check("anything")
    token = auth.ensure_token()
    assert token and auth.check(token) and auth.ensure_token() is None


def test_a_write_that_fails_leaves_the_old_file_whole(monkeypatch):
    token = _secured()
    f = config.path("auth.json")
    before = f.read_text(encoding="utf-8")

    def crash(src, dst):
        raise OSError("disk full")
    with monkeypatch.context() as m:
        m.setattr(auth.os, "replace", crash)
        with pytest.raises(OSError):
            auth.set_pin("")
    assert f.read_text(encoding="utf-8") == before and auth.has_pin() and auth.check(token)
    assert [p.name for p in f.parent.iterdir() if "auth" in p.name] == ["auth.json"]    # no half-written copy beside it
    assert not [p for p in config.path("secrets", "x").parent.iterdir()]


def test_the_file_is_replaced_in_one_step(monkeypatch):
    auth.ensure_token()
    seen = []
    real = auth.os.replace

    def replace(src, dst):
        seen.append((str(src), str(dst), config.path("auth.json").read_text(encoding="utf-8")))
        return real(src, dst)
    monkeypatch.setattr(auth.os, "replace", replace)
    auth.set_pin("4821")
    (src, dst, old), = seen
    assert dst == str(config.path("auth.json")) and src != dst and '"pin"' not in old and auth.has_pin()


# ---- rotation

def test_rotating_the_token_cancels_unused_login_codes():
    token = auth.ensure_token()
    session, code = auth.login(token, "lan"), auth.login_code()
    fresh_token = auth.rotate_token()
    assert auth.login(code, "phone") is None and not auth.check(session) and not auth.check(token)
    assert auth.check(fresh_token) and auth.login(auth.login_code(), "phone")


def test_codes_only_login_refuses_the_access_token():
    token = auth.ensure_token()
    assert auth.login(token, "c", codes_only=True) is None
    assert auth.login(token, "c")
