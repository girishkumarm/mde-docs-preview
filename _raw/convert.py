#!/usr/bin/env python3
"""
Confluence storage-format HTML -> Mintlify MDX converter.
Handles: ac:structured-macro (info/warning/note/code/expand/panel/status),
         ac:image, ac:link, ac:task-list, tables, headers, lists, code.
"""
from __future__ import annotations
import re, html, json, pathlib, sys
from xml.etree import ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT.parent

NS = {
    'ac': 'http://www.atlassian.com/schema/confluence/4/ac/',
    'ri': 'http://www.atlassian.com/schema/confluence/4/ri/',
}

def register():
    for k, v in NS.items():
        ET.register_namespace(k, v)

register()

def strip_ns(tag: str) -> str:
    return tag.split('}', 1)[1] if '}' in tag else tag


def parse(html_text: str):
    # Wrap in root to make it valid XML. Confluence uses HTML entities; map them.
    entities = {
        'nbsp': '&#160;', 'copy': '&#169;', 'reg': '&#174;', 'trade': '&#8482;',
        'mdash': '&#8212;', 'ndash': '&#8211;', 'hellip': '&#8230;',
        'lsquo': '&#8216;', 'rsquo': '&#8217;', 'ldquo': '&#8220;', 'rdquo': '&#8221;',
        'bull': '&#8226;', 'middot': '&#183;', 'deg': '&#176;', 'times': '&#215;',
        'uarr': '&#8593;', 'darr': '&#8595;', 'larr': '&#8592;', 'rarr': '&#8594;',
        'infin': '&#8734;', 'ge': '&#8805;', 'le': '&#8804;', 'ne': '&#8800;',
        'alpha': '&#945;', 'beta': '&#946;', 'gamma': '&#947;', 'delta': '&#948;',
        'sigma': '&#963;', 'mu': '&#956;', 'pi': '&#960;', 'tau': '&#964;',
        'shy': '&#173;', 'amp': '&#38;',
    }
    text = html_text
    def repl(m):
        name = m.group(1)
        return entities.get(name, f"&amp;{name};")
    text = re.sub(r'&([a-zA-Z]+);', repl, text)
    # Wrap
    wrapped = f'<root xmlns:ac="{NS["ac"]}" xmlns:ri="{NS["ri"]}">{text}</root>'
    try:
        return ET.fromstring(wrapped)
    except ET.ParseError as e:
        print(f"  [parse error] {e}", file=sys.stderr)
        # Try aggressive HTML entity escape
        wrapped2 = re.sub(r'&(?![a-zA-Z]+;|#[0-9]+;|#x[0-9a-fA-F]+;)', '&amp;', text)
        wrapped2 = f'<root xmlns:ac="{NS["ac"]}" xmlns:ri="{NS["ri"]}">{wrapped2}</root>'
        return ET.fromstring(wrapped2)


def text_of(elem) -> str:
    """Full text content of an element, including children."""
    parts = []
    if elem.text:
        parts.append(elem.text)
    for c in elem:
        parts.append(text_of(c))
        if c.tail:
            parts.append(c.tail)
    return ''.join(parts)


def get_param(macro_elem, name):
    for p in macro_elem.findall(f'{{{NS["ac"]}}}parameter'):
        if p.get(f'{{{NS["ac"]}}}name') == name:
            return (p.text or '').strip()
    return None


def macro_body(macro_elem):
    body = macro_elem.find(f'{{{NS["ac"]}}}rich-text-body')
    if body is None:
        body = macro_elem.find(f'{{{NS["ac"]}}}plain-text-body')
    return body


def render(elem, ctx):
    """Render element to MDX-ish markdown."""
    tag = strip_ns(elem.tag)

    # ---- Confluence ac:* macros ----
    if tag == 'structured-macro':
        return render_macro(elem, ctx)

    if tag == 'image':
        return render_image(elem, ctx)

    if tag == 'link':
        return render_link(elem, ctx)

    if tag == 'task-list':
        items = []
        for t in elem.findall(f'{{{NS["ac"]}}}task'):
            status = t.find(f'{{{NS["ac"]}}}task-status')
            body = t.find(f'{{{NS["ac"]}}}task-body')
            mark = 'x' if status is not None and (status.text or '').strip() == 'complete' else ' '
            body_md = render_children(body, ctx).strip() if body is not None else ''
            items.append(f"- [{mark}] {body_md}")
        return '\n'.join(items) + '\n\n'

    if tag == 'emoticon':
        name = elem.get(f'{{{NS["ac"]}}}name') or ''
        emoji = {'check-mark': '✅','cross-mark': '❌','warning': '⚠️','information': 'ℹ️','tick': '✅','question': '❓'}
        return emoji.get(name, f":{name}:")

    if tag == 'placeholder':
        return ''

    # ---- HTML tags ----
    if tag in ('h1','h2','h3','h4','h5','h6'):
        level = int(tag[1])
        txt = render_children(elem, ctx).strip()
        return f"\n{'#'*level} {txt}\n\n"

    if tag == 'p':
        inner = render_children(elem, ctx).strip()
        if not inner:
            return '\n'
        return inner + '\n\n'

    if tag in ('strong','b'):
        return f"**{render_children(elem, ctx)}**"
    if tag in ('em','i'):
        return f"*{render_children(elem, ctx)}*"
    if tag == 'u':
        return render_children(elem, ctx)  # MDX has no underline; plain
    if tag in ('s','del','strike'):
        return f"~~{render_children(elem, ctx)}~~"
    if tag == 'code':
        return f"`{render_children(elem, ctx)}`"
    if tag == 'br':
        return '\n'
    if tag == 'hr':
        return '\n---\n\n'
    if tag == 'a':
        href = elem.get('href','')
        txt = render_children(elem, ctx).strip() or href
        return f"[{txt}]({href})"

    if tag == 'ul':
        out = []
        for li in elem.findall('li'):
            item = render_children(li, ctx).strip()
            out.append(f"- {item}")
        return '\n'.join(out) + '\n\n'
    if tag == 'ol':
        out = []
        for i, li in enumerate(elem.findall('li'), 1):
            item = render_children(li, ctx).strip()
            out.append(f"{i}. {item}")
        return '\n'.join(out) + '\n\n'
    if tag == 'li':
        return render_children(elem, ctx)

    if tag == 'table':
        return render_table(elem, ctx)

    if tag in ('thead','tbody','tr','th','td','colgroup','col','caption'):
        return render_children(elem, ctx)

    if tag == 'pre':
        return f"\n```\n{text_of(elem).strip()}\n```\n\n"

    if tag in ('span', 'div', 'root', 'time'):
        return render_children(elem, ctx)

    if tag == 'blockquote':
        inner = render_children(elem, ctx).strip()
        lines = inner.splitlines()
        return '\n' + '\n'.join(f"> {l}" for l in lines) + '\n\n'

    # Unknown tag: fall through
    return render_children(elem, ctx)


def render_children(elem, ctx):
    if elem is None:
        return ''
    parts = []
    if elem.text:
        parts.append(elem.text)
    for c in elem:
        parts.append(render(c, ctx))
        if c.tail:
            parts.append(c.tail)
    return ''.join(parts)


def render_macro(elem, ctx):
    name = elem.get(f'{{{NS["ac"]}}}name') or ''
    body = macro_body(elem)

    if name in ('info','tip'):
        content = render_children(body, ctx).strip() if body is not None else ''
        return f"\n<Info>\n{content}\n</Info>\n\n"
    if name == 'note':
        content = render_children(body, ctx).strip() if body is not None else ''
        return f"\n<Note>\n{content}\n</Note>\n\n"
    if name == 'warning':
        content = render_children(body, ctx).strip() if body is not None else ''
        return f"\n<Warning>\n{content}\n</Warning>\n\n"
    if name in ('panel','status'):
        content = render_children(body, ctx).strip() if body is not None else ''
        title = get_param(elem, 'title') or ''
        if name == 'status':
            return f"`{title or content}`"
        if title:
            return f"\n<Note>\n**{title}**\n\n{content}\n</Note>\n\n"
        return f"\n<Note>\n{content}\n</Note>\n\n"

    if name == 'code':
        lang = get_param(elem, 'language') or ''
        plain = elem.find(f'{{{NS["ac"]}}}plain-text-body')
        code = (plain.text or '').strip() if plain is not None else ''
        # Remove CDATA markers if any
        return f"\n```{lang}\n{code}\n```\n\n"

    if name == 'expand':
        title = get_param(elem, 'title') or 'Details'
        content = render_children(body, ctx).strip() if body is not None else ''
        return f"\n<Accordion title=\"{title}\">\n{content}\n</Accordion>\n\n"

    if name == 'toc':
        return ''  # Mintlify has auto-TOC

    if name == 'children':
        return ''  # Handled by docs.json nav

    if name == 'details':
        # Details macro — render children
        content = render_children(body, ctx).strip() if body is not None else ''
        return f"\n{content}\n\n"

    if name == 'status':
        title = get_param(elem, 'title') or ''
        color = get_param(elem, 'colour') or ''
        return f"`{title}`"

    if name == 'drawio':
        # Drawio: reference PNG with same name in attachments
        diagram_name = get_param(elem, 'diagramName') or get_param(elem, 'name') or 'diagram'
        return f"\n![{diagram_name}](/images/{ctx.get('page_id','')}/{diagram_name}.png)\n\n"

    if name == 'excerpt' or name == 'excerpt-include':
        content = render_children(body, ctx).strip() if body is not None else ''
        return content + '\n\n'

    if name == 'anchor':
        # Named anchor
        return ''

    if name == 'jira':
        key = get_param(elem, 'key') or ''
        return f"[{key}](https://paytmmoney.atlassian.net/browse/{key})"

    if name == 'link':
        return render_children(body, ctx) if body is not None else ''

    # Unknown macro — render body if present, else name
    if body is not None:
        return render_children(body, ctx)
    return ''


def render_image(elem, ctx):
    att = elem.find(f'{{{NS["ri"]}}}attachment')
    url = elem.find(f'{{{NS["ri"]}}}url')
    alt = elem.get(f'{{{NS["ac"]}}}alt') or ''
    if att is not None:
        fname = att.get(f'{{{NS["ri"]}}}filename') or ''
        # Prefer SVG if exists locally, else use filename as-is
        fname_sanitized = fname.replace(' ', '_')
        pid = ctx.get('page_id','')
        return f"\n![{alt or fname}](/images/{pid}/{fname_sanitized})\n\n"
    if url is not None:
        url_val = url.get('{%s}value' % NS["ri"])
        return f"\n![{alt}]({url_val})\n\n"
    return ''


def render_link(elem, ctx):
    att = elem.find(f'{{{NS["ri"]}}}attachment')
    page = elem.find(f'{{{NS["ri"]}}}page')
    body = elem.find(f'{{{NS["ac"]}}}plain-text-link-body')
    link_body = elem.find(f'{{{NS["ac"]}}}link-body')
    txt = ''
    if body is not None:
        txt = (body.text or '').strip()
    elif link_body is not None:
        txt = render_children(link_body, ctx).strip()
    if att is not None:
        fname = att.get(f'{{{NS["ri"]}}}filename') or ''
        pid = ctx.get('page_id','')
        return f"[{txt or fname}](/images/{pid}/{fname.replace(' ','_')})"
    if page is not None:
        pt = page.get(f'{{{NS["ri"]}}}content-title') or ''
        return f"[{txt or pt}](#)"
    return txt


def render_table(elem, ctx):
    """Render HTML table to markdown table."""
    rows = []
    tbody = elem.find('tbody') or elem
    # Collect all rows
    all_rows = list(elem.iter('tr'))
    if not all_rows:
        return ''
    for tr in all_rows:
        cells = []
        for cell in tr:
            if strip_ns(cell.tag) in ('th','td'):
                inner = render_children(cell, ctx).strip().replace('\n',' <br/> ').replace('|', '\\|')
                cells.append(inner or ' ')
        if cells:
            rows.append(cells)
    if not rows:
        return ''
    maxcols = max(len(r) for r in rows)
    # Pad
    rows = [r + [' '] * (maxcols - len(r)) for r in rows]
    # Build md
    header = rows[0]
    sep = ['---'] * maxcols
    body_rows = rows[1:] if len(rows) > 1 else []
    out = ['| ' + ' | '.join(header) + ' |',
           '| ' + ' | '.join(sep) + ' |']
    for r in body_rows:
        out.append('| ' + ' | '.join(r) + ' |')
    return '\n' + '\n'.join(out) + '\n\n'


def clean_output(md: str) -> str:
    # Collapse excess blank lines
    md = re.sub(r'\n{3,}', '\n\n', md)
    # Trim trailing whitespace per line
    md = '\n'.join(line.rstrip() for line in md.splitlines())
    # Unescape leftover HTML entities
    md = html.unescape(md)
    # Collapse "  " spaces not intentional
    md = re.sub(r'[ \t]+\n', '\n', md)
    return md.strip() + '\n'


PAGES = [
    ('683246061', 'root-tdd'),
    ('683475046', 'components-part1'),
    ('683278403', 'components-part2'),
    ('683278423', 'data-models-apis-jobs'),
    ('683376743', 'operations-deployment-migration'),
    ('697008500', 'devops-operating-guide'),
    ('697631021', 'candles-v2-prod-readiness'),
    ('697631042', 'candles-v2-canary-rollback'),
    ('698482839', 'v2-oncall-runbook'),
    ('698056921', 'v2-prod-readiness-checklist'),
    ('699236631', 'price-engine-migration'),
    ('693502030', 'architecture-diagrams'),
    ('697860144', 'kafka-vs-redis-defense'),
    ('698482697', 'candles-v2-running-dualsink'),
    ('697630920', 'candles-v2-diagram-downloads'),
]


def main():
    out_dir = OUT / '_converted'
    out_dir.mkdir(exist_ok=True)
    for pid, slug in PAGES:
        src = ROOT / f"{slug}-{pid}.html"
        meta = json.loads((ROOT / f"{slug}-{pid}.meta.json").read_text())
        html_text = src.read_text(encoding='utf-8')
        try:
            tree = parse(html_text)
        except ET.ParseError as e:
            print(f"  FAIL {slug}: {e}")
            continue
        ctx = {'page_id': pid}
        md = render(tree, ctx)
        md = clean_output(md)
        # Add front-matter
        fm = f"---\ntitle: \"{meta['title']}\"\n---\n\n"
        (out_dir / f"{slug}.mdx").write_text(fm + md)
        print(f"  ✓ {slug}.mdx  ({len(md):,} chars)")

if __name__ == '__main__':
    main()
