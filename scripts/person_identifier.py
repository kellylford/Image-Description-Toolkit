"""
Person Identifier — text-mining and AI-assisted person clustering.

Phase 3 (text-mining): No additional dependencies beyond stdlib.
Phase 4 (AI clustering): Requires a configured Ollama, OpenAI, or Anthropic provider.

Public API
----------
Text-mining (Phase 3):
    extract_person_descriptors(description_text) -> List[str]
    cluster_by_text(images_with_descriptions, threshold=0.6) -> List[PersonGroup]
    generate_grouping_report(groups, output_path=None) -> str

AI-assisted (Phase 4):
    cluster_by_ai(descriptions_dict, provider, model,
                  api_key=None, base_url=None) -> List[PersonGroup]
    match_known_persons_ai(descriptions_dict, persons_db,
                           provider, model, api_key=None,
                           base_url=None) -> Dict[str, List[str]]

Both phases use PersonGroup from data_models and return lists that can be fed
directly to persons_manager.create_group().
"""

import json
import logging
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Import path resolution: supports frozen exe (_MEIPASS) and dev mode
# ---------------------------------------------------------------------------
try:
    from data_models import PersonGroup, ImageWorkspace
except ImportError:
    _project_root = Path(__file__).parent.parent
    for _path in (str(_project_root), str(_project_root / "imagedescriber")):
        if _path not in sys.path:
            sys.path.insert(0, _path)
    from data_models import PersonGroup, ImageWorkspace

# ---------------------------------------------------------------------------
# Descriptor vocabulary for text-mining
# ---------------------------------------------------------------------------

# Words to strip from descriptor tokens (common but non-discriminating)
_STOPWORDS = {
    "a", "an", "the", "and", "or", "is", "are", "was", "were", "in", "on",
    "at", "of", "with", "their", "they", "he", "she", "it", "this", "that",
    "has", "have", "had", "who", "which", "from", "to", "also", "very",
    "appears", "appears to", "person", "image", "photo", "picture",
    "wearing", "wears", "dressed", "standing", "sitting", "looking",
    "visible", "shown", "seen",
}

# Pattern: single person-description sentence start markers
_PERSON_SENTENCE_RE = re.compile(
    r'(?:'
    r'there\s+is\s+(?:a\s+)?|'           # "there is a ..."
    r'(?:a\s+)?(?:man|woman|boy|girl|person|individual|child|figure)\s+|'
    r'the\s+(?:man|woman|boy|girl|person|individual|child|figure)\s+'
    r')',
    re.IGNORECASE,
)

# Physical descriptor patterns (captures normalised tokens)
_DESCRIPTOR_PATTERNS: List[Tuple[str, re.Pattern]] = [
    # Age
    ("age", re.compile(
        r'\b(young|elderly|old|middle.?aged|teenage|teen|infant|baby|toddler|child|'
        r'adolescent|adult|senior|aged?\s+\d{1,3}|\d{1,3}.year.old)\b',
        re.IGNORECASE)),
    # Gender expression
    ("gender", re.compile(
        r'\b(man|woman|male|female|boy|girl|non.?binary|masculine|feminine)\b',
        re.IGNORECASE)),
    # Build / height
    ("build", re.compile(
        r'\b(tall|short|petite|stocky|heavyset|slim|slender|thin|athletic|muscular|'
        r'heavyset|overweight|plus.?size|average.?build)\b',
        re.IGNORECASE)),
    # Hair colour
    ("hair_color", re.compile(
        r'\b(blonde|blond|brunette|auburn|red.?head|ginger|dark|black|white|gray|grey|'
        r'silver|dyed|highlighted|ombre)\s+hair\b|'
        r'\bhair\s+(?:is\s+)?(?:blonde|blond|brunette|auburn|red|dark|black|white|gray|grey|silver)\b',
        re.IGNORECASE)),
    # Hair style / length
    ("hair_style", re.compile(
        r'\b(short|long|medium.?length|curly|wavy|straight|bald|balding|'
        r'buzz.?cut|shaved|ponytail|bun|braided|locs|dreadlocks|afro|'
        r'crew.?cut|pixie|bob)\s+(?:hair|cut|style)?\b|'
        r'\bhair\s+(?:is\s+)?(?:short|long|curly|wavy|straight|in\s+a\s+(?:ponytail|bun|braid))\b',
        re.IGNORECASE)),
    # Facial features
    ("facial_hair", re.compile(
        r'\b(beard|bearded|moustache|mustache|stubble|goatee|clean.?shaven|clean shaven)\b',
        re.IGNORECASE)),
    ("glasses", re.compile(
        r'\b(glasses|spectacles|sunglasses|eyeglasses|prescription glasses|'
        r'reading glasses|rimless|wire.?framed|thick.?framed)\b',
        re.IGNORECASE)),
    # Ethnicity/skin tone (descriptor only — not for bias, for identification accuracy)
    ("skin", re.compile(
        r'\b(fair|light|pale|olive|tan|tanned|dark|brown|black|white)\s+skin\b|'
        r'\bskin\s+(?:is\s+)?(?:fair|light|pale|olive|tan|dark|brown)\b',
        re.IGNORECASE)),
    # Clothing colour (top item only — most stable identifier)
    ("clothing_color", re.compile(
        r'\b(?:wearing|dressed\s+in|in\s+a?)\s+'
        r'(red|blue|green|yellow|orange|purple|pink|white|black|gray|grey|brown|'
        r'navy|teal|maroon|beige|tan|khaki|striped|plaid|patterned)\b',
        re.IGNORECASE)),
    # Specific garments
    ("clothing_item", re.compile(
        r'\b(jacket|coat|suit|dress|shirt|blouse|top|hoodie|sweater|'
        r'vest|hat|cap|helmet|scarf|tie|uniform)\b',
        re.IGNORECASE)),
    # Distinctive marks
    ("distinctive", re.compile(
        r'\b(tattoo|piercing|scar|birthmark|freckles|freckled|distinctive|notable)\b',
        re.IGNORECASE)),
]


# ---------------------------------------------------------------------------
# Phase 3 — Text-mining
# ---------------------------------------------------------------------------

def extract_person_descriptors(description_text: str) -> List[str]:
    """Extract normalised physical-descriptor tokens from a description.

    Returns a deduplicated list of lower-case token strings such as
    ``["young", "woman", "dark hair", "glasses", "blue jacket"]``.
    These are used for Jaccard-similarity clustering.
    """
    tokens: List[str] = []
    for _category, pattern in _DESCRIPTOR_PATTERNS:
        for match in pattern.finditer(description_text):
            token = match.group(0).strip().lower()
            # Normalise multi-word matches to single canonical forms
            token = re.sub(r'\s+', ' ', token)
            token = re.sub(r'\bwearing\s+|\bin\s+a?\s+', '', token).strip()
            if token and token not in _STOPWORDS and len(token) > 1:
                tokens.append(token)
    return list(dict.fromkeys(tokens))  # deduplicate while preserving order


def _jaccard(a: List[str], b: List[str]) -> float:
    """Jaccard similarity between two token lists."""
    if not a and not b:
        return 0.0
    sa, sb = set(a), set(b)
    return len(sa & sb) / len(sa | sb)


def cluster_by_text(
    images_with_descriptions: Dict[str, str],
    threshold: float = 0.35,
) -> List[PersonGroup]:
    """Cluster images by physical descriptors found in their descriptions.

    Uses greedy single-linkage agglomerative clustering: no external deps.

    Args:
        images_with_descriptions: ``{filename: description_text}`` mapping.
        threshold: Minimum Jaccard similarity to merge two images into a group.
                   Lower values = larger groups with looser matches.
                   Recommended range: 0.25–0.60.

    Returns:
        List of PersonGroup objects (method="text"). Groups with only one image
        are omitted — they represent unique individuals that couldn't be paired.
    """
    if not images_with_descriptions:
        return []

    # Build descriptor sets for every image
    descriptors: Dict[str, List[str]] = {
        fname: extract_person_descriptors(desc)
        for fname, desc in images_with_descriptions.items()
    }

    filenames = list(descriptors.keys())
    n = len(filenames)

    # Build similarity matrix (upper triangle only)
    sim: Dict[Tuple[str, str], float] = {}
    for i in range(n):
        for j in range(i + 1, n):
            fi, fj = filenames[i], filenames[j]
            di, dj = descriptors[fi], descriptors[fj]
            if di or dj:  # skip if both empty
                sim[(fi, fj)] = _jaccard(di, dj)

    # Greedy single-linkage clustering
    # cluster_of[filename] -> cluster index
    cluster_of: Dict[str, int] = {f: idx for idx, f in enumerate(filenames)}
    cluster_count = n

    # Sort pairs by similarity descending; merge greedily above threshold
    for (fi, fj), score in sorted(sim.items(), key=lambda x: x[1], reverse=True):
        if score < threshold:
            break
        ci, cj = cluster_of[fi], cluster_of[fj]
        if ci == cj:
            continue
        # Merge smaller cluster index into larger
        old, new = (cj, ci) if ci < cj else (ci, cj)
        for fname in filenames:
            if cluster_of[fname] == old:
                cluster_of[fname] = new
        cluster_count -= 1

    # Collect clusters → PersonGroup
    from collections import defaultdict
    clusters: Dict[int, List[str]] = defaultdict(list)
    for fname, idx in cluster_of.items():
        clusters[idx].append(fname)

    groups: List[PersonGroup] = []
    for cluster_images in clusters.values():
        if len(cluster_images) < 2:
            continue  # skip singletons
        # Build a summary of the shared descriptors
        shared = set(descriptors[cluster_images[0]])
        for fname in cluster_images[1:]:
            shared &= set(descriptors[fname])
        summary = ", ".join(sorted(shared)) if shared else "similar physical appearance"
        group = PersonGroup(
            display_label=f"Group ({summary[:60]})" if summary else "Unnamed group",
            images=sorted(cluster_images),
            description_summary=summary,
            method="text",
        )
        groups.append(group)

    # Sort by group size descending
    groups.sort(key=lambda g: len(g.images), reverse=True)
    return groups


def generate_grouping_report(
    groups: List[PersonGroup],
    output_path: Optional[Path] = None,
) -> str:
    """Generate a human-readable text report of clustering results.

    Args:
        groups: List of PersonGroup objects from cluster_by_text or cluster_by_ai.
        output_path: If given, write the report to this file (UTF-8).

    Returns:
        The report as a string.
    """
    lines = [
        "Person Grouping Report",
        "=" * 60,
        f"Total groups found: {len(groups)}",
        f"Total images grouped: {sum(len(g.images) for g in groups)}",
        "",
    ]
    for i, group in enumerate(groups, 1):
        lines.append(f"Group {i}: {group.display_label}")
        lines.append(f"  Method: {group.method}")
        lines.append(f"  Images ({len(group.images)}):")
        for img in group.images:
            lines.append(f"    - {img}")
        if group.description_summary:
            lines.append(f"  Shared traits: {group.description_summary}")
        if group.resolved_person_id:
            lines.append(f"  Resolved to person ID: {group.resolved_person_id}")
        lines.append("")

    report = "\n".join(lines)

    if output_path:
        try:
            Path(output_path).write_text(report, encoding="utf-8")
            logger.info("Grouping report written to %s", output_path)
        except OSError as exc:
            logger.error("Could not write grouping report: %s", exc)

    return report


# ---------------------------------------------------------------------------
# Phase 4 — AI-assisted clustering
# ---------------------------------------------------------------------------

_AI_CLUSTER_SYSTEM_PROMPT = (
    "You are an expert assistant helping a user identify people across a collection "
    "of image descriptions. Each description may contain physical details about one "
    "or more people. Your task is to group images that appear to show the same person "
    "based ONLY on the physical descriptions provided — not on names, context, or "
    "external knowledge. Be conservative: only group images when the physical "
    "descriptions are strongly consistent. Respond ONLY with valid JSON."
)

_AI_CLUSTER_USER_TEMPLATE = """\
Below are descriptions extracted from {count} images. Each entry is:
  "filename": "...description text..."

Analyze the physical descriptions and return a JSON array of groups.
Each group should have:
  - "images": [list of filenames that likely show the same person]
  - "summary": "brief shared physical traits"
  - "confidence": "high" | "medium" | "low"

Only include groups with 2 or more images. Return [] if no strong matches.

Image descriptions:
{entries}
"""

_AI_MATCH_SYSTEM_PROMPT = (
    "You are an expert assistant helping match image descriptions to known people. "
    "For each image, determine which known person (if any) is most likely depicted "
    "based on physical description alone. Be conservative — only suggest a match "
    "when the description is strongly consistent with the known person's traits. "
    "Return ONLY valid JSON."
)

_AI_MATCH_USER_TEMPLATE = """\
Known people:
{persons}

Image descriptions to match:
{entries}

Return a JSON object mapping each filename to a list of matched person names.
If no match, map to an empty list. Example:
  {{"IMG_001.jpg": ["Alice Smith"], "IMG_002.jpg": [], "IMG_003.jpg": ["Bob Jones"]}}
"""


def _call_ai_text(
    system_prompt: str,
    user_prompt: str,
    provider: str,
    model: str,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> str:
    """Make a text-only AI chat call and return the response string.

    Supports: 'ollama', 'openai', 'anthropic' (case-insensitive).
    Raises RuntimeError on API error.
    """
    provider_lower = provider.lower()

    if provider_lower == "ollama":
        import urllib.request
        url = (base_url or "http://localhost:11434").rstrip("/") + "/api/chat"
        payload = json.dumps({
            "model": model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }).encode("utf-8")
        req = urllib.request.Request(
            url, data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:  # nosec — local service only
            data = json.load(resp)
        return data.get("message", {}).get("content", "")

    if provider_lower == "openai":
        try:
            import openai
        except ImportError as exc:
            raise RuntimeError("openai package not installed") from exc
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=2048,
        )
        return response.choices[0].message.content or ""

    if provider_lower in ("anthropic", "claude"):
        try:
            import anthropic
        except ImportError as exc:
            raise RuntimeError("anthropic package not installed") from exc
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=model,
            max_tokens=2048,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return response.content[0].text if response.content else ""

    raise ValueError(f"Unsupported provider: {provider!r}")


def _extract_json(text: str):
    """Extract the first JSON object or array from a text response."""
    # Strip markdown fences
    text = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.MULTILINE)
    text = re.sub(r"```\s*$", "", text.strip(), flags=re.MULTILINE)

    # Try direct parse first
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # Try to extract first JSON array or object
    for start_char, end_char in (("[", "]"), ("{", "}")):
        start = text.find(start_char)
        if start == -1:
            continue
        depth = 0
        for i, ch in enumerate(text[start:], start):
            if ch == start_char:
                depth += 1
            elif ch == end_char:
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start: i + 1])
                    except json.JSONDecodeError:
                        break
    raise ValueError("No valid JSON found in AI response")


def cluster_by_ai(
    images_with_descriptions: Dict[str, str],
    provider: str,
    model: str,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    batch_size: int = 40,
) -> List[PersonGroup]:
    """Cluster images by asking an AI to find people appearing in multiple images.

    Large collections are processed in batches and results merged.

    Args:
        images_with_descriptions: ``{filename: description_text}`` mapping.
        provider: AI provider name ('ollama', 'openai', 'anthropic').
        model: Model identifier, e.g. ``"gpt-4o"`` or ``"llava"``.
        api_key: Required for OpenAI/Anthropic; ignored for Ollama.
        base_url: Override Ollama base URL (default: ``http://localhost:11434``).
        batch_size: Max images per AI request. Reduce if hitting token limits.

    Returns:
        List of PersonGroup objects with method="ai".
    """
    if not images_with_descriptions:
        return []

    items = list(images_with_descriptions.items())
    all_groups: List[PersonGroup] = []

    for batch_start in range(0, len(items), batch_size):
        batch = items[batch_start: batch_start + batch_size]
        entries_text = "\n".join(
            f'  "{fname}": {json.dumps(desc[:600])}'  # cap per-entry length
            for fname, desc in batch
        )
        user_prompt = _AI_CLUSTER_USER_TEMPLATE.format(
            count=len(batch),
            entries=entries_text,
        )
        try:
            raw_response = _call_ai_text(
                _AI_CLUSTER_SYSTEM_PROMPT, user_prompt,
                provider, model, api_key, base_url,
            )
            groups_data = _extract_json(raw_response)
        except Exception as exc:
            logger.error("AI clustering failed for batch %d: %s", batch_start, exc)
            continue

        if not isinstance(groups_data, list):
            logger.warning("AI clustering returned unexpected type: %s", type(groups_data))
            continue

        for group_dict in groups_data:
            images = group_dict.get("images", [])
            if len(images) < 2:
                continue
            summary = group_dict.get("summary", "")
            confidence = group_dict.get("confidence", "medium")
            group = PersonGroup(
                display_label=f"AI group ({summary[:60]})" if summary else "AI group",
                images=[str(img) for img in images],
                description_summary=f"[{confidence} confidence] {summary}".strip(),
                method="ai",
            )
            all_groups.append(group)

    # Sort by group size descending
    all_groups.sort(key=lambda g: len(g.images), reverse=True)
    return all_groups


def match_known_persons_ai(
    images_with_descriptions: Dict[str, str],
    workspace: "ImageWorkspace",
    provider: str,
    model: str,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    batch_size: int = 30,
) -> Dict[str, List[str]]:
    """Match image descriptions against known persons using AI.

    Args:
        images_with_descriptions: ``{filename: description_text}`` mapping.
        workspace: ImageWorkspace containing the persons DB.
        provider: AI provider name.
        model: Model identifier.
        api_key / base_url: Provider credentials.
        batch_size: Max images per AI request.

    Returns:
        ``{filename: [person_name, ...]}`` — empty list means no match found.
    """
    if not images_with_descriptions or not workspace.persons:
        return {fname: [] for fname in images_with_descriptions}

    # Build persons listing for the prompt
    person_lines = []
    for person in workspace.persons.values():
        line = f'  - Name: "{person.name}"'
        if person.description_traits:
            line += f', Traits: "{person.description_traits}"'
        if person.notes:
            line += f', Notes: "{person.notes}"'
        person_lines.append(line)
    persons_text = "\n".join(person_lines)

    items = list(images_with_descriptions.items())
    result: Dict[str, List[str]] = {}

    for batch_start in range(0, len(items), batch_size):
        batch = items[batch_start: batch_start + batch_size]
        entries_text = "\n".join(
            f'  "{fname}": {json.dumps(desc[:600])}'
            for fname, desc in batch
        )
        user_prompt = _AI_MATCH_USER_TEMPLATE.format(
            persons=persons_text,
            entries=entries_text,
        )
        try:
            raw_response = _call_ai_text(
                _AI_MATCH_SYSTEM_PROMPT, user_prompt,
                provider, model, api_key, base_url,
            )
            match_data = _extract_json(raw_response)
        except Exception as exc:
            logger.error("AI matching failed for batch %d: %s", batch_start, exc)
            # Default to empty matches for this batch
            for fname, _ in batch:
                result[fname] = []
            continue

        if not isinstance(match_data, dict):
            logger.warning("AI matching returned unexpected type: %s", type(match_data))
            for fname, _ in batch:
                result[fname] = []
            continue

        for fname, _ in batch:
            names = match_data.get(fname, [])
            result[fname] = [str(n) for n in names] if isinstance(names, list) else []

    return result
