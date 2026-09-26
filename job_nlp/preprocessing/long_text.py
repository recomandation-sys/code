"""Long-description token selection for XLM-R classification (V1)."""
from __future__ import annotations

import re
from typing import Any

STRATEGY_VERSION = "head250_tail200_v1"
# XLM-R pair: <s> title </s></s> description </s>
_PAIR_SPECIAL_TOKENS = 3

_SECTION_HEADING = re.compile(
    r"(?i)(?:^|\n)\s*("
    r"profil recherch[ée]|"
    r"missions?|"
    r"responsabilit[ée]s|"
    r"activit[ée]s principales(?: du poste)?|"
    r"comp[ée]tences (?:et )?connaissances requises|"
    r"qualifications?|"
    r"[ée]ducation|"
    r"exp[ée]rience|"
    r"requirements?|"
    r"required skills|"
    r"nice to have|"
    r"atouts?|"
    r"preferred"
    r")\s*[:\-]?",
    re.MULTILINE,
)

_SECTION_BUCKET = (
    ("role", ("mission", "responsabilit", "activit", "role")),
    ("requirements", ("profil recherch", "compétence", "competence", "connaissance requise", "requirement", "required skill")),
    ("qualifications", ("qualification", "education", "expérience", "experience", "diplôme", "diplome")),
    ("nice", ("nice to have", "atout", "preferred")),
)


def _section_bucket(heading: str) -> str:
    h = heading.lower()
    for bucket, keys in _SECTION_BUCKET:
        if any(k in h for k in keys):
            return bucket
    return "other"


def _parse_description_sections(description_model: str) -> list[tuple[str, str]]:
    """Split description into (text_with_heading, bucket) chunks."""
    text = description_model or ""
    if not text.strip():
        return []
    matches = list(_SECTION_HEADING.finditer(text))
    if not matches:
        return [(text.strip(), "other")]
    chunks: list[tuple[str, str]] = []
    if matches[0].start() > 0:
        chunks.append((text[: matches[0].start()].strip(), "other"))
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append((chunk, _section_bucket(m.group(1))))
    return chunks


def section_aware_description_view(
    tokenizer: Any,
    description_model: str,
    *,
    max_desc_tokens: int,
) -> str:
    """Priority-ordered section view within token budget; headings preserved."""
    priority = ["role", "requirements", "qualifications", "nice", "other"]
    by_bucket: dict[str, list[str]] = {b: [] for b in priority}
    for chunk, bucket in _parse_description_sections(description_model):
        by_bucket.setdefault(bucket, []).append(chunk)
    ordered: list[str] = []
    for bucket in priority:
        ordered.extend(by_bucket.get(bucket, []))
    parts: list[str] = []
    used = 0
    for section in ordered:
        ids = tokenizer.encode(section, add_special_tokens=False)
        if not ids:
            continue
        if used + len(ids) <= max_desc_tokens:
            parts.append(section)
            used += len(ids)
        elif used < max_desc_tokens:
            parts.append(tokenizer.decode(ids[: max_desc_tokens - used], clean_up_tokenization_spaces=True))
            break
        else:
            break
    if not parts:
        return description_model or ""
    return "\n".join(parts)


def _merge_head_tail(ids: list[int], head: int, tail: int) -> list[int]:
    if len(ids) <= head + tail:
        return ids
    head_ids = ids[:head]
    tail_ids = ids[-tail:]
    overlap = 0
    max_overlap = min(len(head_ids), len(tail_ids))
    for i in range(max_overlap, 0, -1):
        if head_ids[-i:] == tail_ids[:i]:
            overlap = i
            break
    return head_ids + tail_ids[overlap:]


def _title_token_ids(tokenizer: Any, title_model: str) -> list[int]:
    return tokenizer.encode(title_model or "", add_special_tokens=False)


def _description_token_ids(tokenizer: Any, description_model: str) -> list[int]:
    return tokenizer.encode(description_model or "", add_special_tokens=False)


def description_token_budget(
    tokenizer: Any,
    title_model: str,
    *,
    max_length: int = 512,
) -> int:
    """Tokens available for description after preserving full title + specials."""
    title_len = len(_title_token_ids(tokenizer, title_model))
    return max(0, max_length - title_len - _PAIR_SPECIAL_TOKENS)


def description_token_view(
    tokenizer: Any,
    description_model: str,
    *,
    head_tokens: int = 250,
    tail_tokens: int = 200,
    max_desc_tokens: int | None = None,
) -> str:
    """Head+tail description view within optional token budget."""
    ids = _description_token_ids(tokenizer, description_model)
    budget = max_desc_tokens if max_desc_tokens is not None else head_tokens + tail_tokens
    if len(ids) <= budget:
        return description_model or ""
    head = min(head_tokens, max(1, budget // 2))
    tail = min(tail_tokens, max(1, budget - head))
    selected = _merge_head_tail(ids, head, tail)
    if len(selected) > budget:
        selected = selected[:budget]
    return tokenizer.decode(selected, clean_up_tokenization_spaces=True)


def build_xlmr_classifier_text(
    title_model: str,
    description_model: str,
    tokenizer: Any,
    *,
    max_length: int = 512,
    head_tokens: int = 250,
    tail_tokens: int = 200,
    strategy: str = STRATEGY_VERSION,
) -> str:
    """Deterministic classifier view for debugging/inspection."""
    if strategy == "title_only_v1":
        return (title_model or "").strip()
    if strategy == "description_only_v1":
        budget = max_length - _PAIR_SPECIAL_TOKENS
        return description_token_view(
            tokenizer,
            description_model,
            head_tokens=head_tokens or 225,
            tail_tokens=tail_tokens or 225,
            max_desc_tokens=budget,
        )
    budget = description_token_budget(tokenizer, title_model, max_length=max_length)
    if strategy == "section_aware_v1":
        desc_view = section_aware_description_view(
            tokenizer, description_model, max_desc_tokens=budget if budget > 0 else 400
        )
    else:
        desc_view = description_token_view(
            tokenizer,
            description_model,
            head_tokens=head_tokens,
            tail_tokens=tail_tokens,
            max_desc_tokens=budget if budget > 0 else head_tokens + tail_tokens,
        )
    return f"{title_model or ''}\n{desc_view}".strip()


def encode_classification_pair(
    tokenizer: Any,
    title_model: str,
    description_model: str,
    *,
    max_length: int = 512,
    head_tokens: int = 250,
    tail_tokens: int = 200,
    strategy: str = STRATEGY_VERSION,
) -> dict[str, list[int]]:
    """Title (full) + description view; always <= max_length token ids."""
    if strategy == "title_only_v1":
        encoded = tokenizer(
            title_model or "",
            max_length=max_length,
            truncation=True,
            padding=False,
            add_special_tokens=True,
        )
        assert len(encoded["input_ids"]) <= max_length
        return encoded

    if strategy == "description_only_v1":
        budget = max_length - _PAIR_SPECIAL_TOKENS
        desc_view = description_token_view(
            tokenizer,
            description_model,
            head_tokens=head_tokens or 225,
            tail_tokens=tail_tokens or 225,
            max_desc_tokens=budget,
        )
        encoded = tokenizer(
            desc_view,
            max_length=max_length,
            truncation=True,
            padding=False,
            add_special_tokens=True,
        )
        assert len(encoded["input_ids"]) <= max_length
        return encoded

    budget = description_token_budget(tokenizer, title_model, max_length=max_length)
    if strategy == "section_aware_v1":
        desc_view = section_aware_description_view(
            tokenizer, description_model, max_desc_tokens=budget if budget > 0 else 1
        )
    else:
        desc_view = description_token_view(
            tokenizer,
            description_model,
            head_tokens=head_tokens,
            tail_tokens=tail_tokens,
            max_desc_tokens=budget if budget > 0 else 1,
        )
    encoded = tokenizer(
        title_model or "",
        desc_view,
        max_length=max_length,
        truncation="only_second",
        padding=False,
        add_special_tokens=True,
    )
    # ponytail: safety clamp — only_second can still overflow on very long titles
    if len(encoded["input_ids"]) > max_length:
        title_ids = _title_token_ids(tokenizer, title_model)
        if len(title_ids) + _PAIR_SPECIAL_TOKENS >= max_length:
            title_ids = title_ids[: max_length - _PAIR_SPECIAL_TOKENS - 1]
            encoded = tokenizer.prepare_for_model(
                title_ids,
                add_special_tokens=True,
                max_length=max_length,
                truncation=True,
                padding=False,
            )
        else:
            encoded = tokenizer(
                title_model or "",
                desc_view,
                max_length=max_length,
                truncation=True,
                padding=False,
            )
    assert len(encoded["input_ids"]) <= max_length, f"len={len(encoded['input_ids'])}"
    return encoded
