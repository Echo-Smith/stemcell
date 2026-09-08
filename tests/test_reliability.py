import copy
import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from stemcell.llm import CallBudgetExceeded, LLMClient, UsageLedger
from stemcell.modules.quality import QualityModule
from stemcell.schema import validate_base


@pytest.fixture
def base():
    return {
        "goal": "Build",
        "constraints": ["offline"],
        "key_facts": ["FACT_SENTINEL"],
        "preferences": ["PREFERENCE_SENTINEL"],
        "boundaries": ["offline"],
        "context_summary": "Context",
        "unknowns": [],
        "raw_input": "Must work offline.",
        "hard_constraints": [{"id": "C1", "text": "offline", "source_quote": "offline"}],
    }


@pytest.fixture
def candidate():
    return {
        "id": "a",
        "status": "ok",
        "content": "Works offline",
        "perspective_label": "SECRET_ROLE",
    }


def review(status="pass", score=6):
    return {
        "scores": {"feasibility": score, "clarity": score, "risk": score},
        "constraint_checks": [
            {"id": "C1", "status": status, "evidence": "offline", "reason": "Explicit"}
        ],
        "missed_constraints": [],
        "comment": "Model opinion",
    }


def test_judge_has_full_context_but_no_role(base, candidate):
    llm = Mock()
    llm.chat_json.return_value = review()
    result = QualityModule(llm).score_single(candidate, base)
    prompt = llm.chat_json.call_args.args[0]
    assert all(v in prompt for v in ["FACT_SENTINEL", "PREFERENCE_SENTINEL", "Must work offline."])
    assert "SECRET_ROLE" not in prompt
    assert result["review_status"] == "reviewed"


def test_failure_never_gets_default_score(base, candidate):
    llm = Mock()
    llm.chat_json.side_effect = ValueError("bad JSON")
    module = QualityModule(llm)
    result = module.score_single(candidate, base)
    assert result["weighted_total"] is None
    assert result["review_status"] == "unassessed"
    assert module.run([candidate], base, 1) == []


def test_failed_generation_does_not_call_judge(base, candidate):
    llm = Mock()
    assert QualityModule(llm).run([{**candidate, "status": "error"}], base, 1) == []
    llm.chat_json.assert_not_called()


def test_hard_failure_cannot_be_offset_by_scores(base, candidate):
    llm = Mock()
    llm.chat_json.return_value = review("fail", 10)
    assert QualityModule(llm).run([candidate], base, 1) == []


def test_invented_evidence_is_unknown(base, candidate):
    llm = Mock()
    value = review()
    value["constraint_checks"][0]["evidence"] = "made up"
    llm.chat_json.return_value = value
    assert QualityModule(llm).score_single(candidate, base)["review_status"] == "needs_verification"


@pytest.mark.parametrize("value", [True, -1, 11, "8", float("nan"), float("inf")])
def test_invalid_scores_are_unassessed(base, candidate, value):
    llm = Mock()
    llm.chat_json.return_value = review(score=value)
    assert QualityModule(llm).score_single(candidate, base)["weighted_total"] is None


def test_missing_check_and_extra_constraint_are_not_approved(base, candidate):
    llm = Mock()
    value = review()
    value["constraint_checks"] = []
    llm.chat_json.return_value = value
    assert QualityModule(llm).score_single(candidate, base)["review_status"] == "unassessed"
    value = review()
    value["missed_constraints"] = ["Must work offline."]
    llm.chat_json.return_value = value
    assert QualityModule(llm).score_single(candidate, base)["review_status"] == "needs_verification"


def test_custom_dimension_drives_schema(base, candidate):
    llm = Mock()
    value = review()
    value["scores"] = {"cost": 8}
    llm.chat_json.return_value = value
    result = QualityModule(
        llm, {"dimensions": [{"name": "cost", "label": "成本", "weight": 2}]}
    ).score_single(candidate, base)
    assert result["weighted_total"] == 8
    assert '"feasibility"' not in llm.chat_json.call_args.args[0]


def test_source_validation_preserves_raw_and_rejects_omissions(base):
    assert validate_base(base, base["raw_input"])["raw_input"] == base["raw_input"]
    bad = copy.deepcopy(base)
    bad["hard_constraints"][0]["source_quote"] = "invented"
    with pytest.raises(ValueError):
        validate_base(bad, base["raw_input"])
    bad = copy.deepcopy(base)
    bad["hard_constraints"] = []
    with pytest.raises(ValueError):
        validate_base(bad, base["raw_input"])


def fake_sdk_client(content="{}", usage=None, finish="stop", ledger=None):
    client = LLMClient.__new__(LLMClient)
    client.config, client.model, client.provider = {}, "test-model", "generator"
    client.token_parameter, client.max_tokens = "max_tokens", 100
    client.ledger = ledger or UsageLedger()
    client.client = Mock()
    client.client.chat.completions.create.return_value = SimpleNamespace(
        usage=usage,
        choices=[SimpleNamespace(finish_reason=finish, message=SimpleNamespace(content=content))],
    )
    return client


@pytest.mark.parametrize("content", ["[]", '{"a": NaN}', 'prose {"a": 1}', "null"])
def test_json_must_be_object_and_finite(content):
    with pytest.raises((ValueError, json.JSONDecodeError)):
        fake_sdk_client(content).chat_json("test")


def test_usage_cost_and_budget():
    ledger = UsageLedger(
        1, {"generator/test-model": {"input_per_million": 1, "output_per_million": 2}}
    )
    llm = fake_sdk_client(
        usage=SimpleNamespace(prompt_tokens=100, completion_tokens=50), ledger=ledger
    )
    llm.chat_json("test", stage="judge")
    assert ledger.summary()["estimated_cost"] == pytest.approx(0.0002)
    assert ledger.summary()["records"][0]["stage"] == "judge"
    with pytest.raises(CallBudgetExceeded):
        llm.chat_json("test")
    assert llm.client.chat.completions.create.call_count == 1


def test_unknown_usage_not_zero_and_truncation_fails():
    llm = fake_sdk_client(finish="length")
    with pytest.raises(ValueError):
        llm.chat_json("test")
    assert llm.ledger.summary()["input_tokens"] is None
    assert llm.ledger.summary()["records"][0]["status"] == "error"


def test_extreme_weights_do_not_create_nonfinite_score(base, candidate):
    llm = Mock()
    value = review()
    value["scores"] = {"cost": 10}
    llm.chat_json.return_value = value
    module = QualityModule(
        llm, {"dimensions": [{"name": "cost", "label": "Cost", "weight": 1e308}]}
    )
    assert module.score_single(candidate, base)["weighted_total"] == 10
    with pytest.raises(ValueError):
        QualityModule(
            llm,
            {
                "dimensions": [
                    {"name": "a", "label": "A", "weight": 1e308},
                    {"name": "b", "label": "B", "weight": 1e308},
                ]
            },
        )
