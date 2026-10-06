from conftest import signup


def chat(client, headers, message="I am so happy and proud today", **extra):
    r = client.post("/chat", headers=headers, json={"message": message, **extra})
    assert r.status_code == 200, r.text
    return r.json()


def other_user(client, name="mallory"):
    return {"Authorization": f"Bearer {signup(client, name)['token']}"}


class TestHistoryAndRating:
    def test_empty_account(self, client, headers):
        assert client.get("/history", headers=headers).json() == []
        rating = client.get("/rating", headers=headers).json()
        assert rating["score"] is None and rating["entry_count"] == 0

    def test_entries_appear_most_recent_first(self, client, headers):
        chat(client, headers, "I am happy")
        chat(client, headers, "I am sad")
        emotions = [h["emotion"] for h in client.get("/history", headers=headers).json()]
        assert emotions == ["sad", "happy"]

    def test_snippet_is_truncated_to_100_chars(self, client, headers):
        chat(client, headers, "happy " * 60)
        snippet = client.get("/history", headers=headers).json()[0]["journal_snippet"]
        assert len(snippet) == 100

    def test_assistant_replies_are_not_journal_entries(self, client, headers):
        chat(client, headers)
        assert len(client.get("/history", headers=headers).json()) == 1

    def test_happy_history_scores_higher_than_sad_history(self, client, headers):
        for _ in range(3):
            chat(client, headers, "I am so happy")
        happy = client.get("/rating", headers=headers).json()["score"]
        h2 = other_user(client, "bob")
        for _ in range(3):
            chat(client, h2, "I am so sad")
        sad = client.get("/rating", headers=h2).json()["score"]
        assert 0 <= sad < happy <= 100

    def test_users_never_see_each_others_entries(self, client, headers):
        chat(client, headers, "my private happy secret")
        h2 = other_user(client)
        assert client.get("/history", headers=h2).json() == []
        assert client.get("/rating", headers=h2).json()["entry_count"] == 0
        assert client.get("/conversations", headers=h2).json() == []


class TestConversationEndpoints:
    def test_list_shows_opening_line_and_count(self, client, headers):
        chat(client, headers, "I am happy about the first thing")
        convo = client.get("/conversations", headers=headers).json()[0]
        assert convo["opening_line"] == "I am happy about the first thing"
        assert convo["message_count"] == 2

    def test_open_conversation_returns_both_turns_in_order(self, client, headers):
        cid = chat(client, headers)["conversation_id"]
        msgs = client.get(f"/conversations/{cid}/messages", headers=headers).json()
        assert [m["role"] for m in msgs] == ["user", "assistant"]

    def test_reopening_in_another_language_translates_the_thread(self, client, headers):
        cid = chat(client, headers)["conversation_id"]
        msgs = client.get(f"/conversations/{cid}/messages?lang=kn", headers=headers).json()
        assert all(m["content"].startswith("[kn] ") for m in msgs)

    def test_delete_removes_conversation_and_its_messages(self, client, headers):
        cid = chat(client, headers)["conversation_id"]
        assert client.delete(f"/conversations/{cid}", headers=headers).json() == {"deleted": True}
        assert client.get(f"/conversations/{cid}/messages", headers=headers).status_code == 404
        assert client.get("/history", headers=headers).json() == []

    def test_cannot_read_or_delete_someone_elses_conversation(self, client, headers):
        cid = chat(client, headers)["conversation_id"]
        h2 = other_user(client)
        assert client.get(f"/conversations/{cid}/messages", headers=h2).status_code == 404
        assert client.delete(f"/conversations/{cid}", headers=h2).status_code == 404
        assert client.get(f"/conversations/{cid}/messages", headers=headers).status_code == 200

    def test_unknown_conversation_is_404(self, client, headers):
        assert client.get("/conversations/12345/messages", headers=headers).status_code == 404
        assert client.delete("/conversations/12345", headers=headers).status_code == 404


class TestExport:
    def test_journal_export_contains_both_speakers_and_download_header(self, client, headers):
        chat(client, headers, "I am happy to write this")
        r = client.get("/export", headers=headers)
        assert r.status_code == 200 and r.headers["content-type"].startswith("text/plain")
        assert "attachment" in r.headers["content-disposition"]
        assert "You [happy]" in r.text and "Aria:" in r.text and "alice" in r.text

    def test_doctor_report_text(self, client, headers):
        chat(client, headers)
        r = client.get("/export/doctor-report", headers=headers)
        assert r.status_code == 200 and r.headers["content-type"].startswith("text/plain")

    def test_doctor_report_pdf_is_a_real_pdf(self, client, headers, engine):
        chat(client, headers)
        r = client.get("/export/doctor-report?format=pdf", headers=headers)
        assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
        assert r.content.startswith(b"%PDF")
        assert "generate_clinical_summary" in engine.calls

    def test_doctor_report_rejects_unknown_format(self, client, headers):
        assert client.get("/export/doctor-report?format=docx", headers=headers).status_code == 400

    def test_export_does_not_leak_other_users_entries(self, client, headers):
        chat(client, headers, "my private happy secret")
        h2 = other_user(client)
        assert "private happy secret" not in client.get("/export", headers=h2).text


class TestReflection:
    def test_no_entries_means_no_letter(self, client, headers, engine):
        body = client.get("/reflection", headers=headers).json()
        assert body["content"] is None and body["entry_count"] == 0
        assert "generate_reflection" not in engine.calls

    def test_letter_is_generated_once_then_served_from_cache(self, client, headers, engine):
        chat(client, headers)
        first = client.get("/reflection", headers=headers).json()
        second = client.get("/reflection", headers=headers).json()
        assert first["content"] == "Weekly reflection letter" and first["cached"] is False
        assert second["cached"] is True
        assert engine.calls.count("generate_reflection") == 1, "must not regenerate (and re-bill the LLM) on every view"


class TestAccountDeletion:
    def test_delete_account_erases_everything(self, client, headers, fake_db, auth):
        chat(client, headers)
        assert client.delete("/account", headers=headers).json() == {"deleted": True}
        assert fake_db.users == {} and fake_db.messages == [] and fake_db.conversations == {}

    def test_deleted_user_cannot_log_in_again(self, client, headers):
        client.delete("/account", headers=headers)
        r = client.post("/auth/login", json={"username": "alice", "password": "secret123"})
        assert r.status_code == 401

    def test_deleting_one_account_leaves_others_intact(self, client, headers):
        h2 = other_user(client, "bob")
        chat(client, h2, "bob is happy")
        client.delete("/account", headers=headers)
        assert len(client.get("/history", headers=h2).json()) == 1


def test_health_reports_status(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"
    assert r.json()["arbiter"] == "disabled"
