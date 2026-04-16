"""OpenAI tool-calling evaluation — baseline using raw OpenAI client (no framework)."""

# /// script
# dependencies = ["openai>=1.0.0"]
# ///

import json
import os
import time

from openai import OpenAI

API_URL = os.environ.get("MLX_API_URL", "http://127.0.0.1:11434/v1")
MODEL = os.environ["MLX_DEFAULT_MODEL"]
FIXTURE_PATH = "/tmp/eval-test.txt"

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "file_read",
            "description": "Read the benchmark fixture file and return its contents",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "File path to read"}},
                "required": ["path"],
            },
        },
    }
]


def execute_tool(name: str, arguments: str) -> str:
    try:
        args = json.loads(arguments)
    except json.JSONDecodeError:
        return "Error: malformed tool arguments"
    if name == "file_read":
        path = args.get("path", "")
        if path != FIXTURE_PATH:
            return f"Error: path not allowed: {path}"
        try:
            with open(path) as f:
                return f.read()
        except FileNotFoundError:
            return f"Error: File not found: {path}"
    return f"Error: Unknown tool: {name}"


def run_agent(prompt: str, max_steps: int = 5) -> dict:
    client = OpenAI(base_url=API_URL, api_key="EMPTY")
    messages = [
        {"role": "system", "content": "You are a helpful assistant. Use tools when needed."},
        {"role": "user", "content": prompt},
    ]
    total_tokens = 0
    tool_calls_made = []
    start = time.time()

    for step in range(max_steps):
        response = client.chat.completions.create(
            model=MODEL, messages=messages, tools=TOOLS, tool_choice="auto", max_tokens=500, temperature=0
        )
        msg = response.choices[0].message
        if response.usage:
            total_tokens += response.usage.total_tokens or response.usage.completion_tokens or 0

        if msg.tool_calls:
            messages.append(msg)
            for tc in msg.tool_calls:
                result = execute_tool(tc.function.name, tc.function.arguments)
                tool_calls_made.append({"tool": tc.function.name, "args": tc.function.arguments})
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
        else:
            elapsed = time.time() - start
            return {
                "framework": "OpenAI tool-calling (baseline)",
                "answer": msg.content[:200] if msg.content else "(empty)",
                "tool_calls": tool_calls_made,
                "tokens": total_tokens,
                "latency": round(elapsed, 2),
                "steps": step + 1,
            }

    elapsed = time.time() - start
    return {
        "framework": "OpenAI tool-calling (baseline)",
        "answer": "(max steps reached)",
        "tool_calls": tool_calls_made,
        "tokens": total_tokens,
        "latency": round(elapsed, 2),
        "steps": max_steps,
    }


if __name__ == "__main__":
    result = run_agent("Read the file at /tmp/eval-test.txt and summarize its contents in one sentence.")
    print(json.dumps(result, indent=2))
