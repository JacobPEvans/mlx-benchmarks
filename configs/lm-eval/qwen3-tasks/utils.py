"""
Custom filter utilities for Qwen3.x models that emit thinking content before code.

Two problems with the standard humaneval_instruct / mbpp_instruct tasks when
used against thinking-mode Qwen3 models via local-chat-completions:

1. gen_prefix does not work: llama-swap does not support partial-assistant-message
   prefilling via the OpenAI chat API. The model generates a full response that
   includes thinking text and then a markdown code block rather than completing
   an in-progress code snippet.

2. Token budget: the default max_gen_toks (1024/256) is too small — the model
   exhausts the budget on thinking before it writes any code. The qwen3 YAML
   overrides raise this significantly.

Solution: custom filter functions that
  - Strip <think>...</think> XML blocks (used by Qwen3 API-mode)
  - Strip plain-text "Thinking Process:" preambles (used when XML not triggered)
  - Extract the Python code block from the model's markdown response
  - Assemble the final prediction in the format expected by pass_at_k / pass_at_1

Usage:
  lm_eval ... \
    --tasks humaneval_instruct_qwen3,mbpp_instruct_qwen3 \
    --include_path /path/to/qwen3-tasks
"""

import re

# Re-exports: these are resolved by lm-eval's YAML !function utils.X syntax.
# See humaneval_instruct_qwen3.yaml (metric: !function utils.pass_at_k) and
# mbpp_instruct_qwen3.yaml (metric: !function utils.pass_at_1; samples:
# !function utils.list_fewshot_samples).
from lm_eval.tasks.humaneval.utils import pass_at_k
from lm_eval.tasks.mbpp.utils import list_fewshot_samples, pass_at_1

__all__ = [
    "extract_python_block",
    "humaneval_build_predictions_instruct",
    "list_fewshot_samples",
    "mbpp_build_predictions",
    "pass_at_1",
    "pass_at_k",
    "strip_think",
]

_THINK_XML = re.compile(r"<think>.*?</think>", re.DOTALL)
_THINK_TEXT = re.compile(r"^Thinking Process:.*?(?=```python|```\n|Here is|My solution|$)", re.DOTALL)
_PYTHON_BLOCK = re.compile(r"```python\n(.*?)\n?```", re.DOTALL)
_ANY_BLOCK = re.compile(r"```\w*\n(.*?)\n?```", re.DOTALL)


def strip_think(text: str) -> str:
    """Remove think blocks (XML or plain-text) from model output."""
    text = _THINK_XML.sub("", text)
    text = _THINK_TEXT.sub("", text)
    return text.lstrip()


def extract_python_block(text: str) -> str:
    """Return the last Python code block from markdown text, or '' if none."""
    matches = _PYTHON_BLOCK.findall(text)
    if matches:
        return matches[-1]
    matches = _ANY_BLOCK.findall(text)
    return matches[-1] if matches else ""


def humaneval_build_predictions_instruct(resps: list[list[str]], docs: list[dict]) -> list[list[str]]:
    """
    Filter for humaneval_instruct_qwen3.

    The pass_at_k metric expects predictions as:
      doc["prompt"] + <function body completion>

    When gen_prefix works, the model only generates the body. When it does not
    (as with llama-swap), the model generates a full markdown response containing
    a complete code block. This filter handles both cases.
    """
    result = []
    for resp_list, doc in zip(resps, docs, strict=True):
        filtered = []
        for r in resp_list:
            cleaned = strip_think(r)
            code = extract_python_block(cleaned)
            if code and ("def " in code or "return " in code):
                # Model gave us a complete function block — use it as-is if the
                # prompt is already embedded, otherwise prepend it for imports.
                if doc["prompt"].rstrip() in code:
                    filtered.append(code)
                else:
                    filtered.append(doc["prompt"] + code)
            else:
                # Fallback: original build_predictions_instruct logic
                filtered.append(
                    doc["prompt"] + (cleaned if cleaned.find("```") == -1 else cleaned[: cleaned.find("```")])
                )
        result.append(filtered)
    return result


def mbpp_build_predictions(resps: list[list[str]], docs: list[dict]) -> list[list[str]]:
    """
    Filter for mbpp_instruct_qwen3.

    The pass_at_1 metric expects predictions as the extracted code body. This
    filter extracts the first complete Python code block after stripping think
    content. ``docs`` is required by the lm-eval filter signature and is
    validated here for length parity even though the per-doc fields are unused.
    """
    if len(resps) != len(docs):
        raise ValueError(f"mbpp_build_predictions: len(resps)={len(resps)} != len(docs)={len(docs)}")
    result = []
    for resp_list in resps:
        filtered = []
        for r in resp_list:
            cleaned = strip_think(r)
            code = extract_python_block(cleaned)
            filtered.append(code)
        result.append(filtered)
    return result
