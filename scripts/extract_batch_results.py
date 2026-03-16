"""Extract taxonomy v2 batch results from agent output transcripts."""

import json
import re
from pathlib import Path

OUTPUT_DIR = Path("/home/godli/textparse/data/extraction/taxonomy_v2")

# Agent output files mapped to batch numbers
AGENT_FILES = {
    1: "/tmp/claude-1000/-home-godli-textparse/tasks/a459850.output",
    2: "/tmp/claude-1000/-home-godli-textparse/tasks/a6cd006.output",
    3: "/tmp/claude-1000/-home-godli-textparse/tasks/a90b3b1.output",
    4: "/tmp/claude-1000/-home-godli-textparse/tasks/a3349d6.output",
    5: "/tmp/claude-1000/-home-godli-textparse/tasks/a789f11.output",
    6: "/tmp/claude-1000/-home-godli-textparse/tasks/abbd079.output",
    7: "/tmp/claude-1000/-home-godli-textparse/tasks/a51f807.output",
}


def extract_from_write_tool(filepath):
    """Extract JSON from a Write tool_use in JSONL transcript."""
    with open(filepath) as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
            except json.JSONDecodeError:
                continue
            msg = entry.get("message", {})
            content = msg.get("content", [])
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_use" and block.get("name") == "Write":
                        raw = block["input"]["content"]
                        try:
                            return json.loads(raw)
                        except json.JSONDecodeError:
                            continue
    return None


def extract_from_text_block(filepath):
    """Extract JSON from markdown code block in final text message."""
    with open(filepath) as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
            except json.JSONDecodeError:
                continue
            msg = entry.get("message", {})
            content = msg.get("content", [])
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text = block["text"]
                        # Find JSON array in code block
                        match = re.search(r'```json\s*\n(\[[\s\S]*?\])\s*\n```', text)
                        if match:
                            try:
                                data = json.loads(match.group(1))
                                if len(data) > 10:  # Ensure it's the full batch
                                    return data
                            except json.JSONDecodeError:
                                continue
    return None


def main():
    total = 0
    for batch_num, filepath in sorted(AGENT_FILES.items()):
        if not Path(filepath).exists():
            print(f"  Batch {batch_num}: output file not found")
            continue

        # Try Write tool first (more reliable), then text block
        data = extract_from_write_tool(filepath)
        source = "Write tool"
        if not data:
            data = extract_from_text_block(filepath)
            source = "code block"

        if not data:
            print(f"  Batch {batch_num}: COULD NOT EXTRACT")
            continue

        out_path = OUTPUT_DIR / f"batch-{batch_num}.json"
        with open(out_path, "w") as f:
            json.dump(data, f, indent=2)
        print(f"  Batch {batch_num}: {len(data)} concepts extracted from {source}")
        total += len(data)

    print(f"\nTotal extracted: {total} concepts")


if __name__ == "__main__":
    main()
