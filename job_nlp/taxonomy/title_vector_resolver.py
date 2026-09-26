"""Nearest-neighbour fallback over the current reviewed KB job-title index."""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from job_nlp.paths import KNOWLEDGE_BASE_DIR, REPO_ROOT
from job_nlp.taxonomy.calibration_policy import LeafCalibrationPolicy
from job_nlp.taxonomy.model_identity import public_model_identifier
from job_nlp.taxonomy.title_normalization import normalize_occupation_title


def choose_skill_title(
    scored: list[tuple[dict, float]],
    *,
    threshold: float,
    margin: float,
) -> tuple[dict, float, float] | None:
    """Pick one leaf-bearing title. Abstain when the score or the gap is too small."""
    best_by_title: dict[str, tuple[dict, float]] = {}
    for row, score in scored:
        if not str(row.get("leaf_id") or "").strip():
            continue
        if not str(row.get("family_id") or "").strip() or not str(row.get("parent_id") or "").strip():
            continue
        key = str(row.get("title") or "").casefold()
        current = best_by_title.get(key)
        if current is None or score > current[1]:
            best_by_title[key] = (row, score)
    ranked = sorted(best_by_title.values(), key=lambda item: (-item[1], str(item[0].get("title") or "")))
    if not ranked:
        return None
    row, score = ranked[0]
    second = ranked[1][1] if len(ranked) > 1 else 0.0
    gap = float(score - second)
    if score < threshold or gap < margin:
        return None
    return row, score, gap


@dataclass(frozen=True)
class ReviewedTitleMatch:
    title_id: str
    matched_title: str
    family_id: str
    parent_id: str
    leaf_id: str
    score: float
    margin: float


class ReviewedTitleVectorResolver:
    """E5 title retrieval fallback; no taxonomy labels are invented."""

    def __init__(
        self,
        *,
        model=None,
        threshold: float = 0.55,
        margin: float = 0.015,
        top_k: int = 50,
        cache_dir: Path | None = None,
        title_weight: float = 0.60,
        lexical_weight: float = 0.40,
        aggregation_temperature: float = 0.05,
        aggregation_bonus: float = 0.10,
        context_weight: float = 0.25,
    ):
        self.model = model
        self.policy = LeafCalibrationPolicy.load()
        self.threshold = self.policy.title_only_threshold if threshold == 0.55 else threshold
        self.margin = self.policy.margin if margin == 0.015 else margin
        self.top_k = max(2, int(top_k))
        self.title_weight = float(title_weight)
        self.lexical_weight = float(lexical_weight)
        self.aggregation_temperature = max(1e-6, float(aggregation_temperature))
        self.aggregation_bonus = max(0.0, float(aggregation_bonus))
        self.context_weight = min(1.0, max(0.0, float(context_weight)))
        candidate_csv = KNOWLEDGE_BASE_DIR / "exports" / "reviewed_titles_candidate_leaf_sets_v3.csv"
        self.title_csv = (
            candidate_csv
            if candidate_csv.exists()
            else KNOWLEDGE_BASE_DIR / "exports" / "reviewed_titles_with_paths.csv"
        )
        self.uses_candidate_sets = self.title_csv.name == "reviewed_titles_candidate_leaf_sets_v3.csv"
        self.cache_dir = cache_dir or (REPO_ROOT / "job_nlp" / "artifacts" / "models" / "semantic_title_index")
        self._rows: list[dict[str, str]] = []
        self._valid_paths: set[tuple[str, str, str]] = set()
        self._vectors = None
        self.warning = ""
        self.last_decision: dict[str, object] = {}

    def _load_rows(self):
        if not self._rows:
            with self.title_csv.open(encoding="utf-8-sig", newline="") as handle:
                source_rows = list(csv.DictReader(handle))
            if self.uses_candidate_sets:
                expanded_rows: list[dict[str, str]] = []
                for source_row in source_rows:
                    try:
                        paths = json.loads(source_row.get("occupation_paths_json") or "[]")
                    except (TypeError, ValueError, json.JSONDecodeError):
                        paths = []
                    if not isinstance(paths, list):
                        paths = []
                    if not paths and source_row.get("leaf_id"):
                        paths = [{}]
                    for rank, path in enumerate(paths, start=1):
                        path = path if isinstance(path, dict) else {}
                        row = dict(source_row)
                        for field in (
                            "family_id", "family", "parent_id", "parent", "leaf_id",
                            "leaf", "path_rank", "path_role",
                        ):
                            if path.get(field) is not None:
                                row[field] = str(path[field])
                        row["path_rank"] = str(path.get("path_rank", rank))
                        row["path_role"] = str(
                            path.get(
                                "path_role",
                                path.get(
                                    "role",
                                    "alternate_candidate" if rank > 1 else "primary_candidate",
                                ),
                            )
                        )
                        row["candidate_only"] = str(
                            path.get(
                                "candidate_only",
                                str(source_row.get("direct_leaf_allowed", "1")).strip()
                                not in {"1", "true", "yes"},
                            )
                        )
                        row["direct_leaf_allowed"] = str(
                            path.get(
                                "direct_leaf_allowed",
                                source_row.get("direct_leaf_allowed", "1"),
                            )
                        )
                        row["requires_description_validation"] = str(
                            path.get(
                                "requires_description_validation",
                                source_row.get("requires_description_validation", "0"),
                            )
                        )
                        expanded_rows.append(row)
                self._rows = expanded_rows
            else:
                self._rows = source_rows
            db_path = KNOWLEDGE_BASE_DIR / "it_knowledge.sqlite"
            if db_path.exists():
                with sqlite3.connect(db_path) as db:
                    self._valid_paths = {
                        (str(row[0]), str(row[1]), str(row[2]))
                        for row in db.execute("SELECT l.leaf_id, l.parent_id, p.family_id FROM leaf l JOIN parent p ON p.parent_id=l.parent_id")
                    }
                self._rows = [
                    row for row in self._rows
                    if (row.get("leaf_id", ""), row.get("parent_id", ""), row.get("family_id", "")) in self._valid_paths
                ]
                # ``reviewed_titles_with_paths.csv`` contains the primary
                # classification only.  A reviewed title can legitimately
                # have several functional interpretations, so augment the
                # vector index with every additional valid row from the
                # evidence table.  Parent-only titles remain parent-only in
                # the public identity but still provide useful alternatives
                # to the title resolver.
                if not self.uses_candidate_sets:
                    existing = {
                        (str(row.get("title_id", "")), str(row.get("leaf_id", "")))
                        for row in self._rows
                    }
                    with sqlite3.connect(db_path) as db:
                        db.row_factory = sqlite3.Row
                        alternatives = db.execute(
                            """SELECT e.title_id,e.title,i.original_row_number,i.scope,
                                      i.resolution_status,p.family_id,f.label family,
                                      p.parent_id,p.label parent,l.leaf_id,l.label leaf,
                                      e.method,e.review_status
                               FROM leaf_title_evidence e
                               JOIN input_title i ON i.title_id=e.title_id
                               JOIN leaf l ON l.leaf_id=e.leaf_id
                               JOIN parent p ON p.parent_id=l.parent_id
                               JOIN family f ON f.family_id=p.family_id
                               ORDER BY i.original_row_number,e.title_id,e.leaf_id"""
                        ).fetchall()
                    for item in alternatives:
                        row = dict(item)
                        key = (str(row.get("title_id", "")), str(row.get("leaf_id", "")))
                        if key in existing:
                            continue
                        if (
                            str(row.get("leaf_id", "")),
                            str(row.get("parent_id", "")),
                            str(row.get("family_id", "")),
                        ) not in self._valid_paths:
                            continue
                        self._rows.append(row)
        return self._rows

    def load(self) -> bool:
        if self._vectors is not None:
            return self._vectors is not False and self.model is not None
        try:
            if self.model is None:
                from sentence_transformers import SentenceTransformer
                local = REPO_ROOT / "models" / "job-title-normalizer-e5-base"
                self.model = SentenceTransformer(str(local if local.exists() else "Misbahuddin/job-title-normalizer-e5-base"))
            rows = self._load_rows()
            fingerprint = hashlib.sha256(
                "\n".join(
                    "\t".join(
                        str(r.get(field, ""))
                        for field in ("title_id", "title", "family_id", "parent_id", "leaf_id")
                    )
                    for r in rows
                ).encode()
            ).hexdigest()
            vectors_path = self.cache_dir / "title_vectors.npz"
            metadata_path = self.cache_dir / "title_metadata.json"
            if vectors_path.exists() and metadata_path.exists():
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                if metadata.get("fingerprint") == fingerprint:
                    self._vectors = np.load(vectors_path)["vectors"]
                    public_id = public_model_identifier(getattr(self.model, "model_name", "local-e5"))
                    if metadata.get("model") != public_id:
                        metadata["model"] = public_id
                        metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
                    return True
            self._vectors = self.model.encode(
                [f"passage: {r['title']}" for r in rows], normalize_embeddings=True,
                convert_to_numpy=True, show_progress_bar=False, batch_size=32,
            )
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            np.savez_compressed(vectors_path, vectors=self._vectors)
            metadata_path.write_text(json.dumps({"model": public_model_identifier(getattr(self.model, "model_name", "local-e5")), "count": len(rows), "dimensions": int(self._vectors.shape[1]), "fingerprint": fingerprint}, indent=2) + "\n", encoding="utf-8")
            return True
        except Exception as exc:  # noqa: BLE001
            self.warning = f"title_vector_model_unavailable:{type(exc).__name__}"
            self._vectors = False
            return False

    def resolve(
        self,
        title: str,
        *,
        description: str = "",
        allowed_parent: str | None = None,
        allowed_family: str | None = None,
    ) -> ReviewedTitleMatch | None:
        self.last_decision = {"resolver_method": "reviewed_title_vector_fallback", "status": "abstained"}
        if not title.strip() or not self.load():
            return None
        normalized_title = normalize_occupation_title(title) or title.strip()
        query = self.model.encode([f"query: {normalized_title}"], normalize_embeddings=True, convert_to_numpy=True)[0]
        title_scores = self._vectors @ query
        # Keep title retrieval as the high-recall signal, then optionally
        # blend a bounded requirements/skills excerpt.  This makes the second
        # stage use the offer's actual role evidence without allowing company
        # boilerplate or benefits to dominate the title match.
        relevant = self._relevant_text(description)
        context_scores = title_scores
        if relevant and self.context_weight > 0.0:
            context_query = self.model.encode(
                [f"query: {normalized_title}. {relevant}"],
                normalize_embeddings=True,
                convert_to_numpy=True,
            )[0]
            context_scores = self._vectors @ context_query
        scores = (1.0 - self.context_weight) * title_scores + self.context_weight * context_scores
        allowed = np.arange(scores.size)
        if allowed_parent:
            allowed = np.asarray([i for i in allowed if self._rows[int(i)].get("parent_id") == allowed_parent], dtype=int)
        if allowed_family:
            allowed = np.asarray([i for i in allowed if self._rows[int(i)].get("family_id") == allowed_family], dtype=int)
        self.last_decision.update({
            "normalized_title": normalized_title,
            "context_used": bool(relevant and self.context_weight > 0.0),
            "context_weight": self.context_weight,
            "allowed_parent": allowed_parent,
            "allowed_family": allowed_family,
            "candidate_count": int(len(allowed)),
            "model_name": public_model_identifier(getattr(self.model, "model_name", "local-e5")),
            "index_count": len(self._rows),
        })
        if not len(allowed):
            self.last_decision["reason"] = "hierarchy_candidate_set_empty"
            return None
        # A deterministic/semantic parent constraint is already strong
        # evidence. Preserve the conservative historical top-20 title
        # ranking inside that branch; use the broader leaf aggregation only
        # when the title resolver is selecting the complete path itself.
        effective_top_k = 20 if (allowed_parent or allowed_family) else self.top_k
        top = min(effective_top_k, len(allowed))
        local_scores = scores[allowed]
        order = allowed[np.argpartition(local_scores, -top)[-top:]]
        order = order[np.argsort(scores[order])[::-1]]
        query_tokens = self._tokens(normalized_title)
        ranked = []
        for idx in order:
            idx = int(idx)
            profile_tokens = self._tokens(self._rows[idx]["title"])
            overlap = len(query_tokens & profile_tokens) / max(1, len(query_tokens)) if query_tokens else 0.0
            if allowed_parent or allowed_family:
                rerank = 0.80 * float(scores[idx]) + 0.20 * overlap
            else:
                rerank = self.title_weight * float(scores[idx]) + self.lexical_weight * overlap
            ranked.append((rerank, idx, overlap, float(scores[idx])))
        ranked.sort(reverse=True)

        # Several reviewed titles may represent the same leaf. Aggregate the
        # strongest title matches by leaf before choosing a path; otherwise a
        # single near-duplicate title can beat a leaf with broader, consistent
        # title evidence. The log-sum-exp bonus rewards corroboration while
        # retaining the strongest title as the representative evidence.
        by_leaf: dict[str, list[tuple[float, int, float, float]]] = {}
        for candidate in ranked:
            by_leaf.setdefault(self._rows[candidate[1]]["leaf_id"], []).append(candidate)
        leaf_ranked = []
        for leaf_id, candidates in by_leaf.items():
            candidates.sort(reverse=True)
            strongest = candidates[0][0]
            scaled = sum(
                np.exp((candidate[0] - strongest) / self.aggregation_temperature)
                for candidate in candidates
            )
            aggregate = strongest + self.aggregation_bonus * float(np.log(scaled))
            leaf_ranked.append((aggregate, leaf_id, candidates))
        leaf_ranked.sort(reverse=True, key=lambda item: (item[0], item[1]))
        aggregate_mode = not (allowed_parent or allowed_family)
        if aggregate_mode:
            score, best_leaf, best_candidates = leaf_ranked[0]
            second_score = leaf_ranked[1][0] if len(leaf_ranked) > 1 else 0.0
        else:
            score, best, _overlap, _retrieval = ranked[0]
            best_leaf = self._rows[best]["leaf_id"]
            best_candidates = [ranked[0]]
            second_score = ranked[1][0] if len(ranked) > 1 else 0.0
        gap = float(score - second_score)
        best = best_candidates[0][1]
        overlap = best_candidates[0][2]
        row = self._rows[best]
        second_title = ranked[1][1] if len(ranked) > 1 else best
        candidate_paths = []
        for rank, (aggregate, leaf_id, candidates) in enumerate(leaf_ranked[: min(self.top_k, 20)], start=1):
            representative = self._rows[candidates[0][1]]
            strongest = candidates[0]
            candidate_paths.append(
                {
                    "family_id": representative.get("family_id", ""),
                    "parent_id": representative.get("parent_id", ""),
                    "leaf_id": leaf_id,
                    "score": round(float(aggregate), 6),
                    "retrieval_score": round(float(strongest[3]), 6),
                    "lexical_title_overlap": float(strongest[2]),
                    "supporting_title_count": len(candidates),
                    "matched_title": representative.get("title", ""),
                    "rank": rank,
                    "candidate_only": str(
                        representative.get("candidate_only", "")
                    ).strip().casefold() in {"1", "true", "yes"},
                    "direct_leaf_allowed": str(
                        representative.get("direct_leaf_allowed", "1")
                    ).strip().casefold() in {"1", "true", "yes"},
                    "requires_description_validation": str(
                        representative.get("requires_description_validation", "0")
                    ).strip().casefold() in {"1", "true", "yes"},
                    "mapping_mode": representative.get("mapping_mode", ""),
                    "path_role": representative.get("path_role", ""),
                }
            )
        self.last_decision.update({
            "top_title_id": row["title_id"],
            "matched_title": row["title"],
            "top_leaf_id": best_leaf,
            "retrieval_similarity": float(scores[best]),
            "rerank_score": score,
            "lexical_title_overlap": overlap,
            "margin": gap,
            "top2_title_id": self._rows[second_title]["title_id"],
            "candidate_leaf_count": len(leaf_ranked),
            "leaf_aggregation": {
                "mode": "logsumexp" if aggregate_mode else "constrained_top_title",
                "title_weight": self.title_weight,
                "lexical_weight": self.lexical_weight,
                "temperature": self.aggregation_temperature,
                "bonus": self.aggregation_bonus,
            },
            "retrieved_leaf_candidates": [
                {
                    "leaf_id": leaf_id,
                    "aggregate": round(float(aggregate), 6),
                    "best_title": self._rows[candidates[0][1]]["title"],
                    "supporting_title_count": len(candidates),
                }
                for aggregate, leaf_id, candidates in leaf_ranked[:5]
            ],
            "candidate_paths": candidate_paths,
            "threshold_policy_id": self.policy.policy_id,
        })
        # Keep all individually threshold-clearing reviewed-title paths in
        # the decision metadata.  The global margin gate still controls the
        # single primary return value, while callers that support ambiguity
        # can present these valid alternatives as a list.
        accepted_paths = []
        for item in candidate_paths:
            if float(item.get("score", 0.0)) < self.threshold:
                continue
            path = (
                str(item.get("leaf_id", "")),
                str(item.get("parent_id", "")),
                str(item.get("family_id", "")),
            )
            if path not in self._valid_paths:
                continue
            accepted_paths.append({
                **item,
                "margin_to_top": round(float(candidate_paths[0]["score"]) - float(item["score"]), 6),
                "threshold_status": "accepted_candidate",
            })
        self.last_decision["accepted_candidate_paths"] = accepted_paths
        requires_description_validation = str(
            row.get("requires_description_validation", "0")
        ).strip().casefold() in {"1", "true", "yes"}
        if requires_description_validation and not relevant:
            self.last_decision["reason"] = "candidate_set_requires_description"
            return None
        if score < self.threshold or gap < self.margin or not row.get("family_id") or not row.get("parent_id") or not row.get("leaf_id"):
            self.last_decision["reason"] = "invalid_path_or_score_gate" if not row.get("family_id") or not row.get("parent_id") or not row.get("leaf_id") else ("similarity_below_threshold" if score < self.threshold else "margin_below_threshold")
            return None
        self.last_decision.update({"status": "accepted", "title_id": row["title_id"]})
        return ReviewedTitleMatch(row["title_id"], row["title"], row["family_id"], row["parent_id"], row["leaf_id"], score, gap)

    def resolve_from_skills(self, skill_text: str) -> ReviewedTitleMatch | None:
        """Rerank leaf-bearing titles from cleaned skill text. Max over 64-token windows."""
        self.last_decision = {"resolver_method": "reviewed_title_skill_chunks", "status": "abstained"}
        text = " ".join((skill_text or "").split())
        if not text or not self.load():
            self.last_decision["reason"] = "no_skill_text" if not text else "model_unavailable"
            return None
        chunks = self._query_windows(text)
        if not chunks:
            self.last_decision["reason"] = "no_skill_text"
            return None
        encoded = self.model.encode(
            chunks, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False,
        )
        scores = self._vectors @ np.asarray(encoded).T
        best = scores.max(axis=1)
        chosen = choose_skill_title(
            [(self._rows[index], float(best[index])) for index in range(len(self._rows))],
            threshold=self.threshold,
            margin=self.margin,
        )
        self.last_decision.update({
            "query_chunks": len(chunks),
            "threshold": self.threshold,
            "margin_required": self.margin,
            "model_name": public_model_identifier(getattr(self.model, "model_name", "local-e5")),
        })
        if chosen is None:
            self.last_decision["reason"] = "similarity_below_threshold_or_margin"
            return None
        row, score, gap = chosen
        self.last_decision.update({
            "status": "accepted",
            "title_id": row.get("title_id", ""),
            "matched_title": row.get("title", ""),
            "top_leaf_id": row.get("leaf_id", ""),
            "rerank_score": score,
            "margin": gap,
        })
        return ReviewedTitleMatch(
            str(row.get("title_id") or ""),
            str(row.get("title") or ""),
            str(row.get("family_id") or ""),
            str(row.get("parent_id") or ""),
            str(row.get("leaf_id") or ""),
            score,
            gap,
        )

    def _query_windows(self, text: str) -> list[str]:
        limit = int(getattr(self.model, "max_seq_length", 64) or 64)
        prefix = "query: "
        tokenizer = self.model.tokenizer
        prefix_len = len(tokenizer.encode(prefix, add_special_tokens=False))
        budget = max(8, limit - prefix_len - 2)
        ids = tokenizer.encode(text, add_special_tokens=False)
        if not ids:
            return []
        stride = max(1, budget // 2)
        chunks = []
        for start in range(0, len(ids), stride):
            chunks.append(prefix + tokenizer.decode(ids[start : start + budget]))
            if start + budget >= len(ids):
                break
        return chunks

    def resolve_many(
        self,
        title: str,
        *,
        description: str = "",
        allowed_parent: str | None = None,
        allowed_family: str | None = None,
    ) -> list[ReviewedTitleMatch]:
        """Return every reviewed-title leaf clearing the score threshold.

        Unlike :meth:`resolve`, this method deliberately does not apply the
        top-vs-second margin gate.  It is for displaying valid alternative
        leaves and for audit output; the normal single-path resolver remains
        conservative and unchanged.
        """
        self.resolve(
            title,
            description=description,
            allowed_parent=allowed_parent,
            allowed_family=allowed_family,
        )
        matches: list[ReviewedTitleMatch] = []
        for item in self.last_decision.get("accepted_candidate_paths", []) or []:
            matches.append(
                ReviewedTitleMatch(
                    str(item.get("title_id") or ""),
                    str(item.get("matched_title") or ""),
                    str(item.get("family_id") or ""),
                    str(item.get("parent_id") or ""),
                    str(item.get("leaf_id") or ""),
                    float(item.get("score") or 0.0),
                    float(item.get("margin_to_top") or 0.0),
                )
            )
        return matches

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return {x for x in re.findall(r"[a-z0-9][a-z0-9+#./-]*", (text or "").casefold()) if len(x) > 1}

    @staticmethod
    def _relevant_text(description: str) -> str:
        if not description:
            return ""
        text = re.sub(r"<[^>]+>", " ", description)
        text = re.sub(r"\s+", " ", text).strip()
        headings = list(re.finditer(
            r"\b(requirements?|qualifications?|skills?|technologies?|technical skills?|"
            r"responsibilities|what you(?:'|’)ll do|what you will do|must[- ]have|"
            r"nice[- ]to[- ]have|your profile|about the role)\b",
            text,
            re.I,
        ))
        if headings:
            chunks = []
            for i, heading in enumerate(headings[:4]):
                end = headings[i + 1].start() if i + 1 < len(headings) else min(len(text), heading.start() + 1000)
                chunks.append(text[heading.start():end])
            return " ".join(dict.fromkeys(chunks))[:3200]
        return text[:1000]
