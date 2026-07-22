"""Read-only OpenRouter pricing, endpoint, and credit status.

This module never makes a completion request. It reads the API key name and
base URL from the selected config, then queries the public model catalog and
the authenticated credits endpoint.
"""

from __future__ import annotations

import argparse
import json
import os
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from dotenv import load_dotenv

from . import ROOT, load_config


def _json_get(url: str, api_key: str | None = None) -> dict:
    headers = {"Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = Request(url, headers=headers)
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--config",
        default="config_openrouter.yaml",
        help="OpenRouter configuration file",
    )
    args = ap.parse_args()

    cfg = load_config(args.config)
    pcfg = cfg["provider"]
    load_dotenv(
        ROOT / ".env",
        override=bool(pcfg.get("env_file_override", False)),
    )
    api_key = os.environ.get(pcfg["api_key_env"])
    if not api_key:
        raise SystemExit(f"Set {pcfg['api_key_env']} in .env before continuing.")

    base_url = (
        os.environ.get(pcfg["base_url_env"])
        or pcfg["default_base_url"]
    ).rstrip("/")
    model = pcfg["model"]
    author, slug = model.split("/", 1)

    endpoint_data = _json_get(
        f"{base_url}/models/{author}/{slug}/endpoints"
    )["data"]
    endpoints = endpoint_data.get("endpoints", [])
    if not endpoints:
        raise SystemExit(f"OpenRouter reports no active endpoints for {model}.")

    print(f"model={model}")
    for endpoint in endpoints:
        prompt_per_m = float(endpoint["pricing"]["prompt"]) * 1_000_000
        completion_per_m = (
            float(endpoint["pricing"]["completion"]) * 1_000_000
        )
        print(
            f"endpoint={endpoint['provider_name']} "
            f"quantization={endpoint.get('quantization', 'unknown')} "
            f"input=${prompt_per_m:.2f}/M "
            f"output=${completion_per_m:.2f}/M"
        )

    reserve = float(cfg["budget"]["reserve_margin_usd"])
    try:
        credits = _json_get(f"{base_url}/credits", api_key)["data"]
    except HTTPError as err:
        if err.code not in {401, 403}:
            raise
        try:
            key_status = _json_get(f"{base_url}/key", api_key)["data"]
        except HTTPError as key_err:
            if key_err.code == 401:
                raise SystemExit(
                    f"{pcfg['api_key_env']} was rejected by OpenRouter "
                    "with HTTP 401. Replace the invalid or revoked key."
                ) from key_err
            raise
        limit = key_status.get("limit")
        remaining = key_status.get("limit_remaining")
        print("account_balance=unavailable_with_non_management_key")
        print(f"key_usage=${float(key_status['usage']):.6f}")
        print(f"key_limit={'none' if limit is None else f'${float(limit):.6f}'}")
        print(
            "key_limit_remaining="
            f"{'unknown' if remaining is None else f'${float(remaining):.6f}'}"
        )
        print(f"reserve_margin=${reserve:.6f}")
        if remaining is not None:
            ceiling = max(0.0, float(remaining) - reserve)
            print(f"key_limit_based_ceiling=${ceiling:.6f}")
        return

    total_credits = float(credits["total_credits"])
    total_usage = float(credits["total_usage"])
    available = total_credits - total_usage
    ceiling = max(0.0, available - reserve)
    print(f"total_credits=${total_credits:.6f}")
    print(f"total_usage=${total_usage:.6f}")
    print(f"available_balance=${available:.6f}")
    print(f"reserve_margin=${reserve:.6f}")
    print(f"replication_spend_ceiling=${ceiling:.6f}")


if __name__ == "__main__":
    main()
