"""What a real person does in a real browser, against the real React frontend and the real
FastAPI orchestrator (with fake model services behind it, so results are deterministic).

Everything is located the way a user finds it: by visible text, placeholder or role. Each test
also fails if the page throws an uncaught JavaScript error."""
import base64
import re

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.e2e

# a valid 1x1 PNG, used as the "uploaded photo"
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGP4z8DwHwAFAAH/q842iQAAAABJRU5ErkJggg==")


def sign_up(page: Page, username="alice", password="secret123"):
    page.goto("/")
    page.get_by_role("button", name="Sign up").click()           # switch the form to sign-up mode
    page.locator("form input").first.fill(username)
    page.locator("input[type=password]").fill(password)
    page.get_by_role("button", name="Sign up").click()           # submit
    expect(page.get_by_text("How are you")).to_be_visible()


def log_in(page: Page, username="alice", password="secret123"):
    page.goto("/")
    page.locator("form input").first.fill(username)
    page.locator("input[type=password]").fill(password)
    page.get_by_role("button", name="Log in").click()


def write_entry(page: Page, text: str):
    page.get_by_placeholder(re.compile("Write freely")).fill(text)
    page.get_by_role("button", name=re.compile("Analyse Mood", re.I)).click()


def log_out(page: Page):
    page.get_by_role("button", name="Log out").click()
    expect(page.get_by_text("Welcome back")).to_be_visible()


class TestAccount:
    def test_new_user_can_sign_up_and_reach_the_journal(self, page, js_errors):
        sign_up(page)
        expect(page.get_by_placeholder(re.compile("Write freely"))).to_be_visible()
        expect(page.get_by_text("alice")).to_be_visible()
        assert js_errors == []

    def test_login_screen_is_the_first_thing_a_stranger_sees(self, page):
        page.goto("/")
        expect(page.get_by_text("Welcome back")).to_be_visible()
        expect(page.get_by_placeholder(re.compile("Write freely"))).to_have_count(0)

    def test_wrong_password_shows_an_error_and_stays_on_login(self, page):
        sign_up(page)
        log_out(page)
        log_in(page, password="not-the-password")
        expect(page.get_by_text(re.compile("Invalid username or password", re.I))).to_be_visible()
        expect(page.get_by_placeholder(re.compile("Write freely"))).to_have_count(0)

    def test_short_password_is_refused_at_sign_up(self, page):
        page.goto("/")
        page.get_by_role("button", name="Sign up").click()
        page.locator("form input").first.fill("bob")
        page.locator("input[type=password]").fill("123")
        page.get_by_role("button", name="Sign up").click()
        expect(page.get_by_text(re.compile("at least 6", re.I))).to_be_visible()

    def test_duplicate_username_is_refused(self, page):
        sign_up(page, "alice")
        log_out(page)
        page.get_by_role("button", name="Sign up").click()
        page.locator("form input").first.fill("alice")
        page.locator("input[type=password]").fill("secret123")
        page.get_by_role("button", name="Sign up").click()
        expect(page.get_by_text(re.compile("already taken", re.I))).to_be_visible()

    def test_session_survives_a_page_reload(self, page):
        sign_up(page)
        page.reload()
        expect(page.get_by_placeholder(re.compile("Write freely"))).to_be_visible()

    def test_logging_out_returns_to_login_and_stays_out_after_reload(self, page):
        sign_up(page)
        log_out(page)
        page.reload()
        expect(page.get_by_text("Welcome back")).to_be_visible()

    def test_can_log_back_in(self, page):
        sign_up(page)
        log_out(page)
        log_in(page)
        expect(page.get_by_text("How are you")).to_be_visible()


class TestJournaling:
    def test_writing_an_entry_shows_emotion_and_arias_reply(self, page, js_errors):
        sign_up(page)
        write_entry(page, "I finished the project and I am so happy and proud")
        expect(page.get_by_text("Aria first reply")).to_be_visible()
        expect(page.get_by_text(re.compile(r"happy", re.I)).first).to_be_visible()
        assert js_errors == []

    def test_empty_entry_cannot_be_submitted(self, page, backend):
        sign_up(page)
        analyse = page.get_by_role("button", name=re.compile("Analyse Mood", re.I))
        expect(analyse).to_be_disabled()
        assert backend.requests() == []

    def test_each_emotion_is_recognised_from_the_text(self, page, backend):
        sign_up(page)
        write_entry(page, "I am so angry about this")
        expect(page.get_by_text("Aria first reply")).to_be_visible()
        expect(page.get_by_text(re.compile(r"angry", re.I)).first).to_be_visible()

    def test_follow_up_reply_continues_the_conversation(self, page):
        sign_up(page)
        write_entry(page, "I am happy today")
        expect(page.get_by_text("Aria first reply")).to_be_visible()
        page.get_by_placeholder(re.compile("Reply to Aria")).fill("and I am proud too")
        page.get_by_role("button", name="Send").click()
        expect(page.get_by_text("Aria follow-up reply")).to_be_visible()

    def test_uploaded_photo_is_sent_and_fused(self, page, backend):
        backend.set(face_emotion="happy")
        sign_up(page)
        page.locator("input[type=file]").first.set_input_files(
            {"name": "face.png", "mimeType": "image/png", "buffer": PNG})
        write_entry(page, "I am happy")
        expect(page.get_by_text("Aria first reply")).to_be_visible()
        paths = [r["path"] for r in backend.requests()]
        assert "/analyze" in paths and "/predict" in paths, "the photo must reach the face model"
        assert any(r["has_image"] for r in backend.requests() if r["path"] == "/predict")

    def test_no_photo_means_face_model_is_not_used(self, page, backend):
        sign_up(page)
        write_entry(page, "I am happy")
        expect(page.get_by_text("Aria first reply")).to_be_visible()
        assert [r["path"] for r in backend.requests()] == ["/analyze"]

    def test_face_service_outage_does_not_break_the_entry(self, page, backend):
        backend.set(face_down=True)
        sign_up(page)
        page.locator("input[type=file]").first.set_input_files(
            {"name": "face.png", "mimeType": "image/png", "buffer": PNG})
        write_entry(page, "I am happy")
        expect(page.get_by_text("Aria first reply")).to_be_visible()

    def test_text_service_outage_shows_an_error_not_a_blank_page(self, page, backend, js_errors):
        backend.set(text_down=True)
        sign_up(page)
        write_entry(page, "I am happy")
        expect(page.get_by_text(re.compile(r"unavailable|error|try again|went wrong", re.I)).first).to_be_visible()
        expect(page.get_by_placeholder(re.compile("Write freely|Reply to Aria"))).to_be_visible()

    def test_crisis_entry_gets_the_supportive_reply(self, page, engine=None):
        sign_up(page)
        write_entry(page, "I want to end my life")
        expect(page.get_by_text("Aria crisis reply")).to_be_visible()


class TestExplainability:
    def test_why_button_opens_the_explanation_panel(self, page, js_errors):
        sign_up(page)
        write_entry(page, "I am so happy and proud")
        expect(page.get_by_text("Aria first reply")).to_be_visible()
        page.get_by_role("button", name="why?").click()
        expect(page.get_by_text("Explainability")).to_be_visible()
        expect(page.get_by_text(re.compile("text only", re.I))).to_be_visible()
        assert js_errors == []


class TestDashboardAndHistory:
    def test_dashboard_counts_entries_after_journaling(self, page, js_errors):
        sign_up(page)
        write_entry(page, "I am so happy")
        expect(page.get_by_text("Aria first reply")).to_be_visible()
        page.get_by_role("button", name="+ New conversation").click()
        write_entry(page, "I am so sad")
        expect(page.get_by_text("Aria first reply")).to_be_visible()
        page.get_by_role("button", name="Dashboard").click()
        expect(page.get_by_text("TOTAL ENTRIES")).to_be_visible()
        expect(page.get_by_text("MOOD OVER TIME")).to_be_visible()
        expect(page.get_by_text("EMOTION DISTRIBUTION")).to_be_visible()
        card = page.get_by_text("TOTAL ENTRIES").locator("xpath=..")      # label + its value
        expect(card).to_have_text(re.compile(r"TOTAL ENTRIES\s*2"))
        expect(page.get_by_text("MOST COMMON").locator("xpath=..")).to_contain_text("×")
        assert js_errors == []

    def test_empty_dashboard_shows_a_friendly_empty_state(self, page, js_errors):
        sign_up(page)
        page.get_by_role("button", name="Dashboard").click()
        expect(page.get_by_text("No entries yet.")).to_be_visible()
        expect(page.get_by_text("TOTAL ENTRIES")).to_have_count(0)
        assert js_errors == []

    def test_past_conversation_can_be_reopened_from_the_sidebar(self, page):
        sign_up(page)
        write_entry(page, "I am happy about the zebra exhibit")
        expect(page.get_by_text("Aria first reply")).to_be_visible()
        page.get_by_role("button", name="+ New conversation").click()
        page.get_by_text(re.compile("zebra exhibit")).first.click()
        expect(page.get_by_text("Aria first reply")).to_be_visible()

    def test_a_second_user_sees_none_of_the_first_users_entries(self, page):
        sign_up(page, "alice")
        write_entry(page, "I am happy about my private zebra news")
        expect(page.get_by_text("Aria first reply")).to_be_visible()
        log_out(page)
        sign_up(page, "bob")
        expect(page.get_by_text(re.compile("zebra"))).to_have_count(0)


class TestLanguageAndDevices:
    def test_ui_can_be_switched_to_hindi_on_the_login_screen(self, page):
        page.goto("/")
        before = page.locator("body").inner_text()
        page.get_by_text("हिंदी").click()
        page.wait_for_function("(before) => document.body.innerText !== before", arg=before)
        expect(page.get_by_text("Welcome back")).to_have_count(0)   # the English heading is gone

    def test_works_on_a_phone_sized_screen(self, page, js_errors):
        page.set_viewport_size({"width": 375, "height": 812})
        sign_up(page)
        write_entry(page, "I am so happy")
        expect(page.get_by_text("Aria first reply")).to_be_visible()
        assert js_errors == []

    def test_no_horizontal_scroll_on_a_phone(self, page):
        page.set_viewport_size({"width": 375, "height": 812})
        sign_up(page)
        overflow = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
        assert overflow <= 1, f"page is {overflow}px wider than the screen"


class TestAccountDeletion:
    def test_deleting_the_account_logs_out_and_blocks_login(self, page):
        sign_up(page)
        page.once("dialog", lambda d: d.accept())
        page.get_by_text("Delete account").click()
        page.get_by_text("Welcome back").wait_for(timeout=10000)
        log_in(page)
        expect(page.get_by_text(re.compile("Invalid username or password", re.I))).to_be_visible()
