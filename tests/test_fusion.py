"""Unit tests for models/fusion.py, plus a reproduction of the headline result.

The last class runs the *shipped* FusionLayer over the committed paired benchmark data
(research/results/*.json) and checks it still produces the accuracies the paper, report and
README claim. If someone edits a constant or a fusion rule, those claims stop being true and
this fails."""
import json
import math
import os

import pytest

import models.fusion as fusion_mod
from models.fusion import FusionLayer, UNIFIED_EMOTIONS, _normalise, _temperature_scale
from fakes import dist

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


def text(top, p=0.7):
    d = dist(top, p)
    return {"dominant_emotion": top, "confidence": d[top], "all_scores": d}


def face(top, p=0.7):
    d = dist(top, p)
    return {"emotion": top, "confidence": d[top], "all_scores": d}


class TestTemperatureScaling:
    BASE = {"angry": 0.05, "disgusted": 0.05, "fearful": 0.1, "happy": 0.5, "neutral": 0.1,
            "sad": 0.1, "surprised": 0.1}

    @staticmethod
    def entropy(p):
        return -sum(v * math.log(v) for v in p.values() if v > 0)

    def test_temperature_one_is_identity(self):
        out = _temperature_scale(self.BASE, 1.0)
        assert all(out[k] == pytest.approx(self.BASE[k]) for k in self.BASE)

    def test_above_one_softens_below_one_sharpens(self):
        assert self.entropy(_temperature_scale(self.BASE, 1.7)) > self.entropy(self.BASE)
        assert self.entropy(_temperature_scale(self.BASE, 0.7)) < self.entropy(self.BASE)

    @pytest.mark.parametrize("t", [0.5, 0.9171, 1.0, 1.699, 3.0])
    def test_preserves_ranking_and_sums_to_one(self, t):
        out = _temperature_scale(self.BASE, t)
        assert sum(out.values()) == pytest.approx(1.0)
        assert max(out, key=out.get) == "happy"
        assert sorted(out, key=out.get) == sorted(self.BASE, key=self.BASE.get)

    def test_zero_probabilities_do_not_produce_nan_or_inf(self):
        out = _temperature_scale({**self.BASE, "angry": 0.0, "sad": 0.0}, 1.699)
        assert all(math.isfinite(v) for v in out.values())

    def test_all_zero_scores_normalise_to_uniform(self):
        out = _normalise({e: 0.0 for e in UNIFIED_EMOTIONS})
        assert all(v == pytest.approx(1 / 7) for v in out.values())


class TestFuse:
    layer = FusionLayer()

    def test_no_face_returns_text_unchanged(self):
        t = text("sad", 0.8)
        out = self.layer.fuse(t, None)
        assert out["unified_emotion"] == "sad" and out["unified_confidence"] == 0.8
        assert out["modalities_used"] == ["text"] and out["resolution_reason"] == "text_only"
        assert (out["text_weight"], out["face_weight"]) == (1.0, 0.0)

    def test_fused_scores_are_a_distribution_and_confidence_is_its_max(self):
        out = self.layer.fuse(text("sad"), face("angry"))
        assert sum(out["all_scores"].values()) == pytest.approx(1.0)
        assert out["unified_confidence"] == pytest.approx(max(out["all_scores"].values()))
        assert out["unified_emotion"] == max(out["all_scores"], key=out["all_scores"].get)

    def test_product_rule_weights_both_modalities_equally(self):
        out = self.layer.fuse(text("sad"), face("angry"))
        assert (out["text_weight"], out["face_weight"]) == (0.5, 0.5)

    @pytest.mark.parametrize("emotion", UNIFIED_EMOTIONS)
    def test_agreement_is_preserved_for_every_emotion(self, emotion):
        out = self.layer.fuse(text(emotion), face(emotion))
        assert out["unified_emotion"] == emotion

    def test_agreement_raises_confidence_above_either_modality(self):
        out = self.layer.fuse(text("happy", 0.6), face("happy", 0.6))
        assert out["unified_confidence"] > 0.6

    def test_a_confident_modality_outvotes_an_unsure_one(self):
        out = self.layer.fuse(text("sad", 0.95), face("happy", 0.2))
        assert out["unified_emotion"] == "sad"
        out = self.layer.fuse(text("happy", 0.2), face("sad", 0.95))
        assert out["unified_emotion"] == "sad"

    def test_inputs_are_not_mutated(self):
        t, f = text("sad"), face("angry")
        before = (json.dumps(t, sort_keys=True), json.dumps(f, sort_keys=True))
        self.layer.fuse(t, f)
        assert (json.dumps(t, sort_keys=True), json.dumps(f, sort_keys=True)) == before

    def test_degenerate_zero_distribution_still_returns_a_valid_emotion(self):
        t = {"dominant_emotion": "neutral", "confidence": 0.0, "all_scores": {e: 0.0 for e in UNIFIED_EMOTIONS}}
        out = self.layer.fuse(t, face("happy"))
        assert out["unified_emotion"] in UNIFIED_EMOTIONS and math.isfinite(out["unified_confidence"])

    def test_alternate_rules_are_selectable_and_differ_from_default(self, monkeypatch):
        t, f = text("sad", 0.55), face("angry", 0.9)
        default = self.layer.fuse(t, f)
        monkeypatch.setattr(fusion_mod, "_WEIGHTED", True)
        weighted = self.layer.fuse(t, f)
        assert (weighted["text_weight"], weighted["face_weight"]) != (0.5, 0.5)
        assert sum(weighted["all_scores"].values()) == pytest.approx(1.0)
        monkeypatch.setattr(fusion_mod, "_WEIGHTED", False)
        monkeypatch.setattr(fusion_mod, "_LEGACY", True)
        legacy = self.layer.fuse(t, f)
        assert sum(legacy["all_scores"].values()) == pytest.approx(1.0)
        assert default["all_scores"] != legacy["all_scores"]


class TestDeployedConstants:
    def test_temperatures_are_the_values_the_paper_reports(self):
        assert fusion_mod.TEXT_TEMPERATURE == pytest.approx(1.6990, abs=1e-4)
        assert fusion_mod.FACE_TEMPERATURE == pytest.approx(0.9171, abs=1e-4)

    def test_constants_match_the_fitted_file(self):
        c = json.load(open(os.path.join(ROOT, "research", "results", "fusion_constants.json")))
        assert fusion_mod.TEXT_TEMPERATURE == pytest.approx(c["temperature"]["text"], abs=5e-4)
        assert fusion_mod.FACE_TEMPERATURE == pytest.approx(c["temperature"]["face"], abs=5e-4)

    def test_default_rule_is_the_plain_product_rule(self):
        assert fusion_mod._LEGACY is False and fusion_mod._WEIGHTED is False


def _mcnemar_p(a_right, b_right):
    """Two-sided McNemar test (continuity-corrected chi-square, 1 dof), pure Python."""
    n10 = sum(1 for x, y in zip(a_right, b_right) if x and not y)
    n01 = sum(1 for x, y in zip(a_right, b_right) if y and not x)
    if n10 + n01 == 0:
        return 1.0
    chi2 = (abs(n10 - n01) - 1) ** 2 / (n10 + n01)
    return math.erfc(math.sqrt(chi2 / 2))


def _run(pairs):
    layer, out = FusionLayer(), []
    for p in pairs:
        t = {"dominant_emotion": p["text_pred"], "all_scores": p["text_dist"],
             "confidence": max(p["text_dist"].values())}
        f = {"emotion": p["face_pred"], "all_scores": p["face_dist"],
             "confidence": max(p["face_dist"].values())}
        out.append(layer.fuse(t, f)["unified_emotion"])
    return out


def _acc(pred, truth):
    return round(100 * sum(a == b for a, b in zip(pred, truth)) / len(truth), 2)


# set name -> (text-only, face-only, DEPLOYED calibrated product) accuracy claimed in the README
CLAIMED = {"paired_set.json": (49.74, 88.39, 92.37), "paired_set_journal.json": (64.57, 88.69, 92.91)}


@pytest.mark.parametrize("name", CLAIMED)
class TestReproducesHeadlineResult:
    @pytest.fixture
    def test_split(self, name):
        d = json.load(open(os.path.join(ROOT, "research", "results", name)))
        return [p for p in d["pairs"] if p["split"] == "test"]

    def test_shipped_fusion_reproduces_claimed_accuracy(self, name, test_split):
        truth = [p["true"] for p in test_split]
        text_only, face_only, deployed = CLAIMED[name]
        assert _acc([p["text_pred"] for p in test_split], truth) == text_only
        assert _acc([p["face_pred"] for p in test_split], truth) == face_only
        assert _acc(_run(test_split), truth) == deployed

    def test_calibrated_fusion_beats_the_better_single_modality_significantly(self, name, test_split):
        truth = [p["true"] for p in test_split]
        fused = [a == b for a, b in zip(_run(test_split), truth)]
        face_only = [p["face_pred"] == t for p, t in zip(test_split, truth)]
        assert sum(fused) > sum(face_only)
        assert _mcnemar_p(fused, face_only) < 0.001

    def test_old_linear_fusion_was_worse_than_face_alone(self, name, test_split, monkeypatch):
        """The negative finding that motivated the whole calibration study."""
        monkeypatch.setattr(fusion_mod, "_LEGACY", True)
        truth = [p["true"] for p in test_split]
        assert _acc(_run(test_split), truth) < _acc([p["face_pred"] for p in test_split], truth)
