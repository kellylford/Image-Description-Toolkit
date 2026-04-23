"""
Workspace Statistics Dialog for ImageDescriber

Provides one-line-per-stat analysis of the current workspace, organized in
collapsible sections with separator headers. Topics covered:

- Workspace Overview (counts, file types, extracted frames)
- Descriptions (totals, multi-described items)
- Content Analysis (word counts, reading time, vocabulary richness)
- Writing Style (sentence length, thematic detection)
- Providers & Models (breakdown by provider/model/prompt)
- Location Summary (cities, states, countries, geographic spread)
- Token Usage (totals, averages, per-provider, peak image)
- Processing Performance (timing, throughput, projections)
- Activity Timeline (first/most-recent description, busiest day)

Accessibility: wx.ListBox with single tab stop; separator rows are
skipped on arrow-key navigation and cannot receive mouse focus.
"""

import math
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import List, Set, Tuple

import wx

# ── Stop-word list (common English + photography-specific filler) ──────────────
_STOPWORDS = {
    'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
    'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
    'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
    'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these',
    'those', 'it', 'its', 'they', 'them', 'their', 'there', 'here', 'as',
    'up', 'into', 'about', 'also', 'not', 'no', 'so', 'than', 'then',
    'which', 'what', 'who', 'how', 'when', 'where', 'if', 'just', 'while',
    'he', 'she', 'we', 'you', 'i', 'me', 'him', 'her', 'us', 'each',
    'both', 'through', 'during', 'before', 'after', 'above', 'below',
    'between', 'out', 'off', 'over', 'other', 'all', 'some', 'any', 'one',
    'two', 'three', 'across', 'along', 'around', 'near', 'behind',
    's', 't', 'don', 've', 'll', 're',
    # photography/description filler
    'appears', 'appear', 'visible', 'shows', 'show', 'see', 'seen',
    'large', 'small', 'several', 'many', 'few', 'various', 'different',
    'image', 'photo', 'photograph', 'picture', 'scene', 'view',
    'background', 'foreground', 'center', 'left', 'right', 'middle',
    'top', 'bottom', 'side', 'front', 'back', 'area', 'part', 'section',
    # technical metadata artefacts (added by _add_token_usage_info / workers_wx)
    'token', 'tokens', 'usage', 'prompt', 'completion', 'total', 'time',
    'processing', 'seconds', 'response', 'finish', 'reason',
}


def _strip_metadata_affixes(text: str) -> str:
    """Remove the two machine-generated affixes that workers_wx bakes into d.text.

    1. Location byline prefix  – "City, State - " (from _add_location_byline)
    2. Token/time suffix block – everything from "\\n\\n[Token Usage: …]"
       (from _add_token_usage_info)
    """
    # Strip token-usage/time block from the end first
    # Pattern: \n\n[ ... ] at end of string
    text = re.sub(r'\n\n\[Token Usage:[^\]]*\]\s*$', '', text, flags=re.DOTALL).strip()

    # Strip location byline from the beginning
    # Format is "Some Location Text - " where the dash is not inside a sentence
    # Limit prefix scan to first 80 chars to avoid stripping sentences
    prefix_match = re.match(r'^(.{4,60}?)\s+-\s+', text)
    if prefix_match:
        # Only strip if the prefix looks like a location (no sentence-ending punctuation)
        prefix = prefix_match.group(1)
        if not re.search(r'[.!?]', prefix):
            text = text[prefix_match.end():]

    return text

SEP = "─" * 52


def _split_words(text: str) -> List[str]:
    """Extract lowercase words from text."""
    return re.findall(r"[a-z][a-z']*", text.lower())


def _split_sentences(text: str) -> List[str]:
    """Split text into sentences (non-empty only)."""
    return [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]


def _fmt_dur(seconds: float) -> str:
    """Format duration to human-readable string."""
    if seconds < 60:
        return f"{seconds:.1f} sec"
    elif seconds < 3600:
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}m {secs}s"
    else:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        return f"{h}h {m}m"


def _theme_count(keywords: set, texts: List[str]) -> Tuple[int, float]:
    """Count how many texts contain at least one keyword from keywords."""
    count = sum(1 for t in texts if any(f" {k} " in f" {t.lower()} " for k in keywords))
    pct = count / len(texts) * 100 if texts else 0.0
    return count, pct


def _fmt_date(dt: datetime) -> str:
    """Format a datetime without leading zeros (cross-platform)."""
    month = dt.strftime("%b")
    day = str(dt.day)       # no leading zero
    year = dt.strftime("%Y")
    hour = str(dt.hour % 12 or 12)   # 12-hour, no leading zero
    minute = dt.strftime("%M")
    ampm = "AM" if dt.hour < 12 else "PM"
    return f"{month} {day}, {year}  {hour}:{minute} {ampm}"


def compute_workspace_stats(workspace) -> Tuple[List[str], Set[int]]:
    """
    Compute all statistics and return (lines, separator_indices).

    lines             — list of strings to display in the ListBox
    separator_indices — set of line indices that are visual separator rows
    """
    lines: List[str] = []
    sep_idx: Set[int] = set()

    all_items = list(workspace.items.values())
    if not all_items:
        lines.append("No items in workspace yet.")
        return lines, sep_idx

    # ── Section builder helpers ────────────────────────────────────────────────
    def S():
        lines.append(SEP)
        sep_idx.add(len(lines) - 1)

    def H(title: str):
        S()
        lines.append(title)

    def R(label: str, value):
        """Two-column row: left-padded label, right value."""
        label_col = f"  {label}"
        lines.append(f"{label_col:<38}{value}")

    # ── Categorise items ───────────────────────────────────────────────────────
    images    = [i for i in all_items if i.item_type == "image"]
    videos    = [i for i in all_items if i.item_type == "video"]
    frames    = [i for i in all_items if i.item_type == "extracted_frame"]
    downloaded = [i for i in all_items if i.item_type == "downloaded_image"]

    described   = [i for i in all_items if i.descriptions]
    undescribed = [i for i in all_items if not i.descriptions and i.processing_state != "failed"]
    failed      = [i for i in all_items if i.processing_state == "failed"]

    all_descs = [d for i in all_items for d in i.descriptions]
    pct = len(described) / len(all_items) * 100

    # ── Section 1: Workspace Overview ─────────────────────────────────────────
    H("Workspace Overview")
    R("Total items:",                f"{len(all_items):,}")
    R("Described:",                  f"{len(described):,}  ({pct:.0f}% complete)")
    R("Awaiting description:",       f"{len(undescribed):,}")
    if failed:
        R("Failed processing:",      f"{len(failed)}")

    # Item-type breakdown
    type_parts = []
    if images:
        type_parts.append(f"images {len(images):,}")
    if videos:
        type_parts.append(f"videos {len(videos):,}")
    if frames:
        type_parts.append(f"extracted frames {len(frames):,}")
    if downloaded:
        type_parts.append(f"downloaded {len(downloaded):,}")
    if len(type_parts) > 1:
        R("Item types:", "  ·  ".join(type_parts))

    # Extension summary
    ext_counts = Counter(
        Path(i.file_path).suffix.lower().lstrip('.') or 'no-ext'
        for i in all_items
    )
    ext_str = "  ·  ".join(f"{e.upper()} {c}" for e, c in ext_counts.most_common())
    R("File types:", ext_str)

    # Video/frame extraction
    total_frames_extracted = sum(len(v.extracted_frames) for v in videos if v.extracted_frames)
    if total_frames_extracted or frames:
        R("Frames extracted from videos:", f"{total_frames_extracted or len(frames):,}")

    heic_items = [i for i in all_items if Path(i.file_path).suffix.lower() in ('.heic', '.heif')]
    if heic_items:
        R("HEIC/HEIF files in workspace:", f"{len(heic_items)}")

    web_items = [i for i in all_items if i.download_url]
    if web_items:
        R("Images downloaded from web:", f"{len(web_items)}")

    # ── Section 2: Descriptions ────────────────────────────────────────────────
    if all_descs:
        H("Descriptions")
        R("Total descriptions:", f"{len(all_descs):,}")

        multi = [i for i in described if len(i.descriptions) > 1]
        avg_per = len(all_descs) / len(described) if described else 0.0
        R("Average per described item:", f"{avg_per:.1f}")

        if multi:
            champ = max(described, key=lambda i: len(i.descriptions))
            R("Items with multiple descriptions:", f"{len(multi)}")
            R("Most descriptions on one item:",
              f"{len(champ.descriptions)}  ({Path(champ.file_path).name})")

    # ── Section 3: Content Analysis ────────────────────────────────────────────
    # Build (text, item) pairs for analysis — strip metadata affixes first
    desc_pairs = [
        (_strip_metadata_affixes(d.text), i)
        for i in all_items
        for d in i.descriptions
        if d.text and d.text.strip()
    ]

    if desc_pairs:
        H("Content Analysis")
        texts = [t for t, _ in desc_pairs]
        word_counts = [len(t.split()) for t in texts]
        total_words = sum(word_counts)
        avg_words = total_words / len(word_counts)

        idx_min = word_counts.index(min(word_counts))
        idx_max = word_counts.index(max(word_counts))
        min_name = Path(desc_pairs[idx_min][1].file_path).name
        max_name = Path(desc_pairs[idx_max][1].file_path).name

        R("Total words written:",         f"{total_words:,}")
        R("Average words / description:", f"{avg_words:.0f}")
        R("Shortest description:",        f"{min(word_counts)} words  ({min_name})")
        R("Longest description:",         f"{max(word_counts)} words  ({max_name})")

        # Reading time at 200 wpm
        read_secs = total_words / 200 * 60
        R("Total reading time (200 wpm):", _fmt_dur(read_secs))

        # Document-size equivalent
        pages = total_words / 250
        R("Equivalent document length:", f"{pages:.1f} pages  (250 wds/page)")

        # Vocabulary analysis
        all_words = [w for t in texts for w in _split_words(t)]
        content_words = [w for w in all_words if w not in _STOPWORDS and len(w) > 2]
        unique_vocab = len(set(all_words))
        unique_content = set(content_words)
        ttr = len(unique_content) / len(content_words) * 100 if content_words else 0.0

        R("Unique vocabulary:",   f"~{unique_vocab:,} distinct words")
        R("Vocabulary richness:", f"{ttr:.0f}%  (unique / total content words)")

        if content_words:
            top = Counter(content_words).most_common(8)
            R("Most frequent terms:", "  ·  ".join(w for w, _ in top))

    # ── Section 4: Writing Style ───────────────────────────────────────────────
    if desc_pairs and len(texts) >= 3:
        H("Writing Style")

        sent_lists  = [_split_sentences(t) for t in texts]
        sent_counts = [len(s) for s in sent_lists]
        avg_sents   = sum(sent_counts) / len(sent_counts)
        total_sents = sum(sent_counts)
        avg_wps     = total_words / total_sents if total_sents > 0 else 0.0

        R("Avg sentences / description:", f"{avg_sents:.1f}")
        R("Avg words / sentence:",        f"{avg_wps:.1f}")

        # Thematic keyword detection — only show non-zero themes
        themes = [
            ("Featuring people",   {'person', 'people', 'man', 'woman', 'boy', 'girl',
                                    'child', 'children', 'human', 'face', 'figure',
                                    'individual', 'crowd', 'standing', 'sitting', 'walking'}),
            ("Nature / outdoor",   {'tree', 'trees', 'grass', 'flower', 'flowers', 'sky',
                                    'mountain', 'ocean', 'lake', 'river', 'forest', 'field',
                                    'outdoor', 'landscape', 'garden', 'park', 'beach',
                                    'coast', 'hill', 'valley', 'sunset', 'sunrise', 'clouds'}),
            ("Animals present",    {'dog', 'cat', 'bird', 'horse', 'animal', 'wildlife',
                                    'fish', 'deer', 'rabbit', 'fox', 'wolf', 'bear', 'lion',
                                    'tiger', 'elephant', 'monkey', 'cow', 'sheep', 'goat',
                                    'chicken', 'duck', 'squirrel', 'butterfly', 'insect'}),
            ("Food / dining",      {'food', 'meal', 'dish', 'plate', 'fruit', 'vegetable',
                                    'drink', 'beverage', 'coffee', 'tea', 'bread', 'cake',
                                    'salad', 'soup', 'pizza', 'burger', 'restaurant', 'dining',
                                    'cooking', 'eating'}),
            ("Text or signs",      {'text', 'sign', 'label', 'writing', 'letters',
                                    'reads', 'says', 'printed', 'inscription', 'caption',
                                    'headline', 'words', 'written', 'billboard', 'poster'}),
            ("Indoor scenes",      {'room', 'indoor', 'inside', 'interior', 'ceiling',
                                    'floor', 'wall', 'table', 'chair', 'furniture',
                                    'kitchen', 'bedroom', 'office', 'hallway',
                                    'shelf', 'shelves', 'window', 'door', 'sofa', 'couch'}),
            ("Architecture",       {'building', 'house', 'church', 'bridge', 'tower',
                                    'cathedral', 'castle', 'mosque', 'temple', 'skyscraper',
                                    'structure', 'facade', 'architecture', 'roof', 'column'}),
            ("Night / low-light",  {'night', 'dark', 'darkness', 'lit', 'illuminated',
                                    'lights', 'lamp', 'lantern', 'neon', 'candle', 'shadow',
                                    'silhouette', 'glow', 'spotlight', 'dusk', 'dawn'}),
            ("Water",              {'water', 'ocean', 'sea', 'lake', 'river', 'stream',
                                    'pond', 'waterfall', 'pool', 'rain', 'waves', 'shore',
                                    'boat', 'ship', 'reflection', 'ripple', 'splash'}),
        ]
        for label, kw in themes:
            n, p = _theme_count(kw, texts)
            if n > 0:
                R(f"{label}:", f"{n} descriptions  ({p:.0f}%)")

    # ── Section 5: Providers & Models ─────────────────────────────────────────
    if all_descs:
        H("Providers & Models")

        provider_counts = Counter(d.provider for d in all_descs if d.provider)
        model_counts    = Counter(d.model    for d in all_descs if d.model)
        prompt_counts   = Counter(d.prompt_style for d in all_descs if d.prompt_style)

        if provider_counts:
            if len(provider_counts) == 1:
                R("Provider:", list(provider_counts.keys())[0])
            else:
                for prov, cnt in provider_counts.most_common():
                    pp = cnt / len(all_descs) * 100
                    R(f"  {prov}:", f"{cnt} descriptions  ({pp:.0f}%)")

        if model_counts:
            if len(model_counts) == 1:
                R("Model:", list(model_counts.keys())[0])
            else:
                for m, cnt in model_counts.most_common():
                    R(f"  {m}:", f"{cnt} descriptions")

        if prompt_counts:
            if len(prompt_counts) == 1:
                R("Prompt style:", list(prompt_counts.keys())[0])
            else:
                R("Prompt styles:", "  ·  ".join(prompt_counts.keys()))

    # ── Section 6: Location Summary ───────────────────────────────────────────
    # Read from d.metadata which has clean geocoded data (not from d.text byline)
    location_items: list = []  # list of (city, state, country, lat, lon, item)
    for item in all_items:
        for desc in item.descriptions:
            loc = (desc.metadata or {}).get('location', {})
            if not loc:
                continue
            city    = loc.get('city') or loc.get('town') or ''
            state   = loc.get('state') or ''
            country = loc.get('country') or ''
            lat     = loc.get('latitude')
            lon     = loc.get('longitude')
            if city or state or country:
                location_items.append((city, state, country, lat, lon, item))

    if location_items:
        H("Location Summary")
        items_with_loc = len({id(i) for _, _, _, _, _, i in location_items})
        R("Items with location data:",
          f"{items_with_loc}  ({items_with_loc / len(all_items) * 100:.0f}% of workspace)")

        # City / town breakdown
        city_counts: Counter = Counter()
        state_counts: Counter = Counter()
        country_counts: Counter = Counter()
        for city, state, country, lat, lon, _ in location_items:
            if city:
                label = f"{city}, {state}" if state else city
                city_counts[label] += 1
            if state:
                state_counts[state] += 1
            if country:
                country_counts[country] += 1

        if country_counts:
            if len(country_counts) == 1:
                R("Country:", list(country_counts.keys())[0])
            else:
                for c, n in country_counts.most_common():
                    R(f"  {c}:", f"{n} image{'s' if n != 1 else ''}")

        if state_counts and len(state_counts) > 1:
            for s, n in state_counts.most_common(8):
                R(f"  {s}:", f"{n} image{'s' if n != 1 else ''}")
        elif state_counts:
            R("State / region:", list(state_counts.keys())[0])

        if city_counts:
            unique_cities = len(city_counts)
            R("Unique city/town locations:", str(unique_cities))
            top_cities = city_counts.most_common(10)
            for place, n in top_cities:
                R(f"  {place}:", f"{n} image{'s' if n != 1 else ''}")

        # Geo spread: bounding box diagonal if we have GPS
        gps_points = [(lat, lon) for _, _, _, lat, lon, _ in location_items
                      if lat is not None and lon is not None]
        if len(gps_points) >= 2:
            lats = [p[0] for p in gps_points]
            lons = [p[1] for p in gps_points]
            dlat = math.radians(max(lats) - min(lats))
            dlon = math.radians(max(lons) - min(lons))
            avg_lat = math.radians((max(lats) + min(lats)) / 2)
            a = math.sin(dlat/2)**2 + math.cos(avg_lat) * math.sin(dlon/2)**2
            km = 6371 * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            miles = km * 0.621371
            R("Geographic spread (bbox diagonal):",
              f"{km:.0f} km  /  {miles:.0f} miles")

    # ── Section 7: Token Usage ─────────────────────────────────────────────────
    token_data = []
    for item in all_items:
        for desc in item.descriptions:
            if desc.metadata:
                total_t = desc.metadata.get('total_tokens', 0)
                in_t    = desc.metadata.get('input_tokens', 0)
                out_t   = desc.metadata.get('output_tokens', 0)
                if total_t and total_t > 0:
                    token_data.append({
                        'total':    total_t,
                        'input':    in_t,
                        'output':   out_t,
                        'name':     Path(item.file_path).name,
                        'provider': desc.provider or '',
                    })

    if token_data:
        H("Token Usage")
        grand_total = sum(d['total'] for d in token_data)
        avg_total   = grand_total / len(token_data)
        avg_in      = sum(d['input']  for d in token_data) / len(token_data)
        avg_out     = sum(d['output'] for d in token_data) / len(token_data)
        peak        = max(token_data, key=lambda d: d['total'])

        R("Descriptions with token data:", f"{len(token_data)}")
        R("Total tokens consumed:",        f"{grand_total:,}")
        R("Average per description:",      f"{avg_total:,.0f}")
        R("  Avg input tokens:",           f"{avg_in:,.0f}")
        R("  Avg output tokens:",          f"{avg_out:,.0f}")
        R("Most token-hungry image:",
          f"{peak['total']:,} tokens  ({peak['name']})")

        # Per-provider average when mixed
        by_prov = {}
        for d in token_data:
            by_prov.setdefault(d['provider'], []).append(d['total'])
        if len(by_prov) > 1:
            for prov, toks in sorted(by_prov.items()):
                R(f"  {prov} avg:", f"{sum(toks)/len(toks):,.0f} tokens")

    # ── Section 8: Processing Performance ──────────────────────────────────────
    timing_data = []
    for item in all_items:
        for desc in item.descriptions:
            if desc.metadata:
                t = desc.metadata.get('processing_time_seconds')
                if t and t > 0:
                    timing_data.append({'time': t, 'name': Path(item.file_path).name})

    if timing_data:
        H("Processing Performance")
        total_time = sum(d['time'] for d in timing_data)
        avg_time   = total_time / len(timing_data)
        fastest    = min(timing_data, key=lambda d: d['time'])
        slowest    = max(timing_data, key=lambda d: d['time'])
        imgs_per_hr = 3600 / avg_time if avg_time > 0 else 0

        R("Descriptions with timing data:", f"{len(timing_data)}")
        R("Total AI processing time:",      _fmt_dur(total_time))
        R("Average time / image:",          f"{avg_time:.1f} sec")
        R("Fastest image:",                 f"{fastest['time']:.1f} sec  ({fastest['name']})")
        R("Slowest image:",                 f"{slowest['time']:.1f} sec  ({slowest['name']})")
        R("Throughput:",                    f"{imgs_per_hr:.0f} images / hour")
        # Projection for common batch sizes
        for batch_size in (100, 1000):
            proj = avg_time * batch_size
            R(f"Projected time for {batch_size:,} images:", _fmt_dur(proj))

    # ── Section 9: Activity Timeline ──────────────────────────────────────────
    desc_dates = []
    for desc in all_descs:
        try:
            desc_dates.append(datetime.fromisoformat(desc.created))
        except Exception:
            pass

    if desc_dates:
        H("Activity Timeline")
        first = min(desc_dates)
        last  = max(desc_dates)
        span  = (last - first).days

        R("First description:",      _fmt_date(first))
        R("Most recent description:", _fmt_date(last))
        R("Workspace activity span:",
          f"{span} day{'s' if span != 1 else ''}" if span > 0 else "< 1 day")

        # Busiest describing day
        day_counts = Counter(
            d.strftime("%b %d, %Y").replace(" 0", " ")
            for d in desc_dates
        )
        busiest_day, busiest_count = day_counts.most_common(1)[0]
        if busiest_count > 1:
            R("Most productive session:", f"{busiest_day}  ({busiest_count} descriptions)")

        # Rate: descriptions per day of active workspace
        if span > 0:
            rate = len(all_descs) / span
            R("Avg descriptions / day:", f"{rate:.1f}")

    # ── Final separator ────────────────────────────────────────────────────────
    S()
    return lines, sep_idx


class WorkspaceStatsDialog(wx.Dialog):
    """
    Modal dialog showing comprehensive workspace statistics.

    Modeled after BatchProgressDialog: wx.ListBox with monospace font,
    separator rows skippable by keyboard, one-line-per-stat layout.
    """

    def __init__(self, parent, workspace):
        total    = len(workspace.items)
        described = sum(1 for i in workspace.items.values() if i.descriptions)
        pct      = f"{described / total * 100:.0f}%" if total else "0%"
        title    = (f"Workspace Statistics  —  "
                    f"{described:,} of {total:,} described ({pct})")

        super().__init__(
            parent,
            title=title,
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )

        self._build_ui(workspace)
        self.SetSize(660, 600)
        self.Centre()

    def _build_ui(self, workspace):
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Header label
        header = wx.StaticText(panel, label="Workspace Statistics:",
                               name="Workspace statistics title")
        font = header.GetFont()
        font.PointSize += 2
        header.SetFont(font.Bold())
        sizer.Add(header, 0, wx.ALL, 10)

        # Stats ListBox — monospace for column alignment
        self.stats_list = wx.ListBox(
            panel,
            style=wx.LB_SINGLE | wx.LB_NEEDED_SB,
            name="Workspace statistics detail"
        )
        try:
            mono = wx.Font(11, wx.FONTFAMILY_TELETYPE,
                           wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
            self.stats_list.SetFont(mono)
        except Exception:
            pass

        self._lines, self.separator_indices = compute_workspace_stats(workspace)
        for line in self._lines:
            self.stats_list.Append(line)

        self.stats_list.SetMinSize((600, 440))
        sizer.Add(self.stats_list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        # Buttons
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        close_btn = wx.Button(panel, wx.ID_CLOSE, "Close")
        close_btn.SetDefault()
        btn_sizer.Add(close_btn, 0, wx.ALL, 5)
        sizer.Add(btn_sizer, 0, wx.ALIGN_CENTER | wx.ALL, 10)

        panel.SetSizer(sizer)

        dialog_sizer = wx.BoxSizer(wx.VERTICAL)
        dialog_sizer.Add(panel, 1, wx.EXPAND)
        self.SetSizer(dialog_sizer)

        # ── Bindings ──────────────────────────────────────────────────────────
        close_btn.Bind(wx.EVT_BUTTON, lambda e: self.EndModal(wx.ID_CLOSE))
        self.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)
        self.stats_list.Bind(wx.EVT_LISTBOX, self._on_selection)
        self.stats_list.Bind(wx.EVT_KEY_DOWN, self._on_key)

    # ── Accessibility: separator row handling ──────────────────────────────────

    def _on_char_hook(self, event):
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self.EndModal(wx.ID_CLOSE)
        else:
            event.Skip()

    def _on_selection(self, event):
        """Jump away from separator row on mouse click."""
        idx = self.stats_list.GetSelection()
        if idx == wx.NOT_FOUND or idx not in self.separator_indices:
            event.Skip()
            return
        count = self.stats_list.GetCount()
        candidates = list(range(idx + 1, count)) + list(range(idx - 1, -1, -1))
        for c in candidates:
            if c not in self.separator_indices:
                self.stats_list.SetSelection(c)
                return
        self.stats_list.SetSelection(wx.NOT_FOUND)

    def _on_key(self, event):
        """Arrow navigation skips separator rows."""
        key = event.GetKeyCode()
        cur   = self.stats_list.GetSelection()
        count = self.stats_list.GetCount()

        if key == wx.WXK_DOWN and cur != wx.NOT_FOUND:
            nxt = cur + 1
            while nxt < count and nxt in self.separator_indices:
                nxt += 1
            if nxt < count:
                self.stats_list.SetSelection(nxt)
                self.stats_list.EnsureVisible(nxt)
                return

        elif key == wx.WXK_UP and cur != wx.NOT_FOUND:
            prv = cur - 1
            while prv >= 0 and prv in self.separator_indices:
                prv -= 1
            if prv >= 0:
                self.stats_list.SetSelection(prv)
                self.stats_list.EnsureVisible(prv)
                return

        event.Skip()
