#!/usr/bin/env python3
"""
Screenshot automation script for Piruetas.

Usage (from project root):
    uv run python scripts/take_screenshots.py

Requires Playwright browsers: just install-e2e
"""
import os
import shutil
import socket
import sys
import tempfile
import threading
import time
from datetime import date
from pathlib import Path

import bcrypt
import uvicorn
from playwright.sync_api import FloatRect, sync_playwright
from sqlalchemy.orm import make_transient
from sqlmodel import Session

sys.path.insert(0, str(Path(__file__).parent.parent))

import app.database as db_module
from app.auth import SESSION_COOKIE, make_session_token
from app.database import get_engine, init_db
from app.models import Entry, User
from app.settings import get_settings

SECRET_KEY = "screenshots-secret-key-not-for-production"
SCREENSHOT_USERNAME = "demo"
SCREENSHOT_PASSWORD = "piruetas"

DESKTOP_W, DESKTOP_H = 1987, 1365
MOBILE_W, MOBILE_H = 402, 874
README_W, README_H = 1988, 696

ROOT = Path(__file__).parent.parent
SCREENSHOTS_DIR = ROOT / "app" / "static" / "img" / "screenshots"

ENTRIES = [
    (
        date(2026, 4, 21),
        "<p>Took the long route to work this morning — down past the old market, where the flower stalls were just setting up. The smell of fresh carnations at seven in the morning is something else.</p>"
        "<p>Finished the book I've been dragging through for three weeks. <strong>The ending landed harder than I expected.</strong> Sat with it for a while before making coffee.</p>"
        "<p>Quiet evening. Made pasta, listened to the rain. Not every day needs to be productive.</p>",
    ),
    (
        date(2026, 4, 22),
        "<p>Rough start. The kind of morning where nothing works and everything takes twice as long. <em>Deep breath.</em></p>"
        "<p>What turned it around:</p>"
        "<ul><li><p>A good conversation with Mar about the project direction</p></li>"
        "<li><p>Finding that the problem I'd been stuck on for two days had a two-line fix</p></li>"
        "<li><p>Really good coffee from the place next door</p></li></ul>"
        "<p>Funny how fast the weight lifts.</p>",
    ),
    (
        date(2026, 4, 23),
        "<p>Noticed something small today: the fig tree on the corner of my street has its first leaves. Tiny, still folded, but there. Spring doing its thing without asking permission.</p>"
        "<p>These are the details I want to remember. Not the meetings or the emails — the fig tree, the specific grey of the sky this morning, the way the cat next door was sitting in a patch of sun like it owned the world.</p>",
    ),
    (
        date(2026, 4, 24),
        "<p>Trying to figure out where the next few months are going. Not anxiously — just thinking out loud.</p>"
        "<ol><li><p>Finish the current project before taking on anything new</p></li>"
        "<li><p>Spend more actual time outside — not walks between places, but time with no destination</p></li>"
        "<li><p>Call my sister more</p></li>"
        "<li><p>Read more fiction, less news</p></li></ol>"
        "<p>Simple list. Maybe the point is to not overcomplicate it.</p>",
    ),
    (
        date(2026, 4, 25),
        "<p>End of the week. Sat on the balcony with a beer and watched the city go quiet. There's a specific hour on Friday evenings where everything seems to exhale.</p>"
        "<p>This was a good week on balance. Not perfect — <strong>the Tuesday morning made sure of that</strong> — but full in the right ways. Good work, a few real conversations, the fig tree, the pasta.</p>"
        "<p>I keep coming back to this: <a href=\"https://piruet.app\" rel=\"noopener noreferrer nofollow\">writing things down makes them real</a>. Or at least, it makes them mine.</p>",
    ),
]


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def start_server(db_path: str, data_dir: str, port: int) -> uvicorn.Server:
    env_overrides = {
        "DATABASE_URL": f"sqlite:///{db_path}",
        "DATA_DIR": data_dir,
        "SECRET_KEY": SECRET_KEY,
        "SECURE_COOKIES": "false",
        "ADMIN_USERNAME": "admin",
        "ADMIN_PASSWORD": "adminpassword",
        "REGISTRATION_OPEN": "false",
        "DEMO_ENABLED": "false",
        "SHOW_DONATION_PROMPTS": "false",
    }
    os.environ.update(env_overrides)
    get_settings.cache_clear()
    db_module._engine = None

    config = uvicorn.Config(
        "app.main:app",
        host="127.0.0.1",
        port=port,
        log_level="error",
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    base_url = f"http://127.0.0.1:{port}"
    for _ in range(100):
        try:
            import httpx
            if httpx.get(f"{base_url}/health", timeout=0.5).status_code == 200:
                break
        except Exception:
            pass
        time.sleep(0.1)
    else:
        raise RuntimeError("Server did not start in time")

    print(f"  Server up at {base_url}")
    return server


def stop_server(server: uvicorn.Server) -> None:
    server.should_exit = True
    time.sleep(0.5)
    get_settings.cache_clear()
    if db_module._engine is not None:
        db_module._engine.dispose()
    db_module._engine = None


def make_auth_cookie(user: User, domain: str) -> dict:
    assert user.id is not None
    token = make_session_token(
        user_id=user.id,
        is_admin=user.is_admin,
        session_version=user.session_version,
        secret_key=SECRET_KEY,
    )
    return {
        "name": SESSION_COOKIE,
        "value": token,
        "domain": domain,
        "path": "/",
    }


def seed_content() -> User:
    init_db()
    hashed = bcrypt.hashpw(SCREENSHOT_PASSWORD.encode(), bcrypt.gensalt(rounds=4)).decode()
    user = User(username=SCREENSHOT_USERNAME, hashed_password=hashed, is_admin=False)
    with Session(get_engine()) as session:
        session.add(user)
        session.commit()
        session.refresh(user)
        assert user.id is not None
        for entry_date, content in ENTRIES:
            word_count = len(content.split())
            entry = Entry(
                user_id=user.id,
                date=entry_date,
                content=content,
                word_count=word_count,
            )
            session.add(entry)
        session.commit()
        session.refresh(user)
        make_transient(user)
    print(f"  Seeded user '{SCREENSHOT_USERNAME}' with {len(ENTRIES)} entries")
    return user


def set_theme(page, theme: str) -> None:
    """Set theme via localStorage then reload. theme='dark' or ''."""
    page.evaluate(f"() => localStorage.setItem('theme', '{theme}')")
    page.reload()
    page.wait_for_load_state("domcontentloaded")


def take_landing_shots(base_url: str, user: User) -> None:
    print("  Landing gallery shots (journal page shown inside browser/phone frames)...")
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    cookie = make_auth_cookie(user, "127.0.0.1")

    with sync_playwright() as pw:
        for theme, suffix in [("dark", "dark"), ("", "light")]:
            browser = pw.chromium.launch()
            ctx = browser.new_context(viewport={"width": DESKTOP_W, "height": DESKTOP_H})
            page = ctx.new_page()
            page.goto(base_url)
            ctx.add_cookies([cookie])  # type: ignore[arg-type]
            set_theme(page, theme)
            page.goto(f"{base_url}/journal/2026/04/25")
            page.wait_for_load_state("networkidle")
            page.wait_for_selector(".ProseMirror", state="visible")
            page.screenshot(path=str(SCREENSHOTS_DIR / f"desktop-{suffix}.png"), full_page=False)
            print(f"    desktop-{suffix}.png")
            browser.close()

            browser = pw.chromium.launch()
            ctx = browser.new_context(viewport={"width": MOBILE_W, "height": MOBILE_H})
            page = ctx.new_page()
            page.goto(base_url)
            ctx.add_cookies([cookie])  # type: ignore[arg-type]
            set_theme(page, theme)
            page.goto(f"{base_url}/journal/2026/04/25")
            page.wait_for_load_state("networkidle")
            page.wait_for_selector(".ProseMirror", state="visible")
            page.screenshot(path=str(SCREENSHOTS_DIR / f"mobile-{suffix}.png"), full_page=False)
            print(f"    mobile-{suffix}.png")
            browser.close()


def take_feature_shots(base_url: str, user: User) -> None:
    print("  Feature shots...")
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    cookie = make_auth_cookie(user, "127.0.0.1")

    with sync_playwright() as pw:
        # Editor — desktop dark, Friday entry (bold + link visible)
        browser = pw.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        page.goto(base_url)
        ctx.add_cookies([cookie])  # type: ignore[arg-type]
        set_theme(page, "dark")
        page.goto(f"{base_url}/journal/2026/04/25")
        page.wait_for_load_state("networkidle")
        page.wait_for_selector(".ProseMirror", state="visible")
        page.screenshot(path=str(SCREENSHOTS_DIR / "feature-editor.png"), full_page=False)
        print("    feature-editor.png")
        browser.close()

        # Calendar — desktop light, April view (5 entries visible)
        browser = pw.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        page.goto(base_url)
        ctx.add_cookies([cookie])  # type: ignore[arg-type]
        set_theme(page, "")
        page.goto(f"{base_url}/journal/2026/04/25")
        page.wait_for_load_state("networkidle")
        page.wait_for_selector("#calendar", state="visible")
        calendar = page.locator("#calendar")
        calendar.screenshot(path=str(SCREENSHOTS_DIR / "feature-calendar.png"))
        print("    feature-calendar.png")
        browser.close()

        # Mobile toolbar — mobile dark, Tuesday entry (list content)
        browser = pw.chromium.launch()
        ctx = browser.new_context(viewport={"width": MOBILE_W, "height": MOBILE_H})
        page = ctx.new_page()
        page.goto(base_url)
        ctx.add_cookies([cookie])  # type: ignore[arg-type]
        set_theme(page, "dark")
        page.goto(f"{base_url}/journal/2026/04/22")
        page.wait_for_load_state("networkidle")
        page.wait_for_selector(".ProseMirror", state="visible")
        page.screenshot(path=str(SCREENSHOTS_DIR / "feature-mobile.png"), full_page=False)
        print("    feature-mobile.png")
        browser.close()


def take_readme_shots(base_url: str, user: User) -> None:
    print("  README shots...")
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    cookie = make_auth_cookie(user, "127.0.0.1")
    clip: FloatRect = {"x": 0.0, "y": 0.0, "width": float(README_W), "height": float(README_H)}

    with sync_playwright() as pw:
        for theme, suffix in [("dark", "dark-theme"), ("", "light-theme")]:
            browser = pw.chromium.launch()
            ctx = browser.new_context(
                viewport={"width": README_W, "height": README_H + 200},
            )
            page = ctx.new_page()
            page.goto(base_url)
            ctx.add_cookies([cookie])  # type: ignore[arg-type]
            set_theme(page, theme)
            page.goto(f"{base_url}/journal/2026/04/25")
            page.wait_for_load_state("networkidle")
            page.wait_for_selector(".ProseMirror", state="visible")
            page.screenshot(path=str(SCREENSHOTS_DIR / f"{suffix}.png"), clip=clip)
            print(f"    {suffix}.png")
            browser.close()


def take_additional_shots(base_url: str, user: User) -> None:
    print("  Additional shots (mobile menu, account)...")
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    cookie = make_auth_cookie(user, "127.0.0.1")

    with sync_playwright() as pw:
        # Mobile menu open (bottom sheet)
        browser = pw.chromium.launch()
        ctx = browser.new_context(viewport={"width": MOBILE_W, "height": MOBILE_H})
        page = ctx.new_page()
        page.goto(base_url)
        ctx.add_cookies([cookie])  # type: ignore[arg-type]
        set_theme(page, "dark")
        page.goto(f"{base_url}/journal/2026/04/25")
        page.wait_for_load_state("networkidle")
        page.click("#mobile-menu-btn")
        page.wait_for_selector("#mobile-sheet:not([hidden])", state="visible")
        page.wait_for_timeout(400)
        page.screenshot(path=str(SCREENSHOTS_DIR / "feature-mobile-menu.png"), full_page=False)
        print("    feature-mobile-menu.png")
        browser.close()

        # Account security page
        browser = pw.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        page.goto(base_url)
        ctx.add_cookies([cookie])  # type: ignore[arg-type]
        set_theme(page, "")
        page.goto(f"{base_url}/account")
        page.wait_for_load_state("networkidle")
        page.screenshot(path=str(SCREENSHOTS_DIR / "feature-account-security.png"), full_page=False)
        print("    feature-account-security.png")
        browser.close()

        # Account data page
        browser = pw.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        page.goto(base_url)
        ctx.add_cookies([cookie])  # type: ignore[arg-type]
        set_theme(page, "")
        page.goto(f"{base_url}/account/data")
        page.wait_for_load_state("networkidle")
        page.screenshot(path=str(SCREENSHOTS_DIR / "feature-account-data.png"), full_page=False)
        print("    feature-account-data.png")
        browser.close()


def take_all_screenshots(base_url: str, user: User) -> None:
    take_landing_shots(base_url, user)
    take_feature_shots(base_url, user)
    take_readme_shots(base_url, user)
    take_additional_shots(base_url, user)


_server: uvicorn.Server | None = None

if __name__ == "__main__":
    tmp = tempfile.mkdtemp(prefix="piruetas_shots_")
    db_path = os.path.join(tmp, "screenshots.db")
    port = _find_free_port()

    try:
        print("Setting up server...")
        _server = start_server(db_path, tmp, port)
        base_url = f"http://127.0.0.1:{port}"

        print("Seeding content...")
        user = seed_content()

        print("Taking screenshots...")
        take_all_screenshots(base_url, user)

        print("\nDone. Screenshots saved to:")
        print(f"  {SCREENSHOTS_DIR}/")
    finally:
        if _server:
            stop_server(_server)
        shutil.rmtree(tmp, ignore_errors=True)
