# Transformation Specification: `Data/*.xml` → `curriculum/unit_*.tex` + `MathCurriculum.tex`

---

## 1. Purpose

Produce one LaTeX chapter file per XML file found in `Data/`, following the
structure of `curriculum/unit8_JHS.tex`, then register every generated file
in `curriculum/MathCurriculum.tex` in ascending numeric order of the source
file ID.

---

## 2. Source: XML Schema

Each file in `Data/` is named `<ID>.xml` where `<ID>` is a positive integer
(the `id_opus` / course identifier).  The root element is `<opus>`.  Each
child is a `<pagina>` representing one lesson (section).

```
<opus>
  <pagina id_pagina="N" pagina_type="PRE-REQ | ROOT | (empty)">
    <title>…</title>                   ← plain text, section heading
    <short_description>…</short_description>   ← plain text or empty
    <long_description>…</long_description>     ← HTML-encoded body text
    <slo>…</slo>                       ← bullet list, items prefixed with "* "
    <assessment>…</assessment>         ← plain text or bullet list
  </pagina>
  …
</opus>
```

**Known quirks:**

| Quirk | Handling |
|---|---|
| `<long_description>` contains HTML entities (`&lt;`, `&gt;`, `&#13;`) and tags (`<p>`, `<ul>`, `<li>`, `<script>`, etc.) | Strip `<script>…</script>` blocks entirely; unescape HTML entities; strip remaining HTML tags; collapse blank lines |
| `<slo>` items are separated by `\n* ` | Split on `\n*` and trim each item |
| `<assessment>` may contain numbered lines (`1. text`) or `* `-prefixed bullets | Normalise to a single enumerate list |
| Some fields are empty or absent | Omit the corresponding LaTeX subsection entirely |
| `&#13;` (carriage return entity) | Treat as whitespace / line break |

---

## 3. Target: LaTeX Chapter Structure

Model: `curriculum/unit8_JHS.tex`.  Every generated file must follow this
skeleton exactly, with sections derived from `<pagina>` elements and
subsections from `<slo>` / `<assessment>`.

```latex
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
\chapter{Unit <UNIT_NUM>: <CHAPTER_TITLE>}
\label{chap:unit<UNIT_NUM>}
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

%================================================================
\section{<PAGINA_TITLE>}
\label{sec:<SECTION_LABEL>}
%================================================================

<BODY_TEXT>

\subsection{Learning Objectives}   % omit block if <slo> is empty

\begin{enumerate}
    \item <SLO_ITEM_1>
    \item <SLO_ITEM_2>
    …
\end{enumerate}

\subsection{Assessment Instrument}   % omit block if <assessment> is empty

\begin{enumerate}
    \item <ASSESSMENT_ITEM_1>
    …
\end{enumerate}
```

Repeat the `\section{…}` block once per `<pagina>` in document order
(`id_pagina` ascending).

---

## 4. Field Mapping

| LaTeX element | XML source | Notes |
|---|---|---|
| `<UNIT_NUM>` | Rank of the file in the sorted list of all XML IDs | 1-based integer; e.g., `1023.xml` is rank 1 if it is the lowest ID present |
| `<CHAPTER_TITLE>` | `<title>` of the **first** `<pagina>` in the file | Use as-is after LaTeX-escaping |
| `\label{chap:unit<N>}` | Derived from `<UNIT_NUM>` | `\label{chap:unit1}`, `\label{chap:unit2}`, … |
| `<PAGINA_TITLE>` | `<title>` of each `<pagina>` | LaTeX-escaped |
| `<SECTION_LABEL>` | Slugified `<title>`: lowercase, spaces → hyphens, strip non-alphanumeric | e.g., `"Problem Solving Introduction"` → `sec:problem-solving-introduction` |
| `<BODY_TEXT>` | Sanitised `<long_description>` (primary) or `<short_description>` (fallback if long is empty) | See §5 |
| `\item` under *Learning Objectives* | Each bullet in `<slo>` | See §5 |
| `\item` under *Assessment Instrument* | Each item in `<assessment>` | See §5 |

---

## 5. Text Sanitisation Rules

Apply these transformations **in order** to `<long_description>`,
`<short_description>`, `<slo>`, and `<assessment>` before embedding in LaTeX.

### 5a. Strip script blocks
Remove everything matching `<script[^>]*>…</script>` (case-insensitive,
including multi-line).  These contain platform-specific calls
(`LoadWiki`, `LoadPDF`, etc.) that have no LaTeX equivalent.

### 5b. Unescape HTML entities
Convert `&lt;` → `<`, `&gt;` → `>`, `&amp;` → `&`, `&#13;` → newline,
`&nbsp;` → space, numeric entities (`&#NNN;`) → their Unicode characters.
Use a standard HTML-entity decoder (e.g., `html.unescape` in Python).

### 5c. Strip remaining HTML tags
Remove all `<…>` tags.  Treat `<li>` and `<p>` as paragraph/line-break
signals before stripping: replace `<li>` with `\n* ` and `<p>` with `\n\n`
so the list structure is preserved for step 5e.

### 5d. LaTeX-escape special characters
In the resulting plain text, escape: `&` → `\&`, `%` → `\%`,
`$` → `\$`, `#` → `\#`, `_` → `\_`, `{` → `\{`, `}` → `\}`,
`~` → `\textasciitilde{}`, `^` → `\textasciicircum{}`,
`\` → `\textbackslash{}`.

### 5e. Parse bullet lists in `<slo>` and `<assessment>`
Split on line boundaries, detect lines starting with `*` or a digit+`.`
as list items, strip the prefix marker, and trim whitespace.  Each item
becomes one `\item` in the enumerate.

### 5f. Collapse whitespace
Reduce three or more consecutive blank lines to a single blank line.
Trim leading/trailing whitespace from each paragraph.

### 5g. Empty result
If after sanitisation a field is empty or contains only whitespace, omit
the corresponding LaTeX block entirely (no empty `\begin{enumerate}…\end{enumerate}`
or empty `\subsection`).

---

## 6. Output File Naming

```
curriculum/unit_<ID>.tex
```

`<ID>` is the numeric stem of the source XML filename, zero-padded to match
the longest ID in the set (currently 4 digits, e.g., `unit_1023.tex`,
`unit_4233.tex`).

> **Do not** reuse existing hand-authored filenames (`unit1_ethics.tex`, etc.).
> The new auto-generated files coexist with them in the `curriculum/` folder.

---

## 7. Chapter / Unit Numbering

1. Collect all `*.xml` files in `Data/`.
2. Extract the numeric stem from each filename.
3. Sort the list **numerically ascending**.
4. Assign `UNIT_NUM = 1, 2, 3, …` in that order.

Example (from `extract_opus.py` COURSE_IDS after deduplication and sort):

| Rank | ID | Output file |
|---|---|---|
| 1 | 1023 | `unit_1023.tex` |
| 2 | 1043 | `unit_1043.tex` |
| 3 | 1053 | `unit_1053.tex` |
| 4 | 1073 | `unit_1073.tex` |
| 5 | 1093 | `unit_1093.tex` |
| 6 | 1133 | `unit_1133.tex` |
| 7 | 1193 | `unit_1193.tex` |
| 8 | 1214 | `unit_1214.tex` |
| … | … | … |

---

## 8. Master File Update (`MathCurriculum.tex`)

Locate the block between `\tableofcontents \newpage` and `\end{document}`.
Replace **all existing `\input{…}` lines in that block** with a fresh
auto-generated list, one line per unit in ascending order:

```latex
    \input{unit_1023.tex}
    \input{unit_1043.tex}
    \input{unit_1053.tex}
    …
    \input{unit_4233.tex}
```

> **Preserve** everything outside that block (preamble, `\input{../common/…}`,
> `\tableofcontents`, `\end{document}`).

---

## 9. Implementation Notes (Python)

```python
from pathlib import Path
import xml.etree.ElementTree as ET
import html, re

DATA_DIR     = Path("Data")
CURRICULUM   = Path("curriculum")
MASTER_FILE  = CURRICULUM / "MathCurriculum.tex"

# ── helpers ──────────────────────────────────────────────────────────────────

def sanitise(raw: str) -> str:
    """Full pipeline: strip scripts → unescape → strip tags → LaTeX-escape → clean."""
    if not raw:
        return ""
    # 5a — strip script blocks
    text = re.sub(r"<script[^>]*>.*?</script>", "", raw, flags=re.DOTALL | re.IGNORECASE)
    # 5c — mark list/paragraph breaks before unescaping (raw may still be HTML-encoded)
    text = re.sub(r"&lt;li&gt;",  r"\n* ",  text, flags=re.IGNORECASE)
    text = re.sub(r"&lt;p&gt;",   r"\n\n",  text, flags=re.IGNORECASE)
    text = re.sub(r"&lt;/\w+&gt;", "",       text, flags=re.IGNORECASE)
    # 5b — HTML-unescape
    text = html.unescape(text)
    # 5c — strip remaining tags (already-decoded)
    text = re.sub(r"<li[^>]*>",  r"\n* ",  text, flags=re.IGNORECASE)
    text = re.sub(r"<p[^>]*>",   r"\n\n",  text, flags=re.IGNORECASE)
    text = re.sub(r"</?\w+[^>]*>", "",       text)
    # 5d — LaTeX-escape  (order matters: backslash first)
    for char, repl in [
        ("\\", r"\textbackslash{}"),
        ("&",  r"\&"),
        ("%",  r"\%"),
        ("$",  r"\$"),
        ("#",  r"\#"),
        ("_",  r"\_"),
        ("{",  r"\{"),
        ("}",  r"\}"),
        ("~",  r"\textasciitilde{}"),
        ("^",  r"\textasciicircum{}"),
    ]:
        text = text.replace(char, repl)
    # 5f — collapse whitespace
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text

def parse_list(raw: str) -> list[str]:
    """Return a list of item strings from a bullet or numbered raw field."""
    text = sanitise(raw)
    items = []
    for line in text.splitlines():
        line = line.strip()
        if re.match(r"^\*\s+", line):
            items.append(re.sub(r"^\*\s+", "", line))
        elif re.match(r"^\d+\.\s+", line):
            items.append(re.sub(r"^\d+\.\s+", "", line))
        elif line:
            items.append(line)
    return [i for i in items if i]

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

    chapter_title = sanitise(paginas[0].findtext("title", "")) if paginas else xml_path.stem

    lines = []
    lines.append(chapter_comment(
        f"\\chapter{{Unit {unit_num}: {chapter_title}}}\n"
        f"\\label{{chap:unit{unit_num}}}",
        char="%", width=65
    ))
    lines.append("")

    for pagina in paginas:
        title      = sanitise(pagina.findtext("title", ""))
        long_desc  = sanitise(pagina.findtext("long_description", ""))
        short_desc = sanitise(pagina.findtext("short_description", ""))
        body       = long_desc or short_desc
        slo_items  = parse_list(pagina.findtext("slo", ""))
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


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    xml_files = sorted(DATA_DIR.glob("*.xml"), key=lambda p: int(p.stem))

    generated = []
    for unit_num, xml_path in enumerate(xml_files, start=1):
        out_name = f"unit_{xml_path.stem}.tex"
        out_path = CURRICULUM / out_name
        content  = render_chapter(unit_num, xml_path)
        out_path.write_text(content, encoding="utf-8")
        print(f"  [OK] {out_path}")
        generated.append(out_name)

    # Patch MathCurriculum.tex
    master = MASTER_FILE.read_text(encoding="utf-8")
    input_block = "\n".join(f"    \\input{{{name}}}" for name in generated)
    master = re.sub(
        r"(\\tableofcontents\s*\\newpage)(.*?)(\\end\{document\})",
        rf"\1\n\n{input_block}\n\n\3",
        master,
        flags=re.DOTALL,
    )
    MASTER_FILE.write_text(master, encoding="utf-8")
    print(f"  [OK] {MASTER_FILE} updated with {len(generated)} \\input lines.")

if __name__ == "__main__":
    main()
```

---

## 10. Edge Cases

| Scenario | Rule |
|---|---|
| Duplicate IDs in `COURSE_IDS` (e.g., `1073` appears twice in `extract_opus.py`) | Only one `1073.xml` exists on disk; the duplicate is silently ignored by the glob |
| `<pagina>` with all empty content fields | Generate the `\section` heading and label; omit body, `\subsection{Learning Objectives}`, and `\subsection{Assessment Instrument}` |
| `<title>` contains LaTeX special characters (e.g., `&`, `%`) | LaTeX-escape via step 5d before embedding in `\chapter{}`, `\section{}`, `\label{}` |
| `<long_description>` is entirely a `<script>` block | After stripping, result is empty → fall back to `<short_description>` |
| `<slo>` contains free-form prose (no bullet prefix) | Treat entire text as a single `\item` |
| New XML files added to `Data/` later | Re-running `main()` regenerates all `.tex` files and re-patches the master; idempotent |
| Existing hand-authored `unit1_ethics.tex` … `unit8_JHS.tex` | Not touched; only `\input{}` lines in the master block are replaced |
