from __future__ import annotations

import pytest

from scripts.evals.run_comparison import (
    RequestBudget,
    RequestBudgetExhausted,
    checkpoint_report,
    planned_requests,
    validate_live_options,
)


def test_planned_requests_counts_chat_turns_and_non_chat_cases():
    cases = [
        {"interaction": [{"channel": "chat"}, {"channel": "ui"}, {"channel": "chat"}]},
        {"interaction": [{"channel": "ui"}]},
        {"interaction": []},
    ]

    assert planned_requests(cases) == 4


def test_live_preflight_requires_full_three_round_pair_and_provider_budget():
    cases = [{"interaction": [{"channel": "chat"}]} for _ in range(40)]
    cases[-1]["interaction"].append({"channel": "chat"})

    per_architecture, maximum = validate_live_options(
        rounds=3,
        max_requests=246,
        confirm_live=True,
        provider="gemini-api",
        model="gemini-2.5-flash",
        api_key="configured",
        google_project=None,
        cases=cases,
    )

    assert per_architecture == 123
    assert maximum == 246


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"rounds": 1}, "três rodadas"),
        ({"confirm_live": False}, "--confirm-live"),
        ({"api_key": None}, "GOOGLE_API_KEY"),
        ({"max_requests": 245}, "Teto insuficiente"),
    ],
)
def test_live_preflight_rejects_incomplete_or_unauthorized_runs(overrides, message):
    options = {
        "rounds": 3,
        "max_requests": 246,
        "confirm_live": True,
        "provider": "gemini-api",
        "model": "gemini-2.5-flash",
        "api_key": "configured",
        "google_project": None,
        "cases": [{"interaction": [{"channel": "chat"}]} for _ in range(41)],
    }
    options.update(overrides)

    with pytest.raises(ValueError, match=message):
        validate_live_options(**options)


def test_live_preflight_requires_vertex_project_for_adc():
    with pytest.raises(ValueError, match="GOOGLE_CLOUD_PROJECT"):
        validate_live_options(
            rounds=3,
            max_requests=246,
            confirm_live=True,
            provider="vertex-ai",
            model="gemini-2.5-flash",
            api_key=None,
            google_project=None,
            cases=[{"interaction": [{"channel": "chat"}]} for _ in range(41)],
        )


def test_request_budget_caps_and_counts_each_architecture():
    budget = RequestBudget(1)
    budget.reserve("single")

    with pytest.raises(RequestBudgetExhausted):
        budget.reserve("multi")

    assert budget.started == 1
    assert budget.by_architecture == {"single": 1, "multi": 0}
    assert budget.exhaustions == 1


def test_comparison_report_checkpoint_is_atomic(tmp_path):
    report = {"status": "running", "attempts": [{"case_id": "case-1"}]}

    checkpoint_report(tmp_path, report)

    assert (tmp_path / "comparison.json").exists()
    assert not (tmp_path / "comparison.json.tmp").exists()
