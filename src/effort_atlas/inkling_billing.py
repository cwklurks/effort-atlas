"""Read and validate private Tinker billing reconciliation artifacts.

This adapter understands only the documented ``BillingUsageResponse`` JSON
shape.  It performs no network access, pricing, or inference from token totals
to dollars.  ``complete`` records a hash-bound human attestation made after the
documented export lag; it is not cryptographic proof from the provider.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re

from .confirmatory import sha256_json
from .inkling_accounting import BillingEvidence
from .inkling_baseline import MODEL
from .inkling_stage_contract import read_artifact


SCHEMA_VERSION = "inkling-billing-reconciliation-v1"
DEDUCTION_SCHEMA_VERSION = "inkling-account-deduction-v1"
# Tinker documents lag of "up to a few hours" without a numeric maximum.  Four
# hours is a conservative project admission buffer, not a verified hard bound.
EXPORT_LAG_BUFFER = timedelta(hours=4)
MAX_WINDOW = timedelta(days=14)
_RFC3339 = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|\+00:00)\Z"
)
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")

_RECORD_FIELDS = {
    "schema_version", "plan_sha256", "stage", "account_id", "billing_group",
    "model", "window_start", "window_end", "export_observed_at", "complete",
    "billing_scope", "raw_export", "account_deduction", "attestation",
}
_ATTESTATION_FIELDS = {
    "reviewed_by", "reviewed_at", "reviewed_raw_export",
    "reviewed_account_deduction", "no_unrelated_usage",
}
_DEDUCTION_FIELDS = {
    "schema_version", "plan_sha256", "stage", "account_sha256",
    "billing_group_sha256", "model", "window_start", "window_end",
    "raw_export_sha256", "deduction_usd", "statement_artifacts",
}
_EVENT_REQUIRED_FIELDS = {
    "bucket_start", "bucket_end", "base_model", "user_id", "session_id",
    "project_id", "event_info",
}
_EVENT_ALLOWED_FIELDS = _EVENT_REQUIRED_FIELDS | {"user_name"}


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON number is forbidden: {value}")


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key")
        result[key] = value
    return result


def _load_json(data: bytes, label: str) -> dict:
    try:
        value = json.loads(
            data,
            parse_float=Decimal,
            parse_constant=_reject_constant,
            object_pairs_hook=_unique_object,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, TypeError):
        raise ValueError(f"malformed {label} JSON") from None
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def _exact_object(value: object, fields: set[str], label: str) -> dict:
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError(f"{label} fields are missing or unexpected")
    return value


def _text(value: object, label: str) -> str:
    if (not isinstance(value, str) or not value.strip() or len(value) > 512
            or any(ord(char) < 32 or ord(char) == 127 for char in value)):
        raise ValueError(f"invalid {label}")
    return value


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _hash(value: object, label: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise ValueError(f"invalid {label}")
    return value


def _timestamp(value: object, label: str, *, whole_hour: bool = False) -> datetime:
    if not isinstance(value, str) or _RFC3339.fullmatch(value) is None:
        raise ValueError(f"invalid {label}")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError(f"invalid {label}") from None
    if parsed.utcoffset() != timedelta(0):
        raise ValueError(f"{label} must be UTC")
    parsed = parsed.astimezone(timezone.utc)
    if whole_hour and (parsed.minute or parsed.second or parsed.microsecond):
        raise ValueError(f"{label} must be aligned to a UTC hour")
    return parsed


def _positive_integer(value: object, label: str) -> int:
    if type(value) is not int or value <= 0:
        raise ValueError(f"invalid {label}")
    return value


def _positive_money(value: object) -> Decimal:
    if type(value) is int:
        result = Decimal(value)
    elif isinstance(value, Decimal):
        result = value
    else:
        raise ValueError("account deduction must be a JSON number")
    if not result.is_finite() or result <= 0:
        raise ValueError("account deduction must be finite and positive")
    return result


def _scope(record: dict) -> tuple[str, str, tuple[str, ...]]:
    scope = _exact_object(
        record["billing_scope"], {"user_id", "project_id", "session_ids"},
        "billing scope",
    )
    user_id = _text(scope["user_id"], "billing user id")
    project_id = _text(scope["project_id"], "billing project id")
    session_values = scope["session_ids"]
    if not isinstance(session_values, list) or not session_values:
        raise ValueError("billing scope needs at least one session")
    sessions = tuple(_text(value, "billing session id") for value in session_values)
    if len(sessions) != len(set(sessions)) or list(sessions) != sorted(sessions):
        raise ValueError("billing session ids must be unique and sorted")
    return user_id, project_id, sessions


def _validate_sessions(value: object, expected: tuple[str, ...]) -> None:
    if not isinstance(value, dict) or set(value) != set(expected):
        raise ValueError("session side table does not match the dedicated billing scope")
    for session_id, session in value.items():
        _text(session_id, "session side-table id")
        if not isinstance(session, dict) or not set(session).issubset({"user_metadata"}):
            raise ValueError("malformed session side-table row")
        metadata = session.get("user_metadata")
        if metadata is not None and (
            not isinstance(metadata, dict)
            or any(not isinstance(key, str) or not isinstance(item, str)
                   for key, item in metadata.items())
        ):
            raise ValueError("malformed session user metadata")


def _raw_totals(
    raw: dict,
    *,
    model: str,
    window_start: datetime,
    window_end: datetime,
    user_id: str,
    project_id: str,
    session_ids: tuple[str, ...],
) -> tuple[int, int]:
    # The current official response has no cursor.  Exact top-level keys make a
    # later paginated or otherwise changed shape fail closed instead of silently
    # treating one page as a complete export.
    _exact_object(raw, {"data", "sessions"}, "billing export")
    _validate_sessions(raw["sessions"], session_ids)
    events = raw["data"]
    if not isinstance(events, list) or not events:
        raise ValueError("billing export contains no usage")

    prompt_tokens = completion_tokens = 0
    observed_sessions = set()
    seen = set()
    for event in events:
        if (not isinstance(event, dict)
                or not _EVENT_REQUIRED_FIELDS.issubset(event)
                or not set(event).issubset(_EVENT_ALLOWED_FIELDS)):
            raise ValueError("malformed billing event envelope")
        if event["base_model"] != model:
            raise ValueError("billing export contains usage for another model")
        if event["user_id"] != user_id or event["project_id"] != project_id:
            raise ValueError("billing export contains usage outside the dedicated group")
        if event["session_id"] not in session_ids:
            raise ValueError("billing export contains an unapproved session")
        observed_sessions.add(event["session_id"])
        if "user_name" in event and event["user_name"] is not None:
            _text(event["user_name"], "billing user name")

        bucket_start = _timestamp(event["bucket_start"], "bucket start", whole_hour=True)
        bucket_end = _timestamp(event["bucket_end"], "bucket end", whole_hour=True)
        if (bucket_end - bucket_start != timedelta(hours=1)
                or bucket_start < window_start or bucket_end > window_end):
            raise ValueError("billing event is outside the exact hourly window")

        info = event["event_info"]
        if not isinstance(info, dict):
            raise ValueError("malformed billing event information")
        event_type = info.get("type")
        if event_type == "sampling_prefill":
            _exact_object(info, {"type", "cached", "token_count"}, "prefill event")
            if type(info["cached"]) is not bool:
                raise ValueError("malformed cached-prefill flag")
            if info["cached"]:
                raise ValueError("cached prefill requires a separately approved rate class")
            discriminator = (event_type, False)
        elif event_type == "sampling_sample":
            _exact_object(info, {"type", "token_count"}, "sample event")
            discriminator = (event_type, None)
        else:
            raise ValueError("billing export contains unsupported non-sampling usage")
        token_count = _positive_integer(info["token_count"], "billing token count")
        bucket_key = (
            bucket_start, bucket_end, event["base_model"], event["user_id"],
            event["session_id"], event["project_id"], discriminator,
        )
        if bucket_key in seen:
            raise ValueError("duplicate hourly billing bucket")
        seen.add(bucket_key)
        if event_type == "sampling_prefill":
            prompt_tokens += token_count
        else:
            completion_tokens += token_count

    if observed_sessions != set(session_ids):
        raise ValueError("billing scope includes a session with no usage row")
    if not prompt_tokens or not completion_tokens:
        raise ValueError("billing export lacks complete sampling token classes")
    return prompt_tokens, completion_tokens


def _deduction(
    root: Path,
    value: dict,
    *,
    record: dict,
    account_sha256: str,
    billing_group_sha256: str,
) -> tuple[Decimal, tuple[str, ...]]:
    _exact_object(value, _DEDUCTION_FIELDS, "account deduction")
    expected = {
        "schema_version": DEDUCTION_SCHEMA_VERSION,
        "plan_sha256": record["plan_sha256"],
        "stage": record["stage"],
        "account_sha256": account_sha256,
        "billing_group_sha256": billing_group_sha256,
        "model": record["model"],
        "raw_export_sha256": record["raw_export"]["sha256"],
    }
    if any(value[key] != expected_value for key, expected_value in expected.items()):
        raise ValueError("account deduction identity does not match reconciliation")
    if (_timestamp(value["window_start"], "deduction window start", whole_hour=True)
            != _timestamp(record["window_start"], "window start", whole_hour=True)
            or _timestamp(value["window_end"], "deduction window end", whole_hour=True)
            != _timestamp(record["window_end"], "window end", whole_hour=True)):
        raise ValueError("account deduction window does not match reconciliation")
    _hash(value["account_sha256"], "deduction account hash")
    _hash(value["billing_group_sha256"], "deduction billing-group hash")
    _hash(value["raw_export_sha256"], "deduction raw-export hash")

    specs = value["statement_artifacts"]
    if not isinstance(specs, list) or not specs:
        raise ValueError("at least one account-statement artifact is required")
    if any(not isinstance(spec, dict) for spec in specs):
        raise ValueError("malformed account-statement artifact reference")
    paths = []
    hashes = []
    for spec in specs:
        read_artifact(root, spec)
        paths.append(spec["path"])
        hashes.append(_hash(spec["sha256"], "account-statement hash"))
    if paths != sorted(paths) or len(paths) != len(set(paths)):
        raise ValueError("account-statement artifacts must be unique and sorted")
    if len(hashes) != len(set(hashes)):
        raise ValueError("account-statement artifacts must have distinct contents")
    return _positive_money(value["deduction_usd"]), tuple(hashes)


def read_billing_evidence(root: Path, record: dict) -> BillingEvidence:
    """Return hash-bound billing evidence derived only from local artifacts.

    The human attestation establishes that the delayed export and account
    statement were reviewed together.  The adapter independently checks their
    bytes, identities, official JSON structure, attribution, and raw token sums;
    it does not verify the human's reading of the account statement.
    """
    root = Path(root)
    now = datetime.now(timezone.utc)
    _exact_object(record, _RECORD_FIELDS, "billing reconciliation")
    if record["schema_version"] != SCHEMA_VERSION:
        raise ValueError("unsupported billing reconciliation schema")
    _hash(record["plan_sha256"], "plan hash")
    if record["stage"] not in {"medium", "max"}:
        raise ValueError("invalid Inkling stage")
    account_id = _text(record["account_id"], "account identity")
    billing_group = _text(record["billing_group"], "billing-group identity")
    if record["model"] != MODEL:
        raise ValueError("billing reconciliation model mismatch")
    if record["complete"] is not True:
        raise ValueError("billing export lacks a complete human attestation")

    window_start = _timestamp(record["window_start"], "window start", whole_hour=True)
    window_end = _timestamp(record["window_end"], "window end", whole_hour=True)
    if not timedelta(0) < window_end - window_start <= MAX_WINDOW:
        raise ValueError("billing window must be positive and at most 14 days")
    if window_end > now:
        raise ValueError("billing window has not ended")
    observed = _timestamp(record["export_observed_at"], "export observation time")
    if observed > now:
        raise ValueError("billing export observation cannot be in the future")
    if observed < window_end + EXPORT_LAG_BUFFER:
        raise ValueError("billing export was observed before the admission lag elapsed")

    attestation = _exact_object(record["attestation"], _ATTESTATION_FIELDS, "attestation")
    _text(attestation["reviewed_by"], "billing reviewer")
    reviewed = _timestamp(attestation["reviewed_at"], "billing review time")
    if reviewed > now:
        raise ValueError("billing review cannot be in the future")
    if reviewed < observed or any(
        attestation[field] is not True for field in (
            "reviewed_raw_export", "reviewed_account_deduction", "no_unrelated_usage",
        )
    ):
        raise ValueError("billing artifacts lack the required human review attestation")

    user_id, project_id, session_ids = _scope(record)
    raw_bytes = read_artifact(root, record["raw_export"])
    deduction_bytes = read_artifact(root, record["account_deduction"])
    raw_sha256 = _hash(record["raw_export"]["sha256"], "raw-export hash")
    deduction_sha256 = _hash(
        record["account_deduction"]["sha256"], "account-deduction hash",
    )
    if raw_sha256 == deduction_sha256:
        raise ValueError("raw export and account deduction must be distinct artifacts")

    prompt_tokens, completion_tokens = _raw_totals(
        _load_json(raw_bytes, "billing export"),
        model=record["model"],
        window_start=window_start,
        window_end=window_end,
        user_id=user_id,
        project_id=project_id,
        session_ids=session_ids,
    )
    account_sha256 = _sha256_text(account_id)
    billing_group_sha256 = _sha256_text(billing_group)
    deduction_usd, statement_hashes = _deduction(
        root,
        _load_json(deduction_bytes, "account deduction"),
        record=record,
        account_sha256=account_sha256,
        billing_group_sha256=billing_group_sha256,
    )
    source_hashes = (raw_sha256, deduction_sha256, *statement_hashes)
    if len(source_hashes) != len(set(source_hashes)):
        raise ValueError("billing evidence artifacts must have distinct contents")

    return BillingEvidence(
        account_sha256=account_sha256,
        billing_group_sha256=billing_group_sha256,
        model=record["model"],
        window_start=window_start,
        window_end=window_end,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        account_deduction_usd=deduction_usd,
        manifest_sha256=sha256_json(record),
        source_sha256s=source_hashes,
        complete=True,
    )
