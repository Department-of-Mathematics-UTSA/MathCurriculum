#!/usr/bin/env python3
"""Transform Data/*.xml into curriculum/unit_*.tex and update MathCurriculum.tex.

Implements the specification in specs/XML_to_LaTeX_Spec.md, adapted for the
actual XML content format (Markdown with embedded LaTeX math rather than
HTML-encoded text).
"""

from pathlib import Path
import xml.etree.ElementTree as ET
import html
import re

DATA_DIR = Path(__file__).resolve().parent.parent / "Data"
CURRICULUM = Path(__file__).resolve().parent.parent / "curriculum"
MASTER_FILE = CURRICULUM / "MathCurriculum.tex"

_MATH_PH = "\x00MATH{}\x00"


# -- helpers -----------------------------------------------------------------

def _extract_math(text: str):
    """Pull out $$...$$ and $...$ blocks, replacing them with placeholders.

    Returns (text_with_placeholders, list_of_math_blocks).
    """
    blocks = []

    def _repl(m):
        blocks.append(m.group(0))
        return _MATH_PH.format(len(blocks) - 1)

    text = re.sub(r"\$\$.*?\$\$", _repl, text, flags=re.DOTALL)
    text = re.sub(r"\$(?!\$).*?\$", _repl, text)
    return text, blocks


def _restore_math(text: str, blocks: list) -> str:
    """Restore math placeholders."""
    for i, blk in enumerate(blocks):
        text = text.replace(_MATH_PH.format(i), blk)
    return text


def strip_scripts(text: str) -> str:
    """5a: Remove <script>...</script> blocks."""
    return re.sub(r"<script[^>]*>.*?</script>", "", text,
                  flags=re.DOTALL | re.IGNORECASE)


def unescape_entities(text: str) -> str:
    """5b: Unescape HTML entities (&#13;, &lt;, etc.)."""
    text = text.replace("&#13;", "\n")
    text = html.unescape(text)
    return text


def strip_html_tags(text: str) -> str:
    """5c: Replace structural HTML tags with markers, then strip all tags."""
    text = re.sub(r"<li[^>]*>", "\n* ", text, flags=re.IGNORECASE)
    text = re.sub(r"<p[^>]*>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</?\w+[^>]*>", "", text)
    return text


def latex_escape_plain(text: str) -> str:
    """Escape only the characters that conflict with LaTeX in plain text.

    The source content already contains valid LaTeX math ($, ^, _, {, }, \\)
    and Markdown syntax (#, *, [, ]).  We only escape characters that are
    special in LaTeX but have no role in Markdown or the existing math:
    & % ~
    """
    text = text.replace("&", r"\&")
    text = text.replace("%", r"\%")
    text = text.replace("~", r"\textasciitilde{}")
    return text


def md_to_latex(text: str) -> str:
    """Convert Markdown constructs to LaTeX equivalents.

    Handles: headings, bold, italic, images, links, unordered lists.
    Math blocks must already be extracted before calling this.
    """
    lines = text.split("\n")
    out = []
    in_itemize = False

    for line in lines:
        stripped = line.strip()

        # Markdown headings (with or without space after #)
        heading_match = re.match(r"^(#{1,6})\s*(.*)", stripped)
        if heading_match:
            title = heading_match.group(2)
            # Strip markdown anchor tags like {#anchor_id}
            title = re.sub(r"\s*\{#[^}]*\}", "", title)
            if in_itemize:
                out.append(r"\end{itemize}")
                in_itemize = False
            out.append(f"\\paragraph{{{title}}}")
            out.append("")
            continue

        # Markdown unordered list (- item or * item)
        list_match = re.match(r"^[-*]\s+(.*)", stripped)
        if list_match:
            if not in_itemize:
                out.append(r"\begin{itemize}")
                in_itemize = True
            item_text = list_match.group(1)
            out.append(f"    \\item {item_text}")
            continue

        # Close itemize on blank line or non-list content
        if in_itemize and stripped == "":
            out.append(r"\end{itemize}")
            in_itemize = False
            out.append("")
            continue
        elif in_itemize and stripped and not re.match(r"^[-*]\s+", stripped):
            out.append(r"\end{itemize}")
            in_itemize = False

        out.append(line)

    if in_itemize:
        out.append(r"\end{itemize}")

    text = "\n".join(out)

    # Markdown images ![alt](url) -> comment
    text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"% [Image: \1]", text)

    # Markdown links [text](url) -> \href{url}{text}
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\\href{\2}{\1}", text)

    # Bold **text** -> \textbf{text}
    text = re.sub(r"\*\*(.+?)\*\*", r"\\textbf{\1}", text)

    # Italic *text* (single asterisks, not inside item markers)
    text = re.sub(r"(?<![\\*])\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"\\textit{\1}", text)

    return text


def sanitise(raw: str) -> str:
    """Full pipeline for body text."""
    if not raw:
        return ""
    text = strip_scripts(raw)
    text = unescape_entities(text)
    text = strip_html_tags(text)

    # Extract math before any escaping or markdown conversion
    text, math_blocks = _extract_math(text)

    text = latex_escape_plain(text)
    text = md_to_latex(text)

    # Clean up any leftover markdown heading markers and anchor tags
    # that md_to_latex did not catch (e.g. headings inside item text).
    # Preserve # inside \href{...} and \textcolor{#...} by targeting only
    # line-leading hashes and {#...} anchor patterns.
    text = re.sub(r"^(#{1,6})\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\s*\{#[^}]*\}", "", text)

    # Restore math
    text = _restore_math(text, math_blocks)

    # 5f: collapse whitespace
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


def sanitise_title(raw: str) -> str:
    """Sanitise a title for use in \\chapter{} / \\section{}."""
    if not raw:
        return ""
    text = unescape_entities(raw)
    text = strip_html_tags(text)
    text = latex_escape_plain(text)
    return text.strip()


def parse_list(raw: str) -> list:
    """Return a list of item strings from a bullet or numbered raw field."""
    if not raw:
        return []
    text = strip_scripts(raw)
    text = unescape_entities(text)
    text = strip_html_tags(text)

    items = []
    current = []

    for line in text.splitlines():
        stripped = line.strip()
        is_item_start = (re.match(r"^\d+\.\s+", stripped)
                         or re.match(r"^[*-]\s+", stripped))
        if is_item_start:
            if current:
                items.append(" ".join(current))
            entry = re.sub(r"^\d+\.\s+", "", stripped)
            entry = re.sub(r"^[*-]\s+", "", entry)
            current = [entry]
        elif stripped and current:
            current.append(stripped)
        elif stripped and not current:
            current = [stripped]

    if current:
        items.append(" ".join(current))

    # Process each item: extract math, escape, markdown convert, restore
    result = []
    for item in items:
        # Strip markdown heading markers (## Part 1: ...) and anchors from items
        item = re.sub(r"#{1,6}\s+", "", item)
        item = re.sub(r"\s*\{#[^}]*\}", "", item)
        item, math_blocks = _extract_math(item)
        item = latex_escape_plain(item)
        # Bold **text** -> \textbf{text}
        item = re.sub(r"\*\*(.+?)\*\*", r"\\textbf{\1}", item)
        # Italic *text*
        item = re.sub(r"(?<![\\*])\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"\\textit{\1}", item)
        # Links
        item = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\\href{\2}{\1}", item)
        item = _restore_math(item, math_blocks)
        item = item.strip()
        if item:
            result.append(item)
    return result


def slugify(title: str) -> str:
    slug = title.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


FENCE = "%%" + "=" * 63


def chapter_comment(text: str, char: str = "%", width: int = 65) -> str:
    return char * width + "\n" + text + "\n" + char * width


def render_chapter(unit_num: int, xml_path: Path) -> str:
    tree = ET.parse(xml_path)
    root = tree.getroot()
    paginas = root.findall("pagina")

    if paginas:
        chapter_title = sanitise_title(
            paginas[0].findtext("title", ""))
    else:
        chapter_title = xml_path.stem

    lines = []
    lines.append(chapter_comment(
        f"\\chapter{{Unit {unit_num}: {chapter_title}}}\n"
        f"\\label{{chap:unit{unit_num}}}",
        char="%", width=65
    ))
    lines.append("")

    for pagina in paginas:
        title = sanitise_title(pagina.findtext("title", ""))
        long_desc = sanitise(pagina.findtext("long_description", ""))
        short_desc = sanitise(pagina.findtext("short_description", ""))
        body = long_desc or short_desc
        slo_items = parse_list(pagina.findtext("slo", ""))
        asmt_items = parse_list(pagina.findtext("assessment", ""))

        lines.append(FENCE)
        lines.append(f"\\section{{{title}}}")
        lines.append(f"\\label{{sec:{slugify(title)}}}")
        lines.append(FENCE)
        lines.append("")

        if body:
            lines.append(body)
            lines.append("")

        if slo_items:
            lines.append("\\subsection{Learning Objectives}")
            lines.append("")
            lines.append("\\begin{enumerate}")
            for item in slo_items:
                lines.append(f"    \\item {item}")
            lines.append("\\end{enumerate}")
            lines.append("")

        if asmt_items:
            lines.append("\\subsection{Assessment Instrument}")
            lines.append("")
            lines.append("\\begin{enumerate}")
            for item in asmt_items:
                lines.append(f"    \\item {item}")
            lines.append("\\end{enumerate}")
            lines.append("")

    return "\n".join(lines)


def cleanup_hashes(text: str) -> str:
    """Remove stray markdown # characters from generated LaTeX.

    Preserves # inside \\href{...} URLs, \\textcolor{#hex} color codes,
    and \\# escape sequences.
    """
    out_lines = []
    for line in text.split("\n"):
        # Skip lines that are LaTeX comments (%%===, %%%%%...)
        if line.lstrip().startswith("%"):
            out_lines.append(line)
            continue

        # Remove {#anchor_id} patterns (not inside \href)
        if "\\href" not in line:
            line = re.sub(r"\s*\{#[^}]*\}", "", line)
            # Remove [anchor] patterns from heading-like lines
            line = re.sub(r"\s*\[[a-z_\\]+\]$", "", line)

        # Remove leading markdown heading markers ("## or ### etc.)
        # Handles optional leading quote character
        line = re.sub(r'^(\s*)"?(#{1,6})\s*', r'\1', line)

        out_lines.append(line)
    return "\n".join(out_lines)


# -- main --------------------------------------------------------------------

def main():
    xml_files = []
    for p in DATA_DIR.glob("*.xml"):
        try:
            int(p.stem)
            xml_files.append(p)
        except ValueError:
            print(f"  [SKIP] {p.name} (non-numeric stem)")

    xml_files.sort(key=lambda p: int(p.stem))

    if not xml_files:
        print("No XML files found in", DATA_DIR)
        return

    generated = []
    for unit_num, xml_path in enumerate(xml_files, start=1):
        out_name = f"unit_{xml_path.stem}.tex"
        out_path = CURRICULUM / out_name
        try:
            content = render_chapter(unit_num, xml_path)
            content = cleanup_hashes(content)
            out_path.write_text(content, encoding="utf-8")
            print(f"  [OK] {out_path.name}")
            generated.append(out_name)
        except ET.ParseError as exc:
            print(f"  [ERR] {xml_path.name}: {exc}")

    # Patch MathCurriculum.tex
    master = MASTER_FILE.read_text(encoding="utf-8")
    input_block = "\n".join(f"    \\input{{{name}}}" for name in generated)
    m = re.search(
        r"(\\tableofcontents\s*\\newpage)(.*?)(\\end\{document\})",
        master,
        flags=re.DOTALL,
    )
    if m:
        master = master[:m.start(2)] + "\n\n" + input_block + "\n\n" + master[m.start(3):]
    MASTER_FILE.write_text(master, encoding="utf-8")
    print(f"  [OK] MathCurriculum.tex updated with {len(generated)} \\input lines.")


if __name__ == "__main__":
    main()
