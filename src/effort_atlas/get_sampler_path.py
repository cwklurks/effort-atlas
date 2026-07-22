"""Get a tinker:// sampler path for base Inkling (fallback for the OAI endpoint).

Only needed if the OpenAI-compatible endpoint rejects the plain Tinker ID
("thinkingmachines/Inkling") as a model name. The endpoint officially takes
sampler checkpoint paths, so this creates one:

  1. Create a LoRA training client on the base model (rank 8, never trained).
     A freshly initialized LoRA leaves outputs identical to the base model,
     so sampling from this checkpoint IS sampling from base Inkling.
  2. Save weights for sampling and print the tinker:// path.

Costs nothing to train (zero steps); storage for a rank-8 LoRA is negligible
($0.10/GB/month, and this is far under a GB).

Usage:
    pip install tinker
    export TINKER_API_KEY=...   # or put it in .env
    python -m effort_atlas.get_sampler_path

⚠ If the SDK method names have drifted from this (written against July 2026
docs), check https://tinker-docs.thinkingmachines.ai/tinker/quickstart/ —
the two calls below mirror its quickstart.
"""

from __future__ import annotations

import os
from pathlib import Path

BASE_MODEL = "thinkingmachines/Inkling"


def main() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv(Path(__file__).resolve().parents[2] / ".env")
    except ImportError:
        pass

    if not os.environ.get("TINKER_API_KEY"):
        raise SystemExit("Set TINKER_API_KEY first (env or .env).")

    import tinker

    service_client = tinker.ServiceClient()
    print(f"Creating LoRA training client on {BASE_MODEL} (rank 8, no training)…")
    training_client = service_client.create_lora_training_client(
        base_model=BASE_MODEL, rank=8
    )
    print("Saving sampler weights (step 0 = identical to base model)…")
    response = training_client.save_weights_for_sampler(name="base-v0").result()
    print("\nSampler path (paste into config.yaml as provider.model):\n")
    print(f"  {response.path}")


if __name__ == "__main__":
    main()
