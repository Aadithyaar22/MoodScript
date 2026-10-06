import pytest

from models.crisis import assess_crisis
from models.rating import compute_rating, summarize_history


class TestExplicitCrisisLanguage:
    @pytest.mark.parametrize("text", [
        "I want to kill myself", "i keep thinking about killing myself", "I want to end my life",
        "I'm ending my life tonight", "I want to die", "I wanted to die", "I wish I were dead",
        "I wish I was dead", "I don't want to live anymore", "I dont want to be alive",
        "I don't want to exist", "I've been suicidal", "thinking about suicide", "I self-harm",
        "I have been self harming", "I keep cutting myself", "everyone is better off dead without me",
        "there's no reason to live", "no point living", "no point in going on",
        "I WANT TO KILL MYSELF", "...honestly?? i want to die."])
    def test_detected(self, text):
        assert assess_crisis(text, []) == {"is_crisis": True, "reason": "explicit_language"}

    @pytest.mark.parametrize("text", [
        "I feel sad today", "I'm exhausted and stressed about exams", "I'm killing it at work",
        "I'm dying to see that movie", "I killed the presentation", "My life has changed a lot",
        "This is the end of a long week", "I'm so angry at my brother", "", "   "])
    def test_ordinary_text_is_not_flagged(self, text):
        assert assess_crisis(text, [])["is_crisis"] is False

    def test_explicit_language_outranks_the_sustained_pattern(self):
        entries = [{"emotion": "sad", "confidence": 0.9}] * 5
        assert assess_crisis("I want to die", entries)["reason"] == "explicit_language"


class TestSustainedDistress:
    def entries(self, emotions, conf=0.9):
        return [{"emotion": e, "confidence": conf} for e in emotions]

    @pytest.mark.parametrize("emotion", ["sad", "fearful", "angry", "disgusted"])
    def test_five_negative_entries_trigger(self, emotion):
        assert assess_crisis("ok", self.entries([emotion] * 5)) == {"is_crisis": True,
                                                                     "reason": "sustained_distress"}

    def test_mixed_negative_emotions_count_together(self):
        assert assess_crisis("ok", self.entries(["sad", "fearful", "angry", "disgusted", "sad"]))["is_crisis"]

    def test_needs_a_full_window_of_five(self):
        assert not assess_crisis("ok", self.entries(["sad"] * 4))["is_crisis"]

    @pytest.mark.parametrize("breaker", ["happy", "neutral", "surprised"])
    def test_any_non_negative_entry_in_the_window_breaks_it(self, breaker):
        assert not assess_crisis("ok", self.entries(["sad", "sad", breaker, "sad", "sad"]))["is_crisis"]

    def test_only_the_five_most_recent_entries_matter(self):
        recent_first = self.entries(["sad"] * 5 + ["happy"] * 10)
        assert assess_crisis("ok", recent_first)["is_crisis"]
        assert not assess_crisis("ok", self.entries(["happy"] + ["sad"] * 9))["is_crisis"]

    def test_confidence_must_clear_the_threshold(self):
        assert not assess_crisis("ok", self.entries(["sad"] * 5, conf=0.55))["is_crisis"]
        assert assess_crisis("ok", self.entries(["sad"] * 5, conf=0.56))["is_crisis"]


class TestRating:
    def entries(self, emotions, conf=0.9):
        return [{"emotion": e, "confidence": conf} for e in emotions]  # most recent first

    def test_no_entries(self):
        r = compute_rating([])
        assert r["score"] is None and r["entry_count"] == 0 and r["trend"] == "steady"

    def test_all_happy_scores_high_and_all_sad_scores_low(self):
        happy = compute_rating(self.entries(["happy"] * 6))
        sad = compute_rating(self.entries(["sad"] * 6))
        assert happy["score"] >= 70 and happy["label"] == "Doing well"
        assert sad["score"] <= 30 and sad["label"] == "Having a hard time"

    def test_neutral_sits_in_the_middle(self):
        assert compute_rating(self.entries(["neutral"] * 6))["score"] == 50

    @pytest.mark.parametrize("emotions", [["happy"] * 3, ["sad"] * 3, ["angry", "happy", "sad", "neutral"]])
    def test_score_is_always_0_to_100(self, emotions):
        assert 0 <= compute_rating(self.entries(emotions))["score"] <= 100

    def test_recent_entries_weigh_more_than_old_ones(self):
        recent_good = compute_rating(self.entries(["happy"] * 3 + ["sad"] * 3))["score"]
        recent_bad = compute_rating(self.entries(["sad"] * 3 + ["happy"] * 3))["score"]
        assert recent_good > recent_bad

    def test_trend_improving_declining_steady(self):
        assert compute_rating(self.entries(["happy"] * 5 + ["sad"] * 5))["trend"] == "improving"
        assert compute_rating(self.entries(["sad"] * 5 + ["happy"] * 5))["trend"] == "declining"
        assert compute_rating(self.entries(["neutral"] * 10))["trend"] == "steady"

    def test_missing_confidence_falls_back_to_a_neutral_weight(self):
        r = compute_rating([{"emotion": "happy", "confidence": None}, {"emotion": "happy"}])
        assert r["score"] == 100 and r["entry_count"] == 2

    def test_entry_count_is_reported(self):
        assert compute_rating(self.entries(["happy"] * 7))["entry_count"] == 7


class TestHistorySummary:
    def test_empty_history_gives_no_context(self):
        assert summarize_history([]) == ""

    def test_summary_reports_counts_trend_and_wraps_raw_text_as_untrusted(self):
        entries = [{"emotion": "sad", "confidence": 0.9, "content": "rough week at work"}] * 3 + \
                  [{"emotion": "happy", "confidence": 0.9, "content": "good day"}]
        s = summarize_history(entries)
        assert "4 prior entries" in s and "sad (3x)" in s
        assert "rough week at work" in s and "UNTRUSTED" in s.upper()
