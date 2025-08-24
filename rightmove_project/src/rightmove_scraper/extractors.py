from __future__ import annotations

from typing import List, Optional
from lxml import html
import re


def _text_content(node) -> str:
    if node is None:
        return ""
    return " ".join(node.itertext()).strip()


def get_title(doc: html.HtmlElement) -> Optional[str]:
    # Common selector for title header
    for xp in [
        '//h1[contains(@class, "_2uQQ3SV0eMHL1P6t5ZDo2q")]',
        '//h1',
    ]:
        nodes = doc.xpath(xp)
        if nodes:
            text = _text_content(nodes[0])
            if text:
                return text
    return None


def get_price_text(doc: html.HtmlElement) -> Optional[str]:
    # Rightmove price often in elements with data-testid or specific classes
    candidates = [
        '//*[@data-testid="price"]',
        '//*[contains(@class, "_1gfnqJ3Vtd1z40MlC0MzXu")]//text()',
        '//*[contains(@class, "property-header-price")]//text()',
        '//*[contains(@class, "price")]//text()',
        '//span[contains(., "£")]//text()',
    ]
    for xp in candidates:
        try:
            nodes = doc.xpath(xp)
        except Exception:
            nodes = []
        if not nodes:
            continue
        if isinstance(nodes[0], str):
            text = " ".join([n.strip() for n in nodes if isinstance(n, str)]).strip()
        else:
            text = _text_content(nodes[0])
        text = " ".join(text.split())
        if not text:
            continue
        # Clean trailing helper sentences; keep the first currency amount phrase
        m = re.search(r"(£\s?\d{1,3}(?:,\d{3})+)", text)
        if m:
            return m.group(1).replace(" ", "")
        return text
    return None


def get_summary_panel_value(doc: html.HtmlElement, label: str) -> Optional[str]:
    xp = f'//dt[normalize-space()="{label}"]/following-sibling::dd[1]'
    nodes = doc.xpath(xp)
    if nodes:
        val = _text_content(nodes[0])
        return val or None
    return None


def get_key_features(doc: html.HtmlElement) -> List[str]:
    headings = doc.xpath('//*[self::h2 or self::h3][contains(normalize-space(), "Key features")]')
    if headings:
        h = headings[0]
        ul = h.getnext()
        if ul is not None and ul.tag.lower() == "ul":
            lis = [" ".join(li.itertext()).strip() for li in ul.xpath(".//li")] 
            return [x for x in lis if x]
    # Fallback: search any UL with key features near text
    ul_nodes = doc.xpath('//ul[ancestor::*[contains(., "Key features")]]')
    for ul in ul_nodes:
        lis = [" ".join(li.itertext()).strip() for li in ul.xpath(".//li")] 
        out = [x for x in lis if x]
        if out:
            return out
    return []


def get_description(doc: html.HtmlElement) -> Optional[str]:
    # Click-expansion is done in the browser step; here we read text
    for xp in [
        '//*[self::h2 or self::h3][contains(translate(normalize-space(), "DESCRIPTION", "description"), "description")]',
        '//*[contains(., "Description")]',
    ]:
        nodes = doc.xpath(xp)
        if nodes:
            texts: List[str] = []
            n = nodes[0]
            cur = n.getnext()
            while cur is not None and cur.tag.lower() not in {"h2", "h3"}:
                txt = " ".join(cur.itertext()).strip()
                if txt:
                    texts.append(txt)
                cur = cur.getnext()
            result = "\n\n".join(texts).strip()
            if result:
                return result
    return None


def _fact_following_value(doc: html.HtmlElement, label: str) -> Optional[str]:
    # Try multiple patterns; Rightmove can render these in different panels
    xps = [
        f'//*[normalize-space()="{label}"]/following::*[1][self::div or self::span or self::p]',
        f'//dt[normalize-space()="{label}"]/following-sibling::dd[1]',
        f'//*[contains(translate(normalize-space(), " ", ""), "{label.lower().replace(" ", "")}")]/following::*[1]'
    ]
    for xp in xps:
        nodes = doc.xpath(xp)
        if nodes:
            val = _text_content(nodes[0])
            if val:
                return val
    return None


def find_label_value_fuzzy(doc: html.HtmlElement, labels: list[str]) -> Optional[str]:
    # Try several heuristics near the label text
    for label in labels:
        # 1) Exact text node containing label then next sibling
        xp_list = [
            f'//*[contains(translate(normalize-space(), "abcdefghijklmnopqrstuvwxyz", "ABCDEFGHIJKLMNOPQRSTUVWXYZ"), "{label.upper()}")]/following::*[1][self::span or self::div or self::dd or self::p]',
            f'//dt[contains(., "{label}")]/following-sibling::dd[1]',
            f'//*[contains(., "{label}")]/following::*[1]'
        ]
        for xp in xp_list:
            nodes = doc.xpath(xp)
            if nodes:
                val = _text_content(nodes[0])
                if val:
                    return val
    return None


def derive_from_key_features(features: List[str], keywords: list[str]) -> Optional[str]:
    text = "\n".join(features).lower()
    for kw in keywords:
        if kw in text:
            # Return the first matching feature line
            for f in features:
                if kw in f.lower():
                    return f
    return None


def get_fact_after_description(doc: html.HtmlElement, label: str) -> Optional[str]:
    """Extract a labelled fact specifically from the section shown under the Description area.

    Strategy:
    - Find the Description header (h2/h3) first
    - Prefer searching after a 'Show less' anchor if present, else search after the header
    - Locate the first node whose text equals the label (case-insensitive)
    - Return text of the immediate following block node (div/span/p/dd)
    """
    hdrs = doc.xpath(
        '//*[self::h2 or self::h3][contains(translate(normalize-space(), "abcdefghijklmnopqrstuvwxyz", "ABCDEFGHIJKLMNOPQRSTUVWXYZ"), "DESCRIPTION")]'
    )
    if not hdrs:
        return None
    anchor = hdrs[0]
    show_less = anchor.xpath('following::*[normalize-space()="Show less"][1]')
    if show_less:
        anchor = show_less[0]

    label_upper = label.upper()
    # Match nodes that start with the label text (to allow glossary text after the label)
    label_nodes = anchor.xpath(
        f'following::*[starts-with(translate(normalize-space(), "abcdefghijklmnopqrstuvwxyz", "ABCDEFGHIJKLMNOPQRSTUVWXYZ"), "{label_upper}")] | '
        f'following::*[contains(translate(normalize-space(), "abcdefghijklmnopqrstuvwxyz", "ABCDEFGHIJKLMNOPQRSTUVWXYZ"), "{label_upper}")]'
    )
    if not label_nodes:
        return None
    lbl = label_nodes[0]
    # Scan a few following block nodes to skip glossary helper text
    candidates = lbl.xpath('following::*[self::div or self::span or self::p or self::dd][position()<=10]')
    def clean(txt: str) -> str:
        return " ".join(txt.split())
    for node in candidates:
        txt = clean(_text_content(node))
        if not txt:
            continue
        # Skip glossary/help sentences
        if any(k in txt.lower() for k in [
            "read more", "glossary", "payment", "details", "how and where vehicles",
            "has been adapted", "outdoor space"
        ]):
            continue
        if label.upper().startswith("COUNCIL TAX"):
            m = re.search(r"Band\s*:\s*([A-Ha-h])", txt)
            if m:
                return f"Band: {m.group(1).upper()}"
            if txt.lower() in {"ask agent", "not available"}:
                return txt.title() if txt != "not available" else "Not available"
            continue
        # Parking / Garden / Accessibility usually short answers
        if txt.lower() in {"yes", "no", "ask agent"}:
            return txt.title() if txt != "ask agent" else "Ask agent"
        # As a last resort, if the text is short (<40 chars), take it
        if len(txt) <= 40:
            return txt
    return None


def get_fact_grid_value(doc: html.HtmlElement, label: str) -> Optional[str]:
    """Find value from dl/dt/dd grids where dt starts with the label text.

    This targets the Facts row under the Description area on Rightmove which
    renders as <dl><dt>LABEL…</dt><dd>VALUE</dd>…</dl> with glossary hints in dt.
    """
    label_upper = label.upper()
    nodes = doc.xpath(
        f'//dl//dt[starts-with(translate(normalize-space(), "abcdefghijklmnopqrstuvwxyz", "ABCDEFGHIJKLMNOPQRSTUVWXYZ"), "{label_upper}")]/following-sibling::dd[1]'
    )
    if nodes:
        val = _text_content(nodes[0]).strip()
        return val or None
    return None


def get_fact_value(doc: html.HtmlElement, label: str) -> Optional[str]:
    return _fact_following_value(doc, label)


def get_agent(doc: html.HtmlElement) -> Optional[str]:
    for xp in [
        '//*[self::h2 or self::h3][contains(., "MARKETED BY")]/following::*[1]',
        '//*[contains(., "MARKETED BY")]/following::*[1]',
    ]:
        nodes = doc.xpath(xp)
        if nodes:
            text = _text_content(nodes[0])
            if text:
                return text
    return None


