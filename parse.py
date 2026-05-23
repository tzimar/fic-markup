#!/usr/bin/env python3
from __future__ import annotations

import argparse
import dataclasses
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple, Union


class ParseError(Exception):
    pass


def normalise_input(text: str) -> str:

    subs = [
        ( r'\{[\s\S]*?\}', r'' ),
        ( r'\n+', r'\n' ),
        ( r'[ \t]+', r' ' ),
        ( r'\.\.\.', r'…' ),
        ( r'"(.*?)"', r'“\1”' ),
        ( r'\'', r'’' ),
        ( r'---', r'—' ),
        ( r'--', r'–' ),
        ( r' - ', r' – ' ),

        #( r'- ', r'– ' ),
        #( r'-$', r'–' ),
    ]

    for sub in subs:
        text = re.sub(sub[0], sub[1], text)

    text = f"[document]{text}[/document]"
    return text


@dataclass
class Node:
    pass



@dataclass
class Body(Node):
    items: List["BodyItem"]


@dataclass
class Paragraph(Node):
    items: List[Node]


@dataclass
class SectionBreak(Node):
    marker: str
    count: int


@dataclass
class Block(Node):
    tag: str
    modifiers: List[Tuple[str, str]]
    body: Body


@dataclass
class ArrowBlock(Node):
    tag: str
    modifiers: List[Tuple[str, str]]


@dataclass
class Emphasis(Node):
    marker: str
    content: Paragraph


@dataclass
class Prose(Node):
    parts: List[Node]


@dataclass
class Narration(Node):
    items: List[Node]


@dataclass
class Dialogue(Node):
    items: List[Node]


@dataclass
class Text(Node):
    content: str


BodyItem = Union[Paragraph, SectionBreak, ArrowBlock]


def ast_to_dict(node):
    if isinstance(node, list):
        return [ast_to_dict(item) for item in node]
    if dataclasses.is_dataclass(node):
        result = {"type": node.__class__.__name__}
        for field in dataclasses.fields(node):
            result[field.name] = ast_to_dict(getattr(node, field.name))
        return result
    return node


class Parser:
    def __init__(self, text: str, trace_enabled: bool = False) -> None:
        self.text = text
        self.pos = 0
        self.length = len(text)
        self.trace_enabled = trace_enabled
        self.trace_depth = 0

    def trace_enter(self, function_name: Optional[str] = None) -> None:
        if not self.trace_enabled:
            return
        indent = "--" * self.trace_depth
        print(f"{indent} >>>: {function_name} pos={self.pos}, next={self.text[self.pos:self.pos+20]!r}")
        self.trace_depth += 1

    def trace_exit(self, function_name: Optional[str] = None) -> None:
        if not self.trace_enabled:
            return
        self.trace_depth -= 1
        indent = "--" * self.trace_depth
        print(f"{indent} <<<: {function_name} pos={self.pos}, next={self.text[self.pos:self.pos+20]!r}")

    def parse_body(self) -> Body:
        self.trace_enter("parse_body")
        items: List[BodyItem] = []
        while True:
            self.skip_spaces()
            if self.at_eof():
                break
            if self.next_is_closing_block_tag():
                break
            if self.peek("\n"):
                self.advance(1)
                continue
            if self.peek_section_break():
                items.append(self.parse_section_break())
            elif self.peek_arrow_block_start():
                items.append(self.parse_arrow_block())
            else:
                items.append(self.parse_para())
            self.skip_spaces()
            if self.peek("\n"):
                self.advance(1)
        self.trace_exit("parse_body")
        return Body(items=items)

    def parse_para(self) -> Paragraph:
        self.trace_enter("parse_para")
        items: List[Node] = []
        while True:
            self.skip_spaces()
            if self.at_eof() or self.peek("\n") or self.next_is_closing_block_tag():
                break
            node = self.try_parse_para_item()
            if node is not None:
                items.append(node)
                continue
            prose = self.parse_prose()
            if not prose.parts:
                break
            items.append(prose)
        self.trace_exit("parse_para")
        return Paragraph(items=items)

    def parse_prose(self) -> Prose:
        self.trace_enter("parse_prose")
        parts: List[Node] = []
        narration = self.parse_narration_or_dialog(boundary="=")
        parts.append(Narration(items=narration))
        while self.peek("="):
            self.advance(1)
            dialogue = self.parse_narration_or_dialog(boundary="=")
            parts.append(Dialogue(items=dialogue))
            if self.peek("="):
                self.advance(1)
                narration = self.parse_narration_or_dialog(boundary="=")
                parts.append(Narration(items=narration))
            else:
                break
        self.trace_exit("parse_prose")
        return Prose(parts=parts)

    def parse_narration_or_dialog(self, boundary: str) -> List[Node]:
        self.trace_enter("parse_narration_or_dialog")
        items: List[Node] = []
        while True:
            if self.at_eof() or self.peek("\n") or self.peek(boundary) or self.next_is_closing_block_tag():
                break
            node = self.try_parse_para_item()
            if node is not None:
                items.append(node)
                continue
            text_node = self.parse_text(boundary)
            if text_node is None or not text_node.content:
                break
            items.append(text_node)
        self.trace_exit("parse_narration_or_dialog")
        return items

    def parse_text(self, boundary: str) -> Optional[Text]:
        self.trace_enter("parse_text")
        start = self.pos
        while not self.at_eof():
            if self.peek("\n") or self.peek(boundary) or self.next_is_closing_block_tag():
                break
            if self.peek("[") and self.peek_block_or_arrow_or_closing():
                break
            if self.peek_emphasis_start():
                break
            self.advance(1)
        if self.pos == start:
            self.trace_exit("parse_text")
            return None
        self.trace_exit("parse_text")
        return Text(content=self.text[start : self.pos])

    def try_parse_para_item(self) -> Optional[Node]:
        snapshot = self.pos
        try:
            if self.peek("[") and not self.peek("[/"):
                if self.peek_arrow_block_start():
                    return None
                return self.parse_block()
            for marker in ["***", "**", "*", "_", "~", "$"]:
                if self.peek(marker):
                    emphasis = self.parse_emphasis(marker)
                    if emphasis is not None:
                        return emphasis
                    break
            return None
        except ParseError:
            print(f"Backtracking from position {self.pos} to {snapshot} due to parse error")
            self.pos = snapshot
            return None

    def parse_block(self) -> Block:
        self.trace_enter("parse_block")
        self.expect("[")
        self.skip_spaces()
        tag = self.parse_identifier()
        modifiers = self.parse_modifiers()
        self.skip_spaces()
        if self.peek("/"):
            self.expect("/")
            self.skip_spaces()
            self.expect("]")
            self.trace_exit("parse_block")
            return Block(tag=tag, modifiers=modifiers, body=Body(items=[]))
        self.expect("]")
        body = self.parse_body()
        self.parse_closing_tag(tag)
        self.trace_exit("parse_block")
        return Block(tag=tag, modifiers=modifiers, body=body)

    def parse_arrow_block(self) -> ArrowBlock:
        self.trace_enter("parse_arrow_block")
        self.expect("[")
        self.skip_spaces()
        self.expect(">")
        self.skip_spaces()
        tag = self.parse_identifier()
        modifiers = self.parse_modifiers()
        self.skip_spaces()
        self.expect("]")
        self.trace_exit("parse_arrow_block")
        return ArrowBlock(tag=tag, modifiers=modifiers)

    def parse_section_break(self) -> SectionBreak:
        self.trace_enter("parse_section_break")
        if self.peek("~~~"):
            count = 0
            while self.peek("~"):
                self.advance(1)
                count += 1
            return SectionBreak(marker="~", count=count)
        if self.peek(">>>"):
            count = 0
            while self.peek(">"):
                self.advance(1)
                count += 1
            self.trace_exit("parse_section_break")
            return SectionBreak(marker=">", count=count)
        self.trace_exit("parse_section_break")
        raise ParseError(f"Expected section break at position {self.pos}")

    def parse_emphasis(self, marker: str) -> Optional[Emphasis]:
        self.trace_enter(f"parse_emphasis(marker={marker!r})")
        if not self.peek(marker):
            self.trace_exit(f"parse_emphasis(marker={marker!r})")
            return None
        end_pos = self.find_closing_marker(marker)
        if end_pos < 0:
            self.trace_exit(f"parse_emphasis(marker={marker!r})")
            raise ParseError(f"Unterminated emphasis marker {marker!r} at position {self.pos}")
        self.advance(len(marker))
        content_text = self.text[self.pos : end_pos]
        inner_parser = Parser(content_text)
        content_para = inner_parser.parse_para()
        if not inner_parser.at_eof():
            self.trace_exit(f"parse_emphasis(marker={marker!r})")
            raise ParseError(f"Could not consume emphasis content for marker {marker!r}")
        self.pos = end_pos + len(marker)
        self.trace_exit(f"parse_emphasis(marker={marker!r})")
        return Emphasis(marker=marker, content=content_para)

    def find_closing_marker(self, marker: str) -> int:
        self.trace_enter(f"find_closing_marker(marker={marker!r})")
        search_pos = self.pos + len(marker)
        while search_pos < self.length:
            if self.peek_at(search_pos, "\n"):
                return -1
            if self.peek_at(search_pos, marker):
                return search_pos
            search_pos += 1
        return -1

    def parse_modifiers(self) -> List[Tuple[str, str]]:
        self.trace_enter("parse_modifiers")
        modifiers: List[Tuple[str, str]] = []
        while True:
            self.skip_spaces()
            if self.peek(".") or self.peek("#"):
                marker = self.text[self.pos]
                self.advance(1)
                self.skip_spaces()
                identifier = self.parse_identifier()
                modifiers.append((marker, identifier))
                continue
            break
        self.trace_exit("parse_modifiers")
        return modifiers

    def parse_identifier(self) -> str:
        self.trace_enter("parse_identifier")
        self.skip_spaces()
        match = re.match(r"[A-Za-z_][A-Za-z0-9_-]*", self.remaining())
        if not match:
            self.trace_exit("parse_identifier")
            raise ParseError(f"Expected identifier at position {self.pos}")
        identifier = match.group(0)
        self.advance(len(identifier))
        self.trace_exit("parse_identifier")
        return identifier

    def parse_closing_tag(self, expected_tag: str) -> None:
        self.trace_enter(f"parse_closing_tag(expected_tag={expected_tag!r})")
        self.expect("[")
        self.skip_spaces()
        self.expect("/")
        self.skip_spaces()
        closing_tag = self.parse_identifier()
        self.skip_spaces()
        self.expect("]")
        if closing_tag != expected_tag:
            self.trace_exit(f"parse_closing_tag(expected_tag={expected_tag!r})")
            raise ParseError(
                f"Mismatched closing tag at position {self.pos}: expected {expected_tag!r}, found {closing_tag!r}"
            )
        self.trace_exit(f"parse_closing_tag(expected_tag={expected_tag!r})")

    def next_is_closing_block_tag(self) -> bool:
        if not self.peek("["):
            return False
        snapshot = self.pos
        self.advance(1)
        self.skip_spaces()
        is_close = self.peek("/")
        self.pos = snapshot
        return is_close

    def peek_block_or_arrow_or_closing(self) -> bool:
        if self.peek("[/"):
            return True
        if self.peek_arrow_block_start():
            return True
        if self.peek("["):
            try:
                snapshot = self.pos
                self.advance(1)
                self.skip_spaces()
                valid = bool(re.match(r"[A-Za-z_][A-Za-z0-9_-]*", self.remaining()))
                self.pos = snapshot
                return valid
            except Exception:
                self.pos = snapshot
                return False
        return False

    def peek_arrow_block_start(self) -> bool:
        return self.peek("[") and self.peek_at(self.pos + 1, ">")

    def peek_section_break(self) -> bool:
        return self.peek("~~~") or self.peek(">>>")

    def peek_emphasis_start(self) -> bool:
        for marker in ["***", "**", "*", "_", "~", "$"]:
            if self.peek(marker):
                try:
                    return self.find_closing_marker(marker) >= 0
                except ParseError:
                    return False
        return False

    def skip_spaces(self) -> None:
        while (not self.at_eof()) and (self.current_char() in " \t"):
            self.advance(1)

    def peek(self, token: str) -> bool:
        #print(f"PEEK: token={token!r} pos={self.pos} next={self.text[self.pos:self.pos+20]!r}")
        return self.text.startswith(token, self.pos)

    def expect(self, token: str) -> None:
        #print(f"EXPECT: token={token!r} pos={self.pos} next={self.text[self.pos:self.pos+20]!r}")
        if not self.peek(token):
            raise ParseError(f"Expected {token!r} at position {self.pos}")
        self.advance(len(token))

    def peek_at(self, position: int, token: str) -> bool:
        #print(f"PEEK_AT: token={token!r} pos={position} next={self.text[position:position+20]!r}")
        return self.text.startswith(token, position)

    def advance(self, count: int = 1) -> None:
        self.pos += count

    def current_char(self) -> str:
        return self.text[self.pos] if self.pos < self.length else ""

    def at_eof(self) -> bool:
        return self.pos >= self.length

    def remaining(self) -> str:
        return self.text[self.pos :]


def parse(text: str, trace_enabled: bool = False) -> Block:
    normalised = normalise_input(text)
    parser = Parser(normalised, trace_enabled=trace_enabled)
    return parser.parse_block()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", nargs="?", help="Input file; reads stdin if omitted")
    parser.add_argument("--trace", action="store_true", help="Trace logging mode")
    args = parser.parse_args()
    if args.source:
        source_text = Path(args.source).read_text(encoding="utf8")
    else:
        source_text = sys.stdin.read()
    if args.trace:
        print("=== TRACE START ===")
    ast = parse(source_text, args.trace)
    if not args.trace:
        print(json.dumps(ast_to_dict(ast), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
