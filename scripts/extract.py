#!/usr/bin/env python3
"""
Runs the v3 (schema-constrained) prompt against a snippet using a given
model, and writes one <PARAM_NAME>.yaml + <PARAM_NAME>.evidence.json pair
per extracted parameter into results/<model>/.

Requires an API key for whichever provider you're calling:
  - Anthropic (Claude Opus/Fable/Sonnet):  ANTHROPIC_API_KEY
  - GLM (Zhipu direct, OpenAI-compatible): ZHIPU_API_KEY
  - GLM via OpenRouter instead:            OPENROUTER_API_KEY (+ --provider openrouter)

Usage:
    python scripts/extract.py --model claude-opus-4-8 --snippet snippets/cmo_cache_block.txt
    python scripts/extract.py --model glm-4.6 --provider zhipu --snippet snippets/csr_address_mapping.txt
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
PROMPT_PATH = ROOT / "prompts" / "v3_schema_constrained.md"
SCHEMA_PATH = ROOT / "schema" / "param_schema.json"

PROVIDER_BASE_URLS = {
    "zhipu": "https://open.bigmodel.cn/api/paas/v4/",
    "openrouter": "https://openrouter.ai/api/v1",
}
PROVIDER_ENV_VARS = {
    "zhipu": "ZHIPU_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
}


def build_prompt(snippet_path: Path) -> str:
    template = PROMPT_PATH.read_text()
    snippet = snippet_path.read_text()
    schema_json = SCHEMA_PATH.read_text()
    return template.replace("{param_schema_json}", schema_json).replace("{snippet}", snippet)


def call_anthropic(model: str, prompt: str) -> str:
    import anthropic  # pip install anthropic

    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env
    response = client.messages.create(
        model=model,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in response.content if block.type == "text")


def call_openai_compatible(model: str, prompt: str, provider: str) -> str:
    from openai import OpenAI  # pip install openai

    api_key = os.environ.get(PROVIDER_ENV_VARS[provider])
    if not api_key:
        raise SystemExit(f"set {PROVIDER_ENV_VARS[provider]} to call {provider}")

    client = OpenAI(api_key=api_key, base_url=PROVIDER_BASE_URLS[provider])
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


FENCE_RE = re.compile(r"```(?P<lang>\w+)?\n(?P<body>.*?)```", re.DOTALL)


def split_fences(raw_text: str) -> tuple[list[str], list[str]]:
    """Returns (yaml_blocks, json_blocks) found in the model's raw response."""
    yaml_blocks, json_blocks = [], []
    for m in FENCE_RE.finditer(raw_text):
        lang = (m.group("lang") or "").lower()
        body = m.group("body")
        if lang in ("yaml", "yml"):
            yaml_blocks.append(body)
        elif lang == "json":
            json_blocks.append(body)
    return yaml_blocks, json_blocks


def write_results(model_slug: str, snippet_path: Path, raw_text: str) -> None:
    out_dir = ROOT / "results" / model_slug
    out_dir.mkdir(parents=True, exist_ok=True)

    raw_path = out_dir / f"{snippet_path.stem}.raw.txt"
    raw_path.write_text(raw_text)

    yaml_blocks, json_blocks = split_fences(raw_text)
    evidence: dict = {}
    for block in json_blocks:
        try:
            evidence.update(json.loads(block))
        except json.JSONDecodeError:
            continue

    param_count = 0
    for block in yaml_blocks:
        for doc in yaml.safe_load_all(block):
            if not doc or "name" not in doc:
                continue
            name = doc["name"]
            (out_dir / f"{name}.yaml").write_text(yaml.dump(doc, sort_keys=False))
            if name in evidence:
                (out_dir / f"{name}.evidence.json").write_text(
                    json.dumps({name: evidence[name]}, indent=2)
                )
            param_count += 1

    if param_count == 0:
        (out_dir / f"{snippet_path.stem}.NO_PARAMETERS_FOUND.txt").write_text(
            "Model returned zero parameters for this snippet -- see .raw.txt for the full response."
        )

    print(f"wrote {param_count} parameter(s) to {out_dir} (raw response: {raw_path.name})")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, help="e.g. claude-opus-4-8, glm-4.6")
    ap.add_argument("--snippet", required=True, type=Path)
    ap.add_argument(
        "--provider",
        choices=["anthropic", "zhipu", "openrouter"],
        default="anthropic",
    )
    args = ap.parse_args()

    prompt = build_prompt(args.snippet)

    if args.provider == "anthropic":
        raw_text = call_anthropic(args.model, prompt)
    else:
        raw_text = call_openai_compatible(args.model, prompt, args.provider)

    model_slug = args.model.replace("/", "_")
    write_results(model_slug, args.snippet, raw_text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
