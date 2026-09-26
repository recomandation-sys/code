PRAGMA foreign_keys = ON;
CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE source (source_id TEXT PRIMARY KEY, name TEXT NOT NULL, version TEXT NOT NULL, language TEXT NOT NULL DEFAULT 'en', url TEXT, attribution TEXT);
CREATE TABLE source_file (file_id TEXT PRIMARY KEY, source_id TEXT REFERENCES source, relative_path TEXT NOT NULL UNIQUE, sha256 TEXT NOT NULL, byte_size INTEGER NOT NULL, processing_note TEXT);
CREATE TABLE evidence (evidence_id TEXT PRIMARY KEY, file_id TEXT REFERENCES source_file, locator TEXT NOT NULL, record_json TEXT NOT NULL CHECK(json_valid(record_json)));

CREATE TABLE family (family_id TEXT PRIMARY KEY, label TEXT NOT NULL UNIQUE, definition TEXT NOT NULL, taxonomy_version TEXT NOT NULL);
CREATE TABLE parent (parent_id TEXT PRIMARY KEY, family_id TEXT NOT NULL REFERENCES family, label TEXT NOT NULL, definition TEXT NOT NULL, UNIQUE(parent_id,family_id));
CREATE TABLE leaf (leaf_id TEXT PRIMARY KEY, parent_id TEXT NOT NULL REFERENCES parent, label TEXT NOT NULL UNIQUE, definition TEXT NOT NULL, scope TEXT NOT NULL CHECK(scope IN ('core','conditional')), status TEXT NOT NULL DEFAULT 'proposed', UNIQUE(leaf_id,parent_id));
CREATE TABLE legacy_taxonomy_crosswalk (legacy_version TEXT NOT NULL, legacy_level TEXT NOT NULL CHECK(legacy_level IN ('family','parent','leaf')), legacy_id TEXT NOT NULL, new_level TEXT NOT NULL CHECK(new_level IN ('family','parent','leaf')), new_id TEXT NOT NULL, relation TEXT NOT NULL, review_status TEXT NOT NULL, PRIMARY KEY(legacy_version,legacy_level,legacy_id,new_level,new_id));

CREATE TABLE occupation_group (group_id TEXT PRIMARY KEY, source_id TEXT NOT NULL REFERENCES source, native_id TEXT NOT NULL, label TEXT NOT NULL, level TEXT NOT NULL, description TEXT, evidence_id TEXT REFERENCES evidence);
CREATE TABLE occupation_group_edge (child_id TEXT NOT NULL REFERENCES occupation_group, parent_id TEXT NOT NULL REFERENCES occupation_group, evidence_id TEXT REFERENCES evidence, PRIMARY KEY(child_id,parent_id), CHECK(child_id<>parent_id));
CREATE TABLE occupation (occupation_id TEXT PRIMARY KEY, source_id TEXT NOT NULL REFERENCES source, native_id TEXT NOT NULL, preferred_label TEXT NOT NULL, description TEXT, group_id TEXT REFERENCES occupation_group, scope TEXT NOT NULL CHECK(scope IN ('core','conditional','reference_only')), scope_reason TEXT NOT NULL, evidence_id TEXT REFERENCES evidence, UNIQUE(source_id,native_id));
CREATE TABLE occupation_alias (alias_id TEXT PRIMARY KEY, occupation_id TEXT NOT NULL REFERENCES occupation, label TEXT NOT NULL, normalized_label TEXT NOT NULL, alias_type TEXT NOT NULL, evidence_id TEXT REFERENCES evidence, UNIQUE(occupation_id,label,alias_type));
CREATE INDEX occupation_alias_norm ON occupation_alias(normalized_label);
CREATE TABLE occupation_classification (occupation_id TEXT PRIMARY KEY REFERENCES occupation, family_id TEXT NOT NULL REFERENCES family, parent_id TEXT NOT NULL, leaf_id TEXT, mapping_relation TEXT NOT NULL CHECK(mapping_relation IN ('equivalent_proposal','source_broader','source_narrower','related_proposal','parent_only')), method TEXT NOT NULL, review_status TEXT NOT NULL, rule_id TEXT NOT NULL, FOREIGN KEY(parent_id,family_id) REFERENCES parent(parent_id,family_id), FOREIGN KEY(leaf_id,parent_id) REFERENCES leaf(leaf_id,parent_id));
CREATE TABLE input_title (title_id TEXT PRIMARY KEY, original_row_number INTEGER NOT NULL UNIQUE, title TEXT NOT NULL, normalized_title TEXT NOT NULL, provided_it_label TEXT NOT NULL, provided_review_status TEXT NOT NULL, scope TEXT NOT NULL CHECK(scope IN ('core','conditional','review','excluded')), resolution_status TEXT NOT NULL, evidence_id TEXT NOT NULL REFERENCES evidence);
CREATE TABLE title_source_match (title_id TEXT NOT NULL REFERENCES input_title, alias_id TEXT NOT NULL REFERENCES occupation_alias, match_method TEXT NOT NULL, interpretation TEXT NOT NULL DEFAULT 'lexical_correspondence_not_original_provenance', PRIMARY KEY(title_id,alias_id));
CREATE TABLE title_classification (title_id TEXT NOT NULL REFERENCES input_title, family_id TEXT NOT NULL REFERENCES family, parent_id TEXT NOT NULL, leaf_id TEXT, method TEXT NOT NULL, rule_id TEXT NOT NULL, review_status TEXT NOT NULL, PRIMARY KEY(title_id,parent_id), FOREIGN KEY(parent_id,family_id) REFERENCES parent(parent_id,family_id), FOREIGN KEY(leaf_id,parent_id) REFERENCES leaf(leaf_id,parent_id));
CREATE TABLE source_crosswalk (from_group_id TEXT NOT NULL REFERENCES occupation_group, to_group_id TEXT NOT NULL REFERENCES occupation_group, relationship_note TEXT NOT NULL, evidence_id TEXT NOT NULL REFERENCES evidence, PRIMARY KEY(from_group_id,to_group_id));

CREATE TABLE skill (skill_id TEXT PRIMARY KEY, source_id TEXT NOT NULL REFERENCES source, native_id TEXT NOT NULL, preferred_label TEXT NOT NULL, normalized_label TEXT NOT NULL, kind TEXT NOT NULL CHECK(kind IN ('technology','software_example','professional_skill','knowledge')), description TEXT, matching_policy TEXT NOT NULL DEFAULT 'SOURCE_ONLY', provided_category TEXT, evidence_id TEXT REFERENCES evidence, UNIQUE(source_id,native_id));
CREATE TABLE skill_alias (alias_id TEXT PRIMARY KEY, skill_id TEXT NOT NULL REFERENCES skill, label TEXT NOT NULL, normalized_label TEXT NOT NULL, alias_type TEXT NOT NULL, evidence_id TEXT REFERENCES evidence, UNIQUE(skill_id,label,alias_type));
CREATE INDEX skill_alias_norm ON skill_alias(normalized_label);
CREATE TABLE skill_crosswalk (from_skill_id TEXT NOT NULL REFERENCES skill, to_skill_id TEXT NOT NULL REFERENCES skill, relation TEXT NOT NULL CHECK(relation IN ('exact_label','curated_equivalent','related_candidate')), method TEXT NOT NULL, review_status TEXT NOT NULL, matched_label TEXT, evidence_id TEXT REFERENCES evidence, PRIMARY KEY(from_skill_id,to_skill_id), CHECK(from_skill_id<>to_skill_id));
CREATE TABLE external_skill_crosswalk (namespace TEXT NOT NULL, external_id TEXT NOT NULL, external_label TEXT, skill_id TEXT NOT NULL REFERENCES skill, relation TEXT NOT NULL, review_status TEXT NOT NULL, PRIMARY KEY(namespace,external_id,skill_id));
CREATE TABLE technology_curation (skill_id TEXT PRIMARY KEY REFERENCES skill, recommended_category TEXT NOT NULL, capability TEXT NOT NULL, reason TEXT NOT NULL, source_url TEXT NOT NULL, status TEXT NOT NULL, evidence_id TEXT NOT NULL REFERENCES evidence);
CREATE TABLE domain (domain_id TEXT PRIMARY KEY, source_id TEXT NOT NULL REFERENCES source, label TEXT NOT NULL, domain_type TEXT NOT NULL, description TEXT, evidence_id TEXT REFERENCES evidence);
CREATE TABLE domain_edge (child_id TEXT NOT NULL REFERENCES domain, parent_id TEXT NOT NULL REFERENCES domain, evidence_id TEXT REFERENCES evidence, PRIMARY KEY(child_id,parent_id), CHECK(child_id<>parent_id));
CREATE TABLE skill_domain (skill_id TEXT NOT NULL REFERENCES skill, domain_id TEXT NOT NULL REFERENCES domain, relation TEXT NOT NULL, method TEXT NOT NULL, review_status TEXT NOT NULL, evidence_id TEXT REFERENCES evidence, PRIMARY KEY(skill_id,domain_id,relation));
CREATE TABLE skill_relation (from_skill_id TEXT NOT NULL REFERENCES skill, to_skill_id TEXT NOT NULL REFERENCES skill, relation TEXT NOT NULL, evidence_id TEXT NOT NULL REFERENCES evidence, PRIMARY KEY(from_skill_id,to_skill_id,relation));
CREATE TABLE occupation_skill (occupation_id TEXT NOT NULL REFERENCES occupation, skill_id TEXT NOT NULL REFERENCES skill, relation TEXT NOT NULL CHECK(relation IN ('essential','optional','software_used','rated_essential_skill','rated_transferable_skill','rated_knowledge')), hot_technology INTEGER CHECK(hot_technology IN (0,1)), in_demand INTEGER CHECK(in_demand IN (0,1)), evidence_id TEXT NOT NULL REFERENCES evidence, PRIMARY KEY(occupation_id,skill_id,relation));
CREATE INDEX occupation_skill_skill ON occupation_skill(skill_id);

CREATE TABLE descriptor (descriptor_id TEXT PRIMARY KEY, source_id TEXT NOT NULL REFERENCES source, native_id TEXT NOT NULL, label TEXT NOT NULL, description TEXT, skill_id TEXT REFERENCES skill, evidence_id TEXT NOT NULL REFERENCES evidence);
CREATE TABLE rating_scale (scale_id TEXT PRIMARY KEY, label TEXT NOT NULL, minimum REAL NOT NULL, maximum REAL NOT NULL, evidence_id TEXT NOT NULL REFERENCES evidence);
CREATE TABLE rating_category (category_id TEXT PRIMARY KEY, category_domain TEXT NOT NULL, element_id TEXT, scale_id TEXT NOT NULL REFERENCES rating_scale, category TEXT NOT NULL, description TEXT NOT NULL, evidence_id TEXT NOT NULL REFERENCES evidence);
CREATE TABLE scale_anchor (anchor_id TEXT PRIMARY KEY, descriptor_id TEXT NOT NULL REFERENCES descriptor, scale_id TEXT NOT NULL REFERENCES rating_scale, value REAL NOT NULL, description TEXT NOT NULL, evidence_id TEXT NOT NULL REFERENCES evidence);
CREATE TABLE occupation_rating (rating_id TEXT PRIMARY KEY, occupation_id TEXT NOT NULL REFERENCES occupation, descriptor_id TEXT NOT NULL REFERENCES descriptor, dataset TEXT NOT NULL, scale_id TEXT NOT NULL REFERENCES rating_scale, category TEXT, value REAL NOT NULL, sample_n REAL, standard_error REAL, ci_low REAL, ci_high REAL, recommend_suppress TEXT, not_relevant TEXT, date TEXT, domain_source TEXT, evidence_id TEXT NOT NULL REFERENCES evidence);
CREATE INDEX occupation_rating_lookup ON occupation_rating(occupation_id,descriptor_id,scale_id);
CREATE TABLE occupation_metadata (metadata_id TEXT PRIMARY KEY, occupation_id TEXT NOT NULL REFERENCES occupation, dataset TEXT NOT NULL, record_json TEXT NOT NULL CHECK(json_valid(record_json)), evidence_id TEXT NOT NULL REFERENCES evidence);
CREATE TABLE job_zone (job_zone INTEGER PRIMARY KEY, label TEXT NOT NULL, experience TEXT, education TEXT, job_training TEXT, examples TEXT, svp_range TEXT, evidence_id TEXT NOT NULL REFERENCES evidence);
CREATE TABLE occupation_job_zone (occupation_id TEXT PRIMARY KEY REFERENCES occupation, job_zone INTEGER NOT NULL REFERENCES job_zone, date TEXT, domain_source TEXT, evidence_id TEXT NOT NULL REFERENCES evidence);
CREATE TABLE related_occupation (occupation_id TEXT NOT NULL REFERENCES occupation, related_occupation_id TEXT NOT NULL REFERENCES occupation, tier TEXT NOT NULL, rank INTEGER NOT NULL, evidence_id TEXT NOT NULL REFERENCES evidence, PRIMARY KEY(occupation_id,related_occupation_id));

CREATE TABLE task (task_id TEXT PRIMARY KEY, source_id TEXT NOT NULL REFERENCES source, native_id TEXT NOT NULL, description TEXT NOT NULL, evidence_id TEXT NOT NULL REFERENCES evidence);
CREATE TABLE occupation_task (occupation_id TEXT NOT NULL REFERENCES occupation, task_id TEXT NOT NULL REFERENCES task, task_type TEXT, date TEXT, domain_source TEXT, evidence_id TEXT NOT NULL REFERENCES evidence, PRIMARY KEY(occupation_id,task_id));
CREATE INDEX occupation_task_task ON occupation_task(task_id);
CREATE TABLE task_rating (rating_id TEXT PRIMARY KEY, occupation_id TEXT NOT NULL, task_id TEXT NOT NULL, scale_id TEXT NOT NULL REFERENCES rating_scale, category TEXT, value REAL NOT NULL, sample_n REAL, recommend_suppress TEXT, evidence_id TEXT NOT NULL REFERENCES evidence, FOREIGN KEY(occupation_id,task_id) REFERENCES occupation_task(occupation_id,task_id));
CREATE TABLE activity (activity_id TEXT PRIMARY KEY, source_id TEXT NOT NULL REFERENCES source, native_id TEXT NOT NULL, label TEXT NOT NULL, level TEXT NOT NULL CHECK(level IN ('GWA','IWA','DWA')), evidence_id TEXT NOT NULL REFERENCES evidence);
CREATE TABLE activity_edge (child_id TEXT NOT NULL REFERENCES activity, parent_id TEXT NOT NULL REFERENCES activity, evidence_id TEXT NOT NULL REFERENCES evidence, PRIMARY KEY(child_id,parent_id));
CREATE TABLE task_activity (occupation_id TEXT NOT NULL, task_id TEXT NOT NULL, activity_id TEXT NOT NULL REFERENCES activity, evidence_id TEXT NOT NULL REFERENCES evidence, PRIMARY KEY(occupation_id,task_id,activity_id), FOREIGN KEY(occupation_id,task_id) REFERENCES occupation_task(occupation_id,task_id));
CREATE TABLE descriptor_activity (descriptor_id TEXT NOT NULL REFERENCES descriptor, activity_id TEXT NOT NULL REFERENCES activity, relation TEXT NOT NULL, evidence_id TEXT NOT NULL REFERENCES evidence, PRIMARY KEY(descriptor_id,activity_id));
CREATE TABLE descriptor_relation (from_descriptor_id TEXT NOT NULL REFERENCES descriptor, to_descriptor_id TEXT NOT NULL REFERENCES descriptor, relation TEXT NOT NULL, evidence_id TEXT NOT NULL REFERENCES evidence, PRIMARY KEY(from_descriptor_id,to_descriptor_id,relation));
CREATE TABLE skill_task_evidence (skill_id TEXT NOT NULL REFERENCES skill, task_id TEXT NOT NULL REFERENCES task, relation TEXT NOT NULL CHECK(relation IN ('literal_mention','reviewed_usage')), method TEXT NOT NULL, matched_text TEXT NOT NULL, start_char INTEGER NOT NULL, end_char INTEGER NOT NULL, review_status TEXT NOT NULL, evidence_id TEXT NOT NULL REFERENCES evidence, PRIMARY KEY(skill_id,task_id,start_char), CHECK(end_char>start_char));
CREATE TABLE task_domain (task_id TEXT NOT NULL REFERENCES task, domain_id TEXT NOT NULL REFERENCES domain, rule_id TEXT NOT NULL, method TEXT NOT NULL, evidence_id TEXT NOT NULL REFERENCES evidence, PRIMARY KEY(task_id,domain_id));
CREATE TABLE domain_parent_candidate (domain_id TEXT NOT NULL REFERENCES domain, parent_id TEXT NOT NULL REFERENCES parent, relation TEXT NOT NULL DEFAULT 'supporting_context_only', review_status TEXT NOT NULL DEFAULT 'proposed', rule_id TEXT NOT NULL, PRIMARY KEY(domain_id,parent_id));

CREATE TABLE review_issue (issue_id TEXT PRIMARY KEY, entity_type TEXT NOT NULL, entity_id TEXT NOT NULL, issue_type TEXT NOT NULL, severity TEXT NOT NULL CHECK(severity IN ('high','medium','low')), detail TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'open');

-- IT_KB_2.0.0 proposal layer. These tables are additive; the v1 taxonomy and
-- runtime mappings remain unchanged until the evidence cards are reviewed.
CREATE TABLE role_track (track_id TEXT PRIMARY KEY, label TEXT NOT NULL UNIQUE, definition TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('active','conditional','excluded')), taxonomy_version TEXT NOT NULL);
CREATE TABLE family_role_track (family_id TEXT NOT NULL REFERENCES family, track_id TEXT NOT NULL REFERENCES role_track, relation TEXT NOT NULL, rationale TEXT NOT NULL, taxonomy_version TEXT NOT NULL, PRIMARY KEY(family_id,track_id));
CREATE TABLE leaf_profile (leaf_id TEXT PRIMARY KEY REFERENCES leaf, taxonomy_version TEXT NOT NULL, definition TEXT NOT NULL, primary_outcome TEXT NOT NULL DEFAULT '', in_scope_json TEXT NOT NULL CHECK(json_valid(in_scope_json)), out_of_scope_json TEXT NOT NULL CHECK(json_valid(out_of_scope_json)), profile_status TEXT NOT NULL CHECK(profile_status IN ('ACTIVE','CONDITIONAL','REVIEW_ONLY','MARKET_DERIVED')), evidence_level TEXT NOT NULL CHECK(evidence_level IN ('SOURCE_MAPPED_PROPOSAL','NONE','MARKET_DERIVED')), readiness_reason TEXT NOT NULL, reviewer TEXT NOT NULL DEFAULT '', reviewed_at TEXT NOT NULL DEFAULT '');
CREATE TABLE leaf_source_occupation (leaf_id TEXT NOT NULL REFERENCES leaf, occupation_id TEXT NOT NULL REFERENCES occupation, source_id TEXT NOT NULL REFERENCES source, native_id TEXT NOT NULL, preferred_label TEXT NOT NULL, mapping_relation TEXT NOT NULL, mapping_method TEXT NOT NULL, review_status TEXT NOT NULL, evidence_id TEXT REFERENCES evidence, PRIMARY KEY(leaf_id,occupation_id));
CREATE TABLE leaf_alias (leaf_id TEXT NOT NULL REFERENCES leaf, alias_id TEXT NOT NULL REFERENCES occupation_alias, source_id TEXT NOT NULL REFERENCES source, alias TEXT NOT NULL, alias_type TEXT NOT NULL, evidence_id TEXT REFERENCES evidence, provenance TEXT NOT NULL DEFAULT 'source_occupation_alias', PRIMARY KEY(leaf_id,alias_id));
CREATE TABLE leaf_task_evidence (leaf_id TEXT NOT NULL REFERENCES leaf, occupation_id TEXT NOT NULL REFERENCES occupation, task_id TEXT NOT NULL REFERENCES task, source_id TEXT NOT NULL REFERENCES source, task_type TEXT, description TEXT NOT NULL, verb TEXT NOT NULL DEFAULT '', object_text TEXT NOT NULL DEFAULT '', context_text TEXT NOT NULL DEFAULT '', evidence_tier TEXT NOT NULL DEFAULT 'source_occupation_task', evidence_id TEXT NOT NULL REFERENCES evidence, PRIMARY KEY(leaf_id,occupation_id,task_id));
CREATE TABLE leaf_skill_profile (leaf_id TEXT NOT NULL REFERENCES leaf, occupation_id TEXT NOT NULL REFERENCES occupation, skill_id TEXT NOT NULL REFERENCES skill, source_id TEXT NOT NULL REFERENCES source, normalized_label TEXT NOT NULL, kind TEXT NOT NULL, relation TEXT NOT NULL, hot_technology INTEGER, in_demand INTEGER, evidence_tier TEXT NOT NULL DEFAULT 'source_occupation_skill', evidence_id TEXT NOT NULL REFERENCES evidence, PRIMARY KEY(leaf_id,occupation_id,skill_id,relation));
CREATE TABLE leaf_technology_profile (leaf_id TEXT NOT NULL REFERENCES leaf, occupation_id TEXT NOT NULL REFERENCES occupation, skill_id TEXT NOT NULL REFERENCES skill, source_id TEXT NOT NULL REFERENCES source, technology_label TEXT NOT NULL, relation TEXT NOT NULL, role_context TEXT NOT NULL DEFAULT 'source_occupation_context', evidence_id TEXT NOT NULL REFERENCES evidence, PRIMARY KEY(leaf_id,occupation_id,skill_id,relation));
CREATE TABLE leaf_confusion_pair (pair_id TEXT PRIMARY KEY, leaf_id TEXT NOT NULL REFERENCES leaf, sibling_leaf_id TEXT NOT NULL REFERENCES leaf, disambiguator TEXT NOT NULL, hard_negative_rule TEXT NOT NULL, taxonomy_version TEXT NOT NULL, reviewer TEXT NOT NULL DEFAULT '', review_status TEXT NOT NULL DEFAULT 'REVIEW_REQUIRED', CHECK(leaf_id<>sibling_leaf_id));
CREATE TABLE leaf_title_evidence (title_id TEXT NOT NULL REFERENCES input_title, leaf_id TEXT NOT NULL REFERENCES leaf, title TEXT NOT NULL, method TEXT NOT NULL, review_status TEXT NOT NULL, evidence_strength TEXT NOT NULL DEFAULT 'title_classification_only', evidence_quote TEXT NOT NULL, taxonomy_version TEXT NOT NULL, PRIMARY KEY(title_id,leaf_id));
CREATE TABLE leaf_custom_profile (profile_id TEXT PRIMARY KEY, leaf_id TEXT NOT NULL REFERENCES leaf, source_id TEXT NOT NULL REFERENCES source, evidence_id TEXT NOT NULL REFERENCES evidence, batch_id TEXT NOT NULL, description TEXT NOT NULL, primary_outcome TEXT NOT NULL, in_scope_json TEXT NOT NULL CHECK(json_valid(in_scope_json)), out_of_scope_json TEXT NOT NULL CHECK(json_valid(out_of_scope_json)), tasks_json TEXT NOT NULL CHECK(json_valid(tasks_json)), professional_skills_json TEXT NOT NULL CHECK(json_valid(professional_skills_json)), technologies_json TEXT NOT NULL CHECK(json_valid(technologies_json)), sibling_disambiguators_json TEXT NOT NULL CHECK(json_valid(sibling_disambiguators_json)), review_status TEXT NOT NULL CHECK(review_status IN ('DRAFT','REVIEW_REQUIRED','APPROVED')), vector_status TEXT NOT NULL CHECK(vector_status IN ('NOT_INCLUDED_UNTIL_APPROVED','APPROVED')), reviewer TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL, UNIQUE(leaf_id,batch_id));
CREATE TABLE taxonomy_v2_crosswalk (old_level TEXT NOT NULL CHECK(old_level IN ('family','parent','leaf')), old_id TEXT NOT NULL, new_level TEXT NOT NULL CHECK(new_level IN ('family','parent','leaf','role_track')), new_id TEXT NOT NULL, relation TEXT NOT NULL, rationale TEXT NOT NULL, taxonomy_version TEXT NOT NULL, PRIMARY KEY(old_level,old_id,new_level,new_id));
CREATE TABLE taxonomy_v2_excluded_node (old_family_id TEXT NOT NULL, old_family_label TEXT NOT NULL, old_parent_id TEXT NOT NULL, old_parent_label TEXT NOT NULL, old_leaf_id TEXT NOT NULL, old_leaf_label TEXT NOT NULL, old_scope TEXT NOT NULL, old_status TEXT NOT NULL, exclusion_reason TEXT NOT NULL, archived_at TEXT NOT NULL, taxonomy_version TEXT NOT NULL, PRIMARY KEY(old_family_id,old_parent_id,old_leaf_id));
CREATE TABLE taxonomy_v2_excluded_title (title_id TEXT NOT NULL, title TEXT NOT NULL, old_family_id TEXT NOT NULL, old_parent_id TEXT NOT NULL, old_leaf_id TEXT NOT NULL, method TEXT NOT NULL, rule_id TEXT NOT NULL, review_status TEXT NOT NULL, exclusion_reason TEXT NOT NULL, archived_at TEXT NOT NULL, taxonomy_version TEXT NOT NULL, PRIMARY KEY(title_id,old_leaf_id));
CREATE INDEX leaf_source_occupation_source_idx ON leaf_source_occupation(source_id);
CREATE INDEX leaf_task_evidence_task_idx ON leaf_task_evidence(task_id);
CREATE INDEX leaf_skill_profile_skill_idx ON leaf_skill_profile(skill_id);
CREATE INDEX leaf_title_evidence_leaf_idx ON leaf_title_evidence(leaf_id);

-- Application ingestion is intentionally empty: source profiles do not create CV/job observations.
CREATE TABLE document (document_id TEXT PRIMARY KEY, document_type TEXT NOT NULL CHECK(document_type IN ('candidate_cv','job_offer')), language TEXT NOT NULL CHECK(language='en'), title TEXT, text TEXT NOT NULL, external_reference TEXT);
CREATE TABLE document_skill (observation_id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES document, skill_id TEXT REFERENCES skill, external_namespace TEXT, external_skill_id TEXT, surface TEXT NOT NULL, section TEXT, start_char INTEGER NOT NULL, end_char INTEGER NOT NULL, evidence_quote TEXT NOT NULL, assertion TEXT NOT NULL CHECK(assertion IN ('possessed','required','preferred','mentioned','negated','unknown')), proficiency TEXT, experience_months REAL CHECK(experience_months>=0), extractor TEXT NOT NULL, extractor_version TEXT, confidence REAL CHECK(confidence BETWEEN 0 AND 1), CHECK(end_char>start_char), CHECK(skill_id IS NOT NULL OR external_skill_id IS NOT NULL));
CREATE TABLE document_role (hypothesis_id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES document, taxonomy_version TEXT NOT NULL, family_id TEXT REFERENCES family, parent_id TEXT, leaf_id TEXT, status TEXT NOT NULL CHECK(status IN ('resolved','parent_only','ambiguous','abstain')), evidence_quote TEXT, resolver TEXT NOT NULL, confidence REAL CHECK(confidence BETWEEN 0 AND 1), FOREIGN KEY(parent_id,family_id) REFERENCES parent(parent_id,family_id), FOREIGN KEY(leaf_id,parent_id) REFERENCES leaf(leaf_id,parent_id), CHECK(leaf_id IS NULL OR parent_id IS NOT NULL), CHECK(parent_id IS NULL OR family_id IS NOT NULL));
CREATE TABLE document_fact (fact_id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES document, fact_type TEXT NOT NULL, value_json TEXT NOT NULL CHECK(json_valid(value_json)), qualifier TEXT NOT NULL, evidence_quote TEXT NOT NULL, extractor TEXT NOT NULL);

CREATE VIEW v_taxonomy AS SELECT f.family_id,f.label family,p.parent_id,p.label parent,l.leaf_id,l.label leaf,l.scope,l.status,f.taxonomy_version FROM family f JOIN parent p USING(family_id) LEFT JOIN leaf l USING(parent_id);
CREATE VIEW v_it_occupations AS SELECT o.*,c.family_id,c.parent_id,c.leaf_id,c.mapping_relation,c.review_status FROM occupation o LEFT JOIN occupation_classification c USING(occupation_id) WHERE o.scope='core';
CREATE VIEW v_skill_resolution AS
 WITH RECURSIVE accepted AS (SELECT from_skill_id,min(to_skill_id) to_skill_id FROM skill_crosswalk WHERE review_status IN ('deterministic_exact','reviewed') GROUP BY from_skill_id HAVING count(*)=1),
 walk(source_skill_id,resolved_skill_id,depth) AS (SELECT skill_id,skill_id,0 FROM skill UNION ALL SELECT w.source_skill_id,a.to_skill_id,w.depth+1 FROM walk w JOIN accepted a ON a.from_skill_id=w.resolved_skill_id WHERE w.depth<8)
 SELECT w.source_skill_id,w.resolved_skill_id FROM walk w LEFT JOIN accepted a ON a.from_skill_id=w.resolved_skill_id WHERE a.from_skill_id IS NULL;
CREATE VIEW v_effective_skill_domains AS
 WITH ranked AS (SELECT sd.*,CASE method WHEN 'documented_technology_curation' THEN 3 WHEN 'onet_category_label_policy' THEN 2 ELSE 1 END priority FROM skill_domain sd WHERE relation='proposed_functional_domain'),
 best AS (SELECT skill_id,max(priority) priority FROM ranked GROUP BY skill_id)
 SELECT r.skill_id,r.domain_id,d.label,r.method,r.review_status,r.evidence_id FROM ranked r JOIN best b USING(skill_id,priority) JOIN domain d USING(domain_id);
CREATE VIEW v_it_occupation_skills AS
 SELECT os.occupation_id,r.resolved_skill_id skill_id,s.preferred_label skill_label,s.kind,os.skill_id source_skill_id,os.relation,os.hot_technology,os.in_demand,os.evidence_id
 FROM occupation_skill os JOIN occupation o USING(occupation_id) JOIN v_skill_resolution r ON r.source_skill_id=os.skill_id JOIN skill s ON s.skill_id=r.resolved_skill_id WHERE o.scope='core';
CREATE VIEW v_skill_role_context AS
 SELECT DISTINCT os.skill_id,os.skill_label,c.family_id,c.parent_id,c.leaf_id,os.occupation_id,os.relation,c.mapping_relation,c.review_status,'occupation_profile_context_not_job_requirement' interpretation
 FROM v_it_occupation_skills os JOIN occupation_classification c USING(occupation_id);
CREATE VIEW v_technology_coverage AS
 WITH oc AS (SELECT skill_id,count(DISTINCT occupation_id) n FROM v_it_occupation_skills GROUP BY skill_id),
 dc AS (SELECT skill_id,sum(relation='official_software_category') categories,sum(relation='proposed_functional_domain') domains FROM skill_domain GROUP BY skill_id),
 tc AS (SELECT skill_id,count(*) n FROM skill_task_evidence GROUP BY skill_id)
 SELECT s.skill_id,s.preferred_label,s.provided_category,s.matching_policy,COALESCE(oc.n,0) core_occupation_count,
 max(COALESCE(dc.categories,0),COALESCE(dcr.categories,0)) official_category_count,COALESCE(tc.n,0) explicit_task_mentions,COALESCE(dc.domains,0) proposed_domain_count
 FROM skill s JOIN v_skill_resolution r ON r.source_skill_id=s.skill_id LEFT JOIN oc ON oc.skill_id=r.resolved_skill_id
 LEFT JOIN dc ON dc.skill_id=s.skill_id LEFT JOIN dc dcr ON dcr.skill_id=r.resolved_skill_id LEFT JOIN tc ON tc.skill_id=r.resolved_skill_id WHERE s.source_id='TECH_V2';
CREATE VIEW v_title_paths AS
 SELECT i.title_id,i.original_row_number,i.title,i.scope,i.resolution_status,c.family_id,f.label family,c.parent_id,p.label parent,c.leaf_id,l.label leaf,c.method,c.review_status
 FROM input_title i LEFT JOIN title_classification c USING(title_id) LEFT JOIN family f USING(family_id) LEFT JOIN parent p USING(parent_id) LEFT JOIN leaf l USING(leaf_id);
CREATE VIEW v_professional_skill_task_paths AS
 SELECT DISTINCT d.skill_id,ta.occupation_id,ta.task_id,da.activity_id gwa_id,ae1.child_id iwa_id,ae2.child_id dwa_id,
 da.evidence_id descriptor_gwa_evidence,ae1.evidence_id gwa_iwa_evidence,ae2.evidence_id iwa_dwa_evidence,ta.evidence_id task_dwa_evidence,
 'indirect_via_general_work_activity_not_direct_skill_task_assertion' interpretation
 FROM descriptor_activity da JOIN descriptor d USING(descriptor_id) JOIN activity_edge ae1 ON ae1.parent_id=da.activity_id JOIN activity_edge ae2 ON ae2.parent_id=ae1.child_id JOIN task_activity ta ON ta.activity_id=ae2.child_id JOIN occupation o USING(occupation_id)
 WHERE d.skill_id IS NOT NULL AND o.scope='core';
CREATE VIEW v_review_queue AS SELECT * FROM review_issue WHERE status='open';
CREATE VIEW v_leaf_skill_profile AS
 SELECT c.leaf_id,os.skill_id,os.skill_label,os.kind,os.occupation_id,os.relation,os.evidence_id,c.review_status,'source_occupation_mapped_to_proposed_leaf' interpretation
 FROM v_it_occupation_skills os JOIN occupation_classification c USING(occupation_id) WHERE c.leaf_id IS NOT NULL;
CREATE VIEW v_skill_parent_candidates AS
 SELECT DISTINCT s.skill_id,s.preferred_label,d.domain_id,d.label functional_domain,p.family_id,p.parent_id,p.label parent,
 d.method domain_method,m.rule_id,m.review_status,'functional_domain_support_not_occupation_assignment' interpretation
 FROM skill s JOIN v_effective_skill_domains d USING(skill_id) JOIN domain_parent_candidate m USING(domain_id) JOIN parent p USING(parent_id);
CREATE VIEW v_leaf_task_profile AS
 SELECT c.leaf_id,t.task_id,t.description,ot.occupation_id,ot.task_type,ot.evidence_id,c.review_status
 FROM occupation_task ot JOIN task t USING(task_id) JOIN occupation o USING(occupation_id) JOIN occupation_classification c USING(occupation_id) WHERE o.scope='core' AND c.leaf_id IS NOT NULL;
CREATE VIEW v_usable_occupation_ratings AS
 SELECT r.*,s.label scale_name,s.minimum,s.maximum,(r.value-s.minimum)/NULLIF(s.maximum-s.minimum,0) scaled_value
 FROM occupation_rating r JOIN rating_scale s USING(scale_id)
 WHERE COALESCE(r.recommend_suppress,'N')<>'Y' AND COALESCE(r.not_relevant,'N')<>'Y';
CREATE VIEW v_osca_occupation_detail AS
 SELECT o.occupation_id,o.native_id,o.preferred_label,o.scope,
 json_extract(e.record_json,'$."Skill Level"') source_skill_level,
 json_extract(e.record_json,'$."Registration or Licensing"') registration_or_licensing,
 json_extract(e.record_json,'$."Inclusion and Exclusion Statements"') inclusion_exclusion,
 json_extract(e.record_json,'$.Specialisations') specialisations,o.evidence_id
 FROM occupation o JOIN evidence e USING(evidence_id) WHERE o.source_id='OSCA';
CREATE VIEW v_esco_occupation_detail AS
 SELECT o.occupation_id,o.native_id,o.preferred_label,o.scope,
 json_extract(e.record_json,'$.code') esco_code,json_extract(e.record_json,'$.iscoGroup') isco_group,
 json_extract(e.record_json,'$.scopeNote') scope_note,json_extract(e.record_json,'$.regulatedProfessionNote') regulated_profession_note,
 json_extract(e.record_json,'$.naceCode') nace_code,json_extract(e.record_json,'$.modifiedDate') modified_date,o.evidence_id
 FROM occupation o JOIN evidence e USING(evidence_id) WHERE o.source_id='ESCO';

CREATE VIEW v_leaf_evidence_summary AS
 WITH so AS (SELECT leaf_id,COUNT(DISTINCT occupation_id) n,GROUP_CONCAT(DISTINCT source_id) sources FROM leaf_source_occupation GROUP BY leaf_id),
      te AS (SELECT leaf_id,COUNT(DISTINCT task_id) n FROM leaf_task_evidence GROUP BY leaf_id),
      sp AS (SELECT leaf_id,COUNT(DISTINCT skill_id) n FROM leaf_skill_profile GROUP BY leaf_id),
      tp AS (SELECT leaf_id,COUNT(DISTINCT skill_id) n FROM leaf_technology_profile GROUP BY leaf_id),
      ti AS (SELECT leaf_id,COUNT(DISTINCT title_id) n FROM leaf_title_evidence GROUP BY leaf_id),
      cp AS (SELECT leaf_id,COUNT(DISTINCT pair_id) n FROM leaf_confusion_pair GROUP BY leaf_id)
 SELECT l.leaf_id,p.parent_id,pa.family_id,COALESCE(so.n,0) source_occupation_count,
        COALESCE(te.n,0) task_count,COALESCE(sp.n,0) skill_count,
        COALESCE(tp.n,0) technology_count,COALESCE(ti.n,0) reviewed_title_count,
        COALESCE(cp.n,0) confusion_pair_count,so.sources source_ids
 FROM leaf l JOIN parent p ON p.parent_id=l.parent_id JOIN family pa ON pa.family_id=p.family_id
 LEFT JOIN so ON so.leaf_id=l.leaf_id LEFT JOIN te ON te.leaf_id=l.leaf_id
 LEFT JOIN sp ON sp.leaf_id=l.leaf_id LEFT JOIN tp ON tp.leaf_id=l.leaf_id
 LEFT JOIN ti ON ti.leaf_id=l.leaf_id LEFT JOIN cp ON cp.leaf_id=l.leaf_id;
