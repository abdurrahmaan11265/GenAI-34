"""
GenAI eval harness for Lexis (PEOS, docs/prompts/peos.md).

Runs each implemented prompt task against a fixed golden dataset, scores the
outputs with deterministic metrics mapped to PEOS targets, and prints a
scorecard. Used for the run -> evaluate -> analyze -> revise loop.

Usage (from backend/):
    python -m evals.run_evals                 # all tasks
    python -m evals.run_evals assessment_evaluator learning_dna_generator

Note: makes real Gemini calls. Ingestion tasks use LLMExtractor (5s/call
proactive rate-limit). Assessment tasks use AssessmentLLM.
"""
from __future__ import annotations

import os
import sys
import json
import asyncio
import statistics
from datetime import datetime, timezone
from typing import Dict, List

from evals.scorers import grounded, fuzzy_match, pct

GOLDEN_DIR = os.path.join(os.path.dirname(__file__), "golden")

# PEOS metric targets (percentages). Keys are "<metric>" per task.
TARGETS = {
    "concept_extraction": {"concept_purity": 98.0, "hallucination_rate": 0.0, "recall": 80.0, "difficulty_valid": 100.0, "schema_valid": 99.0},
    "relationship_extraction": {"accuracy": 95.0, "confidence_valid": 100.0},
    "merge_resolution": {"output_valid": 100.0, "name_reasonable": 90.0},
    "assessment_question_generator": {"schema_valid": 99.0, "mcq_structural": 100.0, "concept_grounded": 98.0, "has_explanation": 90.0, "difficulty_echo": 95.0},
    "assessment_evaluator": {"exact_agreement": 90.0, "binary_agreement": 90.0, "score_sane": 90.0},
    "learning_dna_generator": {"evidence_coverage": 95.0, "unsupported_claims": 0.0, "strength_grounding": 90.0, "weakness_grounding": 90.0},
}

# Lower-is-better metrics (target is a ceiling).
LOWER_IS_BETTER = {"hallucination_rate", "unsupported_claims"}


def _load(task_file: str) -> dict:
    with open(os.path.join(GOLDEN_DIR, task_file), encoding="utf-8") as f:
        return json.load(f)


def _avg(xs: List[float]) -> float:
    return round(statistics.mean(xs), 1) if xs else 0.0


# ---------------------------------------------------------------------------
# Ingestion tasks (LLMExtractor — synchronous)
# ---------------------------------------------------------------------------

def eval_concept_extraction(extractor) -> Dict[str, float]:
    data = _load("concept_extraction.json")
    purity, halluc, recall, diff_ok, schema_ok = [], [], [], [], []
    for s in data["samples"]:
        try:
            res = extractor.extract_concepts(s["text"])
            schema_ok.append(1.0)
        except Exception as e:  # noqa: BLE001
            print(f"  [{s['id']}] FAILED: {e}")
            schema_ok.append(0.0)
            continue
        names = [c.name for c in res.concepts]
        g = [grounded(n, s["text"]) for n in names]
        purity.append(pct(sum(g), len(g)) if g else 0.0)
        halluc.append(pct(len(g) - sum(g), len(g)) if g else 0.0)
        found = sum(1 for gc in s["gold_concepts"] if fuzzy_match(gc, names))
        recall.append(pct(found, len(s["gold_concepts"])))
        diff_ok.append(pct(sum(1 <= c.difficulty <= 5 for c in res.concepts), len(res.concepts)) if res.concepts else 0.0)
        print(f"  [{s['id']}] extracted={names}")
    return {"concept_purity": _avg(purity), "hallucination_rate": _avg(halluc),
            "recall": _avg(recall), "difficulty_valid": _avg(diff_ok),
            "schema_valid": pct(sum(schema_ok), len(schema_ok))}


def eval_relationship_extraction(extractor) -> Dict[str, float]:
    data = _load("relationship_extraction.json")
    correct, conf_ok = [], []
    for s in data["samples"]:
        try:
            rel = extractor.extract_relationship(s["text"], s["a"], s["b"])
        except Exception as e:  # noqa: BLE001
            print(f"  [{s['id']}] FAILED: {e}")
            correct.append(0.0); conf_ok.append(0.0); continue
        ok = rel.relationship_type == s["gold"]
        correct.append(100.0 if ok else 0.0)
        conf_ok.append(100.0 if 0.0 <= rel.confidence <= 1.0 else 0.0)
        print(f"  [{s['id']}] pred={rel.relationship_type} gold={s['gold']} conf={rel.confidence} {'OK' if ok else 'MISS'}")
    return {"accuracy": _avg(correct), "confidence_valid": _avg(conf_ok)}


def eval_merge_resolution(extractor) -> Dict[str, float]:
    data = _load("merge_resolution.json")
    valid, reasonable = [], []
    for s in data["samples"]:
        try:
            m = extractor.resolve_merge(s["candidates"])
        except Exception as e:  # noqa: BLE001
            print(f"  [{s['id']}] FAILED: {e}")
            valid.append(0.0); reasonable.append(0.0); continue
        ok = bool(m.canonical_name) and bool(m.canonical_summary) and 1 <= m.difficulty <= 5
        valid.append(100.0 if ok else 0.0)
        reasonable.append(100.0 if s["gold_canonical_keyword"].lower() in m.canonical_name.lower() else 0.0)
        print(f"  [{s['id']}] canonical={m.canonical_name!r}")
    return {"output_valid": _avg(valid), "name_reasonable": _avg(reasonable)}


# ---------------------------------------------------------------------------
# Assessment tasks (AssessmentLLM — async)
# ---------------------------------------------------------------------------

async def eval_assessment_question(allm) -> Dict[str, float]:
    data = _load("assessment_question.json")
    schema_ok, structural, grounded_q, has_expl, diff_echo = [], [], [], [], []
    for s in data["samples"]:
        try:
            out = await allm.generate_question(s["concept_name"], s["concept_summary"],
                                               s["difficulty"], s["bloom_level"], s["question_type"])
            schema_ok.append(100.0)
        except Exception as e:  # noqa: BLE001
            print(f"  [{s['id']}] FAILED: {e}"); schema_ok.append(0.0); continue
        if s["question_type"] == "MCQ":
            opts = out.options or []
            ok = (len(opts) == 4 and isinstance(out.correct_option, int)
                  and 0 <= out.correct_option < 4
                  and out.expected_answer.strip().lower() == opts[out.correct_option].strip().lower())
            structural.append(100.0 if ok else 0.0)
        else:
            structural.append(100.0 if (not out.options and out.expected_answer.strip()) else 0.0)
        grounded_q.append(100.0 if grounded(s["concept_name"], out.question, " ".join(out.options or []), out.expected_answer) else 0.0)
        has_expl.append(100.0 if out.explanation.strip() else 0.0)
        diff_echo.append(100.0 if out.difficulty.strip().lower() == s["difficulty"].lower() else 0.0)
        print(f"  [{s['id']}] {s['question_type']} grounded={grounded_q[-1]==100.0} Q={out.question[:70]!r}")
    return {"schema_valid": _avg(schema_ok), "mcq_structural": _avg(structural),
            "concept_grounded": _avg(grounded_q), "has_explanation": _avg(has_expl),
            "difficulty_echo": _avg(diff_echo)}


async def eval_assessment_evaluator(allm) -> Dict[str, float]:
    data = _load("assessment_evaluator.json")
    exact, binary, sane = [], [], []
    for s in data["samples"]:
        try:
            ev = await allm.evaluate_answer(s["concept"], s["question"], s["expected_answer"], s["student_answer"])
        except Exception as e:  # noqa: BLE001
            print(f"  [{s['id']}] FAILED: {e}")
            exact.append(0.0); binary.append(0.0); sane.append(0.0); continue
        gold = s["gold_label"]
        exact.append(100.0 if ev.correctness == gold else 0.0)
        binary.append(100.0 if (ev.correctness == "correct") == (gold == "correct") else 0.0)
        if gold == "correct":
            ok = ev.score >= 0.6
        elif gold == "incorrect":
            ok = ev.score <= 0.4
        else:
            ok = 0.2 <= ev.score <= 0.8
        sane.append(100.0 if ok else 0.0)
        print(f"  [{s['id']}] pred={ev.correctness} gold={gold} score={ev.score}")
    return {"exact_agreement": _avg(exact), "binary_agreement": _avg(binary), "score_sane": _avg(sane)}


async def eval_learning_dna(allm) -> Dict[str, float]:
    data = _load("learning_dna.json")
    coverage, unsupported, s_ground, w_ground = [], [], [], []
    for s in data["samples"]:
        try:
            out = await allm.generate_dna(s["book_title"], s["results"], s["confidence_summary"])
        except Exception as e:  # noqa: BLE001
            print(f"  [{s['id']}] FAILED: {e}"); continue
        items = []
        items += [(i.area, i.evidence) for i in out.strengths]
        items += [(i.area, i.evidence) for i in out.weaknesses]
        items += [(i.area, i.reason) for i in out.recommended_focus_areas]
        have = [bool(ev and ev.strip()) for _, ev in items]
        coverage.append(pct(sum(have), len(have)) if have else 0.0)
        unsupported.append(pct(len(have) - sum(have), len(have)) if have else 0.0)
        s_areas = [i.area for i in out.strengths]
        w_areas = [i.area for i in out.weaknesses]
        sg = all(any(fuzzy_match(k, s_areas) for k in [kw]) for kw in s["expected_strength_keywords"])
        wg = all(any(fuzzy_match(k, w_areas) for k in [kw]) for kw in s["expected_weakness_keywords"])
        s_ground.append(100.0 if sg else 0.0)
        w_ground.append(100.0 if wg else 0.0)
        print(f"  [{s['id']}] strengths={s_areas} weaknesses={w_areas}")
    return {"evidence_coverage": _avg(coverage), "unsupported_claims": _avg(unsupported),
            "strength_grounding": _avg(s_ground), "weakness_grounding": _avg(w_ground)}


# ---------------------------------------------------------------------------
# Orchestration + scorecard
# ---------------------------------------------------------------------------

def _print_scorecard(results: Dict[str, Dict[str, float]]):
    print("\n" + "=" * 72)
    print("GENAI EVAL SCORECARD (vs PEOS targets)")
    print("=" * 72)
    overall_pass = True
    for task, metrics in results.items():
        print(f"\n### {task}")
        for metric, value in metrics.items():
            target = TARGETS.get(task, {}).get(metric)
            if target is None:
                print(f"   {metric:22} {value:6.1f}")
                continue
            if metric in LOWER_IS_BETTER:
                ok = value <= target
                comp = f"<= {target}"
            else:
                ok = value >= target
                comp = f">= {target}"
            overall_pass = overall_pass and ok
            print(f"   {metric:22} {value:6.1f}   target {comp:8} {'PASS' if ok else 'FAIL'}")
    print("\n" + "=" * 72)
    print(f"OVERALL: {'ALL TARGETS MET' if overall_pass else 'SOME TARGETS MISSED'}")
    print("=" * 72)


async def main(tasks: List[str]):
    from app.services.llm_extractor import LLMExtractor
    from app.services.assessment_llm import AssessmentLLM

    results: Dict[str, Dict[str, float]] = {}
    extractor = None
    allm = None

    def get_extractor():
        nonlocal extractor
        if extractor is None:
            extractor = LLMExtractor()
        return extractor

    def get_allm():
        nonlocal allm
        if allm is None:
            allm = AssessmentLLM()
        return allm

    plan = [
        ("concept_extraction", lambda: eval_concept_extraction(get_extractor())),
        ("relationship_extraction", lambda: eval_relationship_extraction(get_extractor())),
        ("merge_resolution", lambda: eval_merge_resolution(get_extractor())),
        ("assessment_question_generator", lambda: eval_assessment_question(get_allm())),
        ("assessment_evaluator", lambda: eval_assessment_evaluator(get_allm())),
        ("learning_dna_generator", lambda: eval_learning_dna(get_allm())),
    ]
    for name, fn in plan:
        if tasks and name not in tasks:
            continue
        print(f"\n>>> Evaluating: {name}")
        out = fn()
        results[name] = await out if asyncio.iscoroutine(out) else out

    _print_scorecard(results)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "targets": {k: v for k, v in TARGETS.items() if not tasks or k in tasks},
        "results": results,
    }
    out_path = os.path.join(os.path.dirname(__file__), "last_report.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\nReport written to {out_path}")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))
