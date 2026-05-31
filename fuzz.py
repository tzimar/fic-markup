#!/usr/bin/env python3
from __future__ import annotations

import argparse
import random
import string
from pathlib import Path
from typing import List, Optional
import subprocess
import sys
from parse import parse

METADATA_KEYS = ["title", "author", "date", "chapter", "todo"]
IDENTIFIER_CHARS = string.ascii_letters + string.digits + "_-"
WORDS = (
    "lorem ipsum dolor sit amet consectetur adipiscing elit nullam"
    "consequat mauris vitae aliquet iaculis maecenas venenatis"
    "facilisis leo vel suscipit urna varius in morbi dictum est"
    "eros eget consequat libero vehicula sit amet duis convallis"
    "turpis nunc nec pulvinar eros commodo eu suspendisse auctor"
    "interdum sapien eget rhoncus neque facilisis lacinia vivamus"
    "sagittis erat massa aliquam laoreet dictum arcu vitae pulvinar"
    "nunc non lorem sit amet ante rutrum maximus vitae nec libero"
    "curabitur congue massa nibh at dapibus ex gravida nec nunc"
    "pellentesque nisl mauris vitae consequat lorem pulvinar maximus"
    .split()
)


def rand_word(n=1):
    return " ".join(random.choice(WORDS) for _ in range(n))


def rand_text(min_words=1, max_words=8):
    return rand_word(random.randint(min_words, max_words))


def rand_identifier():
    return "".join(random.choice(IDENTIFIER_CHARS) for _ in range(random.randint(3, 12)))


def metadata_item(allow_text=True) -> str:
    key = random.choice(METADATA_KEYS)
    if key == "end":
        return "{!end}"
    if not allow_text:
        return f"{{!{key}}}"
    if key == "todo":
        txt = rand_text(2, 6)
    else:
        txt = rand_text(1, 4)
    return f"{{!{key} {txt} }}"


def section_break() -> str:
    marker = random.choice(["=", "-", "<", ">"])
    count = random.randint(3, 6)
    return marker * count


def emphasize(inner: str) -> str:
    marker = random.choice(["*", "**", "***", "_", "~", "$"])
    return f"{marker}{inner}{marker}"


def inline_block(content: str = None) -> str:
    attrs = []
    if random.random() < 0.5:
        attrs.append(f".{rand_identifier()}")
    if random.random() < 0.2:
        attrs.insert(0, f"#{rand_identifier()}")
    attrs_str = " ".join(attrs)
    if content is None:
        content = rand_text(1, 4)
    if attrs_str:
        return f"<{attrs_str};{content}>"
    return f"<;{content}>"


def para_item(include_metadata=False) -> str:
    meta = metadata_item() if include_metadata and random.random() < 0.4 else ""
    if random.random() < 0.6:
        inner = rand_text(1, 5)
        return f"{meta}{inline_block(inner)}"
    inner = rand_text(1, 6)
    return f"{meta}{emphasize(inner)}"


def sentence() -> str:
    parts = []
    n = random.randint(3, 30)
    for i in range(n):
        if random.random() < 0.08:
            if random.random() < 0.5:
                parts.append(emphasize(rand_text(1, 3)))
            else:
                parts.append(inline_block(rand_text(1, 3)))
        else:
            parts.append(random.choice(WORDS))
    text = ""
    for i, part in enumerate(parts):
        if i != 0:
            if random.random() < 0.1:
              text += random.choice([",", ";", " -", "...", ":"])
            text += " "
        text += part
    text += random.choice([".", ":"])
    return text.capitalize()


def narration(allow_metadata=True) -> str:
    out = ""
    if allow_metadata and random.random() < 0.25:
        out += metadata_item()
    if random.random() < 0.8:
        out += sentence()
    else:
        out += para_item(include_metadata=allow_metadata)
    return out


def dialog(allow_metadata=True) -> str:
    out = ""
    if allow_metadata and random.random() < 0.25:
        out += metadata_item()
    if random.random() < 0.8:
        out += sentence()
    else:
        out += para_item(include_metadata=allow_metadata)
    return out


def paragraph() -> str:
    text = narration()
    if random.random() < 0.6:
        parts = []
        parts.append(text)
        alt = random.randint(1, 3)
        for i in range(alt):
            parts.append("=")
            if i % 2 == 0:
                parts.append(dialog())
            else:
                parts.append(narration())
        return " ".join(parts)
    return text


def outline_block() -> str:
    attrs = []
    if random.random() < 0.6:
        attrs.append(f"{rand_identifier()}")
    for _ in range(random.randint(0, 2)):
        if random.random() < 0.7:
            attrs.append(f".{rand_identifier()}")
    attrs_str = " ".join(attrs)
    if random.random() < 0.7:
        items = []
        for _ in range(random.randint(1, 3)):
            if random.random() < 0.2:
                items.append(section_break())
            else:
                items.append(paragraph())
        body = "\n".join(items)
        if attrs_str:
            return f"[{attrs_str};{body}]"
        return f"[;{body}]"
    if attrs_str:
        return f"[{attrs_str}]"
    return "[]"


def generate_ffml(max_items=100, allow_top_metadata=True) -> str:
    parts: List[str] = []
    if allow_top_metadata and random.random() < 0.9:
        for _ in range(random.randint(1, 5)):
            parts.append(metadata_item())
    body_items: List[str] = []
    for _ in range(random.randint(3, max_items)):
        r = random.random()
        if r < 0.10:
            if random.random() < 0.4:
                body_items.append(metadata_item())
            body_items.append(section_break())
        elif r < 0.25:
            body_items.append(outline_block())
        elif r < 0.4:
            body_items.append(paragraph())
        else:
            body_items.append(paragraph())
    body = "\n\n".join(body_items)
    modifiers = []
    if random.random() < 0.5:
        modifiers.append(f"#{rand_identifier()}")
    for _ in range(random.randint(0, 2)):
        if random.random() < 0.5:
            modifiers.append(f".{rand_identifier()}")
    modifiers_str = " ".join(modifiers)
    if modifiers_str:
        file_text = f"[{modifiers_str};{body}]"
    else:
        file_text = f"[;{body}]"

    if parts:
        file_text = "\n".join(parts) + "\n\n" + file_text
    return file_text


def validate(text: str) -> bool:
    try:
        parse(text, False)
        return True
    except Exception:
        return False


def main():
    parser = argparse.ArgumentParser(description="Generate random valid FFML files")
    parser.add_argument("-n", "--count", type=int, default=1, help="number of files to generate")
    parser.add_argument("-o", "--output", type=str, default=".", help="output directory")
    parser.add_argument("--seed", type=int, default=None, help="random seed")
    parser.add_argument("--max-attempts", type=int, default=20, help="max attempts to produce a valid file")
    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    for i in range(1, args.count + 1):
        for attempt in range(args.max_attempts):
            text = generate_ffml()
            path = out_dir / f"fuzz-{i:04d}.ffml"
            path.write_text(text, encoding="utf8")
            if validate(text):
                print(f"Wrote {path}")

                subprocess.run(
                    [sys.executable, "render.py", str(out_dir / f"fuzz-{i:04d}.ffml"), "-d", str(out_dir), "--suppress-todos", "-t", "template.html"],
                    capture_output=True,
                    text=True,
                )

                break
            if attempt == args.max_attempts - 1:
                print(f"Failed to generate valid FFML after {args.max_attempts} attempts")


if __name__ == "__main__":
    main()
