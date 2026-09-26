"""Experimental leaf scorer consuming duty text selected by the website adapter.

No website-layout parser, occupation-specific override, or non-IT title list.
The existing E5 bundle and 118-leaf registry remain authoritative.
"""
from __future__ import annotations

import sys
from pathlib import Path

from classifier_config import CLASSIFIER_CONFIG, LeafClassifierConfig
from evidence_decision import aggregate_chunks, decide_leaf, grounded_technology_scores
from it_leaf_pipeline_tech15 import load_bundle, normalize_occupation_title
from support import load_registry

_TECH_DIR = Path(__file__).resolve().parents[1] / "technologies"
if str(_TECH_DIR) not in sys.path:
    sys.path.insert(0, str(_TECH_DIR))
from technology_v2 import recover_full_text  # noqa: E402


def duty_windows(tokenizer, duty_text: str, config: LeafClassifierConfig = CLASSIFIER_CONFIG) -> list[str]:
    """Overlap token windows of already selected job-duty text."""
    prefix = "query: "
    budget = max(1, config.chunk_size - len(tokenizer.encode(prefix, add_special_tokens=False)) - 2)
    ids = tokenizer.encode(duty_text or "", add_special_tokens=False)
    if not ids:
        return []
    stride = max(1, budget - min(config.chunk_overlap, budget - 1))
    chunks = []
    for start in range(0, len(ids), stride):
        chunks.append(prefix + tokenizer.decode(ids[start:start + budget]))
        if start + budget >= len(ids):
            break
    return chunks


def classify_leaf(title: str, duty_text: str, *, technology_text: str | None = None, config: LeafClassifierConfig = CLASSIFIER_CONFIG) -> dict:
    """Score the fixed leaves; return SELECTED, REVIEW_AMBIGUOUS, or NO_LEAF.

    technology_text can include the full offer so explicit requirement technologies
    remain available without using that text as occupational duty evidence.
    """
    bundle = load_bundle()
    leaves, _, _, _, relations, _, _ = load_registry()
    names = [row["leaf_name"] for row in leaves]
    if names != bundle["names"]:
        raise ValueError("leaf registry and embedding bundle disagree")
    model = bundle["model"]
    encode = dict(normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False)
    query = normalize_occupation_title(title or "") or (title or "")
    title_scores = {name: 0.0 for name in names}
    if query.strip():
        vector = model.encode([f"query: {query}"], **encode)[0]
        for index, cosine in enumerate((vector @ bundle["title_vectors"].T).tolist()):
            for name in bundle["catalog_leaves"][index]:
                title_scores[name] = max(title_scores[name], float(cosine))
    definition_scores = {name: 0.0 for name in names}
    task_scores = {name: 0.0 for name in names}
    chunks = duty_windows(model.tokenizer, duty_text, config)
    if chunks:
        vectors = model.encode(chunks, batch_size=64, **encode)
        definition_matrix = vectors @ bundle["definition_vectors"].T
        task_matrix = vectors @ bundle["task_vectors"].T
        for index, name in enumerate(names):
            definition_scores[name] = aggregate_chunks(definition_matrix[:, index], config.definition_aggregation_method, config.top_n_chunks)
            start, end = bundle["task_owner"][index]
            if end > start:
                per_chunk = task_matrix[:, start:end].max(axis=1)
                task_scores[name] = aggregate_chunks(per_chunk, config.task_aggregation_method, config.top_n_chunks)
    tech_text = f"{title or ''}\n{technology_text if technology_text is not None else duty_text or ''}"
    hits = recover_full_text(tech_text) if tech_text.strip() else []
    ids = sorted({hit.taxonomy_id for hit in hits if hit.taxonomy_id in relations})
    technology_scores = grounded_technology_scores(ids, relations, names)
    if not query.strip() and not chunks and not ids:
        return decide_leaf({}, config)
    channels = {name: {"title": title_scores[name], "technology": technology_scores[name], "definition": definition_scores[name], "main_tasks": task_scores[name]} for name in names}
    result = decide_leaf(channels, config)
    result["technology_ids"] = ids
    return result
