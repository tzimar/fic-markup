#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, cast

from parse import (
    Body,
    BodyItem,
    Break,
    Dialogue,
    Emphasis,
    InlineBlock,
    Metadata,
    Narration,
    Node,
    OutlineBlock,
    Paragraph,
    Text,
    parse,
)


def find_metadata(node: Node) -> list[Metadata]:
    metadata: list[Metadata] = []
    if hasattr(node, "metadata"):
        metadata.extend(getattr(node, "metadata", []))

    if isinstance(node, Paragraph):
        for part in node.parts:
            metadata.extend(find_metadata(part))
    elif isinstance(node, (Narration, Dialogue)):
        for part in node.items:
            metadata.extend(find_metadata(part))
    elif isinstance(node, Emphasis):
        metadata.extend(find_metadata(node.content))
    elif isinstance(node, InlineBlock):
        metadata.extend(find_metadata(node.para))

    return metadata


def chapter_name_for_item(item: Node) -> str | None:
    for metadata in find_metadata(item):
        if metadata.identifier == "chapter" and metadata.text.strip():
            return metadata.text.strip()
    return None


def has_end_marker(item: Node) -> bool:
    for metadata in find_metadata(item):
        if metadata.identifier == "end":
            return True
    return False


def split_chapter_documents(ast: OutlineBlock) -> list[tuple[str | None, list[BodyItem]]]:
    documents: list[tuple[str | None, list[BodyItem]]] = []
    pending_items: list[BodyItem] = []
    current_chapter: str | None = None
    current_items: list[BodyItem] = []

    for item in ast.body.items:
        chapter_name = chapter_name_for_item(item)
        if chapter_name is not None:
            if current_chapter is None and not documents and pending_items:
                current_items = pending_items + [item]
            else:
                if current_items:
                    documents.append((current_chapter, current_items))
                current_items = [item]
            current_chapter = chapter_name
        elif has_end_marker(item):
            # End marker stops the current chapter; don't include this item
            if current_items:
                documents.append((current_chapter, current_items))
            current_items = []
            current_chapter = None
        else:
            if current_chapter is None:
                pending_items.append(item)
            else:
                current_items.append(item)

    if current_chapter is None:
        if pending_items:
            documents.append((None, pending_items))
    else:
        documents.append((current_chapter, current_items))

    return documents


def render_html_documents(ast: OutlineBlock, config: RenderConfig) -> list[tuple[str | None, str]]:
    document_groups = split_chapter_documents(ast)

    if len(document_groups) == 1 and document_groups[0][0] is None:
        return [(None, render_html(ast, config))]

    rendered: list[tuple[str | None, str]] = []
    for chapter_name, items in document_groups:
        if chapter_name is None:
            continue
        chapter_ast = OutlineBlock(modifiers=ast.modifiers, body=Body(items=items), metadata=ast.metadata)
        rendered.append((chapter_name, render_html(chapter_ast, config)))

    return rendered


class RenderContext:

    def __init__(self) -> None:
        pass


@dataclass
class BreakType:
    tag: Optional[str]
    class_attr: Optional[str]
    text: Optional[str]


@dataclass
class RenderConfig:
    break_types: Dict[str, BreakType] = field(default_factory=dict)
    small_caps_class: str = "small-caps"

    @classmethod
    def from_path(cls, path: Path) -> "RenderConfig":
        if not path.exists():
            raise FileNotFoundError(path)

        raw = cls._load_config_file(path)

        return cls(
            break_types={
                k: BreakType(
                    tag=v.get("tag", None),
                    class_attr=v.get("class", None),
                    text=v.get("text", None),
                )
                for k, v in cast(
                    dict[str, dict[str, str]], raw.get("breaks", {})
                ).items()
            },
            small_caps_class=raw.get("small_caps_class", cls.small_caps_class),
        )

    @classmethod
    def _load_config_file(cls, path: Path) -> dict[str, Any]:
        text = path.read_text(encoding="utf-8")
        data = json.loads(text)
        if isinstance(data, dict):
            return cast(dict[str, Any], data)
        raise ValueError("Configuration file must contain an object at the top level")


def load_config(path: Optional[Path] = None) -> RenderConfig:
    if path is not None:
        return RenderConfig.from_path(path)

    if Path("config.json").exists():
        return RenderConfig.from_path(Path("config.json"))

    return RenderConfig()


def render_html(ast: OutlineBlock, config: RenderConfig) -> str:
    ctx = RenderContext()
    return render_outline_block(ast, ctx, config, is_root=True)


def render_outline_block(
    block: OutlineBlock,
    ctx: RenderContext,
    config: RenderConfig,
    is_root: bool = False,
    is_first: bool = False,
) -> str:
    if is_root:
        return render_body(block.body, ctx, config, is_first_in_parent=True)

    attrs = render_attributes(block.modifiers)

    inner = render_body(block.body, ctx, config, is_first_in_parent=is_first)

    return f"<div{attrs}>{inner}</div>"


def render_inline_block(
    block: InlineBlock, ctx: RenderContext, config: RenderConfig
) -> str:
    attrs = render_attributes(block.modifiers)
    inner = render_para_content(block.para, config)
    return f"<span{attrs}>{inner}</span>"


def render_body(
    body: Body,
    ctx: RenderContext,
    config: RenderConfig,
    is_first_in_parent: bool = False,
) -> str:
    lines: List[str] = []
    is_first_item = is_first_in_parent

    for item in body.items:
        if isinstance(item, Paragraph):
            html = render_paragraph(item, is_first_item, None, config)
            if html:
                lines.append(html)
                is_first_item = False
        if isinstance(item, OutlineBlock):
            html = render_outline_block(
                item, ctx, config, is_root=False, is_first=is_first_item
            )
            lines.append(html)
            is_first_item = True
        elif isinstance(item, Break):
            html = render_section_break(item, config)
            lines.append(html)
            is_first_item = True

    return "\n".join(lines)


def render_body_inline_content(body: Body, config: RenderConfig) -> str:
    parts: List[str] = []
    for item in body.items:
        if isinstance(item, Paragraph):
            parts.append(render_para_content(item, config))
        elif isinstance(item, Break):
            parts.append(render_section_break(item, config))
    return "".join(parts)


def render_paragraph(
    para: Paragraph,
    is_first: bool = False,
    extra_modifiers: List[Tuple[str, str]] | None = None,
    config: RenderConfig = RenderConfig(),
) -> str:
    if not para.parts:
        return ""

    content = render_para_content(para, config)
    if not content.strip():
        return ""

    modifiers: List[Tuple[str, str]] = []
    if extra_modifiers:
        modifiers.extend(extra_modifiers)

    attrs = render_attributes(modifiers)
    return f"{'<br>' if is_first else ''}<p{attrs}>{content}</p>"


def render_para_content(para: Paragraph, config: RenderConfig) -> str:
    parts: List[str] = []
    for i, part in enumerate(para.parts):
        if isinstance(part, Narration):
            if i > 0:
                # After dialogue
                parts.append(f"&#x202F;— ")
            parts.append(render_narration(part, config))
        elif isinstance(part, Dialogue):
            # Before dialogue
            parts.append(f" —&#x202F;")
            parts.append(render_dialogue(part, config))
    return "".join(parts)


def render_narration(narration: Narration, config: RenderConfig) -> str:
    content = render_content_items(narration.items, config)
    return content.strip(" ")


def render_dialogue(dialogue: Dialogue, config: RenderConfig) -> str:
    content = render_content_items(dialogue.items, config)
    return content.strip(" ")


def render_content_items(items: List[Node], config: RenderConfig) -> str:
    ctx = RenderContext()
    parts: List[str] = []
    for item in items:
        if isinstance(item, Text):
            parts.append(item.content)
        elif isinstance(item, InlineBlock):
            parts.append(render_inline_block(item, ctx, config))
        elif isinstance(item, Emphasis):
            parts.append(render_emphasis(item, config))
        elif isinstance(item, Paragraph):
            parts.append(render_para_content(item, config))
    return "".join(parts)


def render_emphasis(emphasis: Emphasis, config: RenderConfig) -> str:
    marker = emphasis.marker
    content = render_para_content(emphasis.content, config)

    if marker == "*":
        return f"<i>{content}</i>"
    elif marker == "**":
        return f"<b>{content}</b>"
    elif marker == "***":
        return f"<b><i>{content}</i></b>"
    elif marker == "_":
        return f"<u>{content}</u>"
    elif marker == "~":
        return f"<s>{content}</s>"
    elif marker == "$":
        return f'<span class="{config.small_caps_class}">{content}</span>'
    else:
        return content


def render_section_break(section_break: Break, config: RenderConfig) -> str:
    for break_marker, break_type in config.break_types.items():
        if section_break.marker == break_marker and break_type.tag is not None:
            attrs = render_attributes(
                [(".", break_type.class_attr)] if break_type.class_attr else []
            )
            return (
                f'<{break_type.tag}{attrs}>{break_type.text or ""}</{break_type.tag}>'
            )
    return ""


def render_attributes(modifiers: List[Tuple[str, str]]) -> str:
    classes: List[str] = []
    ids: List[str] = []

    for marker, identifier in modifiers:
        if marker == ".":
            classes.append(identifier)
        elif marker == "#":
            ids.append(identifier)

    attrs: List[str] = []
    if classes:
        attrs.append(f'class="{" ".join(classes)}"')
    if ids:
        attrs.append(f'id="{ids[0]}"')

    return f" {' '.join(attrs)}" if attrs else ""


def main() -> int:
    parser = argparse.ArgumentParser(description="Render an AST to HTML")
    parser.add_argument(
        "source", nargs="?", help="input file; reads from stdin if omitted"
    )
    parser.add_argument(
        "--output", "-o", help="output file; writes to stdout if omitted"
    )
    parser.add_argument(
        "--output-dir", "-d", help="directory for output files"
    )
    parser.add_argument(
        "--template", "-t", help="HTML template file with {{content}} placeholder"
    )
    parser.add_argument("--config", "-c", help="JSON config file")
    args = parser.parse_args()

    if args.source:
        source_text = Path(args.source).read_text(encoding="utf-8")
    else:
        source_text = sys.stdin.read()

    config = load_config(Path(args.config)) if args.config else load_config()

    template = "{{content}}"
    if args.template:
        template = Path(args.template).read_text(encoding="utf8")
        if "{{content}}" not in template:
            print(
                "Error: Template file must contain {{content}} placeholder",
                file=sys.stderr,
            )
            return 1

    ast = parse(source_text)
    documents = render_html_documents(ast, config)

    output_path = args.output
    output_dir = None
    if args.output_dir:
        output_dir = Path(args.output_dir)
        if output_path:
            output_path = str(output_dir / Path(output_path).name)
        elif args.source:
            source_path = Path(args.source)
            output_filename = source_path.stem + ".html"
            output_path = str(output_dir / output_filename)

    if len(documents) > 1 and not output_dir:
        print(
            "Error: source contains multiple chapter documents; use --output-dir to write files",
            file=sys.stderr,
        )
        return 1

    if len(documents) == 1:
        _, html = documents[0]
        templated_html = template.replace("{{content}}", html)
        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).write_text(templated_html, encoding="utf-8")
        else:
            try:
                print(templated_html)
            except UnicodeEncodeError:
                sys.stdout.buffer.write(templated_html.encode("utf-8"))
        return 0

    assert output_dir is not None
    output_dir.mkdir(parents=True, exist_ok=True)
    output_base = Path(output_path).stem if output_path else (Path(args.source).stem if args.source else "")

    for chapter_name, html in documents:
        if output_base:
            output_filename = f"{output_base}-{chapter_name}.html"
        else:
            output_filename = f"{chapter_name}.html"
        chapter_path = output_dir / output_filename
        templated_html = template.replace("{{content}}", html)
        chapter_path.write_text(templated_html, encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
