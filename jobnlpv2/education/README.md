# Education extraction

Run `python -m job_nlp.extraction.education [input.json] --country UK`. Input may be a JSON object, JSON array, or JSONL; each record contains `title` and `description`. Output is one JSON result per line.

The only public output is `{"required_education_levels": [...]}`. The list is deduplicated and contains only the production tiers `UNKNOWN`, `ASSOCIATE`, `BACHELOR`, and `MASTER_OR_HIGHER`. High-school mentions normalize to `UNKNOWN`; vocational/BTS/DUT credentials normalize to `ASSOCIATE`; Master, engineering/Bac+5, PhD, and doctorate credentials normalize to `MASTER_OR_HIGHER`. An empty list means no requirement was stated.

The default country is `MA` (or `EDUCATION_COUNTRY`). Pass a constructor/CLI country for jurisdiction-sensitive engineering-degree credentials. Extend `dictionaries.py` with a lower-cased alias; its level pattern is generated automatically, and add a regression test for any ambiguous credential.

For audit and service-internal consumers, `EducationResult.to_dict(detailed=True)` exposes the normalized value,
modality, alternatives, preferred level, equivalent-experience flag, confidence, exact evidence offsets, and
diagnostic flags. The default `to_dict()` output remains the original one-field compatibility shape.
