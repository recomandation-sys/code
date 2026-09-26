# KB semantic family fallback

`SemanticFamilyResolver` is the final family/parent/leaf fallback in the
existing `JobNLPService` cascade. It never emits retired taxonomy IDs:
profiles are built from the current KB leaf rows (124 leaves after the
functional-development cleanup) in
`job_nlp/knowledge_base/it_knowledge.sqlite` and every accepted `leaf_id` is a KB
leaf.

## Flow

```text
reviewed KB title -> regex/aliases -> RapidFuzz -> ESCO paths -> TF-IDF parent
                 -> E5 top-20 retrieval -> title/requirements/technology rerank
                 -> hierarchy + lexical gate -> UNKNOWN
```

The E5 model receives `query: <incoming title>` for high-recall retrieval and
profiles receive `passage: <KB label>. <reviewed title variant>`. The top 20
retrieved leaves are reranked with an enriched query containing the title,
requirements/qualifications/skills sections, and observed technologies. A
lexical title-overlap guard prevents description boilerplate from changing the
occupation. Every emitted path is validated through the KB leaf → parent →
family relation.

Profile vectors are normalized and cached at
`job_nlp/artifacts/models/semantic_family/profile_vectors.npz`, with a
fingerprint manifest in `profile_metadata.json`. Rebuild after reviewed KB
title changes with:

```bash
python -m job_nlp.scripts.calibrate_semantic_family --rebuild
```

The provisional operating parameters are configurable (`top_k=20`,
`threshold=0.55`, `margin=0.015`). Separate family, parent, leaf,
title-only, and title-plus-description thresholds are exposed for calibration.
The resolver records retrieval score, rerank score, lexical overlap, candidate
rank, margin, and abstention reason in `last_decision`, which the service adds
to quality warnings as `semantic_decision:{...}`.

## Evaluation and calibration

Provide JSON/JSONL records with `title`, `description`, and reviewed
`family`/`parent`/`leaf`:

```bash
python -m job_nlp.scripts.calibrate_semantic_family --input reviewed.json \
  --output job_nlp/artifacts/reports/semantic_family_calibration.json
```

The report measures accepted-semantic precision, coverage, and abstention.
The model's upstream benchmark is not used as project accuracy; the reviewed
124-leaf KB set is authoritative.

The model is loaded once by the service's resolver instance and profile
embeddings are computed once per cache fingerprint. If model weights are not
available locally, the resolver records `semantic_model_unavailable` and the
normal deterministic pipeline continues, ending in `UNKNOWN` only after all
enabled tiers abstain.
