from __future__ import annotations

from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent
DATA_DIR = PACKAGE_ROOT / "data"
INGESTION_DIR = PACKAGE_ROOT / "ingestion"
KNOWLEDGE_BASE_DIR = PACKAGE_ROOT / "knowledge_base"
CONFIG_DIR = PACKAGE_ROOT / "config"
WORKING_CSV = DATA_DIR / "04_job_extraction_pipeline_working_v1.csv"
SPLITS_DIR = DATA_DIR / "splits"
TAXONOMIES_DIR = DATA_DIR / "taxonomies"
TAXONOMY_JSON = TAXONOMIES_DIR / "job_family_taxonomy_v1_1.json"
ARTIFACTS_DIR = PACKAGE_ROOT / "artifacts"
REPORTS_DIR = ARTIFACTS_DIR / "reports"
MODELS_DIR = ARTIFACTS_DIR / "models"
PARENT_TFIDF_DIR = MODELS_DIR / "job_family_parent" / "tfidf_svm_v1"
PARENT_XLMR_DIR = MODELS_DIR / "job_family_parent" / "xlmr_base_v1_section_aware"
PARENT_XLMR_REPORTS = REPORTS_DIR / "job_family_parent" / "xlmr_base_v1_section_aware"
ARCHIVE_DIR = ARTIFACTS_DIR / "archive"
EXPERIMENT_REGISTRY = REPORTS_DIR / "transformer_comparison_v1" / "experiment_registry.csv"
LEAF_MODELS_DIR = MODELS_DIR / "job_family_leaf"
LEAF_DATA_DIR = DATA_DIR / "processed" / "job_family_leaf"
PHASE_G_REPORTS = REPORTS_DIR / "phase_g"
H2_XLMR_THRESHOLD = 0.65
LEAF_REGISTRY_PATH = LEAF_MODELS_DIR / "registry.json"
SENIORITY_MODELS_DIR = MODELS_DIR / "seniority"
SENIORITY_DATA_DIR = DATA_DIR / "processed" / "seniority"
PHASE_H_REPORTS = REPORTS_DIR / "phase_h"
SENIORITY_RULES_CONFIG = CONFIG_DIR / "seniority_rules_v1.json"
SENIORITY_REGISTRY_PATH = SENIORITY_MODELS_DIR / "registry.json"
NER_DATA_DIR = DATA_DIR / "ner"
SKILL_ALIASES_PATH = NER_DATA_DIR / "skill_aliases_v1.json"
SKILL_SPANS_AUTO_PATH = NER_DATA_DIR / "skill_spans_auto_v1.jsonl"
SKILL_SPANS_REVIEWED_PATH = NER_DATA_DIR / "skill_spans_reviewed_v1.jsonl"
SKILL_SPAN_AUDIT_QUEUE_PATH = NER_DATA_DIR / "skill_span_audit_queue_v1.csv"
SKILL_SPAN_UNMATCHED_PATH = NER_DATA_DIR / "skill_span_unmatched_v1.csv"
SKILL_SPAN_CONFLICTS_PATH = NER_DATA_DIR / "skill_span_conflicts_v1.csv"
SKILL_ALIAS_USAGE_PATH = NER_DATA_DIR / "skill_alias_usage_v1.csv"
SKILL_SPAN_REPORT_JSON = NER_DATA_DIR / "skill_span_dataset_report_v1.json"
PHASE_I_REPORTS = REPORTS_DIR / "phase_i"
SKILL_ALIASES_V1_1_PATH = NER_DATA_DIR / "skill_aliases_v1_1.json"
SKILL_SPANS_AUTO_V1_1_PATH = NER_DATA_DIR / "skill_spans_auto_v1_1.jsonl"
SKILL_SPAN_AUDIT_QUEUE_V1_1_PATH = NER_DATA_DIR / "skill_span_audit_queue_v1_1.csv"
SKILL_SPAN_UNMATCHED_V1_1_PATH = NER_DATA_DIR / "skill_span_unmatched_v1_1.csv"
SKILL_SPAN_CONFLICTS_V1_1_PATH = NER_DATA_DIR / "skill_span_conflicts_v1_1.csv"
SKILL_ALIAS_USAGE_V1_1_PATH = NER_DATA_DIR / "skill_alias_usage_v1_1.csv"
SKILL_SPAN_REPORT_V1_1_JSON = NER_DATA_DIR / "skill_span_dataset_report_v1_1.json"
SKILL_ALIAS_COLLISIONS_PATH = NER_DATA_DIR / "skill_alias_collisions_v1.csv"
SKILL_ALIAS_RESOLUTION_LOG_PATH = NER_DATA_DIR / "skill_alias_resolution_log_v1_1.csv"
PHASE_I1_REPORTS = REPORTS_DIR / "phase_i1"
SKILL_NER_DATA_DIR = NER_DATA_DIR / "xlmr_v1"
SKILL_NER_MODELS_DIR = MODELS_DIR / "skill_ner"
PHASE_J_REPORTS = REPORTS_DIR / "phase_j"
SKILL_NER_REGISTRY_PATH = PHASE_J_REPORTS / "experiment_registry.json"
SKILL_NER_CONFIG_DIR = CONFIG_DIR
SKILL_NER_CHAMPION_DIR = SKILL_NER_MODELS_DIR / "skill_ner_xlmr_unweighted_v1"
PHASE_K_REPORTS = REPORTS_DIR / "phase_k"

REPO_ROOT = PACKAGE_ROOT.parent


def parent_experiment_dirs(experiment_id: str) -> tuple[Path, Path]:
    return MODELS_DIR / "job_family_parent" / experiment_id, REPORTS_DIR / "job_family_parent" / experiment_id
