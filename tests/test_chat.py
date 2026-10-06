import pytest

from conftest import signup


def chat(client, headers, message="I feel proud of myself today", **extra):
    return client.post("/chat", headers=headers, json={"message": message, **extra})


class TestTextOnly:
    def test_returns_full_analysis(self, client, headers):
        r = chat(client, headers)
        assert r.status_code == 200
        body = r.json()
        for key in ("conversation_id", "unified_emotion", "unified_confidence", "text_result",
                    "face_result", "fusion_result", "xai", "response", "emotion_arc",
                    "persona_id", "crisis", "rating"):
            assert key in body, f"/chat response is missing '{key}'"

    def test_text_only_emotion_and_modalities(self, client, headers):
        body = chat(client, headers, "I am so happy and proud").json()
        assert body["unified_emotion"] == "happy"
        assert body["face_result"] is None
        assert body["fusion_result"]["modalities_used"] == ["text"]
        assert body["fusion_result"]["resolution_reason"] == "text_only"

    def test_first_message_uses_opening_reply_and_stores_both_turns(self, client, headers, engine, fake_db, auth):
        body = chat(client, headers).json()
        assert body["response"] == "Aria first reply" and body["persona_id"] == 3
        assert "generate" in engine.calls and "generate_reply" not in engine.calls
        msgs = fake_db.get_conversation_messages(body["conversation_id"], auth[1])
        assert [m["role"] for m in msgs] == ["user", "assistant"]
        assert msgs[0]["emotion"] is not None, "user message must carry its detected emotion"
        assert msgs[1]["emotion"] is None, "Aria's reply must not be counted as a journal entry"

    def test_confidence_is_a_probability(self, client, headers):
        c = chat(client, headers).json()["unified_confidence"]
        assert 0.0 < c <= 1.0

    @pytest.mark.parametrize("message", ["", "   ", "\n\t"])
    def test_blank_message_rejected(self, client, headers, message):
        assert chat(client, headers, message).status_code == 400


class TestWithFace:
    def test_both_modalities_are_fused(self, client, headers, stub):
        stub.face_emotion = "happy"
        body = chat(client, headers, "I am happy", image_base64="AAAA").json()
        assert body["face_result"]["emotion"] == "happy"
        assert body["fusion_result"]["modalities_used"] == ["text", "face"]
        assert body["unified_emotion"] == "happy"

    def test_agreeing_modalities_are_more_confident_than_either_alone(self, client, headers, stub):
        stub.face_emotion = "happy"
        alone = chat(client, headers, "I am happy").json()["unified_confidence"]
        fused = chat(client, headers, "I am happy", image_base64="AAAA").json()["unified_confidence"]
        assert fused > alone

    def test_disagreement_still_resolves_to_one_of_the_two(self, client, headers, stub):
        stub.face_emotion = "angry"
        body = chat(client, headers, "I am so sad", image_base64="AAAA").json()
        assert body["unified_emotion"] in {"sad", "angry"}
        assert body["fusion_result"]["modalities_used"] == ["text", "face"]

    def test_face_service_failure_degrades_to_text_only(self, client, headers, stub):
        stub.face_down = True
        r = chat(client, headers, "I am happy", image_base64="AAAA")
        assert r.status_code == 200
        assert r.json()["face_result"] is None
        assert r.json()["fusion_result"]["modalities_used"] == ["text"]

    def test_no_image_means_face_service_is_never_called(self, client, headers, stub):
        chat(client, headers, "I am happy")
        assert [p for p, _ in stub.requests] == ["/analyze"]


class TestServiceFailure:
    def test_text_service_down_is_a_clear_502(self, client, headers, stub):
        stub.text_down = True
        r = chat(client, headers)
        assert r.status_code == 502 and "unavailable" in r.json()["detail"].lower()

    def test_failed_analysis_stores_nothing(self, client, headers, stub, fake_db):
        stub.text_down = True
        chat(client, headers)
        assert fake_db.messages == [], "a failed analysis must not leave a half-written entry"


class TestConversations:
    def test_follow_up_continues_same_conversation(self, client, headers, engine, fake_db, auth):
        first = chat(client, headers).json()
        second = chat(client, headers, "and another thing, I am happy",
                      conversation_id=first["conversation_id"]).json()
        assert second["conversation_id"] == first["conversation_id"]
        assert second["response"] == "Aria follow-up reply"
        assert engine.calls.count("generate") == 1 and "generate_reply" in engine.calls
        assert second["persona_id"] == first["persona_id"], "persona must stay stable within a thread"
        assert len(fake_db.get_conversation_messages(first["conversation_id"], auth[1])) == 4

    def test_unknown_conversation_is_404(self, client, headers):
        assert chat(client, headers, conversation_id=999).status_code == 404

    def test_cannot_post_into_another_users_conversation(self, client, headers):
        cid = chat(client, headers).json()["conversation_id"]
        other = signup(client, "mallory")
        h2 = {"Authorization": f"Bearer {other['token']}"}
        assert chat(client, h2, "let me in", conversation_id=cid).status_code == 404


class TestCrisis:
    @pytest.mark.parametrize("text", ["I want to end my life", "i want to kill myself",
                                      "there is no reason to live anymore"])
    def test_explicit_language_triggers_crisis_path(self, client, headers, engine, fake_db, auth, text):
        body = chat(client, headers, text).json()
        assert body["crisis"] == {"is_crisis": True, "reason": "explicit_language"}
        assert body["response"] == "Aria crisis reply"
        assert "generate_crisis_reply" in engine.calls and "generate" not in engine.calls
        user_msg = fake_db.get_conversation_messages(body["conversation_id"], auth[1])[0]
        assert user_msg["crisis_flag"] == 1, "the stored entry must be flagged for the doctor report"

    def test_ordinary_sadness_is_not_a_crisis(self, client, headers, engine):
        body = chat(client, headers, "I feel sad and tired today").json()
        assert body["crisis"]["is_crisis"] is False
        assert "generate_crisis_reply" not in engine.calls

    def test_sustained_distress_over_five_entries_triggers(self, client, headers, fake_db, auth, engine):
        fake_db.seed_entries(auth[1], ["sad"] * 5)
        body = chat(client, headers, "still feeling sad").json()
        assert body["crisis"] == {"is_crisis": True, "reason": "sustained_distress"}
        assert engine.last_crisis_reason == "sustained_distress"

    def test_four_distressed_entries_is_not_yet_a_pattern(self, client, headers, fake_db, auth):
        fake_db.seed_entries(auth[1], ["sad"] * 4)
        assert chat(client, headers, "still feeling sad").json()["crisis"]["is_crisis"] is False

    def test_one_good_entry_in_the_window_breaks_the_pattern(self, client, headers, fake_db, auth):
        fake_db.seed_entries(auth[1], ["sad", "sad", "happy", "sad", "sad"])
        assert chat(client, headers, "still feeling sad").json()["crisis"]["is_crisis"] is False

    def test_low_confidence_negative_entries_do_not_count(self, client, headers, fake_db, auth):
        fake_db.seed_entries(auth[1], ["sad"] * 5, confidence=0.4)
        assert chat(client, headers, "still feeling sad").json()["crisis"]["is_crisis"] is False


class TestLanguageSupport:
    def test_non_english_entry_is_translated_in_and_reply_translated_out(self, client, headers, fake_db, auth):
        body = chat(client, headers, "मैं बहुत खुश हूँ", lang="hi").json()
        assert body["response"].startswith("[hi] "), "reply must come back in the user's language"
        stored = fake_db.get_conversation_messages(body["conversation_id"], auth[1])
        assert stored[0]["content"].startswith("[en] "), "journal text is stored in English"
        assert not stored[1]["content"].startswith("[hi]"), "Aria's reply is stored in English too"


class TestRatingAfterChat:
    def test_rating_reflects_entries(self, client, headers):
        first = chat(client, headers, "I am happy and proud").json()["rating"]
        assert first["entry_count"] == 1 and 0 <= first["score"] <= 100
