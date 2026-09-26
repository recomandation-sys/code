# Leaf extraction

`extractionv2` calls `assign_leaf(title, description)` in `it_leaf_pipeline_tech15.py` after the English gate has accepted the offer. The function returns one string: the enriched leaf name. Family and parent are not chosen here. `extractionv2` looks that name up in `inputs/leaves_best.csv`. The row is kept only when the name is one of those 118 `leaf_name` values. `OUT_OF_IT_DOMAIN` and any other name become a refuse row with reason `NO_LEAF`. Education, contract, work mode, experience, and technologies do not run on that row.

`load_bundle` runs once per process and keeps the encoded catalog. Each later offer only encodes its own title and job text.

## Inputs

| File | Role |
|---|---|
| `inputs/leaves_best.csv` | 118 leaves, 24 parents, 8 families. `load_registry` stops if those counts fail, or if the `L0001` name in `leafs_best.csv` equals the `L001` name here. Joining is by leaf name, not by stripping an id. |
| `inputs/it_titles_master_taxonomy_no_seniority_best.csv` | Catalog titles. Column `Title` is encoded. Column `Leafs` lists the leaves that title may vote for, separated by `;`. |
| `inputs/leaf_profiles_compact_118_24_8_enriched_best.json` | Each leaf's `technologies` list. Those names are the technology passages. Task and skill lines in the profile are not encoded. |
| `inputs/definitions_best.csv` | One `definition` passage per leaf. |
| `inputs/main_tasks_best.csv` | `main_tasks`, split on `;` into one passage per task. |
| `models/job-title-normalizer-e5-base` | The encoder. Vectors are L2-normalized, so cosine similarity is the dot product. |

Catalog titles, technology names, definitions, and task lines are encoded as `passage: ...`. The offer title and the job-text windows are encoded as `query: ...`.

## One offer

1. The page title is the title scraped from the `/en/` offer. `normalize_occupation_title` in `job_nlp/taxonomy/title_normalization.py` strips seniority, work arrangement, job ids, salary fragments, and a trailing location. Role words and technology tokens stay. If that result is empty, the scraped title is the query. The stored offer title stays the scraped title.
2. `sections` takes the text between `Job :` and `Required profile :`. That span is the duties. If the pattern is missing, duties are empty and the whole description is the fallback text.
3. The text that is windowed is duties, or the required-profile tail when duties are empty, or the whole description when both are empty.
4. `windows` tokenizes that text with the model tokenizer. The budget is 64 tokens minus the `query: ` prefix minus 2, and at least 8. Windows overlap by half that budget. Each window is already prefixed with `query: `.
5. The title vector is one encoding of `query: ` plus the retrieval query. Its dot product with every catalog title vector is the title cosine of that catalog row.
6. A catalog row gives its cosine to every leaf named in `Leafs` that exists in `leaves_best.csv`. A leaf's title score is the highest cosine among catalog titles that name it. A leaf with no catalog title stays at 0.
7. When windows exist, three more scores are computed from those window vectors:
   - Technology: the maximum cosine between any window and any technology name of that leaf.
   - Definition: the maximum cosine between any window and that leaf's definition.
   - Main tasks: for each task, the maximum cosine over windows, then the mean of those maxima. A leaf with no tasks stays at 0.
8. When there are no windows, technology, definition, and main tasks stay 0. The title score is still computed.

Definitions, catalog titles, and technology names are encoded as one passage each. They are not split by `windows`. A passage longer than the model's 64-token limit produces the tokenizer warning seen during a real run.

## The score that is returned

`choose` scores every leaf, then sorts with `rank`: highest score first, and the leaf name A to Z when scores tie.

Baseline, computed and discarded by `assign_leaf`:

```text
0.75 * title + 0.25 * technology
```

Enriched, the score whose winner is returned:

```text
0.70 * title + 0.15 * technology + 0.15 * (definition + main_tasks) / 2
```

After that winner is chosen, `role_override` may replace it. The same function also runs on the baseline winner, which only matters for the 100-offer report. The override looks at the scraped title and the duties:

- A project-manager title whose winner is Artificial Intelligence Engineer, Machine Learning Engineer, NLP Engineer, or Computer Vision Engineer becomes IT Project Manager.
- A Python developer or Python engineer title, without "machine learning" or "data scientist", whose winner is Machine Learning Engineer, Artificial Intelligence Engineer, DevOps Engineer, or Cloud Engineer becomes Backend Developer.
- A Salesforce, ServiceNow, Workday, or Oracle title that also says "cloud", whose winner is Cloud Engineer or Cloud Architect, becomes IT Consultant when the duties do not mention aws, azure, gcp, landing zone, or vpc.
- A support title whose winner is Software Test Engineer or Test Automation Engineer becomes Application Support Specialist when the title or duties mention ticket, sla, incident, applicatif, or java.

`is_out` runs after the override. It sets the name to `OUT_OF_IT_DOMAIN` when the scraped title contains "comptable" or "accountant", or when it contains "commercial", "sédentaire", "sedentaire", or "inside sales" and does not contain engineer, developer, support, analyst, or informatique. `extractionv2` then refuses that name because it is not one of the 118 leaves.

## Batch report

`python jobnlpv2/leaf/it_leaf_pipeline_tech15.py` from the `leaf` directory runs `main` on `inputs/rekrute_it_100_translated_best.jsonl`. It uses the same `choose` function and writes both the baseline leaf and the enriched leaf to `reports/rekrute_it_100_title70_tech15/README.md`. A copy of that report is `frozen_title70_tech15/README.md`. The live pipeline does not read those reports. It calls `assign_leaf` and keeps only the enriched name.
