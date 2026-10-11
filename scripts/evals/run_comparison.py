"""Paired offline comparison of single and multi-agent architectures."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.agent import PROMPT_VERSION, ProviderError, make_agent  # noqa: E402
from app.agents.coordinator import COORDINATOR_PROMPT_VERSION, CoordinatorAgent  # noqa: E402
from app.data_validation import load_session_seed  # noqa: E402
from app.evaluators import evaluate_case, execute_case_state, load_cases, run_case  # noqa: E402
from app.schemas import Session  # noqa: E402
from app.storage import Storage  # noqa: E402
from evals.harness import (  # noqa: E402
    exercise_faq_contamination_fixture,
    exercise_mcp_process_failures,
    multi_failure_result,
    single_agent_for_case,
)
from scripts.checks.candidate import candidate_digest  # noqa: E402

LIVE_PROVIDERS = {"gemini-api", "vertex-ai"}


class RequestBudgetExhausted(ProviderError):
    """The paired evaluation reached its configured provider request cap."""


class RequestBudget:
    def __init__(self, maximum: int) -> None:
        self.maximum = maximum
        self.started = 0
        self.by_architecture = {"single": 0, "multi": 0}
        self.exhaustions = 0

    def reserve(self, architecture: str) -> None:
        if self.started >= self.maximum:
            self.exhaustions += 1
            raise RequestBudgetExhausted("Teto de chamadas do comparativo pareado atingido.")
        self.started += 1
        self.by_architecture[architecture] += 1


class BudgetedCoordinator(CoordinatorAgent):
    def __init__(self, *args: Any, request_budget: RequestBudget, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.request_budget = request_budget

    async def _route_with_model(self, message: str) -> tuple[bool, bool]:
        self.request_budget.reserve("multi")
        return await super()._route_with_model(message)


def planned_requests(cases: list[dict[str, Any]]) -> int:
    return sum(
        sum(item.get("channel") == "chat" for item in case.get("interaction", [])) or 1
        for case in cases
    )


def checkpoint_report(out_dir: Path, report: dict[str, Any]) -> None:
    temporary = out_dir / "comparison.json.tmp"
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(out_dir / "comparison.json")


def validate_live_options(
    *,
    rounds: int,
    max_requests: int | None,
    confirm_live: bool,
    provider: str,
    model: str,
    api_key: str | None,
    google_project: str | None,
    cases: list[dict[str, Any]],
) -> tuple[int, int]:
    if rounds != 3:
        raise ValueError("Comparação live exige exatamente três rodadas completas.")
    if not confirm_live:
        raise ValueError("Comparação live pode consumir quota. Reexecute com --confirm-live.")
    if provider not in LIVE_PROVIDERS:
        raise ValueError("Provider live inválido; use gemini-api ou vertex-ai.")
    if not model.strip():
        raise ValueError("Informe um modelo Gemini não vazio.")
    if provider == "gemini-api" and not api_key:
        raise ValueError("Configure GOOGLE_API_KEY para provider gemini-api.")
    if provider == "vertex-ai" and not google_project:
        raise ValueError("Configure GOOGLE_CLOUD_PROJECT para provider vertex-ai.")
    expected = planned_requests(cases) * rounds * 2
    configured = expected if max_requests is None else max_requests
    if configured < expected:
        raise ValueError(
            f"Teto insuficiente: são necessárias pelo menos {expected} chamadas "
            "lógicas pareadas para completar as duas arquiteturas."
        )
    return expected // 2, configured


def validate_local_options(
    *, rounds: int, max_requests: int | None, cases: list[dict[str, Any]]
) -> tuple[int, int]:
    if rounds != 3:
        raise ValueError("Comparação local pareada exige exatamente três rodadas.")
    expected = planned_requests(cases) * rounds * 2
    configured = expected if max_requests is None else max_requests
    if configured < expected:
        raise ValueError(
            f"Teto local insuficiente: são necessárias pelo menos {expected} "
            "chamadas planejadas para completar as duas arquiteturas."
        )
    return expected // 2, configured


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


async def run(args: argparse.Namespace) -> int:
    with TemporaryDirectory(prefix="eventops-comparison-") as directory:
        api_key = os.getenv("GOOGLE_API_KEY") if args.mode == "live" else None
        return await compare(
            args.rounds,
            Path(directory) / "catalog.sqlite3",
            mode=args.mode,
            provider=args.provider,
            model=args.model,
            max_requests=args.max_requests,
            confirm_live=args.confirm_live,
            api_key=api_key,
            google_project=os.getenv("GOOGLE_CLOUD_PROJECT"),
            google_location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
            ollama_context_length=int(os.getenv("OLLAMA_CONTEXT_LENGTH", "4096")),
        )


async def compare(
    rounds: int,
    database: Path,
    *,
    mode: str = "offline",
    provider: str = "gemini-api",
    model: str = "gemini-3.8-flash",
    max_requests: int | None = None,
    confirm_live: bool = False,
    api_key: str | None = None,
    google_project: str | None = None,
    google_location: str = "us-central1",
    ollama_base_url: str = "http://127.0.0.1:11434",
    ollama_context_length: int = 4096,
) -> int:
    if not 1 <= rounds <= 3:
        raise ValueError("--rounds deve estar entre 1 e 3.")
    if mode not in {"offline", "live", "local"}:
        raise ValueError("--mode aceita offline, local ou live.")
    dataset = ROOT / "evals/cases.jsonl"
    cases = load_cases(dataset)
    sessions = [Session.model_validate(item) for item in load_session_seed()]
    Storage(database).seed_sessions_if_empty(load_session_seed())
    planned_per_architecture = planned_requests(cases) * rounds
    multi: CoordinatorAgent
    if mode == "live":
        planned_per_architecture, max_requests = validate_live_options(
            rounds=rounds,
            max_requests=max_requests,
            confirm_live=confirm_live,
            provider=provider,
            model=model,
            api_key=api_key,
            google_project=google_project,
            cases=cases,
        )
        assert max_requests is not None
        budget = RequestBudget(max_requests)
        vertex_ai = provider == "vertex-ai"
        single = make_agent(
            sessions,
            "live",
            model,
            api_key,
            google_vertex_ai=vertex_ai,
            google_project=google_project,
            google_location=google_location,
            before_model_callback=lambda _context, _request: budget.reserve("single"),
        )
        multi = BudgetedCoordinator(
            sessions,
            mode="live",
            model=model,
            use_mcp=True,
            database=database,
            api_key=api_key,
            vertex_ai=vertex_ai,
            google_project=google_project,
            google_location=google_location,
            request_budget=budget,
        )
    elif mode == "local":
        planned_per_architecture, max_requests = validate_local_options(
            rounds=rounds, max_requests=max_requests, cases=cases
        )
        assert max_requests is not None
        budget = RequestBudget(max_requests)
        single = make_agent(
            sessions,
            "local",
            model,
            None,
            ollama_base_url=ollama_base_url,
            ollama_model=model,
            ollama_context_length=ollama_context_length,
            before_provider_call_callback=lambda: budget.reserve("single"),
        )
        multi = BudgetedCoordinator(
            sessions,
            mode="local",
            model=model,
            use_mcp=True,
            database=database,
            ollama_base_url=ollama_base_url,
            request_budget=budget,
        )
    else:
        budget = None
        max_requests = None
        single = make_agent(sessions, "offline", "offline", None)
        multi = CoordinatorAgent(
            sessions, mode="offline", model="offline", use_mcp=True, database=database
        )
    report: dict[str, Any] = {
        "run_id": datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8],
        "candidate_sha256": candidate_digest(),
        "created_at": datetime.now(UTC).isoformat(),
        "mode": f"{mode}-paired",
        "provider": provider if mode == "live" else "ollama" if mode == "local" else "offline",
        "model": model if mode in {"live", "local"} else "offline",
        "live_authorized": mode == "live" and confirm_live,
        "max_requests_configured": max_requests,
        "planned_requests_per_architecture": planned_per_architecture,
        "planned_requests_total": planned_per_architecture * 2,
        "request_budget_scope": (
            "ADK before-model callbacks and coordinator routes before SDK-internal retries"
            if mode in {"live", "local"}
            else "offline"
        ),
        "dataset_sha256": digest(dataset),
        "catalog_sha256": digest(ROOT / "app/data/sessions.json"),
        "architectures": {
            "single": {
                "prompt_version": PROMPT_VERSION,
                "transport": "internal",
                "provider": provider
                if mode == "live"
                else "ollama"
                if mode == "local"
                else "offline",
                "model": model if mode in {"live", "local"} else "offline",
            },
            "multi": {
                "prompt_version": COORDINATOR_PROMPT_VERSION,
                "transport": "MCP stdio",
                "provider": provider
                if mode == "live"
                else "ollama"
                if mode == "local"
                else "offline",
                "model": model if mode in {"live", "local"} else "offline",
            },
        },
        "rounds_requested": rounds,
        "rounds_completed": 0,
        "status": "running",
        "passed": False,
        "mcp_process_failures": await exercise_mcp_process_failures(),
        "faq_contamination_fixture": exercise_faq_contamination_fixture(),
        "attempts": [],
    }
    out_dir = ROOT / "reports" / report["run_id"]
    out_dir.mkdir(parents=True, exist_ok=False)
    checkpoint_report(out_dir, report)
    for round_number in range(1, rounds + 1):
        for case in cases:
            for name, agent in (("single", single), ("multi", multi)):
                requests_before = budget.started if budget is not None else 0
                exhaustions_before = budget.exhaustions if budget is not None else 0
                attempt: dict[str, Any] = {
                    "round": round_number,
                    "case_id": case["id"],
                    "category": case["category"],
                    "adversarial": case["adversarial"],
                    "architecture": name,
                    "status": "running",
                    "provider_request_status": "not_started",
                }
                report["attempts"].append(attempt)
                checkpoint_report(out_dir, report)
                if name == "single":
                    case_agent = single_agent_for_case(sessions, case, single, failure_mode=mode)
                    result = await run_case(case_agent, case)
                elif case.get("category") in {"tool_failure", "model_failure"}:
                    result = multi_failure_result(str(case["category"]), mode=mode)
                else:
                    result = await run_case(agent, case)
                if budget is not None:
                    request_delta = budget.started - requests_before
                    result.trace["provider_calls"] = request_delta
                    result.trace["comparison_provider_invocations_for_attempt"] = request_delta
                    result.trace["comparison_provider_invocations"] = budget.started
                    result.trace["comparison_requests_by_architecture"] = dict(
                        budget.by_architecture
                    )
                    result.trace["comparison_budget_exhaustions"] = budget.exhaustions
                execute_case_state(case, result, sessions)
                verdict = evaluate_case(case, result)
                attempt.update(
                    {
                        "status": "completed",
                        "answer": result.answer,
                        "session_ids": result.session_ids,
                        "sources": result.sources,
                        "reservation_proposal": result.reservation_proposal,
                        "error": result.error,
                        "trace": result.trace,
                        "provider_request_status": (
                            "controlled_failure_fixture"
                            if case.get("category") in {"tool_failure", "model_failure"}
                            else "provider_invocation_recorded"
                            if budget is not None and budget.started > requests_before
                            else "budget_exhausted"
                            if budget is not None and budget.exhaustions > exhaustions_before
                            else mode
                        ),
                        "evaluation": verdict,
                    }
                )
                checkpoint_report(out_dir, report)
        report["rounds_completed"] = round_number
        checkpoint_report(out_dir, report)
    report["summary"] = [
        {
            "round": round_number,
            "architecture": architecture,
            "category": category,
            "passed": sum(
                item["evaluation"]["passed"]
                for item in report["attempts"]
                if item["round"] == round_number
                and item["architecture"] == architecture
                and item["category"] == category
            ),
            "total": sum(
                1
                for item in report["attempts"]
                if item["round"] == round_number
                and item["architecture"] == architecture
                and item["category"] == category
            ),
        }
        for round_number in range(1, rounds + 1)
        for architecture in ("single", "multi")
        for category in sorted({case["category"] for case in cases})
    ]
    report["human_review_required"] = True
    report["passed"] = (
        all(item["evaluation"]["passed"] for item in report["attempts"])
        and all(item.get("handled") for item in report["mcp_process_failures"].values())
        and report["faq_contamination_fixture"]["passed"]
        and (budget is None or budget.exhaustions == 0)
    )
    if budget is not None:
        report["provider_invocations_started"] = budget.started
        report["provider_invocations_by_architecture"] = budget.by_architecture
        report["request_budget_exhaustions"] = budget.exhaustions
    report["status"] = "passed" if report["passed"] else "failed"
    checkpoint_report(out_dir, report)
    lines = [
        f"# Comparação pareada — {report['run_id']}",
        "",
        f"Modo {report['mode']}; provider {report['provider']}; modelo {report['model']}.",
        "Single usa ferramentas internas e multi usa MCP stdio.",
        "A diferença de transporte faz parte do experimento pareado.",
        f"Chamadas planejadas: {report['planned_requests_total']} no total; "
        f"teto configurado: {report['max_requests_configured']}.",
        (
            "Alegações livres exigem revisão humana; resultado live vale apenas para "
            "o candidato/provider/modelo registrados."
            if mode == "live"
            else (
                "Avaliação local sem consumo de API; alegações livres exigem revisão humana."
                if mode == "local"
                else "Alegações livres exigem revisão humana; resultado offline não aprova "
                "qualidade live G4."
            )
        ),
        "",
        "| Rodada | Arquitetura | Categoria | Aprovados | Total |",
        "|---:|---|---|---:|---:|",
    ]
    lines.extend(
        "| {round} | {architecture} | {category} | {passed} | {total} |".format(**item)
        for item in report["summary"]
        if item["total"]
    )
    (out_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        json.dumps({"run_id": report["run_id"], "passed": report["passed"], "report": str(out_dir)})
    )
    return 0 if report["passed"] else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["offline", "local", "live"], default="offline")
    parser.add_argument(
        "--provider", choices=[*sorted(LIVE_PROVIDERS), "ollama"], default="gemini-api"
    )
    parser.add_argument("--model", default=os.getenv("EVENTOPS_AGENT_MODEL", "gemini-3.8-flash"))
    parser.add_argument("--rounds", type=int, default=1)
    parser.add_argument("--max-requests", type=int)
    parser.add_argument("--confirm-live", action="store_true")
    args = parser.parse_args()
    try:
        return asyncio.run(run(args))
    except (ValueError, OSError) as exc:
        print(json.dumps({"status": "preflight_failed", "message": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
