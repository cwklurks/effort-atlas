"""Offline integrity gates for pilot selections and their local source rows.

All errors are content-free. GPQA skeleton hashes are pins for withheld full rows,
not hashes of the skeleton itself. No acquisition, rendering, or network calls run
here; callers receive only rows whose current bytes and content were verified.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from . import ROOT

RESTRICTED_FILES = {"gpqa_main": "restricted_local/gpqa_main.RESTRICTED.jsonl"}


def _sha(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def _canonical(value, *, source=False) -> bytes:
    # Match capabilities/acquire.py for source rows, pilot_select.py otherwise.
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=not source, allow_nan=False).encode("utf-8")


def _string(value, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a nonempty string")
    return value


def _integer(value, label: str, *, minimum=0) -> int:
    if type(value) is not int or value < minimum:
        raise ValueError(f"{label} must be an integer >= {minimum}")
    return value


def _digest(value, label: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise ValueError(f"{label} must be a SHA-256 digest")
    return value


def _relative_path(value) -> Path:
    _string(value, "source path")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ValueError("source path must be relative and cannot escape the capabilities directory")
    return path


def _safe_path(root: Path, relative) -> Path:
    path = root / _relative_path(relative)
    try:
        resolved = path.resolve()
    except (OSError, RuntimeError, ValueError):
        raise ValueError("source path cannot be resolved safely") from None
    if not resolved.is_relative_to(root):
        raise ValueError("source path escapes the capabilities directory")
    return resolved


def verify_selection(selection: dict) -> str:
    """Verify the selection digest and count/identity metadata; return its digest."""
    if not isinstance(selection, dict):
        raise ValueError("selection must be an object")
    claimed = _digest(selection.get("selection_sha256"), "selection_sha256")
    unsigned = {key: value for key, value in selection.items() if key != "selection_sha256"}
    try:
        actual = _sha(_canonical(unsigned))
    except (TypeError, ValueError, UnicodeError):
        raise ValueError("selection is not canonical JSON") from None
    if actual != claimed:
        raise ValueError("selection_sha256 does not match the selection content")
    if selection.get("schema_version") != "pilot-selection-v1":
        raise ValueError("unsupported selection schema_version")
    n = _integer(selection.get("n_per_dataset"), "selection.n_per_dataset", minimum=1)
    datasets = selection.get("datasets")
    if not isinstance(datasets, dict) or not datasets:
        raise ValueError("selection.datasets must be a nonempty object")
    for name, spec in datasets.items():
        _string(name, "dataset name")
        if not isinstance(spec, dict):
            raise ValueError("selection dataset must be an object")
        _relative_path(spec.get("file"))
        _digest(spec.get("file_sha256"), "selection file_sha256")
        _string(spec.get("source_revision"), "selection source_revision")
        split = _string(spec.get("split"), "selection split")
        if _integer(spec.get("n"), "selection dataset n", minimum=1) != n:
            raise ValueError("selection dataset n differs from n_per_dataset")
        items = spec.get("items")
        if not isinstance(items, list) or len(items) != n:
            raise ValueError("selection items count differs from declared n")
        ids, coordinates = set(), set()
        for entry in items:
            if not isinstance(entry, dict):
                raise ValueError("selection item must be an object")
            item_id = _string(entry.get("source_item_id"), "selected source_item_id")
            index = _integer(entry.get("source_row_index"), "selected source_row_index")
            if entry.get("split") != split:
                raise ValueError("selected split differs from the dataset split")
            if item_id in ids or (split, index) in coordinates:
                raise ValueError("duplicate selected source_item_id or split/index")
            ids.add(item_id)
            coordinates.add((split, index))
            _digest(entry.get("prompt_sha256"), "selected prompt_sha256")
            if "full_row_sha256" in entry:
                _digest(entry["full_row_sha256"], "selected full_row_sha256")
            if entry.get("stratum") is not None:
                _string(entry["stratum"], "selected stratum")
        counts = spec.get("strata_counts")
        if not isinstance(counts, dict):
            raise ValueError("selection strata_counts must be an object")
        for stratum, count in counts.items():
            _string(stratum, "selection stratum")
            _integer(count, "selection stratum count")
        observed = Counter(entry.get("stratum") or "uniform" for entry in items)
        if {key: count for key, count in counts.items() if count} != dict(observed):
            raise ValueError("selection strata_counts differ from selected items")
    return actual


def _unique_object(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("duplicate JSON key")
        out[key] = value
    return out


def _invalid_constant(_value):
    raise ValueError("nonfinite JSON value")


def _json(blob: bytes, label: str):
    try:
        return json.loads(blob, object_pairs_hook=_unique_object, parse_constant=_invalid_constant)
    except (ValueError, UnicodeError):
        # Never include a parser's document or any restricted source text.
        raise ValueError(f"{label}: invalid JSON") from None


def _read(path: Path, label: str) -> bytes:
    try:
        return path.read_bytes()
    except OSError:
        raise ValueError(f"{label}: required source file is missing or unreadable") from None


def _manifest_entries(manifest: dict, section: str) -> dict[str, dict]:
    entries = manifest.get(section)
    if not isinstance(entries, list):
        raise ValueError(f"manifest {section} must be a list")
    out = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("manifest output must be an object")
        path = str(_relative_path(entry.get("path")))
        if path in out:
            raise ValueError("manifest contains a duplicate output path")
        _digest(entry.get("sha256"), "manifest output sha256")
        _integer(entry.get("rows"), "manifest output rows")
        _integer(entry.get("bytes"), "manifest output bytes")
        out[path] = entry
    return out


def _load_rows(root: Path, relative: str, metadata: dict | None, *, selected_hash=None) -> list[dict]:
    path = _safe_path(root, relative)
    if metadata is None:
        raise ValueError("source file has no manifest output entry")
    blob = _read(path, "source")
    actual = _sha(blob)
    if selected_hash is not None and actual != selected_hash:
        raise ValueError("selection file_sha256 differs from actual source bytes")
    if actual != metadata["sha256"] or len(blob) != metadata["bytes"]:
        raise ValueError("manifest output digest or byte count differs from actual source bytes")
    # Byte newlines preserve embedded U+2028/U+2029 source text verbatim.
    rows = [_json(line, "source row") for line in blob.split(b"\n") if line.strip()]
    if not rows:
        raise ValueError("required source file contains no rows")
    if len(rows) != metadata["rows"]:
        raise ValueError("manifest output row count differs from actual source rows")
    return rows


def _index_rows(rows: list[dict], dataset: str, revision: str, *, skeleton=False) -> dict[tuple, dict]:
    indexed, ids = {}, set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("source row must be an object")
        if row.get("schema_version") != "source-item-v1":
            raise ValueError("unsupported source row schema_version")
        if row.get("dataset") != dataset or row.get("source_revision") != revision:
            raise ValueError("source dataset or revision differs from selection")
        item_id = _string(row.get("source_item_id"), "source_item_id")
        split = _string(row.get("split"), "source split")
        index = _integer(row.get("source_row_index"), "source_row_index")
        coordinate = (split, index)
        if item_id in ids or coordinate in indexed:
            raise ValueError("duplicate source_item_id or source split/index")
        ids.add(item_id)
        indexed[coordinate] = row
        _digest(row.get("full_row_sha256"), "source full_row_sha256")
        _digest(row.get("prompt_sha256"), "source prompt_sha256")
        if skeleton:
            if (row.get("prompt_text") is not None or row.get("choices") is not None
                    or row.get("grading") != {"kind": "gold_choice", "gold": None, "gold_index": None}
                    or row.get("license_policy") != "restricted_no_plaintext"):
                raise ValueError("GPQA skeleton must contain only sanitized content")
            continue
        unsigned = {key: value for key, value in row.items() if key != "full_row_sha256"}
        if _sha(_canonical(unsigned, source=True)) != row["full_row_sha256"]:
            raise ValueError("source full_row_sha256 differs from actual row content")
        if dataset == "wildbench_v2":
            conversation = row.get("conversation_input")
            if not isinstance(conversation, list) or not conversation or row.get("prompt_text") is not None:
                raise ValueError("WildBench requires source conversation_input and null prompt_text")
            prompt_hash = _sha(_canonical(conversation, source=True))
        else:
            prompt = _string(row.get("prompt_text"), "source prompt_text")
            prompt_hash = _sha(prompt.encode("utf-8"))
        if prompt_hash != row["prompt_sha256"]:
            raise ValueError("source prompt_sha256 differs from actual prompt content")
    return indexed


def _merge_restricted(skeletons: dict[tuple, dict], full: dict[tuple, dict]) -> dict[tuple, dict]:
    if skeletons.keys() != full.keys():
        raise ValueError("GPQA restricted rows do not cover every skeleton row")
    for coordinate, skeleton in skeletons.items():
        row = full[coordinate]
        if (row.get("license_policy") != "restricted_no_plaintext"
                or not isinstance(row.get("choices"), list) or len(row["choices"]) != 4
                or any(not isinstance(choice, str) or not choice.strip() for choice in row["choices"])
                or row.get("grading") != {"kind": "gold_choice", "gold": row["choices"][0], "gold_index": 0}):
            raise ValueError("GPQA restricted row is missing full source choices or grading")
        sanitized = {**row, "prompt_text": None, "choices": None,
                     "grading": {"kind": "gold_choice", "gold": None, "gold_index": None}}
        if sanitized != skeleton:
            raise ValueError("GPQA skeleton differs from the verified restricted row")
    return full


def load_selected_items(cfg: dict, selection: dict, *, cap_dir: Path | None = None) -> list[dict]:
    """Return selected, fully verified source rows; raise ValueError on mismatch.

    File paths (including symlinks) must stay inside the caller's capabilities
    directory. Only selected datasets are read; all rows in each such source file
    are checked. The selection digest and all selection metadata are always checked.
    """
    verify_selection(selection)
    try:
        wanted = cfg["pilot"]["datasets"]
        root = Path(cap_dir if cap_dir is not None else ROOT / cfg["paths"]["data"]).resolve()
    except (KeyError, TypeError, OSError, RuntimeError, ValueError):
        raise ValueError("pilot configuration requires datasets and a capabilities directory") from None
    if not isinstance(wanted, list) or not wanted or any(not isinstance(name, str) for name in wanted):
        raise ValueError("pilot.datasets must be a nonempty list of dataset names")
    if len(set(wanted)) != len(wanted):
        raise ValueError("duplicate pilot dataset")
    if any(name not in selection["datasets"] for name in wanted):
        raise ValueError("selection does not contain every requested dataset")
    manifest = _json(_read(_safe_path(root, "sources_manifest.json"), "manifest"), "manifest")
    if not isinstance(manifest, dict) or manifest.get("schema_version") != "capabilities-source-manifest-v1":
        raise ValueError("unsupported source manifest schema_version")
    outputs = _manifest_entries(manifest, "outputs")
    out = []
    for name in wanted:
        spec = selection["datasets"][name]
        relative = str(_relative_path(spec["file"]))
        rows = _load_rows(root, relative, outputs.get(relative), selected_hash=spec["file_sha256"])
        indexed = _index_rows(rows, name, spec["source_revision"], skeleton=name in RESTRICTED_FILES)
        if name in RESTRICTED_FILES:
            restricted_path = RESTRICTED_FILES[name]
            restricted_outputs = _manifest_entries(manifest, "restricted_local_outputs")
            # acquire.write_jsonl records the basename even for restricted files.
            full_rows = _load_rows(root, restricted_path, restricted_outputs.get(Path(restricted_path).name))
            full = _index_rows(full_rows, name, spec["source_revision"])
            indexed = _merge_restricted(indexed, full)
        for entry in spec["items"]:
            row = indexed.get((entry["split"], entry["source_row_index"]))
            if row is None:
                raise ValueError("selected source row is absent")
            if row["source_item_id"] != entry["source_item_id"]:
                raise ValueError("selected source_item_id differs from source row")
            if row["prompt_sha256"] != entry["prompt_sha256"]:
                raise ValueError("selected prompt_sha256 differs from verified source row")
            if "full_row_sha256" in entry and row["full_row_sha256"] != entry["full_row_sha256"]:
                raise ValueError("selected full_row_sha256 differs from verified source row")
            out.append(row)
    return out


def rendered_digest(rendered) -> str:
    """Digest ordered, content-free wrapper manifests for per-run identity."""
    return _sha(_canonical([item.manifest_row() for item in rendered]))
