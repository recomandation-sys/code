"""Inference-only semantic fallback for the family/parent/leaf resolver.

Profiles are built exclusively from the IT Knowledge Base's reviewed title
paths and canonical hierarchy. No training or new labels are introduced.
"""
from __future__ import annotations

import sqlite3
import hashlib
import html
import json
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from job_nlp.paths import KNOWLEDGE_BASE_DIR, REPO_ROOT
from job_nlp.taxonomy.calibration_policy import LeafCalibrationPolicy
from job_nlp.taxonomy.decision_layer_v2 import responsibility_sections
from job_nlp.taxonomy.model_identity import public_model_identifier
from job_nlp.taxonomy.title_normalization import normalize_occupation_title


ENRICHED_PROFILE_FILE = REPO_ROOT / "leaf_profiles_compact_118_24_8_enriched.json"


@dataclass(frozen=True)
class SemanticMatch:
    family_id: str
    parent_id: str
    leaf_id: str
    score: float
    runner_up_score: float
    margin: float
    profile_text: str
    rank: int = 1


class SemanticFamilyResolver:
    """Lazy sentence-embedding matcher with an explicit abstention gate."""

    def __init__(
        self,
        db_path: Path | None = None,
        *,
        model_name: str | Path | None = None,
        threshold: float = 0.55,
        margin: float = 0.015,
        top_k: int = 20,
        family_threshold: float | None = None,
        parent_threshold: float | None = None,
        leaf_threshold: float | None = None,
        title_only_threshold: float | None = None,
        title_description_threshold: float | None = None,
        cache_dir: Path | None = None,
        policy: LeafCalibrationPolicy | None = None,
    ) -> None:
        self.db_path = db_path or (KNOWLEDGE_BASE_DIR / "it_knowledge.sqlite")
        local_model = REPO_ROOT / "models" / "job-title-normalizer-e5-base"
        self.model_name = str(model_name or (local_model if local_model.exists() else "Misbahuddin/job-title-normalizer-e5-base"))
        self.policy = policy or LeafCalibrationPolicy.load()
        self.threshold = threshold
        self.margin = margin
        self.top_k = max(2, int(top_k))
        # Separate operating points are intentionally exposed for calibration.
        self.family_threshold = family_threshold if family_threshold is not None else self.policy.family_threshold
        self.parent_threshold = parent_threshold if parent_threshold is not None else self.policy.parent_threshold
        self.leaf_threshold = leaf_threshold if leaf_threshold is not None else self.policy.leaf_threshold
        self.title_only_threshold = title_only_threshold if title_only_threshold is not None else self.policy.title_only_threshold
        self.title_description_threshold = title_description_threshold if title_description_threshold is not None else self.policy.title_description_threshold
        self.margin = self.policy.margin if margin == 0.015 else margin
        self.cache_dir = cache_dir or (REPO_ROOT / "job_nlp" / "artifacts" / "models" / "semantic_family")
        self._model = None
        self._profiles: list[tuple[str, str, str, str]] = []
        self._reviewed_title_count = 0
        self._vectors = None
        self.warning: str = ""
        self.last_decision: dict[str, object] = {}

    def _load_profiles(self) -> list[tuple[str, str, str, str]]:
        if self._profiles:
            return self._profiles
        if ENRICHED_PROFILE_FILE.exists():
            self._profiles = self._load_enriched_profiles()
            self._reviewed_title_count = sum(
                len(profile.get("related_titles", []))
                for profile in json.loads(ENRICHED_PROFILE_FILE.read_text(encoding="utf-8"))["leaf_profiles"]
            )
            return self._profiles
        with sqlite3.connect(self.db_path) as db:
            rows = db.execute(
                """
                SELECT l.leaf_id, l.parent_id, p.family_id, l.label,
                       group_concat(v.title, ' | ') AS titles
                FROM leaf AS l
                JOIN parent AS p ON p.parent_id = l.parent_id
                LEFT JOIN v_title_paths AS v
                  ON v.leaf_id = l.leaf_id AND v.scope='core'
                GROUP BY l.leaf_id, l.parent_id, p.family_id, l.label
                ORDER BY l.leaf_id
                """
            ).fetchall()
            self._reviewed_title_count = int(
                db.execute(
                    "SELECT count(DISTINCT title_id) FROM v_title_paths WHERE title IS NOT NULL"
                ).fetchone()[0]
            )
            try:
                custom_rows = db.execute(
                    """SELECT leaf_id,description,primary_outcome,tasks_json,
                              professional_skills_json,technologies_json
                       FROM leaf_custom_profile
                       WHERE review_status='APPROVED' AND vector_status='APPROVED'"""
                ).fetchall()
            except sqlite3.OperationalError:
                # Older snapshots do not have the additive custom-evidence
                # table; the official/title evidence path remains usable.
                custom_rows = []
            approved_custom: dict[str, list[str]] = {}
            for leaf_id, description, primary_outcome, tasks_json, skills_json, technologies_json in custom_rows:
                values = [str(description or ""), str(primary_outcome or "")]
                for raw in (tasks_json, skills_json, technologies_json):
                    try:
                        parsed = json.loads(raw or "[]")
                    except json.JSONDecodeError:
                        parsed = []
                    if isinstance(parsed, list):
                        values.extend(
                            str(item if isinstance(item, str) else item.get("rule", ""))
                            for item in parsed
                            if item
                        )
                approved_custom[str(leaf_id)] = [value for value in values if value]
            # Definitions are deliberately not embedded: this model is tuned
            # for short title retrieval and long prose adds unrelated signals.
        self._profiles = []
        for leaf_id, parent_id, family_id, label, titles in rows:
            # Only labels and reviewed title variants already in the KB are
            # used; no external aliases or invented taxonomy names.
            variants = [str(label or "")]
            variants.extend(t.strip() for t in (titles or "").split("|") if t.strip())
            variants.extend(approved_custom.get(str(leaf_id), []))
            profile = ". ".join(dict.fromkeys(v for v in variants if v))
            self._profiles.append((family_id, parent_id, leaf_id, profile))
        return self._profiles

    def _load_enriched_profiles(self) -> list[tuple[str, str, str, str]]:
        """Load and validate the production leaf-profile source.

        The enriched file is the canonical semantic-profile input. It must
        contain exactly one complete profile for every live leaf and preserve
        the live leaf→parent→family hierarchy before vectors are built.
        """
        payload = json.loads(ENRICHED_PROFILE_FILE.read_text(encoding="utf-8"))
        profiles = payload.get("leaf_profiles")
        if payload.get("schema_version") != "leaf_profiles_comprehensive_v1" or not isinstance(profiles, list):
            raise ValueError("invalid enriched leaf-profile schema")
        with sqlite3.connect(self.db_path) as db:
            hierarchy = {
                row[0]: (row[1], row[2], row[3], row[4])
                for row in db.execute(
                    """SELECT l.leaf_id,l.parent_id,p.family_id,l.label,p.label
                       FROM leaf l JOIN parent p ON p.parent_id=l.parent_id"""
                )
            }
        if len(profiles) != len(hierarchy) or len({p.get("leaf_id") for p in profiles}) != len(profiles):
            raise ValueError("enriched leaf-profile count or uniqueness check failed")

        required = ("family_id", "parent_id", "leaf_id", "definition", "related_titles", "tasks", "professional_skills", "technologies")
        loaded: list[tuple[str, str, str, str]] = []
        for profile in profiles:
            if any(not profile.get(field) for field in required):
                raise ValueError(f"incomplete enriched profile: {profile.get('leaf_id', '<missing>')}")
            leaf_id = str(profile["leaf_id"])
            expected = hierarchy.get(leaf_id)
            if expected is None:
                raise ValueError(f"unknown enriched leaf: {leaf_id}")
            parent_id, family_id, leaf_label, parent_label = expected[:4]
            if profile["parent_id"] != parent_id or profile["family_id"] != family_id:
                raise ValueError(f"hierarchy mismatch for enriched leaf: {leaf_id}")
            parts = [
                f"Family: {profile.get('family') or family_id}",
                f"Parent: {profile.get('parent') or parent_label}",
                f"Leaf: {profile.get('leaf') or leaf_label}",
                f"Definition: {profile['definition']}",
                "Related titles: " + "; ".join(str(value) for value in profile["related_titles"]),
                "Tasks: " + "; ".join(str(value) for value in profile["tasks"]),
                "Professional skills: " + "; ".join(str(value) for value in profile["professional_skills"]),
                "Technologies: " + "; ".join(str(value) for value in profile["technologies"]),
            ]
            loaded.append((str(family_id), str(parent_id), leaf_id, ". ".join(parts)))
        return loaded

    def build_profiles(self) -> list[dict[str, str]]:
        """Return the deterministic current-KB leaf profile manifest."""
        return [
            {"family_id": f, "parent_id": p, "leaf_id": l, "profile_text": text}
            for f, p, l, text in self._load_profiles()
        ]

    def rebuild_cache(self) -> bool:
        """Force profile-vector regeneration after KB title changes."""
        for name in ("profile_vectors.npz", "profile_metadata.json"):
            path = self.cache_dir / name
            if path.exists():
                path.unlink()
        self._vectors = None
        return self.load()

    def load(self) -> bool:
        if self._vectors is not None:
            return self._vectors is not False and self._model is not None
        try:
            from sentence_transformers import SentenceTransformer

            # The model is expected to be pre-cached in production. The
            # installed sentence-transformers version does not expose a
            # stable local_files_only argument, so loading is intentionally
            # delegated to its normal cache resolution.
            self._model = SentenceTransformer(self.model_name)
            profiles = self._load_profiles()
            fingerprint = hashlib.sha256(
                (self.model_name + "\n" + "\n".join(p[3] for p in profiles)).encode("utf-8")
            ).hexdigest()
            vectors_path = self.cache_dir / "profile_vectors.npz"
            metadata_path = self.cache_dir / "profile_metadata.json"
            if vectors_path.exists() and metadata_path.exists():
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                if metadata.get("fingerprint") == fingerprint:
                    import numpy as np

                    self._vectors = np.load(vectors_path)["vectors"]
                    public_id = public_model_identifier(self.model_name)
                    if metadata.get("model_name") != public_id:
                        metadata["model_name"] = public_id
                        metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
                    return True
            self._vectors = self._model.encode(
                [f"passage: {p[3]}" for p in profiles],
                normalize_embeddings=True,
                convert_to_numpy=True,
                show_progress_bar=False,
            )
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            import numpy as np

            np.savez_compressed(vectors_path, vectors=self._vectors)
            metadata_path.write_text(
                json.dumps(
                    {
                        "model_name": public_model_identifier(self.model_name),
                        "fingerprint": fingerprint,
                        "profile_count": len(profiles),
                        "reviewed_title_count": self._reviewed_title_count,
                        "dimensions": int(self._vectors.shape[1]),
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            return True
        except Exception as exc:  # noqa: BLE001
            self.warning = f"semantic_model_unavailable:{type(exc).__name__}"
            self._vectors = False
            return False

    def resolve(
        self,
        title: str,
        description: str = "",
        *,
        allowed_parent: str | None = None,
        allowed_family: str | None = None,
    ) -> SemanticMatch | None:
        self.last_decision = {"resolver_method": "semantic_embedding_fallback", "status": "abstained"}
        if not title.strip() or not self.load():
            if self.warning:
                self.last_decision["reason"] = self.warning
            return None
        # E5 title retrieval is deliberately short and high-recall. Description
        # evidence is used only in the rerank stage below.  A normalized query
        # removes hiring metadata without changing the raw evidence captured by
        # the outer pipeline.
        normalized_title = normalize_occupation_title(title) or title.strip()
        query = f"query: {normalized_title}"
        vector = self._model.encode([query], normalize_embeddings=True, convert_to_numpy=True)[0]
        scores = self._vectors @ vector
        allowed = np.arange(scores.size)
        if allowed_parent:
            allowed = np.asarray([i for i in allowed if self._profiles[int(i)][1] == allowed_parent], dtype=int)
        if allowed_family:
            allowed = np.asarray([i for i in allowed if self._profiles[int(i)][0] == allowed_family], dtype=int)
        if not len(allowed):
            self.last_decision.update({"reason": "hierarchy_candidate_set_empty", "allowed_parent": allowed_parent, "allowed_family": allowed_family})
            return None
        top = min(self.top_k, len(allowed))
        local_scores = scores[allowed]
        order = allowed[np.argpartition(local_scores, -top)[-top:]]
        order = order[np.argsort(scores[order])[::-1]]
        title_tokens = self._tokens(normalized_title)
        relevant = self._relevant_text(description)
        enriched_text = " ".join(x for x in (normalized_title, relevant) if x).strip()
        enriched_scores = scores
        if relevant:
            enriched_vector = self._model.encode(
                [f"query: {enriched_text}"], normalize_embeddings=True, convert_to_numpy=True
            )[0]
            enriched_scores = self._vectors @ enriched_vector
        ranked: list[tuple[float, int, float, float, float]] = []
        for idx in order:
            idx = int(idx)
            lexical_title, lexical_detail = self._lexical_scores(title_tokens, relevant, self._profiles[idx][3])
            # Bi-encoder retrieval supplies recall; lexical evidence prevents a
            # close semantic neighbour from winning without role evidence.
            rerank = 0.70 * float(enriched_scores[idx]) + 0.20 * lexical_title + 0.10 * lexical_detail
            ranked.append((rerank, idx, float(scores[idx]), lexical_title, lexical_detail))
        ranked.sort(reverse=True)
        rerank_score, best_idx, retrieval_score, lexical_title, lexical_detail = ranked[0]
        runner_score = ranked[1][0] if len(ranked) > 1 else 0.0
        gap = rerank_score - runner_score
        best_profile = self._profiles[best_idx]
        retrieval_best_idx = int(order[0])
        # Keep the complete top-k leaf evidence for the outer occupation-path
        # selector.  The resolver still returns one accepted match for legacy
        # callers, while the pipeline can now retain several nearby,
        # taxonomy-valid paths without recomputing embeddings.
        candidate_paths = []
        for rank, (candidate_score, candidate_idx, candidate_retrieval, candidate_title_overlap, candidate_detail_overlap) in enumerate(ranked[: self.top_k], start=1):
            candidate_family, candidate_parent, candidate_leaf, _candidate_profile = self._profiles[int(candidate_idx)]
            candidate_paths.append(
                {
                    "family_id": candidate_family,
                    "parent_id": candidate_parent,
                    "leaf_id": candidate_leaf,
                    "score": round(float(candidate_score), 6),
                    "retrieval_score": round(float(candidate_retrieval), 6),
                    "lexical_title_overlap": float(candidate_title_overlap),
                    "lexical_detail_overlap": float(candidate_detail_overlap),
                    "rank": rank,
                }
            )
        self.last_decision.update(
            {
                "top_leaf_id": best_profile[2],
                "normalized_title": normalized_title,
                "allowed_parent": allowed_parent,
                "allowed_family": allowed_family,
                "candidate_count": int(len(allowed)),
                "model_name": public_model_identifier(self.model_name),
                "profile_count": len(self._profiles),
                "reviewed_title_count": self._reviewed_title_count,
                "retrieval_similarity": retrieval_score,
                "rerank_score": rerank_score,
                "margin": gap,
                "semantic_candidate_rank": int(list(order).index(best_idx) + 1) if best_idx in order else None,
                "top2_leaf_id": self._profiles[int(order[1])][2] if len(order) > 1 else None,
                "retrieved_candidates": [
                    {"leaf_id": self._profiles[idx][2], "retrieval": round(float(scores[idx]), 4), "rerank": round(float(r), 4)}
                    for r, idx, _s, _lt, _ld in ranked[:3]
                ],
                "candidate_paths": candidate_paths,
                "lexical_title_overlap": lexical_title,
                "lexical_detail_overlap": lexical_detail,
                "rerank_changed_candidate": retrieval_best_idx != best_idx,
                "threshold_policy_id": self.policy.policy_id,
                "thresholds": {
                    "family": self.family_threshold,
                    "parent": self.parent_threshold,
                    "leaf": self.leaf_threshold,
                    "mode": "title_description" if relevant else "title_only",
                },
            }
        )
        mode = "title_description" if relevant else "title_only"
        operating_threshold = self.title_description_threshold if relevant else self.title_only_threshold
        if rerank_score < operating_threshold:
            self.last_decision["reason"] = "similarity_below_threshold"
            return None
        # A reranker may not overrule a title constraint without evidence. This
        # is the abstention guard for semantic/lexical disagreement.
        if title_tokens and lexical_title == 0.0 and retrieval_best_idx != best_idx and retrieval_score < self.title_only_threshold:
            self.last_decision["reason"] = "reranker_lexical_disagreement"
            return None
        family_id, parent_id, leaf_id, profile = self._profiles[best_idx]
        if gap < self.margin:
            # Leaf is ambiguous: aggregate evidence by valid parent path and
            # emit only a parent when the parent-level margin is sufficient.
            parent_scores: dict[tuple[str, str], float] = {}
            # Only retrieved candidates may vote for the parent.  Letting every
            # profile participate with a raw title score could select a parent
            # that was not in the top-k retrieval set.
            for score, idx, _retrieval, _lt, _ld in ranked:
                fam, parent = self._profiles[idx][0], self._profiles[idx][1]
                key = (fam, parent)
                parent_scores[key] = max(parent_scores.get(key, -1.0), float(score))
            ranked_parents = sorted(parent_scores.items(), key=lambda item: item[1], reverse=True)
            if len(ranked_parents) < 2 or ranked_parents[0][1] - ranked_parents[1][1] < self.margin:
                self.last_decision["reason"] = "margin_below_threshold"
                return None
            (family_id, parent_id), parent_score = ranked_parents[0]
            self.last_decision.update({"status": "accepted", "leaf_id": "", "parent_id": parent_id})
            parent_threshold = self.policy.threshold("parent", mode=mode, parent_id=parent_id, method="semantic_embedding")
            family_threshold = self.policy.threshold("family", mode=mode, parent_id=parent_id, method="semantic_embedding")
            if parent_score < parent_threshold:
                self.last_decision["reason"] = "parent_score_below_threshold"
                return None
            if parent_score < family_threshold:
                self.last_decision["reason"] = "family_score_below_threshold"
                return None
            return SemanticMatch(family_id, parent_id, "", parent_score, ranked_parents[1][1], parent_score - ranked_parents[1][1], "parent-level semantic profile", 1)
        leaf_threshold = self.policy.threshold("leaf", mode=mode, parent_id=parent_id, leaf_id=leaf_id, method="semantic_embedding")
        if rerank_score < leaf_threshold:
            self.last_decision["reason"] = "leaf_score_below_threshold"
            return None
        if rerank_score < self.policy.threshold("parent", mode=mode, parent_id=parent_id, method="semantic_embedding") or rerank_score < self.policy.threshold("family", mode=mode, parent_id=parent_id, method="semantic_embedding"):
            self.last_decision["reason"] = "hierarchy_score_below_threshold"
            return None
        self.last_decision.update({"status": "accepted", "leaf_id": leaf_id})
        return SemanticMatch(family_id, parent_id, leaf_id, rerank_score, runner_score, gap, profile, 1)

    def resolve_responsibilities(
        self,
        description: str,
        *,
        allowed_parent: str | None = None,
        allowed_family: str | None = None,
    ) -> SemanticMatch | None:
        """Retrieve an occupation from duties/role-summary text independently.

        This reuses the loaded enriched profile index; it is a second signal,
        not a second taxonomy.  A technology list or company boilerplate is
        excluded before the query is encoded.
        """
        self.last_decision = {
            "resolver_method": "responsibility_embedding_fallback",
            "source_mode": "responsibilities",
            "status": "abstained",
        }
        relevant = responsibility_sections(description)
        if not relevant or not self.load():
            self.last_decision["reason"] = "responsibilities_unavailable"
            return None
        vector = self._model.encode(
            [f"query: {relevant}"],
            normalize_embeddings=True,
            convert_to_numpy=True,
        )[0]
        scores = self._vectors @ vector
        allowed = np.arange(scores.size)
        if allowed_parent:
            allowed = np.asarray(
                [i for i in allowed if self._profiles[int(i)][1] == allowed_parent],
                dtype=int,
            )
        if allowed_family:
            allowed = np.asarray(
                [i for i in allowed if self._profiles[int(i)][0] == allowed_family],
                dtype=int,
            )
        if not len(allowed):
            self.last_decision["reason"] = "hierarchy_candidate_set_empty"
            return None
        top = min(self.top_k, len(allowed))
        local_scores = scores[allowed]
        order = allowed[np.argpartition(local_scores, -top)[-top:]]
        order = order[np.argsort(scores[order])[::-1]]
        ranked: list[tuple[float, int, float, float]] = []
        for index in order:
            index = int(index)
            _title_overlap, detail_overlap = self._lexical_scores(
                set(), relevant, self._profiles[index][3]
            )
            rerank = 0.75 * float(scores[index]) + 0.25 * detail_overlap
            ranked.append((rerank, index, float(scores[index]), detail_overlap))
        ranked.sort(reverse=True)
        rerank_score, best_index, retrieval_score, detail_overlap = ranked[0]
        runner_score = ranked[1][0] if len(ranked) > 1 else 0.0
        gap = float(rerank_score - runner_score)
        candidate_paths = []
        for rank, (score, index, retrieval, lexical_detail) in enumerate(
            ranked[: self.top_k], start=1
        ):
            family_id, parent_id, leaf_id, _profile = self._profiles[int(index)]
            candidate_paths.append(
                {
                    "family_id": family_id,
                    "parent_id": parent_id,
                    "leaf_id": leaf_id,
                    "score": round(float(score), 6),
                    "retrieval_score": round(float(retrieval), 6),
                    "lexical_title_overlap": 0.0,
                    "lexical_detail_overlap": float(lexical_detail),
                    "responsibility_support": True,
                    "rank": rank,
                }
            )
        best_profile = self._profiles[best_index]
        self.last_decision.update(
            {
                "normalized_title": "",
                "responsibility_text": relevant,
                "allowed_parent": allowed_parent,
                "allowed_family": allowed_family,
                "candidate_count": int(len(allowed)),
                "model_name": public_model_identifier(self.model_name),
                "profile_count": len(self._profiles),
                "retrieval_similarity": retrieval_score,
                "rerank_score": rerank_score,
                "margin": gap,
                "semantic_candidate_rank": int(list(order).index(best_index) + 1)
                if best_index in order
                else None,
                "top_leaf_id": best_profile[2],
                "top2_leaf_id": self._profiles[int(order[1])][2]
                if len(order) > 1
                else None,
                "retrieved_candidates": [
                    {
                        "leaf_id": self._profiles[index][2],
                        "retrieval": round(float(scores[index]), 4),
                        "rerank": round(float(score), 4),
                    }
                    for score, index, _retrieval, _detail in ranked[:3]
                ],
                "candidate_paths": candidate_paths,
                "lexical_title_overlap": 0.0,
                "lexical_detail_overlap": detail_overlap,
                "threshold_policy_id": self.policy.policy_id,
                "thresholds": {
                    "family": self.family_threshold,
                    "parent": self.parent_threshold,
                    "leaf": self.leaf_threshold,
                    "mode": "responsibilities",
                },
            }
        )
        if rerank_score < self.title_description_threshold:
            self.last_decision["reason"] = "responsibility_score_below_threshold"
            return None
        if gap < self.margin:
            self.last_decision["reason"] = "responsibility_margin_below_threshold"
            return None
        family_id, parent_id, leaf_id, profile = best_profile
        self.last_decision.update(
            {"status": "accepted", "leaf_id": leaf_id, "responsibility_support": True}
        )
        return SemanticMatch(
            family_id,
            parent_id,
            leaf_id,
            rerank_score,
            runner_score,
            gap,
            profile,
            1,
        )

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return {t for t in re.findall(r"[a-z0-9][a-z0-9+#./-]*", text.casefold()) if len(t) > 1}

    @classmethod
    def _relevant_text(cls, description: str) -> str:
        if not description:
            return ""
        text = html.unescape(re.sub(r"<[^>]+>", " ", description))
        text = re.sub(r"\s+", " ", text).strip()
        # Keep only bounded role/qualification sections when headings exist;
        # benefits, culture and employer boilerplate are not occupation
        # evidence and routinely create false semantic neighbours.
        matches = list(re.finditer(
            r"\b(requirements?|qualifications?|skills?|technologies?|technical skills?|"
            r"responsibilities|what you(?:'|’)ll do|what you will do|must[- ]have|"
            r"nice[- ]to[- ]have|your profile|about the role)\b",
            text,
            re.I,
        ))
        if matches:
            chunks = []
            for i, match in enumerate(matches[:4]):
                end = matches[i + 1].start() if i + 1 < len(matches) else min(len(text), match.start() + 1400)
                chunks.append(text[match.start():end])
            return " ".join(dict.fromkeys(chunks))[:4200]
        return text[:1200]

    @classmethod
    def _lexical_scores(cls, title_tokens: set[str], detail: str, profile: str) -> tuple[float, float]:
        profile_tokens = cls._tokens(profile)
        if not title_tokens or not profile_tokens:
            title_overlap = 0.0
        else:
            title_overlap = len(title_tokens & profile_tokens) / max(1, len(title_tokens))
        detail_tokens = cls._tokens(detail)
        detail_overlap = len(detail_tokens & profile_tokens) / max(1, len(detail_tokens)) if detail_tokens else 0.0
        return round(min(1.0, title_overlap), 4), round(min(1.0, detail_overlap), 4)
