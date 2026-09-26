"""Create portable snapshots, human-review CSVs, coverage metrics and a data dictionary."""
import collections,csv,gzip,hashlib,json,sqlite3
from pathlib import Path
import policy
ROOT=Path(__file__).resolve().parents[1]
def base_tables():
    c=sqlite3.connect(':memory:');c.executescript((ROOT/'schema.sql').read_text(encoding='utf-8'))
    result=[r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY rowid")];c.close();return result
def export_csv(c,name,query):
    cur=c.execute(query)
    with (ROOT/'exports'/name).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow([x[0] for x in cur.description]);w.writerows(cur)
def main():
    c=sqlite3.connect(ROOT/'it_knowledge.sqlite');c.row_factory=sqlite3.Row;tables=base_tables()
    (ROOT/'config/taxonomy_policy.json').write_text(json.dumps({'version':policy.VERSION,'tree':policy.TREE,'label_rules':[{'leaf':l,'regex':p,'priority':v} for l,p,v in policy.RULE_SPECS],'functional_domains':policy.FUNCTIONAL_DOMAINS,'provided_category_domain_proposals':policy.CATEGORY_DOMAINS,'functional_keyword_rules':policy.DOMAIN_PATTERNS,'functional_domain_parent_candidates':policy.DOMAIN_PARENT_CANDIDATES},indent=2),encoding='utf-8')
    manifest={};dictionary=['# Data dictionary','', 'All labels and source records are English. SQLite foreign keys and CHECK constraints are defined in `schema.sql`. Source profiles describe occupations; application observations describe actual CV/job evidence.','']
    with gzip.open(ROOT/'data/normalized_snapshot.jsonl.gz','wt',encoding='utf-8',compresslevel=6) as out:
        for table in tables:
            cols=c.execute('PRAGMA table_info("'+table+'")').fetchall();pk=[x['name'] for x in sorted(cols,key=lambda x:x['pk']) if x['pk']]
            q='SELECT * FROM "'+table+'"'+(' ORDER BY '+','.join('"'+x+'"' for x in pk) if pk else '')
            h=hashlib.sha256();count=0
            for row in c.execute(q):
                rec=dict(row);canonical=json.dumps(rec,sort_keys=True,separators=(',',':'),ensure_ascii=False)+'\n';h.update(canonical.encode());count+=1
                out.write(json.dumps({'table':table,'row':rec},ensure_ascii=False,separators=(',',':'))+'\n')
            manifest[table]={'rows':count,'sha256_of_sorted_json_rows':h.hexdigest(),'primary_key':pk}
            dictionary.extend(['## '+table,'',f'{count:,} rows.','', '| Column | SQLite type | Required | Primary key |','|---|---|---|---|'])
            for col in cols:dictionary.append(f"| `{col['name']}` | {col['type']} | {'yes' if col['notnull'] or col['pk'] else 'no'} | {'yes' if col['pk'] else ''} |")
            fks=c.execute('PRAGMA foreign_key_list("'+table+'")').fetchall()
            if fks:dictionary.extend(['','Foreign-key references: '+', '.join('`'+x['from']+'` → `'+x['table']+'.'+str(x['to'] or '(primary key)')+'`' for x in fks)+'.'])
            dictionary.append('')
    views=[r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='view' ORDER BY name")]
    dictionary.extend(['## Query views','']+['- `'+x+'`' for x in views])
    (ROOT/'docs/DATA_DICTIONARY.md').write_text('\n'.join(dictionary),encoding='utf-8')
    (ROOT/'data/snapshot_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    queries={
      'canonical_taxonomy.csv':'SELECT * FROM v_taxonomy ORDER BY family,parent,leaf',
      'reviewed_titles_with_paths.csv':'''SELECT p.*,(SELECT count(DISTINCT a.occupation_id) FROM title_source_match m JOIN occupation_alias a USING(alias_id) WHERE m.title_id=p.title_id) source_concept_matches FROM v_title_paths p ORDER BY original_row_number''',
      'title_source_correspondences.csv':'''SELECT i.title_id,i.title,o.source_id,o.native_id,o.preferred_label source_label,o.scope source_scope,a.label matched_source_title,a.alias_type,m.match_method,m.interpretation,a.evidence_id FROM input_title i JOIN title_source_match m USING(title_id) JOIN occupation_alias a USING(alias_id) JOIN occupation o USING(occupation_id) ORDER BY i.original_row_number,o.source_id,o.native_id''',
      'it_source_occupations.csv':'''SELECT o.occupation_id,o.source_id,o.native_id,o.preferred_label,o.description,o.scope,o.scope_reason,c.family_id,c.parent_id,c.leaf_id,c.mapping_relation,c.review_status,o.evidence_id FROM occupation o LEFT JOIN occupation_classification c USING(occupation_id) WHERE o.scope<>'reference_only' ORDER BY source_id,preferred_label''',
      'technology_coverage.csv':'''WITH task_counts AS (SELECT s.skill_id,count(DISTINCT ot.task_id) n FROM v_it_occupation_skills s JOIN occupation_task ot USING(occupation_id) GROUP BY s.skill_id)
      SELECT v.*,r.resolved_skill_id canonical_representative_id,COALESCE(cur.recommended_category,v.provided_category) effective_category,cur.capability,cur.source_url curation_source,
      (SELECT group_concat(DISTINCT d.label) FROM v_effective_skill_domains d WHERE d.skill_id=v.skill_id) effective_functional_domains,
      COALESCE(tc.n,0) shared_occupation_task_candidates,
      CASE WHEN v.explicit_task_mentions>0 THEN 'literal_text_mention_needs_review' WHEN COALESCE(tc.n,0)>0 THEN 'indirect_candidates_only' ELSE 'no_task_link' END task_link_status
      FROM v_technology_coverage v JOIN v_skill_resolution r ON r.source_skill_id=v.skill_id LEFT JOIN technology_curation cur USING(skill_id) LEFT JOIN task_counts tc ON tc.skill_id=r.resolved_skill_id ORDER BY v.preferred_label''',
      'technology_category_corrections.csv':'''SELECT s.skill_id,s.preferred_label,s.provided_category,c.recommended_category,c.capability,c.reason,c.source_url,c.status FROM technology_curation c JOIN skill s USING(skill_id) ORDER BY s.preferred_label''',
      'skill_crosswalks.csv':'''SELECT c.*,a.preferred_label from_label,b.preferred_label to_label FROM skill_crosswalk c JOIN skill a ON a.skill_id=c.from_skill_id JOIN skill b ON b.skill_id=c.to_skill_id ORDER BY from_label''',
      'skill_catalog.csv':'SELECT * FROM skill ORDER BY source_id,preferred_label',
      'skill_parent_candidates.csv':'SELECT * FROM v_skill_parent_candidates ORDER BY skill_id,parent_id',
      'skill_domains.csv':'''SELECT sd.skill_id,s.preferred_label,d.label domain,d.domain_type,sd.relation,sd.method,sd.review_status,sd.evidence_id FROM skill_domain sd JOIN skill s USING(skill_id) JOIN domain d USING(domain_id) ORDER BY sd.skill_id,d.domain_id''',
      'source_tasks.csv':'''SELECT t.*,ot.occupation_id,o.preferred_label occupation,ot.task_type,o.scope FROM task t JOIN occupation_task ot USING(task_id) JOIN occupation o USING(occupation_id) ORDER BY t.source_id,o.preferred_label,t.task_id''',
      'review_queue.csv':'SELECT * FROM v_review_queue ORDER BY CASE severity WHEN \'high\' THEN 0 WHEN \'medium\' THEN 1 ELSE 2 END,issue_type,entity_id',
      'source_manifest.csv':'''SELECT f.*,s.version,(SELECT count(*) FROM evidence e WHERE e.file_id=f.file_id) retained_evidence_rows FROM source_file f JOIN source s USING(source_id) ORDER BY f.source_id,f.relative_path'''
    }
    for fn,q in queries.items():export_csv(c,fn,q)
    (ROOT/'exports/nesta_crosswalk_template.csv').write_text('namespace,external_id,external_label,skill_id,relation,review_status\n',encoding='utf-8')
    (ROOT/'exports/legacy_taxonomy_crosswalk_template.csv').write_text('legacy_version,legacy_level,legacy_id,new_level,new_id,relation,review_status\n',encoding='utf-8')
    def listq(q):return [dict(x) for x in c.execute(q)]
    coverage={
      'taxonomy_version':policy.VERSION,'table_counts':{t:v['rows'] for t,v in manifest.items()},'view_count':len(views),
      'occupation_scope':listq('SELECT source_id,scope,count(*) n FROM occupation GROUP BY source_id,scope'),
      'title_scope':listq('SELECT scope,count(*) n FROM input_title GROUP BY scope'),
      'title_resolution':listq('SELECT resolution_status,count(*) n FROM input_title GROUP BY resolution_status'),
      'source_matching':listq('SELECT match_method,count(DISTINCT title_id) title_count FROM title_source_match GROUP BY match_method'),
      'technology_coverage':listq('SELECT count(*) technologies,sum(core_occupation_count>0) direct_core_occupation_link,sum(official_category_count>0) official_software_category,sum(proposed_domain_count>0) functional_domain_proposal,sum(explicit_task_mentions>0) literal_task_mention FROM v_technology_coverage')[0],
      'skills_by_kind':listq('SELECT source_id,kind,count(*) n FROM skill GROUP BY source_id,kind'),
      'task_counts':listq('SELECT source_id,count(*) n FROM task GROUP BY source_id'),
      'review_counts':listq('SELECT issue_type,severity,count(*) n FROM review_issue GROUP BY issue_type,severity ORDER BY n DESC'),
      'database_bytes':(ROOT/'it_knowledge.sqlite').stat().st_size,
      'language':'en','classification_accuracy':'not_measured_no_gold_dataset','recommendation_accuracy':'not_measured_no_gold_dataset'
    }
    (ROOT/'docs/coverage_metrics.json').write_text(json.dumps(coverage,indent=2),encoding='utf-8')
    print(json.dumps(coverage['technology_coverage']));print('Tables',len(tables),'families',manifest['family']['rows'],'parents',manifest['parent']['rows'],'leaves',manifest['leaf']['rows']);c.close()
if __name__=='__main__':main()
