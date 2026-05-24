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
    ]

    for sub in subs:
        text = re.sub(sub[0], sub[1], text)

    text = f"[;{text}]"
    return text

def normalise_text(text: str) -> str:
    subs = [
        ( r'`', r''),
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

    return text

@dataclass
class Node:
    pass



@dataclass
class Body(Node):
    items: List["BodyItem"]


@dataclass
class Paragraph(Node):
    parts: List[Node]


@dataclass
class Break(Node):
    marker: str
    count: int

@dataclass
class OutlineBlock(Node):
    modifiers: List[Tuple[str, str]]
    body: Body

@dataclass
class InlineBlock(Node):
    modifiers: List[Tuple[str, str]]
    para: Paragraph


@dataclass
class Emphasis(Node):
    marker: str
    content: Paragraph


@dataclass
class Narration(Node):
    items: List[Node]


@dataclass
class Dialogue(Node):
    items: List[Node]


@dataclass
class Text(Node):
    content: str


BodyItem = Union[Paragraph, Break]


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
        self.break_types = [ "=", "-", ">", "<" ]

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

    def trace_emit(self, node: Node) -> None:
        if not self.trace_enabled:
            return
        indent = "--" * self.trace_depth
        print(f"{indent} NODE: {node}")

    def parse_body(self) -> Body:
        self.trace_enter("parse_body")
        items: List[BodyItem] = []
        while True:
            self.skip_spaces()
            if self.at_eof():
                break
            if self.peek("]"):
                break
            if self.peek("\n"):
                self.advance(1)
                continue
            if self.peek_break():
                items.append(self.parse_break())
            elif self.peek("["):
                items.append(self.parse_outline_block())
            else:
                items.append(self.parse_paragraph())
            self.skip_spaces()
            if self.peek("\n"):
                self.advance(1)
        self.trace_exit("parse_body")
        return Body(items=items)

    def parse_paragraph(self) -> Paragraph:
        self.trace_enter("parse_paragraph")
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
        self.trace_exit("parse_paragraph")
        para = Paragraph(parts=parts)
        self.trace_emit(para)
        return para

    def parse_narration_or_dialog(self, boundary: str) -> List[Node]:
        self.trace_enter("parse_narration_or_dialog")
        items: List[Node] = []
        while True:
            if self.at_eof() or self.peek("\n") or self.peek(boundary) or self.peek(">") or self.peek("]"):
                break
            node = self.try_parse_paragraph_item()
            if node is not None:
                items.append(node)
                continue
            text_node = self.parse_text(boundary)
            if not text_node is None:
                items.append(text_node)
            
        self.trace_exit("parse_narration_or_dialog")
        return items

    def parse_text(self, boundary: str) -> Optional[Text]:
        self.trace_enter("parse_text")
        start = self.pos
        in_escaped_text = False
        while not self.at_eof():
            if in_escaped_text:
                if self.peek("`"):
                    in_escaped_text = False
                self.advance(1)
                continue
            if self.peek("\n") or self.peek(boundary) or self.peek(">") or self.peek("]"):
                break
            if self.peek("<"):
                break
            if self.peek_emphasis_start():
                break
            if self.peek("`"):
                in_escaped_text = True
            self.advance(1)
        if self.pos == start:
            self.trace_exit("parse_text")
            return None
        self.trace_exit("parse_text")
        return Text(content=normalise_text(self.text[start : self.pos]))

    def try_parse_paragraph_item(self) -> Optional[Node]:
        self.trace_enter("try_parse_paragraph_item")
        snapshot = self.pos
        try:
            if self.peek("<"):
                return self.parse_inline_block()
            for marker in ["***", "**", "*", "_", "~", "$"]:
                if self.peek(marker):
                    emphasis = self.parse_emphasis(marker)
                    if emphasis is not None:
                        self.trace_exit("try_parse_paragraph_item")
                        return emphasis
                    break
            self.trace_exit("try_parse_paragraph_item")
            return None
        except ParseError:
            print(f"Backtracking from position {self.pos} to {snapshot} due to parse error")
            self.pos = snapshot
            self.trace_exit("try_parse_paragraph_item")
            return None

    def parse_outline_block(self) -> OutlineBlock:
        self.trace_enter("parse_outline_block")
        self.expect("[")
        self.skip_spaces()
        modifiers = self.parse_modifiers()
        self.skip_spaces()
        if self.peek(";"):
            self.expect(";")
            body = self.parse_body()
        self.skip_spaces()
        self.expect("]")
        self.trace_exit("parse_outline_block")
        return OutlineBlock(modifiers=modifiers, body=body)

    def parse_inline_block(self) -> InlineBlock:
        self.trace_enter("parse_inline_block")
        self.expect("<")
        self.skip_spaces()
        modifiers = self.parse_modifiers()
        self.skip_spaces()
        if self.peek(";"):
            self.expect(";")
            self.skip_spaces()
            para = self.parse_paragraph()
        self.skip_spaces()
        self.expect(">")
        self.trace_exit("parse_inline_block")
        return InlineBlock(modifiers=modifiers, para=para)

    def parse_break(self) -> Break:
        self.trace_enter("parse_break")       

        for break_type in self.break_types:
            if self.peek(break_type * 3):
                count = 0
                while self.peek(break_type):
                    self.advance(1)
                    count += 1
                self.trace_exit("parse_break")
                return Break(marker=break_type, count=count)

        self.trace_exit("parse_break")
        raise ParseError(f"Expected break at position {self.pos}")

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
        content_para = inner_parser.parse_paragraph()
        if not inner_parser.at_eof():
            self.trace_exit(f"parse_emphasis(marker={marker!r})")
            raise ParseError(f"Could not consume emphasis content for marker {marker!r}")
        self.pos = end_pos + len(marker)
        self.trace_exit(f"parse_emphasis(marker={marker!r})")
        return Emphasis(marker=marker, content=content_para)

    def find_closing_marker(self, marker: str) -> int:
        #self.trace_enter(f"find_closing_marker(marker={marker!r})")
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
        self.skip_spaces()
        if not self.peek(".") and not self.peek(";"):
            identifier = self.parse_identifier()
            modifiers.append(("#", identifier))
        while True:
            self.skip_spaces()
            if self.peek("."):
                marker = self.current_char()
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

    def peek_identifier(self) -> bool:
        self.skip_spaces()
        return bool(re.match(r"[A-Za-z_][A-Za-z0-9_-]*", self.remaining()))

    def peek_break(self) -> bool:
        return any(self.peek(break_type * 3) for break_type in self.break_types)

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
            raise ParseError(f"Expected {token!r} at position {self.pos} but found {self.text[self.pos:self.pos+20]!r}")
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


def parse(text: str, trace_enabled: bool = False) -> OutlineBlock:
    normalised = normalise_input(text)
    parser = Parser(normalised, trace_enabled=trace_enabled)
    return parser.parse_outline_block()


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
