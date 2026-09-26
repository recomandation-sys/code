# Integrating the database into the English IT extraction pipeline

## 1. Keep observations and occupational knowledge separate

Use the existing extraction architecture:

`NESTA + TECH_TAXONOMY_V2 + BOUNDED_V2_FULL_TEXT_RECOVERY`

Continue extracting professional skills with Nesta and technologies with the existing V2 extractor. Do not re-enable the previously disabled ESCO semantic skill mapping or silently expand the runtime lexicon from the new source-only skill catalog.

The database adds contextual knowledge. It supplies possible occupations, allowed hierarchy paths, official occupation skill profiles, task statements, occupational requirements context, and traceable conflicts. It does not add inferred skills to the CV or offer's observed skill list.

| Information | Store as | Safe interpretation |
|---|---|---|
| Python named in a candidate's experience | `document_skill`, `assertion=possessed` | Evidence of the candidate's reported skill |
| Python explicitly required in an offer | `document_skill`, `assertion=required` | Requirement of this offer |
| Python marked as a plus | `document_skill`, `assertion=preferred` | Optional preference of this offer |
| Python linked to an O*NET occupation | `occupation_skill`, `software_used` | Occupational software profile |
| ESCO essential skill | `occupation_skill`, `essential` | Essential in the source occupation profile, not automatically in this offer |
| O*NET importance/level rating | `occupation_rating` with its scale | Occupational measurement, not candidate proficiency |
| OSCA skill level or O*NET Job Zone | Source qualification context | Typical occupational preparation; not years of candidate experience |
| Technology category or capability | `skill_domain` / `technology_curation` | Product function and possible domain context |

Negated, preferred and unspecified requirements must remain distinct. A phrase such as “no Kubernetes experience required” must not create a required Kubernetes skill. The adapter assumes that these assertions were identified upstream; it does not implement negation or requirement extraction.

## 2. Canonicalize IDs without losing namespaces

The 6,959 TECH V2 IDs are preserved exactly. Use `v_skill_resolution` to obtain a representative ID where a documented equivalence exists. Deduplicate by that representative when comparing profiles, while retaining all original observations and their evidence spans.

The resolution graph includes:

- O*NET software example → TECH V2 through an unambiguous normalized preferred/alternate label.
- ESCO skill → TECH V2 through an unambiguous preferred/alternate label, where available.
- Selected duplicate TECH V2 products → one existing representative ID, with primary-documentation evidence.

This is identity resolution, not broad semantic similarity. C++, C and C# stay distinct. AWS, AWS EC2 and Kubernetes are not equivalent. React and “JavaScript Framework” are not equivalent. A skill such as “use database software” is not identical to MySQL.

ESCO hidden labels are retained for audit/search but excluded from identity lookup: in the supplied data they can contain product examples or even a conflicting product label. Preferred labels take priority over alternate labels. The SQL Server/MySQL collision found in the source files is a regression test.

The runtime `CONTEXT_REQUIRED` policy is preserved. Bare-word matching is not enough for such terms. An already-validated upstream `tech_id` is an accepted input; a bare ambiguous label remains unresolved.

Nesta IDs must be imported using `external_skill_crosswalk(namespace, external_id, skill_id, relation, review_status)`. The archive contains no actual Nesta output, so the table is initially empty. Unknown Nesta IDs remain unresolved, even if their displayed labels look similar to another source concept. Use `src/import_reviewed_crosswalk.py` after preparing the real mapping.

## 3. Resolve the occupation hierarchically

Preserve the previously selected H2 parent resolver, its TF-IDF/XLM-R components and its existing `0.65` threshold. The supplied archive did not include that model, its taxonomy files or a usable legacy-ID crosswalk, so this package cannot validate or replace its predictions.

Recommended integration sequence:

1. Extract the job title, duties, actual skills and separate constraints.
2. Normalize already-extracted technology IDs and reviewed professional-skill IDs.
3. Run the existing H2 parent resolver.
4. Map the legacy parent ID to this proposed version only through an explicit reviewed `legacy_taxonomy_crosswalk`. If that mapping is missing or ambiguous, preserve the legacy result and return `taxonomy_mapping_required` to the integration layer.
5. Query candidate titles/source occupations and retrieve supporting skill/task context.
6. Restrict the leaf resolver to `SELECT leaf_id FROM leaf WHERE parent_id=?`.
7. Score title specificity, actual duty evidence, observed-skill support and competing sibling leaves using your development/validation data.
8. Emit a leaf only when evidence is sufficient. Otherwise keep the parent and `leaf=null`.
9. Derive the family from the accepted parent. Record the taxonomy version, resolver version, evidence and abstention reason.

Do not run three unrelated family, parent and leaf predictions and accept contradictory paths. Composite foreign keys in `occupation_classification`, `title_classification` and `document_role` enforce hierarchy consistency.

**Example:** `Python Developer` supports Software Development but does not distinguish backend, desktop, automation or another specialization. An offer describing Django REST APIs may support Backend Developer; an offer discussing model training may support an AI/data occupation. The current title lookup intentionally does not invent the missing duty evidence.

The separate canonical hierarchy is an analyst proposal. `exports/canonical_taxonomy.csv` and the rule IDs make it reviewable. It is not represented as the official hierarchy of any source or an approved replacement for the existing taxonomy.

## 4. Use three kinds of skill/task context

### A. Direct source occupation profiles

`v_it_occupation_skills` resolves skill identities and limits default results to core IT occupations. `occupation_task` supplies actual tasks of those occupations. These are source-backed facts with original source-row evidence.

The O*NET Software Skills file has occupation/software links, category IDs, Hot Technology and In Demand flags. It does not contain a task ID. Its In Demand flag is occupation-specific and source-snapshot-specific; it is not a requirement of the offer currently being parsed.

### B. Indirect paths through an occupation or activity

`task_candidates()` first retrieves tasks of core source occupations linked to the observed skill. The result is labeled `candidate_via_shared_occupation_not_direct_usage` unless there is a separate literal task mention.

For professional skills, `v_professional_skill_task_paths` follows official descriptor → general work activity → intermediate activity → detailed activity → task edges. The complete path preserves the evidence for each step. Its endpoint is still an indirect association, not an official direct skill/task assertion.

`v_leaf_skill_profile` and `v_leaf_task_profile` aggregate sources under a proposed leaf. For example, an ESCO Data Engineer skill profile can be inspected alongside OSCA Data Engineer tasks. This cross-source alignment depends on the proposed canonical occupation mapping.

### C. Functional-domain proposals for uncovered technologies

Many modern tools in the supplied taxonomy have no exact O*NET/ESCO occupation link. Their functional category can still supply weak context through:

`technology → effective functional domain → candidate parent`

These rows are in `v_skill_parent_candidates` and `exports/skill_parent_candidates.csv`. They are explicitly **supporting context, not occupation assignments**. A deployment tool can support several infrastructure parents; it does not make every user a DevOps engineer.

If no source-linked task candidates exist, the adapter exposes a separate `domain_fallback_candidates` list. These use a proposed functional domain, candidate parent and matching task tags. They are weaker than a source occupation path and must not be promoted to extracted job requirements, candidate skills, or direct software/task facts.

Technologies with insufficient evidence remain in the coverage/review files. Preserving those gaps is preferable to manufacturing specific tasks for thousands of tools.

## 5. Build recommendation features from actual CV and offer evidence

For each candidate/offer pair, compute distinct features rather than one opaque score:

- Parent agreement, or an explicit transition/related-occupation signal.
- Leaf agreement only where both leaves are sufficiently reliable.
- Coverage of explicitly required, resolved job skills.
- Coverage of explicitly preferred, resolved job skills.
- Unresolved skill counts and proportion of requirement evidence that was normalized.
- Actual documented experience, language, qualification and work-preference compatibility.

`compare_profiles()` demonstrates observed-only required/preferred comparison. Duplicate product IDs do not inflate the numerator or denominator. A null ratio means no resolved requirements of that type, not a perfect match. Unresolved required skills are returned separately; they are not silently treated as satisfied or as missing competence.

An “unobserved required skill” means absent from the parsed CV evidence, not proof that the person lacks it. A source occupation's full skill profile never becomes the candidate's skill inventory. Occupational interests, work styles and preparation data are optional reference context, not inferred personal traits or mandatory candidate filters.

The `rank` CLI supplies an inspectable retrieval baseline with source evidence. It uses IDF-weighted observed-skill overlap and an exact-title-alias signal. Its scores are not calibrated probabilities, and profile breadth differs across sources. It is a debugging/reference starting point for your existing resolver, not evidence that recommendation quality has improved.

## 6. Evaluate before changing production behavior

Construct an English validation set of real IT offers and CVs with independent human labels. Include generic titles, near-neighbor leaves, mixed responsibilities, sparse descriptions, emerging technologies, non-IT network terms, and context-dependent product words.

Use separate train/development/test splits; deduplicate near-identical offers before splitting. Keep the final test set closed during threshold, taxonomy and rule development. Titles and taxonomy entries alone are not a gold dataset of real job-offer classifications.

Measure parent and leaf macro-F1, hierarchical exact match, leaf precision conditional on emission, abstention/coverage, title-link precision and task-link precision by evidence tier. For recommendations, evaluate Recall@K and nDCG@K on labeled candidate/offer relevance, with required-skill mismatch review. Slice results by occupation frequency and ambiguous title type.

Compare the current pipeline against additions incrementally: source-title candidates, official skill profiles, task evidence, then weak functional-domain features. A feature can increase coverage while worsening precision; retain it only when the measured tradeoff is acceptable.

## 7. Provenance, refresh and database deployment

Every source fact has an evidence ID pointing to a file fingerprint, row/sheet locator and original source record. Ratings preserve scale IDs, update dates, suppression flags, sample sizes and available uncertainty fields. Use `v_usable_occupation_ratings` to exclude suppressed/not-relevant rows and inspect the original scale before combining measurements.

For updates, retain stable source URIs/codes and user tech IDs. Bump the knowledge/taxonomy version, regenerate source mappings, compare additions/deletions and review changed meanings. Do not replace a reviewed mapping solely because a newer string match appears.

The runtime opens SQLite read-only. In an application, keep the reference snapshot separate from mutable user documents, or import the schema/data into your application's database. Enable SQLite foreign keys on every writing connection. The portable snapshot preserves SQL values and types; PostgreSQL adoption requires replacing SQLite-specific JSON/FTS syntax and configuring an equivalent search index.

Primary reference documentation:

- O*NET software skills: https://www.onetcenter.org/dictionary/31.0/csv/software_skills.html
- O*NET task/activity edges: https://www.onetcenter.org/dictionary/31.0/csv/tasks_to_dwas.html
- ESCO model: https://esco.ec.europa.eu/en/about-esco/escopedia/escopedia/two-pillar-structure-esco
- OSCA structure: https://www.abs.gov.au/statistics/classifications/osca-occupation-standard-classification-australia/2024-version-1-0/osca-structure

## 8. IT_KB_2.0.0 additive evidence/profile layer

The migration `src/apply_taxonomy_v2_evidence_migration.py` adds a non-destructive evidence layer. Existing family, parent, leaf, title and occupation IDs remain unchanged. The new tables are:

- `role_track` and `family_role_track` for cross-functional design, delivery, enablement, specialized-domain and exclusion tracks;
- `leaf_profile` for versioned definitions, readiness status and missing-gate reasons;
- `leaf_source_occupation` and `leaf_alias` for source IDs and source occupation labels;
- `leaf_task_evidence`, `leaf_skill_profile`, and `leaf_technology_profile` for source-linked evidence;
- `leaf_confusion_pair` for human-reviewed sibling disambiguation rules;
- `leaf_title_evidence` for title evidence (title-only, not original source provenance);
- `taxonomy_v2_crosswalk` for identity and role-track migration relationships.

Current migration status: the canonical hierarchy is restricted to 8 families, 26 parents and 128 operational leaves. There are 128 profiles, 85 `CONDITIONAL` source-mapped profiles, 43 `REVIEW_ONLY` profiles, 168 source-occupation links, 777 task rows, 11,835 skill/knowledge rows, 3,878 technology rows, and 1,294 assigned title evidence rows. Two excluded nodes and their 42 titles remain archived outside the canonical hierarchy. Five additional non-core repair/telecom leaves and their 104 titles were removed completely from the working database. SCADA/OT leaves and their five titles are also excluded. No leaf is `ACTIVE`; no confusion pairs have been reviewed yet.

Use `artifacts/reports/taxonomy_v2_leaf_readiness.csv` to see the missing gates for every leaf, `artifacts/reports/taxonomy_v2_leaf_source_provenance.csv` to inspect original source IDs, and the historical residual-taxonomy enrichment template for the pre-retirement 125-leaf stage. The deletion audit is `artifacts/reports/removed_noncore_it_roles.json`; the pre-deletion database backup is `it_knowledge.sqlite.pre_noncore_it_role_removal.bak`. Do not promote a profile to `ACTIVE` until source provenance, duties, skills, technologies, reviewed titles and hard-negative sibling rules are complete.

## 9. IT_KB_2.3.0 functional-subdomain migration

Position/seniority is extracted independently from the job title and description. The canonical occupation taxonomy therefore excludes the 19 position-only leaves (`CTO`, `CIO`, `CDO`, `CISO`, departmental/general IT managers and governance managers). Their 123 reviewed titles and 21 source occupations were retained and deterministically remapped to functional leaves; no title row was deleted.

`PROJECT_PRODUCT` was renamed to `AGILE_PRODUCT_AND_PROJECT_DELIVERY`. `IT_PRODUCT_MANAGER`, `IT_PROJECT_MANAGER`, and `SCRUM_MASTER` remain functional product/project/agile leaves under that parent.

At the IT_KB_2.3.0 stage, the operational counts were **8 families, 28 parents, 130 leaves, 1,341 input titles, and 1,299 assigned title paths**. The subsequent IT_KB_2.4.0 migration is the current production state below. The stage audit is `artifacts/reports/removed_position_leaves.json`; the rollback snapshot is `it_knowledge.sqlite.pre_position_leaf_removal.bak`.

The retired position IDs must not be reintroduced by the old correction workbook. `apply_taxonomy_correction_v2.py` rejects those leaves and the old `PROJECT_PRODUCT` parent. Use the current database export and `AGILE_PRODUCT_AND_PROJECT_DELIVERY` paths for production inference.

## 10. IT_KB_2.4.0 core cloud-platform migration

`OPERATIONAL_TECHNOLOGY` and its `OT_TECHNICIAN`/`SCADA_OT_ENGINEER` leaves are outside the core IT scope and were removed with five classified titles. `CLOUD_ENGINEERING` and `DEVOPS_PLATFORM` were merged into the single parent `CLOUD_AND_PLATFORM` so Cloud Architect, Cloud Engineer, DevOps Engineer, SRE, Platform Engineer, Release Engineer, and the retained Cloud Administrator share one candidate domain. The complete audit is `artifacts/reports/cloud_platform_merge_drop_ot.json`; the rollback snapshot is `it_knowledge.sqlite.pre_cloud_platform_merge.bak`.

## 11. IT_KB_2.5.0 residual taxonomy corrections

The historical production snapshot was **8 families, 24 parents, 125 leaves, 1,336 input titles, 1,294 classified title paths, 1,287 leaf paths and 7 parent-only paths**. `SERVICE_GOVERNANCE` was folded into `SYSTEMS_OPERATIONS` and `HARDWARE_SUPPORT` into `USER_APPLICATION_SUPPORT`; the distinct `SUSTAINABLE_IT` and `COMPUTER_TECHNICIAN` leaves were retained under those functional parents. The former generic programmer sink was subsequently retired and its titles were remapped to functional leaves.

`DATA_SPECIALIST_GENERAL` and `SYSTEMS_SPECIALIST_GENERAL` were removed as semantic sinks. Their titles remain classified at the appropriate parent with `leaf_id=NULL` and an explicit parent-only abstention method. This preserves recall without inventing a specialized leaf.

The former generic software-development sink is no longer a valid enum. Its
59 reviewed titles were remapped to existing functional leaves: ordinary
programmer/developer titles to the most specific surviving software leaf,
systems wording to
`SYSTEMS_ARCHITECT`/`SYSTEMS_PROGRAMMER`, web/XML to surviving functional
developer leaves, network
and radio wording to the corresponding network/telecommunications leaves,
scientific/statistical wording to the computing/data-science leaves, and 3D
development to `GAME_DEVELOPER`. No title row or semantic vector can emit the
retired ID; the full route-by-route audit is
`archive/job_nlp/taxonomy_migrations/`.

`SYSTEMS_ENGINEER` is defined as systems integration/MBSE rather than generic server administration. `EMBEDDED_DESIGNER` is hardware/PCB design; `EMBEDDED_DEVELOPER` is firmware/embedded software. Four directed hard-negative confusion pairs were added for these boundaries. The residual stage had 24 parents/125 leaves; later migrations reduced the live result to 24 parents/118 leaves. Audit: `artifacts/reports/residual_taxonomy_consolidation.json`; rollback snapshots and retired-leaf removal audits are kept under `archive/job_nlp/taxonomy_migrations/`.

## 12. IT_KB_2.5.1 generic-management abstention

Fifteen generic IT-management/CIO titles previously remapped to `ENTERPRISE_ARCHITECT` were corrected to `PLATFORM_INFRASTRUCTURE → SYSTEMS_OPERATIONS` with `leaf_id=NULL`. Three corresponding source-occupation mappings were also changed to parent-only and their leaf evidence was removed. This prevents organizational-management titles from inflating the Enterprise Architect semantic profile; seniority remains an independent extraction field.

The policy now routes future `IT Manager`, `MIS Manager/Director`, `ICT Manager`, `Information Technology Director`, `CIO`, and equivalent generic management titles to the same parent-only path. Current counts are **1,336 titles, 1,272 leaf paths, 22 parent-only paths, and 42 excluded titles**. Audit: `artifacts/reports/generic_it_management_abstention.json`; rollback: `it_knowledge.sqlite.pre_generic_management_abstention.bak`.

## 13. IT_KB_3.0.0 reviewed real-world title enrichment

`src/integrate_enriched_title_hierarchy.py` imports the reviewed artifact
`archive/job_nlp/taxonomy_migrations/application_developer_retirement/title_leaf_parent_family_enriched_124_24_8.json`. It adds
457 unique, manually reviewed market title variants with stable IDs
`TITLE:ENRICHED_100001` through `TITLE:ENRICHED_100457`. The artifact is title
evidence only: it does not create taxonomy nodes, invent source occupations, or
overwrite an existing classification. Existing 2.5.1 generic-management
parent-only corrections therefore remain authoritative.

Each imported title has a required `evidence` row, a `title_classification`
path, and `leaf_title_evidence` linked to the enrichment source file. The
relational foreign keys validate every leaf -> parent -> family path. The source
is explicitly labelled as analyst-provided market enrichment, not ESCO, O*NET,
ISCO or OSCA provenance.

The live KB now contains **1,793 reviewed input titles, 1,869 valid leaf-vector
rows, 74 parent-only/null path records, 8 families, 24 parents and 118
operational leaves**. The canonical reviewed-title source is
`reviewed_titles_candidate_leaf_sets_v3.csv`: it preserves multiple candidate
leaves for ambiguous titles and marks whether description validation is
required. Candidate-only titles never force a single leaf from the title alone.
Five generic sinks (`SECURITY_SPECIALIST_GENERAL`,
`TELECOM_SPECIALIST_GENERAL`, `IT_GENERALIST`, `WEB_DEVELOPER`, and
`MOBILE_DEVELOPER`) were retired in `IT_KB_2.7.0_REMOVE_GENERIC_LEAVES`.
Titles with explicit evidence were remapped to narrow functional leaves;
ambiguous generic and managerial titles remain parent-only. Their valid
alternative reviewed leaf paths are retained in `leaf_title_evidence` for
multi-candidate retrieval. The E5 title index now contains **1,869 vectors x
768 dimensions**, built from the v3 candidate paths; parent-only and
unresolved records are intentionally excluded from leaf vectors.

The exact generic title `Application Developer` is handled by a small live
replacement alias (without reintroducing the retired leaf):
`BACKEND_DEVELOPER`, `FULLSTACK_DEVELOPER`, and `FRONTEND_DEVELOPER`. The first is
the legacy-compatible primary; all three are returned in `occupation_paths`.
Other generic titles such as `Software Engineer` remain parent/leaf
abstentions until the posting supplies distinguishing evidence.

Authoritative outputs:

- `artifacts/reports/title_hierarchy/titles_1793_hierarchy_118_24_8.json`
- `artifacts/reports/title_hierarchy/enriched_title_integration.json`
- `knowledge_base/exports/reviewed_titles_candidate_leaf_sets_v3.csv`
- `knowledge_base/exports/reviewed_titles_with_paths.csv` (legacy fallback)
- `artifacts/models/semantic_title_index/title_metadata.json`

Rollback: `knowledge_base/it_knowledge.sqlite.pre_enriched_title_hierarchy.bak`.

## 14. Custom leaf-profile evidence batches

Official occupation evidence is not available for every canonical leaf. Custom
profile batches therefore use a separate `CUSTOM_LEAF_PROFILE` source and the
`leaf_custom_profile` table. A custom card can provide a role description,
primary outcome, in/out-of-scope boundaries, task signatures, professional
skills, technologies and sibling disambiguators without being presented as an
ESCO, O*NET, ISCO or OSCA fact.

Every batch has a source-file hash and one evidence record per leaf. New cards
are staged as `REVIEW_REQUIRED` and
`NOT_INCLUDED_UNTIL_APPROVED`; they do not enter the semantic vector cache or
change deterministic title resolution. Only a reviewer-approved card with
`review_status='APPROVED'` and `vector_status='APPROVED'` is appended to the
semantic leaf profile text.

Batch 01 is staged for ten high-value leaves. Input:
`knowledge_base/custom_sources/leaf_profiles/batch_01_core_unprofiled.json`.
Staging report:
`artifacts/reports/leaf_evidence/leaf_profile_batch_01_core_unprofiled_staging_report.json`.
The rollback snapshot is
`knowledge_base/it_knowledge.sqlite.pre_custom_leaf_profile_batch_01.bak`.

## 15. Enriched compact leaf profiles and semantic vectors

`leaf_profiles_compact_118_24_8_enriched.json` is the canonical semantic-profile
source for the current 118-leaf vector cache. It contains one validated profile
per live leaf with the hierarchy path, definition, reviewed titles, task
signatures, professional skills, technologies and hard-negative sibling names.
The runtime validates the file against the SQLite leaf/parent/family hierarchy
before loading it; an invalid count, duplicate leaf, missing field or path
mismatch blocks profile loading instead of silently falling back.

The E5 cache is rebuilt with 118 normalized 768-dimensional passage vectors at
`artifacts/models/semantic_family/profile_vectors.npz`, with metadata at
`artifacts/models/semantic_family/profile_metadata.json`. Rebuild it with
`python -m job_nlp.scripts.rebuild_enriched_leaf_vectors` and audit the source
with `python job_nlp/scripts/audit_enriched_leaf_profiles.py`.

The profile file is structurally ready for vector generation, but vector
validity is not the same as classification readiness. The current diagnostic
report is `artifacts/reports/semantic_family_enriched_vector_quality.json` and
the held-out calibration is
`artifacts/reports/semantic_family_calibration_500_enriched.json`. Leaf
classification remains conditional until held-out precision/coverage meets the
deployment policy; description reranking and abstention must remain enabled.
