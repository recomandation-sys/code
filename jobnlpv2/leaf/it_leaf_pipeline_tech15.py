"""100-offer test: technology lines replace profile evidence.

Baseline = 0.75 * title + 0.25 * technology cosine.
Enriched = 0.70 * title + 0.15 * technology + 0.15 * (definition + main tasks) / 2.

Technology lines are the `technologies` field of each leaf profile, not the
task or skill lines. The frozen best pipeline is not changed.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np

from support import (
    MODEL,
    OFFERS,
    PROFILES,
    REPORT,
    TITLES,
    is_out,
    load_registry,
    name_key,
    parts,
    read_csv,
    role_override,
    sections,
    windows,
)
_TITLE_NORMALIZATION = Path(__file__).resolve().parents[2] / "job_nlp" / "taxonomy" / "title_normalization.py"
_spec = importlib.util.spec_from_file_location("title_normalization", _TITLE_NORMALIZATION)
if _spec is None or _spec.loader is None:
    raise ImportError(str(_TITLE_NORMALIZATION))
_title_normalization = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_title_normalization)
normalize_occupation_title = _title_normalization.normalize_occupation_title

ROOT_OUT = REPORT


def rank(scores: dict) -> list[tuple[str, float]]:
    return sorted(scores.items(), key=lambda item: (-item[1], item[0]))


def leaf_max(chunk_matrix, owner, names: list[str]) -> dict[str, float]:
    scores = {name: 0.0 for name in names}
    for index, name in enumerate(names):
        start, end = owner[index]
        if end > start:
            scores[name] = float(chunk_matrix[:, start:end].max())
    return scores


def choose(raw, english, duties, names, leaf_title, leaf_tech, leaf_definition, leaf_tasks):
    """Frozen 70/15/15 leaf. Baseline is computed and not emitted."""
    baseline = {
        name: 0.75 * leaf_title[name] + 0.25 * leaf_tech[name]
        for name in names
    }
    enriched = {
        name: 0.70 * leaf_title[name] + 0.15 * leaf_tech[name] + 0.15 * (leaf_definition[name] + leaf_tasks[name]) / 2.0
        for name in names
    }
    base_leaf = rank(baseline)[0][0]
    rich_leaf = rank(enriched)[0][0]
    moved = role_override(raw, english, duties, base_leaf)
    if moved:
        base_leaf = moved
    moved = role_override(raw, english, duties, rich_leaf)
    if moved:
        rich_leaf = moved
    if is_out(raw, english):
        base_leaf, rich_leaf = "OUT_OF_IT_DOMAIN", "OUT_OF_IT_DOMAIN"
    return base_leaf, rich_leaf


def main():
    leaves, by_name, definitions, tasks, by_id, keys, _unmatched = load_registry()
    names = [row["leaf_name"] for row in leaves]
    profiles = json.loads(PROFILES.read_text(encoding="utf-8"))["leaf_profiles"]
    tech_by_leaf = {
        name_key(profile["leaf"]): [str(item) for item in profile["technologies"] if str(item).strip()]
        for profile in profiles
    }
    tech_lines, tech_owner = [], []
    task_lines, task_owner = [], []
    for row in leaves:
        items = tech_by_leaf.get(name_key(row["leaf_name"]), [])
        tech_owner.append((len(tech_lines), len(tech_lines) + len(items)))
        tech_lines.extend(items)
        atoms = parts(tasks[name_key(row["leaf_name"])]["main_tasks"])
        task_owner.append((len(task_lines), len(task_lines) + len(atoms)))
        task_lines.extend(atoms)
    catalog = [row for row in read_csv(TITLES) if (row.get("Title") or "").strip()]
    catalog_leaves = []
    for row in catalog:
        catalog_leaves.append([
            by_name[name_key(leaf)]["leaf_name"]
            for leaf in parts(row.get("Leafs") or "")
            if name_key(leaf) in by_name
        ])
    offers = [json.loads(line) for line in OFFERS.read_text(encoding="utf-8").splitlines() if line.strip()]
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(str(MODEL))
    title_vectors = model.encode(
        [f"passage: {row['Title']}" for row in catalog],
        normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False, batch_size=64,
    )
    tech_vectors = model.encode(
        [f"passage: {line}" for line in tech_lines],
        normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False, batch_size=64,
    )
    definition_vectors = model.encode(
        [f"passage: {definitions[name_key(name)]['definition']}" for name in names],
        normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False,
    )
    task_vectors = model.encode(
        [f"passage: {line}" for line in task_lines],
        normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False, batch_size=64,
    )
    prepared, chunk_text = [], []
    for offer in offers:
        raw = offer.get("title") or ""
        query = normalize_occupation_title(raw) or raw
        duties, required, quality = sections(offer.get("description") or "")
        chunks = windows(model.tokenizer, duties or required or offer.get("description") or "")
        prepared.append((raw, query, duties, required, quality, len(chunk_text), len(chunk_text) + len(chunks)))
        chunk_text.extend(chunks)
    query_vectors = model.encode(
        [f"query: {item[1]}" for item in prepared],
        normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False,
    )
    chunk_vectors = model.encode(
        chunk_text, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False, batch_size=64,
    )
    title_cosine = query_vectors @ title_vectors.T
    rows = ["| Job title | Baseline leaf | Enriched leaf |", "|---|---|---|"]
    details = []
    differ = 0
    for index, offer in enumerate(offers):
        raw, _query, duties, required, _quality, start, end = prepared[index]
        leaf_title = {name: 0.0 for name in names}
        for row_index, score in enumerate(title_cosine[index].tolist()):
            for leaf_name in catalog_leaves[row_index]:
                if score > leaf_title[leaf_name]:
                    leaf_title[leaf_name] = float(score)
        leaf_tech = {name: 0.0 for name in names}
        leaf_definition = {name: 0.0 for name in names}
        leaf_tasks = {name: 0.0 for name in names}
        if end > start:
            tech_matrix = chunk_vectors[start:end] @ tech_vectors.T
            definition_matrix = chunk_vectors[start:end] @ definition_vectors.T
            task_matrix = chunk_vectors[start:end] @ task_vectors.T
            leaf_tech = leaf_max(tech_matrix, tech_owner, names)
            for leaf_index, name in enumerate(names):
                leaf_definition[name] = float(definition_matrix[:, leaf_index].max())
                task_start, task_end = task_owner[leaf_index]
                if task_end > task_start:
                    leaf_tasks[name] = float(task_matrix[:, task_start:task_end].max(axis=0).mean())
        base_leaf, rich_leaf = choose(
            raw, raw, duties, names, leaf_title, leaf_tech, leaf_definition, leaf_tasks,
        )
        if base_leaf != rich_leaf:
            differ += 1
        title = raw.replace("|", "/")
        rows.append(f"| {title} | {base_leaf} | {rich_leaf} |")
        details.extend(["", f"## {raw}", "", f"Baseline: {base_leaf}", "", f"Enriched: {rich_leaf}", "", duties or "(no Job section)", ""])
        print(f"{offer.get('n')} {base_leaf} | {rich_leaf} | {raw[:40]}", flush=True)
    lines = [
        "# 100 offers: title 70, technology 15, role text 15",
        "",
        "Profile task and skill lines are not used. Technology is the max cosine between the Job section and that leaf's technology names. The Job section is the text between Job and Required profile.",
        "",
        "Baseline = 0.75 title + 0.25 technology.",
        "",
        "Enriched = 0.70 title + 0.15 technology + 0.15 (definition + main tasks) / 2.",
        "",
        f"The two leaves differ on {differ} offers.",
        "",
        *rows,
        "",
        *details,
    ]
    ROOT_OUT.mkdir(parents=True, exist_ok=True)
    (ROOT_OUT / "README.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"differ {differ}", flush=True)
    print(f"wrote {ROOT_OUT / 'README.md'}", flush=True)


_BUNDLE = None


def load_bundle():
    """Catalog vectors for one-offer scoring. The 100-offer script keeps its own batch path."""
    global _BUNDLE
    if _BUNDLE is not None:
        return _BUNDLE
    leaves, by_name, definitions, tasks, _by_id, _keys, _unmatched = load_registry()
    names = [row["leaf_name"] for row in leaves]
    profiles = json.loads(PROFILES.read_text(encoding="utf-8"))["leaf_profiles"]
    tech_by_leaf = {
        name_key(profile["leaf"]): [str(item) for item in profile["technologies"] if str(item).strip()]
        for profile in profiles
    }
    tech_lines, tech_owner = [], []
    task_lines, task_owner = [], []
    for row in leaves:
        items = tech_by_leaf.get(name_key(row["leaf_name"]), [])
        tech_owner.append((len(tech_lines), len(tech_lines) + len(items)))
        tech_lines.extend(items)
        atoms = parts(tasks[name_key(row["leaf_name"])]["main_tasks"])
        task_owner.append((len(task_lines), len(task_lines) + len(atoms)))
        task_lines.extend(atoms)
    catalog = [row for row in read_csv(TITLES) if (row.get("Title") or "").strip()]
    catalog_leaves = []
    for row in catalog:
        catalog_leaves.append([
            by_name[name_key(leaf)]["leaf_name"]
            for leaf in parts(row.get("Leafs") or "")
            if name_key(leaf) in by_name
        ])
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(str(MODEL))
    encode = dict(normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False)
    _BUNDLE = {
        "names": names,
        "by_name": by_name,
        "model": model,
        "catalog_leaves": catalog_leaves,
        "tech_owner": tech_owner,
        "task_owner": task_owner,
        "title_vectors": model.encode([f"passage: {row['Title']}" for row in catalog], batch_size=64, **encode),
        "tech_vectors": model.encode([f"passage: {line}" for line in tech_lines], batch_size=64, **encode),
        "definition_vectors": model.encode(
            [f"passage: {definitions[name_key(name)]['definition']}" for name in names], **encode,
        ),
        "task_vectors": model.encode([f"passage: {line}" for line in task_lines], batch_size=64, **encode),
    }
    return _BUNDLE


def assign_leaf(title: str, description: str) -> str:
    """Enriched leaf name for one offer. OUT_OF_IT_DOMAIN is not one of the 118 leaves."""
    bundle = load_bundle()
    raw = title or ""
    query = normalize_occupation_title(raw) or raw
    duties, required, _quality = sections(description or "")
    model = bundle["model"]
    chunks = windows(model.tokenizer, duties or required or description or "")
    encode = dict(normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False)
    query_vector = model.encode([f"query: {query}"], **encode)[0]
    names = bundle["names"]
    leaf_title = {name: 0.0 for name in names}
    for row_index, score in enumerate((query_vector @ bundle["title_vectors"].T).tolist()):
        for leaf_name in bundle["catalog_leaves"][row_index]:
            if score > leaf_title[leaf_name]:
                leaf_title[leaf_name] = float(score)
    leaf_tech = {name: 0.0 for name in names}
    leaf_definition = {name: 0.0 for name in names}
    leaf_tasks = {name: 0.0 for name in names}
    if chunks:
        chunk_vectors = model.encode(chunks, batch_size=64, **encode)
        tech_matrix = chunk_vectors @ bundle["tech_vectors"].T
        definition_matrix = chunk_vectors @ bundle["definition_vectors"].T
        task_matrix = chunk_vectors @ bundle["task_vectors"].T
        leaf_tech = leaf_max(tech_matrix, bundle["tech_owner"], names)
        for leaf_index, name in enumerate(names):
            leaf_definition[name] = float(definition_matrix[:, leaf_index].max())
            task_start, task_end = bundle["task_owner"][leaf_index]
            if task_end > task_start:
                leaf_tasks[name] = float(task_matrix[:, task_start:task_end].max(axis=0).mean())
    _base, rich = choose(raw, raw, duties, names, leaf_title, leaf_tech, leaf_definition, leaf_tasks)
    return rich


if __name__ == "__main__":
    main()
