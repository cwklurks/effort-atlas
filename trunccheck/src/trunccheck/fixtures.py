"""Fixture generation, loading, and validation."""

from __future__ import annotations

from collections import Counter, defaultdict
import gzip
import hashlib
import io
import json
from pathlib import Path
import random
from typing import Any, BinaryIO, Iterable, Mapping, Sequence

from .schemas import Fixture, SCHEMA_VERSION

DEFAULT_SEED = 1729
REAL_CORPUS_SHA256 = "b84adb85eccd6b628829cdadb71c29fa25eb4dc0a37d387f554464b312d96f43"
REAL_CORPUS_COUNT = 195
REAL_CORPUS_KIND_COUNTS = {"truncated": 131, "control_correct": 64}
SYNTHETIC_SHAPES = (
    "mid_box",
    "mid_multiple_choice_enumeration",
    "post_final_answer",
    "degeneration_loop_plausible_number",
    "mid_latex_expression",
)


class CorpusValidationError(ValueError):
    """A corpus is unreadable or does not satisfy declared validation values."""


def _read_bytes(path: str | Path) -> bytes:
    try:
        return Path(path).read_bytes()
    except OSError as exc:
        raise CorpusValidationError(f"cannot read corpus {path}: {exc}") from exc


def _decompressed_lines(path: str | Path, raw: bytes) -> list[bytes]:
    try:
        if str(path).lower().endswith(".gz"):
            data = gzip.decompress(raw)
        else:
            data = raw
    except (OSError, EOFError) as exc:
        raise CorpusValidationError(f"invalid gzip corpus {path}: {exc}") from exc
    lines = data.splitlines()
    if not lines and data:
        raise CorpusValidationError("corpus has no JSONL records")
    return lines


def _parse_lines(lines: Sequence[bytes]) -> list[tuple[Mapping[str, Any], bytes]]:
    parsed: list[tuple[Mapping[str, Any], bytes]] = []
    for line_number, line in enumerate(lines, 1):
        if not line.strip():
            raise CorpusValidationError(f"blank JSONL line at {line_number}")
        try:
            value = json.loads(line.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise CorpusValidationError(f"invalid JSON at line {line_number}: {exc}") from exc
        if not isinstance(value, Mapping):
            raise CorpusValidationError(f"JSONL line {line_number} must be an object")
        parsed.append((value, line))
    return parsed


def _fixture_from_record(
    record: Mapping[str, Any], raw_line: bytes, ordinal: int, *, source: str
) -> Fixture:
    # Native trunccheck schema receives strict field validation.
    if "fixture_id" in record and "stratum" in record:
        try:
            return Fixture.from_dict(record)
        except (TypeError, ValueError) as exc:
            raise CorpusValidationError(str(exc)) from exc

    required = {"kind", "text"}
    missing = required - record.keys()
    if missing:
        raise CorpusValidationError(f"missing required fields: {sorted(missing)}")
    kind = record["kind"]
    if kind not in {"truncated", "control_correct"}:
        raise CorpusValidationError(f"invalid kind: {kind!r}")
    if not isinstance(record["text"], str):
        raise CorpusValidationError("text must be a string")
    gold = record.get("gold_answer")
    if gold is not None and not isinstance(gold, str):
        # Source corpora sometimes encode numeric gold answers. Preserve them
        # without making implicit correctness judgments.
        gold = str(gold)
    digest = hashlib.sha256(raw_line).hexdigest()
    fixture_id = f"{source}-{kind}-{digest[:16]}-{ordinal:03d}"
    known = {"kind", "text", "gold_answer"}
    return Fixture(
        fixture_id=fixture_id,
        kind=kind,
        stratum="real_truncated" if kind == "truncated" else "finished_control",
        text=record["text"],
        gold_answer=gold,
        truncated=kind == "truncated",
        metadata={key: value for key, value in record.items() if key not in known},
    )


def load_jsonl_fixtures(
    path: str | Path,
    *,
    expected_sha256: str | None = None,
    expected_count: int | None = None,
    expected_kind_counts: Mapping[str, int] | None = None,
    source: str = "corpus",
) -> tuple[Fixture, ...]:
    """Load JSONL or JSONL.GZ without dropping empty texts or duplicate rows.

    The optional SHA-256 is over the compressed file bytes (or plain file bytes
    for JSONL). Duplicate source records receive increasing ordinals in stable
    IDs; none are deduplicated.
    """

    if not isinstance(source, str) or not source:
        raise ValueError("source must be a non-empty string")
    raw = _read_bytes(path)
    actual_hash = hashlib.sha256(raw).hexdigest()
    if expected_sha256 is not None:
        if len(expected_sha256) != 64 or any(c not in "0123456789abcdefABCDEF" for c in expected_sha256):
            raise ValueError("expected_sha256 must be 64 hexadecimal characters")
        if actual_hash.lower() != expected_sha256.lower():
            raise CorpusValidationError(
                f"SHA-256 mismatch: expected {expected_sha256.lower()}, got {actual_hash}"
            )
    records = _parse_lines(_decompressed_lines(path, raw))
    if expected_count is not None and len(records) != expected_count:
        raise CorpusValidationError(
            f"row count mismatch: expected {expected_count}, got {len(records)}"
        )
    counts = Counter(record["kind"] for record, _ in records if "kind" in record)
    if expected_kind_counts is not None:
        expected = dict(expected_kind_counts)
        if dict(counts) != expected:
            raise CorpusValidationError(f"kind counts mismatch: expected {expected}, got {dict(counts)}")

    seen: defaultdict[bytes, int] = defaultdict(int)
    fixtures: list[Fixture] = []
    for record, raw_line in records:
        seen[raw_line] += 1
        fixtures.append(_fixture_from_record(record, raw_line, seen[raw_line], source=source))
    ids = [fixture.fixture_id for fixture in fixtures]
    if len(ids) != len(set(ids)):
        raise CorpusValidationError("corpus produced duplicate fixture IDs")
    return tuple(fixtures)


def load_real_fixtures(
    path: str | Path,
    *,
    expected_sha256: str = REAL_CORPUS_SHA256,
    expected_count: int = REAL_CORPUS_COUNT,
    expected_kind_counts: Mapping[str, int] = REAL_CORPUS_KIND_COUNTS,
) -> tuple[Fixture, ...]:
    """Load and validate the fixed 195-row REAP real corpus."""

    return load_jsonl_fixtures(
        path,
        expected_sha256=expected_sha256,
        expected_count=expected_count,
        expected_kind_counts=expected_kind_counts,
        source="real",
    )


def _synthetic_text(shape: str, index: int, gold: str, rng: random.Random) -> tuple[str, str, dict[str, Any]]:
    a = rng.randint(2, 98)
    b = rng.randint(2, 98)
    stem = f"Problem {index + 1}: compute the requested value. {a} + {b} is considered in the work."
    if shape == "mid_box":
        prefix_len = max(1, len(gold) // 2)
        return f"{stem}\nTherefore the answer is \\boxed{{{gold[:prefix_len]}", "cut_mid_box", {"box_prefix_length": prefix_len}
    if shape == "mid_multiple_choice_enumeration":
        option = rng.choice(("A", "B", "C", "D"))
        return (
            f"{stem}\nOptions:\n(A) {a}\n(B) {b}\n(C) {gold}\n(D",
            "cut_mid_option",
            {"cut_option": option, "rendered_cut_option": "D"},
        )
    if shape == "post_final_answer":
        return (
            f"{stem}\nFinal answer: {gold}\nVerification begins by substituting {gold} into",
            "cut_after_correct_final_answer",
            {"final_answer_precedes_cut": True},
        )
    if shape == "degeneration_loop_plausible_number":
        repeats = rng.randint(3, 7)
        plausible = str(rng.randint(10, 999))
        loop = " ".join(["recheck the arithmetic"] * repeats)
        return (
            f"{stem}\n{loop} {plausible}",
            "token_limit_after_degeneration_loop",
            {"loop_repetitions": repeats, "plausible_terminal_number": plausible},
        )
    if shape == "mid_latex_expression":
        power = rng.randint(2, 9)
        return (
            f"{stem}\nWe obtain $x = \\frac{{{a} + \\sqrt{{{b}}}}}{{{power}",
            "cut_mid_latex_expression",
            {"expression_power": power},
        )
    raise AssertionError(f"unhandled synthetic shape: {shape}")


def generate_synthetic_fixtures(seed: int = DEFAULT_SEED) -> tuple[Fixture, ...]:
    """Generate exactly 100 fixtures, 20 for each documented truncation shape."""

    if type(seed) is not int or seed < 0:
        raise ValueError("seed must be a non-negative integer")
    rng = random.Random(seed)
    fixtures: list[Fixture] = []
    for shape in SYNTHETIC_SHAPES:
        for shape_index in range(20):
            gold = str(rng.randint(0, 999))
            text, marker, parameters = _synthetic_text(shape, shape_index, gold, rng)
            fixtures.append(
                Fixture(
                    fixture_id=f"synthetic-{seed}-{shape}-{shape_index + 1:03d}",
                    kind="truncated",
                    stratum="synthetic_truncated",
                    text=text,
                    gold_answer=gold,
                    truncated=True,
                    shape=shape,
                    seed=seed,
                    truncation_marker=marker,
                    generation_parameters={"generator_version": 1, "shape_index": shape_index, **parameters},
                )
            )
    return tuple(fixtures)


def fixtures_to_jsonl(fixtures: Iterable[Fixture]) -> bytes:
    """Serialize fixtures as canonical UTF-8 JSONL with one trailing newline."""

    lines = [
        json.dumps(fixture.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        for fixture in fixtures
    ]
    return (("\n".join(lines) + "\n") if lines else "").encode("utf-8")


def write_fixtures_jsonl(path: str | Path, fixtures: Iterable[Fixture]) -> None:
    Path(path).write_bytes(fixtures_to_jsonl(fixtures))
