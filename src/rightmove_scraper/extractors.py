from __future__ import annotations

import re

from lxml import html


def _text_content(node) -> str:
    if node is None:
        return ""
    return " ".join(node.itertext()).strip()


def get_title(doc: html.HtmlElement) -> str | None:
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


def get_price_text(doc: html.HtmlElement) -> str | None:
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


def get_summary_panel_value(doc: html.HtmlElement, label: str) -> str | None:
    xp = f'//dt[normalize-space()="{label}"]/following-sibling::dd[1]'
    nodes = doc.xpath(xp)
    if nodes:
        val = _text_content(nodes[0])
        return val or None
    return None


def get_key_features(doc: html.HtmlElement) -> list[str]:
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


def get_description(doc: html.HtmlElement) -> str | None:
    # Click-expansion is done in the browser step; here we read text
    for xp in [
        '//*[self::h2 or self::h3][contains(translate(normalize-space(), "DESCRIPTION", "description"), "description")]',
        '//*[contains(., "Description")]',
    ]:
        nodes = doc.xpath(xp)
        if nodes:
            texts: list[str] = []
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


def _fact_following_value(doc: html.HtmlElement, label: str) -> str | None:
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


def find_label_value_fuzzy(doc: html.HtmlElement, labels: list[str]) -> str | None:
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


def derive_from_key_features(features: list[str], keywords: list[str]) -> str | None:
    text = "\n".join(features).lower()
    for kw in keywords:
        if kw in text:
            # Return the first matching feature line
            for f in features:
                if kw in f.lower():
                    return f
    return None


def get_fact_after_description(doc: html.HtmlElement, label: str) -> str | None:
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


def get_fact_grid_value(doc: html.HtmlElement, label: str) -> str | None:
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


def get_fact_value(doc: html.HtmlElement, label: str) -> str | None:
    return _fact_following_value(doc, label)


def get_agent(doc: html.HtmlElement) -> str | None:
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


# New helpers per template.csv

def get_photo_urls(doc: html.HtmlElement, limit: int = 10) -> list[str]:
    """Extract up to `limit` full-size photo URLs in order.

    Heuristics:
    - Look for meta itemprop contentUrl under the photo collage
    - Fallback to <img> sources inside the photo collage/thumb strip
    - De-duplicate and keep order
    """
    urls: list[str] = []
    seen: set[str] = set()

    # 1) Prefer itemprop contentUrl nodes
    for xp in [
        '//*[@data-testid="photo-collage"]//meta[@itemprop="contentUrl"]/@content',
        '//meta[@itemprop="contentUrl" and contains(@content, "/IMG_")]/@content',
    ]:
        for u in doc.xpath(xp):
            if isinstance(u, str) and u and u not in seen:
                seen.add(u)
                urls.append(u)
                if len(urls) >= limit:
                    return urls

    # 2) Fallback to <img src> within collage/thumbs
    for xp in [
        '//*[@data-testid="photo-collage"]//img/@src',
        '//img[contains(@src, "/IMG_")]/@src',
    ]:
        for u in doc.xpath(xp):
            if isinstance(u, str) and u and u not in seen:
                seen.add(u)
                urls.append(u)
                if len(urls) >= limit:
                    return urls

    return urls[:limit]


def get_floorplan_url(doc: html.HtmlElement) -> str | None:
    """Extract a floorplan image URL if present.

    Normalize resized variants to the original full-size URL by:
    - Removing '/dir/' path segment (e.g., https://media.rightmove.co.uk/dir/88k/... -> https://media.rightmove.co.uk/88k/...)
    - Stripping '_max_{WxH}' suffix before extension (e.g., _max_296x197.png -> .png)
    """
    candidates = [
        '//img[contains(@src, "_FLP_")]/@src',
        '//meta[@itemprop="image" and contains(@content, "_FLP_")]/@content',
        '//a[contains(@href, "/floorplan")]/img/@src',
    ]
    def _normalize(u: str) -> str:
        v = u
        # Drop '/dir/' path segment
        v = v.replace("/dir/", "/")
        # Remove _max_{WxH} before extension
        v = re.sub(r"_max_\d+x\d+(?=\.)", "", v)
        return v

    for xp in candidates:
        vals = doc.xpath(xp)
        for v in vals:
            if isinstance(v, str) and v:
                return _normalize(v)
    return None


def get_agent_address(doc: html.HtmlElement) -> str | None:
    """Extract the agent address block near 'About <agent>' or 'MARKETED BY'."""
    # Try the aside contact panel address title tooltip
    nodes = doc.xpath('//div[@class="OojFk4MTxFDKIfqreGNt0" and @title]')
    if nodes:
        t = nodes[0].get("title") or ""
        t = t.strip()
        if t:
            # Address often contains newlines; normalize to lines separated by commas
            return re.sub(r"\s*,?\s*\n\s*", ",\n", t)

    # Fallback: textual block under About agent
    for xp in [
        '//*[self::h3][contains(., "About")]/following::*[contains(@class, "address")][1]',
        '//*[contains(@class, "aboutAgent")]//*[contains(@class, "address")]'
    ]:
        nodes = doc.xpath(xp)
        if nodes:
            text = _text_content(nodes[0])
            if text:
                return text
    return None


def get_agent_phone(doc: html.HtmlElement) -> str | None:
    # Look for tel: links or displayed numbers near contact tray
    for xp in [
        '//a[starts-with(@href, "tel:")]/@href',
        '//*[contains(@class, "contact-agent-tray")]//a[starts-with(@href, "tel:")]/@href',
        '//a[contains(@href, "propertyId") and contains(., "Call agent")]/following::a[starts-with(@href, "tel:")][1]/@href'
    ]:
        vals = doc.xpath(xp)
        for v in vals:
            if isinstance(v, str) and v.startswith("tel:"):
                num = re.sub(r"[^0-9]", "", v)
                if num:
                    # Keep local dialing format if present (e.g., 02039106089)
                    return num
    # Sometimes presented as plain text next to icon
    txt_nodes = doc.xpath('//*[contains(@class, "contact-agent")]//*[contains(text(), "020") or contains(text(), "01") or contains(text(), "+44")]//text()')
    if txt_nodes:
        txt = "".join([t.strip() for t in txt_nodes]).strip()
        m = re.search(r"(\+44\s?\d[\d\s]{8,}|0\d{9,})", txt)
        if m:
            return re.sub(r"\s+", "", m.group(1))
    return None


def get_lat_lng(doc: html.HtmlElement) -> tuple[float | None, float | None]:
    """Attempt to extract latitude/longitude from embedded scripts or map widgets.

    If not present, return (None, None). Snapshot pages sometimes omit coordinates.
    """
    # Try JSON blobs on window.PAGE_MODEL/adInfo if present
    script_texts = doc.xpath('//script[contains(text(), "propertyData")]//text()')
    for s in script_texts:
        try:
            # Look for patterns like "latitude":51.xxx, "longitude":-0.xxx
            mlat = re.search(r'\"latitude\"\s*:\s*(-?\d+\.\d+)', s)
            mlng = re.search(r'\"longitude\"\s*:\s*(-?\d+\.\d+)', s)
            if mlat and mlng:
                return float(mlat.group(1)), float(mlng.group(1))
        except Exception:
            pass
    return None, None


def get_listing_history(doc: html.HtmlElement) -> str | None:
    """Extract recent listing history snippet (e.g., 'Reduced on 10/06/2025')."""
    # The history often appears near the mortgage widget/price area
    for xp in [
        '//*[contains(@class, "_1q3dx8PQU8WWiT7uw7J9Ck")]//div[contains(@class, "_2nk2x6QhNB1UrxdI5KpvaF")]',
        '//*[contains(., "Reduced on") or contains(., "Added on")]'
    ]:
        nodes = doc.xpath(xp)
        for n in nodes:
            txt = _text_content(n)
            if not txt:
                continue
            m = re.search(r"(Reduced on\s+\d{2}/\d{2}/\d{4}|Added on\s+\d{2}/\d{2}/\d{4})", txt)
            if m:
                return m.group(1)
    return None

