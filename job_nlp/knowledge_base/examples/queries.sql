-- 1. Inspect the proposed hierarchy. None of these IDs silently replace legacy IDs.
SELECT * FROM v_taxonomy ORDER BY family,parent,leaf;

-- 2. Original title -> canonical proposal -> source concept evidence.
SELECT * FROM v_title_paths WHERE title='Data Engineer';
SELECT i.title,o.source_id,o.native_id,o.preferred_label,o.scope,
       m.match_method,m.interpretation,a.evidence_id
FROM input_title i JOIN title_source_match m USING(title_id)
JOIN occupation_alias a USING(alias_id) JOIN occupation o USING(occupation_id)
WHERE i.title='Data Engineer';

-- 3. Every supplied technology, including gaps, not just successfully linked ones.
SELECT * FROM v_technology_coverage ORDER BY core_occupation_count DESC;

-- 4. Distinguish an original category from a documented correction.
SELECT s.skill_id,s.preferred_label,s.provided_category,c.recommended_category,c.capability,c.source_url
FROM skill s JOIN technology_curation c USING(skill_id);

-- 5. Canonical skill -> core IT occupation profiles. These are NOT job requirements.
SELECT DISTINCT os.skill_label,o.preferred_label,os.relation,os.in_demand,os.evidence_id
FROM v_it_occupation_skills os JOIN occupation o USING(occupation_id)
WHERE os.skill_id='TECH::python' ORDER BY o.preferred_label;

-- 6. Data Engineer leaf -> ESCO skills and OSCA tasks. Their shared leaf is a
-- proposed harmonization, not an official direct cross-source skill/task edge.
SELECT * FROM v_leaf_skill_profile WHERE leaf_id='DATA_ENGINEER';
SELECT * FROM v_leaf_task_profile WHERE leaf_id='DATA_ENGINEER';

-- 7. A software/task path through the SAME source occupation is a candidate only.
SELECT DISTINCT s.skill_label,o.preferred_label,t.description,
       'shared_occupation_only_not_direct_software_usage' relation
FROM v_it_occupation_skills s JOIN occupation o USING(occupation_id)
JOIN occupation_task ot USING(occupation_id) JOIN task t USING(task_id)
WHERE s.skill_id='TECH::python' LIMIT 20;

-- 8. Official professional-skill -> GWA -> IWA -> DWA -> task path.
SELECT * FROM v_professional_skill_task_paths
WHERE skill_id='ONET_SKILL:2.B.3.e' LIMIT 20;

-- 9. Use rating scales and quality flags; do not confuse source importance with
-- candidate proficiency or the requirements of one actual job offer.
SELECT o.preferred_label,d.label,r.scale_name,r.value,r.minimum,r.maximum,r.scaled_value
FROM v_usable_occupation_ratings r JOIN occupation o USING(occupation_id)
JOIN descriptor d USING(descriptor_id)
WHERE o.scope='core' AND o.native_id='15-1252.00' AND r.dataset='transferable_skills';

-- 10. Trace a fact to the exact supplied source record.
SELECT f.relative_path,f.sha256,e.locator,e.record_json
FROM evidence e JOIN source_file f USING(file_id)
WHERE e.evidence_id=(SELECT evidence_id FROM occupation_skill LIMIT 1);

-- 11. Missing links and scope conflicts remain reviewable.
SELECT issue_type,severity,count(*) count FROM v_review_queue GROUP BY issue_type,severity;

-- 12. Only actual observations can create a required-skill gap.
-- Replace :candidate_id and :job_id with your ingested document IDs.
SELECT DISTINCT r.resolved_skill_id
FROM document_skill js JOIN v_skill_resolution r ON r.source_skill_id=js.skill_id
WHERE js.document_id=:job_id AND js.assertion='required'
AND NOT EXISTS (
 SELECT 1 FROM document_skill cs JOIN v_skill_resolution cr ON cr.source_skill_id=cs.skill_id
 WHERE cs.document_id=:candidate_id AND cs.assertion='possessed'
 AND cr.resolved_skill_id=r.resolved_skill_id
);
