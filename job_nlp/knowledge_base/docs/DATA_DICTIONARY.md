# Data dictionary

All labels and source records are English. SQLite foreign keys and CHECK constraints are defined in `schema.sql`. Source profiles describe occupations; application observations describe actual CV/job evidence.

## metadata

46 rows.

| Column | SQLite type | Required | Primary key |
|---|---|---|---|
| `key` | TEXT | yes | yes |
| `value` | TEXT | yes |  |

## source

9 rows.

| Column | SQLite type | Required | Primary key |
|---|---|---|---|
| `source_id` | TEXT | yes | yes |
| `name` | TEXT | yes |  |
| `version` | TEXT | yes |  |
| `language` | TEXT | yes |  |
| `url` | TEXT | no |  |
| `attribution` | TEXT | no |  |

## source_file

82 rows.

| Column | SQLite type | Required | Primary key |
|---|---|---|---|
| `file_id` | TEXT | yes | yes |
| `source_id` | TEXT | no |  |
| `relative_path` | TEXT | yes |  |
| `sha256` | TEXT | yes |  |
| `byte_size` | INTEGER | yes |  |
| `processing_note` | TEXT | no |  |

Foreign-key references: `source_id` → `source.(primary key)`.

## evidence

187,144 rows.

| Column | SQLite type | Required | Primary key |
|---|---|---|---|
| `evidence_id` | TEXT | yes | yes |
| `file_id` | TEXT | no |  |
| `locator` | TEXT | yes |  |
| `record_json` | TEXT | yes |  |

Foreign-key references: `file_id` → `source_file.(primary key)`.

## family

8 rows.

| Column | SQLite type | Required | Primary key |
|---|---|---|---|
| `family_id` | TEXT | yes | yes |
| `label` | TEXT | yes |  |
| `definition` | TEXT | yes |  |
| `taxonomy_version` | TEXT | yes |  |

## parent

24 rows.

| Column | SQLite type | Required | Primary key |
|---|---|---|---|
| `parent_id` | TEXT | yes | yes |
| `family_id` | TEXT | yes |  |
| `label` | TEXT | yes |  |
| `definition` | TEXT | yes |  |

Foreign-key references: `family_id` → `family.(primary key)`.

## leaf

118 rows.

| Column | SQLite type | Required | Primary key |
|---|---|---|---|
| `leaf_id` | TEXT | yes | yes |
| `parent_id` | TEXT | yes |  |
| `label` | TEXT | yes |  |
| `definition` | TEXT | yes |  |
| `scope` | TEXT | yes |  |
| `status` | TEXT | yes |  |

Foreign-key references: `parent_id` → `parent.(primary key)`.

## legacy_taxonomy_crosswalk

0 rows.

| Column | SQLite type | Required | Primary key |
|---|---|---|---|
| `legacy_version` | TEXT | yes | yes |
| `legacy_level` | TEXT | yes | yes |
| `legacy_id` | TEXT | yes | yes |
| `new_level` | TEXT | yes | yes |
| `new_id` | TEXT | yes | yes |
| `relation` | TEXT | yes |  |
| `review_status` | TEXT | yes |  |

## occupation_group

5,407 rows.

| Column | SQLite type | Required | Primary key |
|---|---|---|---|
| `group_id` | TEXT | yes | yes |
| `source_id` | TEXT | yes |  |
| `native_id` | TEXT | yes |  |
| `label` | TEXT | yes |  |
| `level` | TEXT | yes |  |
| `description` | TEXT | no |  |
| `evidence_id` | TEXT | no |  |

Foreign-key references: `evidence_id` → `evidence.(primary key)`, `source_id` → `source.(primary key)`.

## occupation_group_edge

5,389 rows.

| Column | SQLite type | Required | Primary key |
|---|---|---|---|
| `child_id` | TEXT | yes | yes |
| `parent_id` | TEXT | yes | yes |
| `evidence_id` | TEXT | no |  |

Foreign-key references: `evidence_id` → `evidence.(primary key)`, `parent_id` → `occupation_group.(primary key)`, `child_id` → `occupation_group.(primary key)`.

## occupation

360 rows.

| Column | SQLite type | Required | Primary key |
|---|---|---|---|
| `occupation_id` | TEXT | yes | yes |
| `source_id` | TEXT | yes |  |
| `native_id` | TEXT | yes |  |
| `preferred_label` | TEXT | yes |  |
| `description` | TEXT | no |  |
| `group_id` | TEXT | no |  |
| `scope` | TEXT | yes |  |
| `scope_reason` | TEXT | yes |  |
| `evidence_id` | TEXT | no |  |

Foreign-key references: `evidence_id` → `evidence.(primary key)`, `group_id` → `occupation_group.(primary key)`, `source_id` → `source.(primary key)`.

## occupation_alias

11,493 rows.

| Column | SQLite type | Required | Primary key |
|---|---|---|---|
| `alias_id` | TEXT | yes | yes |
| `occupation_id` | TEXT | yes |  |
| `label` | TEXT | yes |  |
| `normalized_label` | TEXT | yes |  |
| `alias_type` | TEXT | yes |  |
| `evidence_id` | TEXT | no |  |

Foreign-key references: `evidence_id` → `evidence.(primary key)`, `occupation_id` → `occupation.(primary key)`.

## occupation_classification

195 rows.

| Column | SQLite type | Required | Primary key |
|---|---|---|---|
| `occupation_id` | TEXT | yes | yes |
| `family_id` | TEXT | yes |  |
| `parent_id` | TEXT | yes |  |
| `leaf_id` | TEXT | no |  |
| `mapping_relation` | TEXT | yes |  |
| `method` | TEXT | yes |  |
| `review_status` | TEXT | yes |  |
| `rule_id` | TEXT | yes |  |

Foreign-key references: `leaf_id` → `leaf.leaf_id`, `parent_id` → `leaf.parent_id`, `parent_id` → `parent.parent_id`, `family_id` → `parent.family_id`, `family_id` → `family.(primary key)`, `occupation_id` → `occupation.(primary key)`.

## input_title

1,793 rows.

| Column | SQLite type | Required | Primary key |
|---|---|---|---|
| `title_id` | TEXT | yes | yes |
| `original_row_number` | INTEGER | yes |  |
| `title` | TEXT | yes |  |
| `normalized_title` | TEXT | yes |  |
| `provided_it_label` | TEXT | yes |  |
| `provided_review_status` | TEXT | yes |  |
| `scope` | TEXT | yes |  |
| `resolution_status` | TEXT | yes |  |
| `evidence_id` | TEXT | yes |  |

Foreign-key references: `evidence_id` → `evidence.(primary key)`.

## title_source_match

1,844 rows.

| Column | SQLite type | Required | Primary key |
|---|---|---|---|
| `title_id` | TEXT | yes | yes |
| `alias_id` | TEXT | yes | yes |
| `match_method` | TEXT | yes |  |
| `interpretation` | TEXT | yes |  |

Foreign-key references: `alias_id` → `occupation_alias.(primary key)`, `title_id` → `input_title.(primary key)`.

## title_classification

1,751 rows.

| Column | SQLite type | Required | Primary key |
|---|---|---|---|
| `title_id` | TEXT | yes | yes |
| `family_id` | TEXT | yes |  |
| `parent_id` | TEXT | yes | yes |
| `leaf_id` | TEXT | no |  |
| `method` | TEXT | yes |  |
| `rule_id` | TEXT | yes |  |
| `review_status` | TEXT | yes |  |

Foreign-key references: `leaf_id` → `leaf.leaf_id`, `parent_id` → `leaf.parent_id`, `parent_id` → `parent.parent_id`, `family_id` → `parent.family_id`, `family_id` → `family.(primary key)`, `title_id` → `input_title.(primary key)`.

## source_crosswalk

1,448 rows.

| Column | SQLite type | Required | Primary key |
|---|---|---|---|
| `from_group_id` | TEXT | yes | yes |
| `to_group_id` | TEXT | yes | yes |
| `relationship_note` | TEXT | yes |  |
| `evidence_id` | TEXT | yes |  |

Foreign-key references: `evidence_id` → `evidence.(primary key)`, `to_group_id` → `occupation_group.(primary key)`, `from_group_id` → `occupation_group.(primary key)`.

## skill

12,923 rows.

| Column | SQLite type | Required | Primary key |
|---|---|---|---|
| `skill_id` | TEXT | yes | yes |
| `source_id` | TEXT | yes |  |
| `native_id` | TEXT | yes |  |
| `preferred_label` | TEXT | yes |  |
| `normalized_label` | TEXT | yes |  |
| `kind` | TEXT | yes |  |
| `description` | TEXT | no |  |
| `matching_policy` | TEXT | yes |  |
| `provided_category` | TEXT | no |  |
| `evidence_id` | TEXT | no |  |

Foreign-key references: `evidence_id` → `evidence.(primary key)`, `source_id` → `source.(primary key)`.

## skill_alias

24,772 rows.

| Column | SQLite type | Required | Primary key |
|---|---|---|---|
| `alias_id` | TEXT | yes | yes |
| `skill_id` | TEXT | yes |  |
| `label` | TEXT | yes |  |
| `normalized_label` | TEXT | yes |  |
| `alias_type` | TEXT | yes |  |
| `evidence_id` | TEXT | no |  |

Foreign-key references: `evidence_id` → `evidence.(primary key)`, `skill_id` → `skill.(primary key)`.

## skill_crosswalk

3,479 rows.

| Column | SQLite type | Required | Primary key |
|---|---|---|---|
| `from_skill_id` | TEXT | yes | yes |
| `to_skill_id` | TEXT | yes | yes |
| `relation` | TEXT | yes |  |
| `method` | TEXT | yes |  |
| `review_status` | TEXT | yes |  |
| `matched_label` | TEXT | no |  |
| `evidence_id` | TEXT | no |  |

Foreign-key references: `evidence_id` → `evidence.(primary key)`, `to_skill_id` → `skill.(primary key)`, `from_skill_id` → `skill.(primary key)`.

## external_skill_crosswalk

0 rows.

| Column | SQLite type | Required | Primary key |
|---|---|---|---|
| `namespace` | TEXT | yes | yes |
| `external_id` | TEXT | yes | yes |
| `external_label` | TEXT | no |  |
| `skill_id` | TEXT | yes | yes |
| `relation` | TEXT | yes |  |
| `review_status` | TEXT | yes |  |

Foreign-key references: `skill_id` → `skill.(primary key)`.

## technology_curation

21 rows.

| Column | SQLite type | Required | Primary key |
|---|---|---|---|
| `skill_id` | TEXT | yes | yes |
| `recommended_category` | TEXT | yes |  |
| `capability` | TEXT | yes |  |
| `reason` | TEXT | yes |  |
| `source_url` | TEXT | yes |  |
| `status` | TEXT | yes |  |
| `evidence_id` | TEXT | yes |  |

Foreign-key references: `evidence_id` → `evidence.(primary key)`, `skill_id` → `skill.(primary key)`.

## domain

1,297 rows.

| Column | SQLite type | Required | Primary key |
|---|---|---|---|
| `domain_id` | TEXT | yes | yes |
| `source_id` | TEXT | yes |  |
| `label` | TEXT | yes |  |
| `domain_type` | TEXT | yes |  |
| `description` | TEXT | no |  |
| `evidence_id` | TEXT | no |  |

Foreign-key references: `evidence_id` → `evidence.(primary key)`, `source_id` → `source.(primary key)`.

## domain_edge

1,444 rows.

| Column | SQLite type | Required | Primary key |
|---|---|---|---|
| `child_id` | TEXT | yes | yes |
| `parent_id` | TEXT | yes | yes |
| `evidence_id` | TEXT | no |  |

Foreign-key references: `evidence_id` → `evidence.(primary key)`, `parent_id` → `domain.(primary key)`, `child_id` → `domain.(primary key)`.

## skill_domain

25,459 rows.

| Column | SQLite type | Required | Primary key |
|---|---|---|---|
| `skill_id` | TEXT | yes | yes |
| `domain_id` | TEXT | yes | yes |
| `relation` | TEXT | yes | yes |
| `method` | TEXT | yes |  |
| `review_status` | TEXT | yes |  |
| `evidence_id` | TEXT | no |  |

Foreign-key references: `evidence_id` → `evidence.(primary key)`, `domain_id` → `domain.(primary key)`, `skill_id` → `skill.(primary key)`.

## skill_relation

799 rows.

| Column | SQLite type | Required | Primary key |
|---|---|---|---|
| `from_skill_id` | TEXT | yes | yes |
| `to_skill_id` | TEXT | yes | yes |
| `relation` | TEXT | yes | yes |
| `evidence_id` | TEXT | yes |  |

Foreign-key references: `evidence_id` → `evidence.(primary key)`, `to_skill_id` → `skill.(primary key)`, `from_skill_id` → `skill.(primary key)`.

## occupation_skill

16,262 rows.

| Column | SQLite type | Required | Primary key |
|---|---|---|---|
| `occupation_id` | TEXT | yes | yes |
| `skill_id` | TEXT | yes | yes |
| `relation` | TEXT | yes | yes |
| `hot_technology` | INTEGER | no |  |
| `in_demand` | INTEGER | no |  |
| `evidence_id` | TEXT | yes |  |

Foreign-key references: `evidence_id` → `evidence.(primary key)`, `skill_id` → `skill.(primary key)`, `occupation_id` → `occupation.(primary key)`.

## descriptor

3,006 rows.

| Column | SQLite type | Required | Primary key |
|---|---|---|---|
| `descriptor_id` | TEXT | yes | yes |
| `source_id` | TEXT | yes |  |
| `native_id` | TEXT | yes |  |
| `label` | TEXT | yes |  |
| `description` | TEXT | no |  |
| `skill_id` | TEXT | no |  |
| `evidence_id` | TEXT | yes |  |

Foreign-key references: `evidence_id` → `evidence.(primary key)`, `skill_id` → `skill.(primary key)`, `source_id` → `source.(primary key)`.

## rating_scale

33 rows.

| Column | SQLite type | Required | Primary key |
|---|---|---|---|
| `scale_id` | TEXT | yes | yes |
| `label` | TEXT | yes |  |
| `minimum` | REAL | yes |  |
| `maximum` | REAL | yes |  |
| `evidence_id` | TEXT | yes |  |

Foreign-key references: `evidence_id` → `evidence.(primary key)`.

## rating_category

341 rows.

| Column | SQLite type | Required | Primary key |
|---|---|---|---|
| `category_id` | TEXT | yes | yes |
| `category_domain` | TEXT | yes |  |
| `element_id` | TEXT | no |  |
| `scale_id` | TEXT | yes |  |
| `category` | TEXT | yes |  |
| `description` | TEXT | yes |  |
| `evidence_id` | TEXT | yes |  |

Foreign-key references: `evidence_id` → `evidence.(primary key)`, `scale_id` → `rating_scale.(primary key)`.

## scale_anchor

483 rows.

| Column | SQLite type | Required | Primary key |
|---|---|---|---|
| `anchor_id` | TEXT | yes | yes |
| `descriptor_id` | TEXT | yes |  |
| `scale_id` | TEXT | yes |  |
| `value` | REAL | yes |  |
| `description` | TEXT | yes |  |
| `evidence_id` | TEXT | yes |  |

Foreign-key references: `evidence_id` → `evidence.(primary key)`, `scale_id` → `rating_scale.(primary key)`, `descriptor_id` → `descriptor.(primary key)`.

## occupation_rating

28,294 rows.

| Column | SQLite type | Required | Primary key |
|---|---|---|---|
| `rating_id` | TEXT | yes | yes |
| `occupation_id` | TEXT | yes |  |
| `descriptor_id` | TEXT | yes |  |
| `dataset` | TEXT | yes |  |
| `scale_id` | TEXT | yes |  |
| `category` | TEXT | no |  |
| `value` | REAL | yes |  |
| `sample_n` | REAL | no |  |
| `standard_error` | REAL | no |  |
| `ci_low` | REAL | no |  |
| `ci_high` | REAL | no |  |
| `recommend_suppress` | TEXT | no |  |
| `not_relevant` | TEXT | no |  |
| `date` | TEXT | no |  |
| `domain_source` | TEXT | no |  |
| `evidence_id` | TEXT | yes |  |

Foreign-key references: `evidence_id` → `evidence.(primary key)`, `scale_id` → `rating_scale.(primary key)`, `descriptor_id` → `descriptor.(primary key)`, `occupation_id` → `occupation.(primary key)`.

## occupation_metadata

4,486 rows.

| Column | SQLite type | Required | Primary key |
|---|---|---|---|
| `metadata_id` | TEXT | yes | yes |
| `occupation_id` | TEXT | yes |  |
| `dataset` | TEXT | yes |  |
| `record_json` | TEXT | yes |  |
| `evidence_id` | TEXT | yes |  |

Foreign-key references: `evidence_id` → `evidence.(primary key)`, `occupation_id` → `occupation.(primary key)`.

## job_zone

4 rows.

| Column | SQLite type | Required | Primary key |
|---|---|---|---|
| `job_zone` | INTEGER | yes | yes |
| `label` | TEXT | yes |  |
| `experience` | TEXT | no |  |
| `education` | TEXT | no |  |
| `job_training` | TEXT | no |  |
| `examples` | TEXT | no |  |
| `svp_range` | TEXT | no |  |
| `evidence_id` | TEXT | yes |  |

Foreign-key references: `evidence_id` → `evidence.(primary key)`.

## occupation_job_zone

38 rows.

| Column | SQLite type | Required | Primary key |
|---|---|---|---|
| `occupation_id` | TEXT | yes | yes |
| `job_zone` | INTEGER | yes |  |
| `date` | TEXT | no |  |
| `domain_source` | TEXT | no |  |
| `evidence_id` | TEXT | yes |  |

Foreign-key references: `evidence_id` → `evidence.(primary key)`, `job_zone` → `job_zone.(primary key)`, `occupation_id` → `occupation.(primary key)`.

## related_occupation

483 rows.

| Column | SQLite type | Required | Primary key |
|---|---|---|---|
| `occupation_id` | TEXT | yes | yes |
| `related_occupation_id` | TEXT | yes | yes |
| `tier` | TEXT | yes |  |
| `rank` | INTEGER | yes |  |
| `evidence_id` | TEXT | yes |  |

Foreign-key references: `evidence_id` → `evidence.(primary key)`, `related_occupation_id` → `occupation.(primary key)`, `occupation_id` → `occupation.(primary key)`.

## task

1,101 rows.

| Column | SQLite type | Required | Primary key |
|---|---|---|---|
| `task_id` | TEXT | yes | yes |
| `source_id` | TEXT | yes |  |
| `native_id` | TEXT | yes |  |
| `description` | TEXT | yes |  |
| `evidence_id` | TEXT | yes |  |

Foreign-key references: `evidence_id` → `evidence.(primary key)`, `source_id` → `source.(primary key)`.

## occupation_task

1,101 rows.

| Column | SQLite type | Required | Primary key |
|---|---|---|---|
| `occupation_id` | TEXT | yes | yes |
| `task_id` | TEXT | yes | yes |
| `task_type` | TEXT | no |  |
| `date` | TEXT | no |  |
| `domain_source` | TEXT | no |  |
| `evidence_id` | TEXT | yes |  |

Foreign-key references: `evidence_id` → `evidence.(primary key)`, `task_id` → `task.(primary key)`, `occupation_id` → `occupation.(primary key)`.

## task_rating

7,380 rows.

| Column | SQLite type | Required | Primary key |
|---|---|---|---|
| `rating_id` | TEXT | yes | yes |
| `occupation_id` | TEXT | yes |  |
| `task_id` | TEXT | yes |  |
| `scale_id` | TEXT | yes |  |
| `category` | TEXT | no |  |
| `value` | REAL | yes |  |
| `sample_n` | REAL | no |  |
| `recommend_suppress` | TEXT | no |  |
| `evidence_id` | TEXT | yes |  |

Foreign-key references: `occupation_id` → `occupation_task.occupation_id`, `task_id` → `occupation_task.task_id`, `evidence_id` → `evidence.(primary key)`, `scale_id` → `rating_scale.(primary key)`.

## activity

2,460 rows.

| Column | SQLite type | Required | Primary key |
|---|---|---|---|
| `activity_id` | TEXT | yes | yes |
| `source_id` | TEXT | yes |  |
| `native_id` | TEXT | yes |  |
| `label` | TEXT | yes |  |
| `level` | TEXT | yes |  |
| `evidence_id` | TEXT | yes |  |

Foreign-key references: `evidence_id` → `evidence.(primary key)`, `source_id` → `source.(primary key)`.

## activity_edge

2,419 rows.

| Column | SQLite type | Required | Primary key |
|---|---|---|---|
| `child_id` | TEXT | yes | yes |
| `parent_id` | TEXT | yes | yes |
| `evidence_id` | TEXT | yes |  |

Foreign-key references: `evidence_id` → `evidence.(primary key)`, `parent_id` → `activity.(primary key)`, `child_id` → `activity.(primary key)`.

## task_activity

1,071 rows.

| Column | SQLite type | Required | Primary key |
|---|---|---|---|
| `occupation_id` | TEXT | yes | yes |
| `task_id` | TEXT | yes | yes |
| `activity_id` | TEXT | yes | yes |
| `evidence_id` | TEXT | yes |  |

Foreign-key references: `occupation_id` → `occupation_task.occupation_id`, `task_id` → `occupation_task.task_id`, `evidence_id` → `evidence.(primary key)`, `activity_id` → `activity.(primary key)`.

## descriptor_activity

916 rows.

| Column | SQLite type | Required | Primary key |
|---|---|---|---|
| `descriptor_id` | TEXT | yes | yes |
| `activity_id` | TEXT | yes | yes |
| `relation` | TEXT | yes |  |
| `evidence_id` | TEXT | yes |  |

Foreign-key references: `evidence_id` → `evidence.(primary key)`, `activity_id` → `activity.(primary key)`, `descriptor_id` → `descriptor.(primary key)`.

## descriptor_relation

501 rows.

| Column | SQLite type | Required | Primary key |
|---|---|---|---|
| `from_descriptor_id` | TEXT | yes | yes |
| `to_descriptor_id` | TEXT | yes | yes |
| `relation` | TEXT | yes | yes |
| `evidence_id` | TEXT | yes |  |

Foreign-key references: `evidence_id` → `evidence.(primary key)`, `to_descriptor_id` → `descriptor.(primary key)`, `from_descriptor_id` → `descriptor.(primary key)`.

## skill_task_evidence

2 rows.

| Column | SQLite type | Required | Primary key |
|---|---|---|---|
| `skill_id` | TEXT | yes | yes |
| `task_id` | TEXT | yes | yes |
| `relation` | TEXT | yes |  |
| `method` | TEXT | yes |  |
| `matched_text` | TEXT | yes |  |
| `start_char` | INTEGER | yes | yes |
| `end_char` | INTEGER | yes |  |
| `review_status` | TEXT | yes |  |
| `evidence_id` | TEXT | yes |  |

Foreign-key references: `evidence_id` → `evidence.(primary key)`, `task_id` → `task.(primary key)`, `skill_id` → `skill.(primary key)`.

## task_domain

1,027 rows.

| Column | SQLite type | Required | Primary key |
|---|---|---|---|
| `task_id` | TEXT | yes | yes |
| `domain_id` | TEXT | yes | yes |
| `rule_id` | TEXT | yes |  |
| `method` | TEXT | yes |  |
| `evidence_id` | TEXT | yes |  |

Foreign-key references: `evidence_id` → `evidence.(primary key)`, `domain_id` → `domain.(primary key)`, `task_id` → `task.(primary key)`.

## domain_parent_candidate

44 rows.

| Column | SQLite type | Required | Primary key |
|---|---|---|---|
| `domain_id` | TEXT | yes | yes |
| `parent_id` | TEXT | yes | yes |
| `relation` | TEXT | yes |  |
| `review_status` | TEXT | yes |  |
| `rule_id` | TEXT | yes |  |

Foreign-key references: `parent_id` → `parent.(primary key)`, `domain_id` → `domain.(primary key)`.

## review_issue

7,544 rows.

| Column | SQLite type | Required | Primary key |
|---|---|---|---|
| `issue_id` | TEXT | yes | yes |
| `entity_type` | TEXT | yes |  |
| `entity_id` | TEXT | yes |  |
| `issue_type` | TEXT | yes |  |
| `severity` | TEXT | yes |  |
| `detail` | TEXT | yes |  |
| `status` | TEXT | yes |  |

## role_track

5 rows.

| Column | SQLite type | Required | Primary key |
|---|---|---|---|
| `track_id` | TEXT | yes | yes |
| `label` | TEXT | yes |  |
| `definition` | TEXT | yes |  |
| `status` | TEXT | yes |  |
| `taxonomy_version` | TEXT | yes |  |

## family_role_track

0 rows.

| Column | SQLite type | Required | Primary key |
|---|---|---|---|
| `family_id` | TEXT | yes | yes |
| `track_id` | TEXT | yes | yes |
| `relation` | TEXT | yes |  |
| `rationale` | TEXT | yes |  |
| `taxonomy_version` | TEXT | yes |  |

Foreign-key references: `track_id` → `role_track.(primary key)`, `family_id` → `family.(primary key)`.

## leaf_profile

118 rows.

| Column | SQLite type | Required | Primary key |
|---|---|---|---|
| `leaf_id` | TEXT | yes | yes |
| `taxonomy_version` | TEXT | yes |  |
| `definition` | TEXT | yes |  |
| `primary_outcome` | TEXT | yes |  |
| `in_scope_json` | TEXT | yes |  |
| `out_of_scope_json` | TEXT | yes |  |
| `profile_status` | TEXT | yes |  |
| `evidence_level` | TEXT | yes |  |
| `readiness_reason` | TEXT | yes |  |
| `reviewer` | TEXT | yes |  |
| `reviewed_at` | TEXT | yes |  |

Foreign-key references: `leaf_id` → `leaf.(primary key)`.

## leaf_source_occupation

159 rows.

| Column | SQLite type | Required | Primary key |
|---|---|---|---|
| `leaf_id` | TEXT | yes | yes |
| `occupation_id` | TEXT | yes | yes |
| `source_id` | TEXT | yes |  |
| `native_id` | TEXT | yes |  |
| `preferred_label` | TEXT | yes |  |
| `mapping_relation` | TEXT | yes |  |
| `mapping_method` | TEXT | yes |  |
| `review_status` | TEXT | yes |  |
| `evidence_id` | TEXT | no |  |

Foreign-key references: `evidence_id` → `evidence.(primary key)`, `source_id` → `source.(primary key)`, `occupation_id` → `occupation.(primary key)`, `leaf_id` → `leaf.(primary key)`.

## leaf_alias

2,137 rows.

| Column | SQLite type | Required | Primary key |
|---|---|---|---|
| `leaf_id` | TEXT | yes | yes |
| `alias_id` | TEXT | yes | yes |
| `source_id` | TEXT | yes |  |
| `alias` | TEXT | yes |  |
| `alias_type` | TEXT | yes |  |
| `evidence_id` | TEXT | no |  |
| `provenance` | TEXT | yes |  |

Foreign-key references: `evidence_id` → `evidence.(primary key)`, `source_id` → `source.(primary key)`, `alias_id` → `occupation_alias.(primary key)`, `leaf_id` → `leaf.(primary key)`.

## leaf_task_evidence

722 rows.

| Column | SQLite type | Required | Primary key |
|---|---|---|---|
| `leaf_id` | TEXT | yes | yes |
| `occupation_id` | TEXT | yes | yes |
| `task_id` | TEXT | yes | yes |
| `source_id` | TEXT | yes |  |
| `task_type` | TEXT | no |  |
| `description` | TEXT | yes |  |
| `verb` | TEXT | yes |  |
| `object_text` | TEXT | yes |  |
| `context_text` | TEXT | yes |  |
| `evidence_tier` | TEXT | yes |  |
| `evidence_id` | TEXT | yes |  |

Foreign-key references: `evidence_id` → `evidence.(primary key)`, `source_id` → `source.(primary key)`, `task_id` → `task.(primary key)`, `occupation_id` → `occupation.(primary key)`, `leaf_id` → `leaf.(primary key)`.

## leaf_skill_profile

10,854 rows.

| Column | SQLite type | Required | Primary key |
|---|---|---|---|
| `leaf_id` | TEXT | yes | yes |
| `occupation_id` | TEXT | yes | yes |
| `skill_id` | TEXT | yes | yes |
| `source_id` | TEXT | yes |  |
| `normalized_label` | TEXT | yes |  |
| `kind` | TEXT | yes |  |
| `relation` | TEXT | yes | yes |
| `hot_technology` | INTEGER | no |  |
| `in_demand` | INTEGER | no |  |
| `evidence_tier` | TEXT | yes |  |
| `evidence_id` | TEXT | yes |  |

Foreign-key references: `evidence_id` → `evidence.(primary key)`, `source_id` → `source.(primary key)`, `skill_id` → `skill.(primary key)`, `occupation_id` → `occupation.(primary key)`, `leaf_id` → `leaf.(primary key)`.

## leaf_technology_profile

3,450 rows.

| Column | SQLite type | Required | Primary key |
|---|---|---|---|
| `leaf_id` | TEXT | yes | yes |
| `occupation_id` | TEXT | yes | yes |
| `skill_id` | TEXT | yes | yes |
| `source_id` | TEXT | yes |  |
| `technology_label` | TEXT | yes |  |
| `relation` | TEXT | yes | yes |
| `role_context` | TEXT | yes |  |
| `evidence_id` | TEXT | yes |  |

Foreign-key references: `evidence_id` → `evidence.(primary key)`, `source_id` → `source.(primary key)`, `skill_id` → `skill.(primary key)`, `occupation_id` → `occupation.(primary key)`, `leaf_id` → `leaf.(primary key)`.

## leaf_confusion_pair

4 rows.

| Column | SQLite type | Required | Primary key |
|---|---|---|---|
| `pair_id` | TEXT | yes | yes |
| `leaf_id` | TEXT | yes |  |
| `sibling_leaf_id` | TEXT | yes |  |
| `disambiguator` | TEXT | yes |  |
| `hard_negative_rule` | TEXT | yes |  |
| `taxonomy_version` | TEXT | yes |  |
| `reviewer` | TEXT | yes |  |
| `review_status` | TEXT | yes |  |

Foreign-key references: `sibling_leaf_id` → `leaf.(primary key)`, `leaf_id` → `leaf.(primary key)`.

## leaf_title_evidence

1,805 rows.

| Column | SQLite type | Required | Primary key |
|---|---|---|---|
| `title_id` | TEXT | yes | yes |
| `leaf_id` | TEXT | yes | yes |
| `title` | TEXT | yes |  |
| `method` | TEXT | yes |  |
| `review_status` | TEXT | yes |  |
| `evidence_strength` | TEXT | yes |  |
| `evidence_quote` | TEXT | yes |  |
| `taxonomy_version` | TEXT | yes |  |

Foreign-key references: `leaf_id` → `leaf.(primary key)`, `title_id` → `input_title.(primary key)`.

## leaf_custom_profile

35 rows.

| Column | SQLite type | Required | Primary key |
|---|---|---|---|
| `profile_id` | TEXT | yes | yes |
| `leaf_id` | TEXT | yes |  |
| `source_id` | TEXT | yes |  |
| `evidence_id` | TEXT | yes |  |
| `batch_id` | TEXT | yes |  |
| `description` | TEXT | yes |  |
| `primary_outcome` | TEXT | yes |  |
| `in_scope_json` | TEXT | yes |  |
| `out_of_scope_json` | TEXT | yes |  |
| `tasks_json` | TEXT | yes |  |
| `professional_skills_json` | TEXT | yes |  |
| `technologies_json` | TEXT | yes |  |
| `sibling_disambiguators_json` | TEXT | yes |  |
| `review_status` | TEXT | yes |  |
| `vector_status` | TEXT | yes |  |
| `reviewer` | TEXT | yes |  |
| `created_at` | TEXT | yes |  |

Foreign-key references: `evidence_id` → `evidence.(primary key)`, `source_id` → `source.(primary key)`, `leaf_id` → `leaf.(primary key)`.

## taxonomy_v2_crosswalk

221 rows.

| Column | SQLite type | Required | Primary key |
|---|---|---|---|
| `old_level` | TEXT | yes | yes |
| `old_id` | TEXT | yes | yes |
| `new_level` | TEXT | yes | yes |
| `new_id` | TEXT | yes | yes |
| `relation` | TEXT | yes |  |
| `rationale` | TEXT | yes |  |
| `taxonomy_version` | TEXT | yes |  |

## taxonomy_v2_excluded_node

2 rows.

| Column | SQLite type | Required | Primary key |
|---|---|---|---|
| `old_family_id` | TEXT | yes | yes |
| `old_family_label` | TEXT | yes |  |
| `old_parent_id` | TEXT | yes | yes |
| `old_parent_label` | TEXT | yes |  |
| `old_leaf_id` | TEXT | yes | yes |
| `old_leaf_label` | TEXT | yes |  |
| `old_scope` | TEXT | yes |  |
| `old_status` | TEXT | yes |  |
| `exclusion_reason` | TEXT | yes |  |
| `archived_at` | TEXT | yes |  |
| `taxonomy_version` | TEXT | yes |  |

## taxonomy_v2_excluded_title

42 rows.

| Column | SQLite type | Required | Primary key |
|---|---|---|---|
| `title_id` | TEXT | yes | yes |
| `title` | TEXT | yes |  |
| `old_family_id` | TEXT | yes |  |
| `old_parent_id` | TEXT | yes |  |
| `old_leaf_id` | TEXT | yes | yes |
| `method` | TEXT | yes |  |
| `rule_id` | TEXT | yes |  |
| `review_status` | TEXT | yes |  |
| `exclusion_reason` | TEXT | yes |  |
| `archived_at` | TEXT | yes |  |
| `taxonomy_version` | TEXT | yes |  |

## document

0 rows.

| Column | SQLite type | Required | Primary key |
|---|---|---|---|
| `document_id` | TEXT | yes | yes |
| `document_type` | TEXT | yes |  |
| `language` | TEXT | yes |  |
| `title` | TEXT | no |  |
| `text` | TEXT | yes |  |
| `external_reference` | TEXT | no |  |

## document_skill

0 rows.

| Column | SQLite type | Required | Primary key |
|---|---|---|---|
| `observation_id` | TEXT | yes | yes |
| `document_id` | TEXT | yes |  |
| `skill_id` | TEXT | no |  |
| `external_namespace` | TEXT | no |  |
| `external_skill_id` | TEXT | no |  |
| `surface` | TEXT | yes |  |
| `section` | TEXT | no |  |
| `start_char` | INTEGER | yes |  |
| `end_char` | INTEGER | yes |  |
| `evidence_quote` | TEXT | yes |  |
| `assertion` | TEXT | yes |  |
| `proficiency` | TEXT | no |  |
| `experience_months` | REAL | no |  |
| `extractor` | TEXT | yes |  |
| `extractor_version` | TEXT | no |  |
| `confidence` | REAL | no |  |

Foreign-key references: `skill_id` → `skill.(primary key)`, `document_id` → `document.(primary key)`.

## document_role

0 rows.

| Column | SQLite type | Required | Primary key |
|---|---|---|---|
| `hypothesis_id` | TEXT | yes | yes |
| `document_id` | TEXT | yes |  |
| `taxonomy_version` | TEXT | yes |  |
| `family_id` | TEXT | no |  |
| `parent_id` | TEXT | no |  |
| `leaf_id` | TEXT | no |  |
| `status` | TEXT | yes |  |
| `evidence_quote` | TEXT | no |  |
| `resolver` | TEXT | yes |  |
| `confidence` | REAL | no |  |

Foreign-key references: `leaf_id` → `leaf.leaf_id`, `parent_id` → `leaf.parent_id`, `parent_id` → `parent.parent_id`, `family_id` → `parent.family_id`, `family_id` → `family.(primary key)`, `document_id` → `document.(primary key)`.

## document_fact

0 rows.

| Column | SQLite type | Required | Primary key |
|---|---|---|---|
| `fact_id` | TEXT | yes | yes |
| `document_id` | TEXT | yes |  |
| `fact_type` | TEXT | yes |  |
| `value_json` | TEXT | yes |  |
| `qualifier` | TEXT | yes |  |
| `evidence_quote` | TEXT | yes |  |
| `extractor` | TEXT | yes |  |

Foreign-key references: `document_id` → `document.(primary key)`.

## Query views

- `v_effective_skill_domains`
- `v_esco_occupation_detail`
- `v_it_occupation_skills`
- `v_it_occupations`
- `v_leaf_evidence_summary`
- `v_leaf_skill_profile`
- `v_leaf_task_profile`
- `v_osca_occupation_detail`
- `v_professional_skill_task_paths`
- `v_review_queue`
- `v_skill_parent_candidates`
- `v_skill_resolution`
- `v_skill_role_context`
- `v_taxonomy`
- `v_technology_coverage`
- `v_title_paths`
- `v_usable_occupation_ratings`