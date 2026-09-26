# English IT Knowledge Base — delivery report

## Result

A populated SQLite knowledge database, reproducible ingestion code, a portable data snapshot, review exports, and a Python integration adapter. All supplied 6,959 technology records and 1,445 reviewed job-title rows are retained. The manual-complete application taxonomy `IT_KB_1.1.0_MANUAL_COMPLETE` contains **13 families, 31 parents and 156 leaves**.

The taxonomy is an application-level harmonization proposal. ESCO, O*NET, OSCA and ISCO retain their separate native IDs, hierarchies and evidence. They are not treated as interchangeable classification systems.

## Measured contents

| Content | Records | Interpretation |
|---|---:|---|
| Original technologies | 6,959 | Original IDs, names, aliases and categories preserved |
| All source-specific skill/knowledge records | 12,923 | Includes original technologies; not a deduplicated unique-skill count |
| Reviewed input titles | 1,445 | Every original row retained |
| Core IT source occupations | 175 | 106 ESCO, 29 O*NET, 40 OSCA |
| Conditional source occupations | 36 | Require IT duties/context before application use |
| Reference-only source occupations | 157 | Retained to explain collisions; excluded from IT skill/task profiles |
| Occupation–skill relationships | 16,637 | Relationship types and source evidence retained |
| Source task statements | 1,173 | 885 O*NET and 288 OSCA |
| Task–activity relationships | 1,147 | Source-backed activity links |
| Source evidence records | 186,652 | File and record locators plus original record JSON |
| Relational tables | 52 | Includes empty application observation and integration tables |
| Query views | 16 | Ready-made joins for pipeline use |

See `coverage_metrics.json` for exact machine-readable counts. Domain records include multiple source classification systems and functional proposals; their count is not the number of independent IT business domains.

## Technology coverage: different evidence levels

These measures overlap and must not be added together.

| Coverage across the 6,959 supplied technologies | Count | Share |
|---|---:|---:|
| Core IT occupation link through source relationships and accepted identity mappings | 1,070 | 15.4% |
| Official software-category association through mapped source examples | 3,379 | 48.6% |
| Proposed functional domain | 6,050 | 86.9% |
| Functional domain still unresolved | 909 | 13.1% |
| Literal technology mentions in task text requiring review | 2 | 0.03% |

**The data does not justify a specific task for every technology.** O*NET software examples and tasks are independently connected to occupations. The path `technology → occupation → task` produces useful task candidates, but does not assert that the technology performs that task. The adapter and exports identify these links as indirect. Even the two literal text mentions are review evidence, not automatically verified usage relationships.

For all technologies, `exports/technology_coverage.csv` exposes domains, category corrections, occupation coverage, task-candidate counts and missing links. `exports/skill_parent_candidates.csv` supplies weak domain-derived parent candidates for retrieval. These proposals do not authorize a final occupation assignment.

## Title scope and hierarchy

| Input scope | Titles | Treatment |
|---|---:|---|
| Core IT | 996 | Eligible for proposed taxonomy resolution |
| Conditional | 145 | Require supporting duties from the actual document |
| Review | 295 | Ambiguity, source conflicts, credentials or unresolved meaning |
| Excluded | 9 | Outside IT scope |

Normalized exact source-title correspondences exist for 1,360 titles. A title matching a source label proves lexical correspondence, not the historical origin of the mixed input row. Multiple matching source concepts are retained. Broad titles can resolve to a parent with a null leaf: for example, Python Developer does not by itself establish Backend Developer.

The title-level correction release supplies a reviewed primary path for all 1,445 supplied titles; 42 are explicitly excluded or non-operational labels. The 156 leaves remain taxonomy proposals and should be calibrated against real job offers. Unseen titles require the existing resolver or a separately validated classifier.

## Corrections and safeguards

- Preserve supplied technology categories and add an evidence-backed correction layer: examples include MySQL, PyTorch, Docker and Amazon EC2. Corrections are selective, not a claim that every supplied category has been audited.
- Distinguish preferred/alternative labels from hidden search labels. Hidden ESCO labels are excluded from identity resolution to avoid incorrectly merging MySQL with SQL Server or PyTorch with a generic software-library concept.
- Resolve selected duplicate products while retaining every original technology ID.
- Keep C++, C#, .NET and context-sensitive aliases distinct.
- Keep reference-only non-IT occupations out of IT occupation skill/task profiles.
- Preserve essential/optional/software-used relationships and O*NET rating scales; source occupational expectations are never inserted as observed CV competence or actual job requirements.

## Use in your extraction pipeline

1. Run the existing Nesta professional-skills extractor and TECH V2 extractor on the candidate CV and job offer. Retain evidence spans, negation and required/preferred/possessed status.
2. Normalize extracted technology IDs against the database. Resolve Nesta IDs only through a reviewed, namespaced crosswalk.
3. Retrieve occupation candidates using the title, extracted skills and actual duty statements. Source skill/task profiles supply supporting evidence.
4. Keep the existing parent resolver as the production authority until the proposed taxonomy has a reviewed crosswalk and evaluation. Resolve a leaf only within the accepted parent; allow an unresolved leaf.
5. Compare actual candidate observations with actual job requirements. Use source expectations to explain or retrieve candidates, not to manufacture missing skills.
6. Evaluate parent/leaf accuracy and ranking quality on annotated English IT offers and CVs before tuning weights or deploying this baseline.

`INTEGRATION.md` contains the architecture, schemas, uncertainty handling, example calls and evaluation protocol. The bundled `match` example uses explicitly synthetic records; it is not evidence of real candidate performance. The `rank` command is an untuned retrieval baseline, not a probability of suitability.

## Validation and remaining work

`validation_report.json` records executed integrity tests and snapshot reconstruction checks. The tests cover row preservation, foreign keys, path constraints, scope, skill identity, category precedence, evidence spans and observed-only matching. Snapshot hashes verify table contents survive rebuilding.

No annotated classification/recommendation gold set was supplied, so accuracy is **not measured**. The archive also lacks the actual Nesta extraction IDs and previous production taxonomy IDs. Empty mapping tables, CSV templates and a reviewed Nesta importer are included; integration does not invent those mappings.

The review queue contains multiple issue types per entity, including missing occupation links, unresolved functional domains and competing source parents. Prioritize high-severity identity/category/scope conflicts, then review the most frequent technologies and titles in your real offers. This database is a usable, auditable foundation with explicit gaps; it does not claim universal skill-to-task coverage.

## Source documentation

- O*NET 31.0 software skills: https://www.onetcenter.org/dictionary/31.0/csv/software_skills.html
- O*NET task-to-activity links: https://www.onetcenter.org/dictionary/31.0/csv/tasks_to_dwas.html
- O*NET attribution and license: https://www.onetcenter.org/license_db.html
- European Commission ESCO: https://esco.ec.europa.eu/en/use-esco
- ABS OSCA 2024 v1.0: https://www.abs.gov.au/statistics/classifications/osca-occupation-standard-classification-australia/2024-version-1-0
- ILO ISCO: https://ilostat.ilo.org/methods/concepts-and-definitions/classification-occupation/

The supplied source versions are frozen in the manifest. Product-level corrections cite official documentation individually in `config/technology_enrichment.json`. Original source workbooks remain in the user's uploaded archive; the package contains normalized records and evidence sufficient for snapshot reconstruction.
