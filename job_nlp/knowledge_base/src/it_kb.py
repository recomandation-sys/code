"""Read-only, dependency-free integration adapter for the SQLite reference database.

This supplies retrieval/evidence features to an extraction pipeline. It is not a
replacement for the existing H2 parent resolver or a calibrated classifier.
"""
import argparse, collections, csv, json, math, re, sqlite3
from pathlib import Path
try:
    from .policy import norm, title_norm, VERSION
except ImportError:  # direct `python src/it_kb.py ...` execution
    from policy import norm, title_norm, VERSION

DEFAULT_DB=Path(__file__).resolve().parents[1]/'it_knowledge.sqlite'
CANDIDATE_TITLE_SETS_CSV=Path(__file__).resolve().parents[1]/'exports'/'reviewed_titles_candidate_leaf_sets_v3.csv'

# Retired generic title labels are represented at runtime by explicit,
# ambiguity-preserving replacement sets. This keeps multi-leaf alternatives
# without reintroducing a generic sink into the live relational taxonomy.
REPLACEMENT_TITLE_LEAVES = {
    'application developer': ('BACKEND_DEVELOPER', 'FULLSTACK_DEVELOPER', 'FRONTEND_DEVELOPER'),
    'web developer': ('FULLSTACK_DEVELOPER', 'FRONTEND_DEVELOPER', 'BACKEND_DEVELOPER'),
    'mobile developer': ('ANDROID_DEVELOPER', 'IOS_DEVELOPER'),
    'cybersecurity specialist': ('SECURITY_ANALYST', 'SECURITY_ENGINEER'),
    'security specialist': ('SECURITY_ANALYST', 'SECURITY_ENGINEER'),
    'telecommunications specialist': ('TELECOM_ENGINEER', 'TELECOM_ANALYST'),
}

class ITKnowledgeBase:
    def __init__(self,path=DEFAULT_DB):
        self.db=sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True)
        self.db.row_factory=sqlite3.Row
        self._candidate_title_index = None
    def rows(self,query,args=()):return [dict(r) for r in self.db.execute(query,args)]
    def close(self):self.db.close()
    def canonical_id(self,id):
        rows=self.rows('SELECT resolved_skill_id FROM v_skill_resolution WHERE source_skill_id=?',(id,))
        return rows[0]['resolved_skill_id'] if len(rows)==1 else None
    def normalize_skill(self,item):
        """Names respect matching_policy; supplied stable IDs are already-resolved inputs.
        Nesta IDs require an explicit reviewed crosswalk, even if a label looks similar.
        """
        if isinstance(item,str):item={'label':item}
        provided=item.get('skill_id')
        if provided:
            id=self.canonical_id(provided)
            skill=self.rows('SELECT preferred_label,kind FROM skill WHERE skill_id=?',(id,)) if id else []
            return {'input':item,'status':'resolved_id' if id else 'unknown_id','skill_id':id,
             'label':skill[0]['preferred_label'] if skill else None,'kind':skill[0]['kind'] if skill else None}
        ns=item.get('namespace');external=item.get('external_id')
        if ns and external is not None:
            ids={r['skill_id'] for r in self.rows("SELECT skill_id FROM external_skill_crosswalk WHERE namespace=? AND external_id=? AND review_status='reviewed' AND relation IN ('exact','equivalent')",(ns,str(external)))}
            roots={self.canonical_id(i) for i in ids};roots.discard(None)
            return {'input':item,'status':'resolved_crosswalk' if len(roots)==1 else 'external_crosswalk_missing' if not roots else 'ambiguous_external_crosswalk','skill_id':next(iter(roots)) if len(roots)==1 else None,'candidates':sorted(roots)}
        label=item.get('label','')
        # Preferred labels take precedence over aliases. ESCO hidden labels can denote
        # examples or broader concepts, so they are never used as identity equivalences.
        rows=self.rows('SELECT DISTINCT r.resolved_skill_id skill_id,s.preferred_label,s.kind,s.matching_policy,CASE a.alias_type WHEN \'preferred\' THEN 2 ELSE 1 END label_priority FROM skill_alias a JOIN v_skill_resolution r ON r.source_skill_id=a.skill_id JOIN skill s ON s.skill_id=r.resolved_skill_id WHERE a.normalized_label=? AND a.alias_type<>\'hidden_label\'',(norm(label),))
        if rows:
            priority=max(r['label_priority'] for r in rows)
            rows=list({r['skill_id']:r for r in rows if r['label_priority']==priority}.values())
        if len(rows)!=1:return {'input':item,'status':'unknown_label' if not rows else 'ambiguous_label','skill_id':None,'candidates':rows}
        r=rows[0]
        if r['matching_policy']=='CONTEXT_REQUIRED':return {'input':item,'status':'context_required','skill_id':None,'candidates':rows}
        return {'input':item,'status':'resolved_label','skill_id':r['skill_id'],'label':r['preferred_label'],'kind':r['kind']}
    @staticmethod
    def _csv_bool(value, default=True):
        if value is None or value == '':
            return default
        return str(value).strip().casefold() in {'1', 'true', 'yes', 'y'}

    def _load_candidate_title_index(self):
        """Load the reviewed v3 title candidate sets once per KB instance."""
        if self._candidate_title_index is not None:
            return self._candidate_title_index
        index = collections.defaultdict(list)
        if CANDIDATE_TITLE_SETS_CSV.exists():
            with CANDIDATE_TITLE_SETS_CSV.open(encoding='utf-8-sig', newline='') as handle:
                for raw in csv.DictReader(handle):
                    title = str(raw.get('title') or '').strip()
                    normalized = title_norm(title)
                    if not normalized:
                        continue
                    try:
                        paths = json.loads(raw.get('occupation_paths_json') or '[]')
                    except (TypeError, ValueError, json.JSONDecodeError):
                        paths = []
                    if not isinstance(paths, list):
                        paths = []
                    if not paths and raw.get('leaf_id'):
                        paths = [{}]
                    for rank, path in enumerate(paths, start=1):
                        path = path if isinstance(path, dict) else {}
                        item = dict(raw)
                        for field in (
                            'family_id', 'family', 'parent_id', 'parent', 'leaf_id',
                            'leaf', 'path_rank', 'path_role',
                        ):
                            if path.get(field) is not None:
                                item[field] = path[field]
                        item['title'] = title
                        item['path_rank'] = path.get('path_rank', rank)
                        item['path_role'] = path.get(
                            'path_role',
                            path.get('role', 'alternate_candidate' if rank > 1 else 'primary_candidate'),
                        )
                        item['candidate_only'] = self._csv_bool(
                            path.get('candidate_only'),
                            self._csv_bool(raw.get('direct_leaf_allowed'), True) is False,
                        )
                        item['direct_leaf_allowed'] = self._csv_bool(
                            path.get('direct_leaf_allowed'),
                            self._csv_bool(raw.get('direct_leaf_allowed'), True),
                        )
                        item['requires_description_validation'] = self._csv_bool(
                            path.get('requires_description_validation'),
                            self._csv_bool(raw.get('requires_description_validation'), False),
                        )
                        item['_source'] = 'reviewed_candidate_leaf_sets_v3'
                        index[normalized].append(item)
        for key, rows in index.items():
            rows.sort(key=lambda row: (
                int(row.get('path_rank') or 10**9),
                str(row.get('leaf_id') or ''),
            ))
            deduped = []
            seen = set()
            for row in rows:
                identity = (
                    row.get('family_id'),
                    row.get('parent_id'),
                    row.get('leaf_id'),
                )
                if identity in seen:
                    continue
                seen.add(identity)
                deduped.append(row)
            index[key] = deduped
        self._candidate_title_index = dict(index)
        return self._candidate_title_index

    def normalize_title(self,title):
        """Return the primary reviewed path plus any reviewed alternatives.

        ``title_classification`` stores the primary route while
        ``leaf_title_evidence`` may contain additional human-reviewed routes
        for genuinely ambiguous titles.  The first route remains the legacy
        single-path answer; ``candidate_paths`` is the lossless multi-path
        view used by the production extractor.
        """
        result=self.lookup_title(title)
        if not result['canonical_proposals']:
            replacement = self._replacement_title_proposals(title)
            if replacement:
                result['canonical_proposals'] = replacement
        candidates=[]; seen=set()
        for rank,row in enumerate(result['canonical_proposals'], start=1):
            key=(row.get('family_id'),row.get('parent_id'),row.get('leaf_id'))
            if not row.get('parent_id') or not row.get('leaf_id') or key in seen:
                continue
            seen.add(key)
            candidates.append({
                'title_id': row.get('title_id'), 'title': row.get('title') or title,
                'family_id': row.get('family_id'), 'family': row.get('family'),
                'parent_id': row.get('parent_id'), 'parent': row.get('parent'),
                'leaf_id': row.get('leaf_id'), 'leaf': row.get('leaf'),
                'score': 1.0, 'lexical_title_overlap': 1.0,
                'matched_title': row.get('title') or title, 'rank': rank,
                'source': row.get('_source', 'reviewed_kb_title'),
                'candidate_only': bool(row.get('candidate_only', False)),
                'direct_leaf_allowed': self._csv_bool(row.get('direct_leaf_allowed'), True),
                'requires_description_validation': self._csv_bool(
                    row.get('requires_description_validation'), False
                ),
                'mapping_mode': row.get('mapping_mode'),
                'path_role': row.get('path_role'),
            })
        if not candidates:
            if result.get('canonical_proposals'):
                row = result['canonical_proposals'][0]
                return {
                    'status': 'candidate_title_parent_only',
                    'input': title,
                    'normalized_title': row.get('title') or title,
                    'family_id': row.get('family_id'),
                    'family': row.get('family'),
                    'parent_id': row.get('parent_id'),
                    'parent': row.get('parent'),
                    'leaf_id': None,
                    'leaf': None,
                    'candidate_paths': [],
                    'taxonomy_version': result['taxonomy_version'],
                    'requires_description_validation': True,
                }
            return {'status':'no_match','input':title}
        row=candidates[0]
        family,parent,leaf=row['family_id'],row['parent_id'],row['leaf_id']
        candidate_set = any(
            item.get('_source') == 'reviewed_candidate_leaf_sets_v3'
            for item in result.get('canonical_proposals', [])
        )
        direct_allowed = all(
            self._csv_bool(item.get('direct_leaf_allowed'), True)
            for item in candidates
        )
        if candidate_set and not direct_allowed:
            return {
                'status': 'candidate_title_requires_description',
                'input': title,
                'normalized_title': row['title'],
                'family_id': family,
                'family': row['family'],
                'parent_id': parent,
                'parent': row['parent'],
                'leaf_id': None,
                'leaf': None,
                'candidate_paths': candidates,
                'taxonomy_version': result['taxonomy_version'],
                'direct_leaf_allowed': False,
                'requires_description_validation': True,
            }
        return {'status':'resolved_title' if len(candidates)==1 else 'resolved_title_with_alternatives',
         'input':title,'normalized_title':row['title'],
         'family_id':family,'family':row['family'],'parent_id':parent,'parent':row['parent'],
         'leaf_id':leaf,'leaf':row['leaf'],'candidate_paths':candidates,
         'taxonomy_version':result['taxonomy_version']}

    def _replacement_title_proposals(self, title):
        """Return live paths for an explicit generic-title replacement alias."""
        key = title_norm(title)
        # Seniority and level suffixes do not change the functional route;
        # strip only those bounded qualifiers, never arbitrary title words.
        key = re.sub(r'^(?:senior|sr\.?|junior|jr\.?|lead|principal|staff)\s+', '', key)
        key = re.sub(r'\s+(?:[1-9]|i{1,4}|v)$', '', key)
        targets = REPLACEMENT_TITLE_LEAVES.get(key, ())
        if not targets:
            return []
        rows = []
        for leaf_id in targets:
            found = self.rows('''SELECT l.leaf_id,l.label leaf,p.parent_id,p.label parent,
                                        f.family_id,f.label family,l.scope
                                 FROM leaf l JOIN parent p ON p.parent_id=l.parent_id
                                 JOIN family f ON f.family_id=p.family_id
                                 WHERE l.leaf_id=? AND l.scope='core' ''', (leaf_id,))
            if not found:
                continue
            row = found[0]
            row.update({
                'title_id': None,
                'title': title,
                'original_row_number': None,
                'scope': 'core',
                'resolution_status': 'source_supported_proposal',
                '_source': 'reviewed_replacement_alias',
            })
            rows.append(row)
        return rows
    def normalize_skills(self,items):
        rs=[self.normalize_skill(x) for x in items]
        return {'resolved_skill_ids':sorted({r['skill_id'] for r in rs if r.get('skill_id')}),'observations':rs,'unresolved':[r for r in rs if not r.get('skill_id')]}
    def lookup_title(self,title,include_conditional=False):
        rows=self.rows('SELECT * FROM v_title_paths WHERE title_id IN (SELECT title_id FROM input_title WHERE normalized_title=?)',(title_norm(title),))
        allowed={'core','conditional'} if include_conditional else {'core'}
        enabled=[r for r in rows if r['scope'] in allowed]
        candidate_rows = [
            dict(row)
            for row in self._load_candidate_title_index().get(title_norm(title), [])
            if row.get('scope') in allowed
        ]
        if candidate_rows:
            # v3 is the reviewed source of truth for title ambiguity.  Do not
            # merge the old single-path export back into these candidate sets.
            enabled = candidate_rows
        # A reviewed title may have more than one valid leaf path.  Keep the
        # primary classification from v_title_paths and append only live,
        # relationally valid alternatives recorded in leaf_title_evidence.
        evidence_rows=[]
        if not candidate_rows and self.db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='leaf_title_evidence'"
        ).fetchone():
            evidence_rows=self.rows('''
                SELECT i.title_id,i.original_row_number,i.title,i.scope,i.resolution_status,
                       f.family_id,f.label family,p.parent_id,p.label parent,
                       e.leaf_id,l.label leaf,e.method,e.review_status
                FROM input_title i
                JOIN leaf_title_evidence e USING(title_id)
                JOIN leaf l USING(leaf_id)
                JOIN parent p ON p.parent_id=l.parent_id
                JOIN family f ON f.family_id=p.family_id
                WHERE i.normalized_title=?
                ORDER BY CASE WHEN e.evidence_strength='reviewed_title_mapping' THEN 0 ELSE 1 END,
                         e.leaf_id''',(title_norm(title),))
        if not candidate_rows:
            existing={(r.get('family_id'),r.get('parent_id'),r.get('leaf_id')) for r in enabled}
            for row in evidence_rows:
                if row['scope'] in allowed and (row['family_id'],row['parent_id'],row['leaf_id']) not in existing:
                    enabled.append(row)
                    existing.add((row['family_id'],row['parent_id'],row['leaf_id']))
        source=self.rows('SELECT DISTINCT o.occupation_id,o.source_id,o.preferred_label,o.scope,c.family_id,c.parent_id,c.leaf_id,c.mapping_relation FROM occupation_alias a JOIN occupation o USING(occupation_id) LEFT JOIN occupation_classification c USING(occupation_id) WHERE a.normalized_label=? AND o.scope IN ('+','.join('?' for _ in allowed)+')',(title_norm(title),*sorted(allowed)))
        return {'title':title,'taxonomy_version':VERSION,'status':'proposal_available' if enabled else 'review_required' if rows else 'no_reviewed_title_match','canonical_proposals':enabled,'source_candidates':source,'reviewed_title_records':candidate_rows or rows,'candidate_source':'reviewed_titles_candidate_leaf_sets_v3' if candidate_rows else 'sqlite_reviewed_title_paths','interpretation':'Supply these candidates to the existing resolver; this is not a calibrated prediction.'}
    def skill_context(self,item):
        result=self.normalize_skill(item)
        if not result.get('skill_id'):return result
        id=result['skill_id']
        return {'normalization':result,'skill':self.rows('SELECT * FROM skill WHERE skill_id=?',(id,))[0],
         'functional_domains':self.rows('SELECT * FROM v_effective_skill_domains WHERE skill_id=?',(id,)),
         'official_domains':self.rows("SELECT d.domain_id,d.label,sd.relation,sd.method,sd.evidence_id FROM skill_domain sd JOIN domain d USING(domain_id) WHERE sd.skill_id=? AND sd.relation IN ('official_software_category','official_broader','collection_membership')",(id,)),
         'curation':self.rows('SELECT * FROM technology_curation WHERE skill_id=?',(id,)),
         'role_context':self.rows('SELECT * FROM v_skill_role_context WHERE skill_id=?',(id,)),
         'proposed_parent_context':self.rows('SELECT * FROM v_skill_parent_candidates WHERE skill_id=?',(id,)),
         'literal_task_mentions':self.rows('SELECT t.task_id,t.description,e.matched_text,e.review_status,e.evidence_id FROM skill_task_evidence e JOIN task t USING(task_id) WHERE e.skill_id=?',(id,))}
    def task_candidates(self,item,limit=12):
        result=self.normalize_skill(item)
        if not result.get('skill_id'):return result
        id=result['skill_id']
        query='''WITH roles AS (SELECT DISTINCT occupation_id FROM v_it_occupation_skills WHERE skill_id=?),
        candidates AS (SELECT DISTINCT t.task_id,t.description,t.evidence_id,ot.occupation_id FROM roles JOIN occupation_task ot USING(occupation_id) JOIN task t USING(task_id))
        SELECT c.task_id,c.description,group_concat(DISTINCT c.occupation_id) occupation_ids,c.evidence_id,
        (SELECT count(DISTINCT td.domain_id) FROM task_domain td JOIN v_effective_skill_domains sd USING(domain_id) WHERE td.task_id=c.task_id AND sd.skill_id=?) functional_overlap,
        EXISTS(SELECT 1 FROM skill_task_evidence st WHERE st.skill_id=? AND st.task_id=c.task_id) has_literal_mention
        FROM candidates c GROUP BY c.task_id ORDER BY has_literal_mention DESC,functional_overlap DESC,c.task_id LIMIT ?'''
        tasks=self.rows(query,(id,id,id,int(limit)))
        for t in tasks:t['relation']='literal_mention_needs_usage_review' if t['has_literal_mention'] else 'candidate_via_shared_occupation_not_direct_usage'
        fallback=[]
        if not tasks:
            fallback=self.rows('''SELECT DISTINCT t.task_id,t.description,ot.occupation_id,td.domain_id,t.evidence_id
            FROM v_effective_skill_domains sd JOIN domain_parent_candidate dp USING(domain_id)
            JOIN occupation_classification oc USING(parent_id) JOIN occupation o USING(occupation_id)
            JOIN occupation_task ot USING(occupation_id) JOIN task t USING(task_id)
            JOIN task_domain td ON td.task_id=t.task_id AND td.domain_id=sd.domain_id
            WHERE sd.skill_id=? AND o.scope='core' ORDER BY t.task_id LIMIT ?''',(id,int(limit)))
            for t in fallback:t['relation']='proposed_functional_domain_path_no_source_software_occupation_link'
        return {'skill_id':id,'tasks':tasks,'domain_fallback_candidates':fallback,'interpretation':'Functional overlap is a proposed retrieval signal. A source software/occupation/task path does not prove that the software performs this task. Domain fallbacks are weaker still and never become requirements.'}
    def rank_occupations(self,skills,title='',limit=10):
        """Untuned retrieval features. Ranking scores are not confidence probabilities.
        Only observed input skills are used; inferred source-profile skills are never
        appended to the candidate CV or job requirements.
        """
        parsed=self.normalize_skills(skills);ids=parsed['resolved_skill_ids'];hits=collections.defaultdict(set);evidence=collections.defaultdict(set)
        if ids:
            q='SELECT DISTINCT occupation_id,skill_id,evidence_id FROM v_it_occupation_skills WHERE skill_id IN ('+','.join('?' for _ in ids)+')'
            for r in self.rows(q,ids):hits[r['occupation_id']].add(r['skill_id']);evidence[r['occupation_id']].add(r['evidence_id'])
        exact={r['occupation_id'] for r in self.rows("SELECT DISTINCT o.occupation_id FROM occupation_alias a JOIN occupation o USING(occupation_id) WHERE a.normalized_label=? AND o.scope='core'",(title_norm(title),))} if title else set()
        pool=set(hits)|exact
        if title:
            tokens=[t for t in re.findall(r'[a-z0-9]+',title.casefold()) if t not in {'senior','junior','lead','principal','the','and','of','a','an'}]
            query=' OR '.join('"'+t+'"' for t in tokens)
            if query:
                for r in self.rows("SELECT x.occupation_id FROM occupation_search x JOIN occupation o ON o.occupation_id=x.occupation_id WHERE occupation_search MATCH ? AND o.scope='core' ORDER BY bm25(occupation_search,0,6,3,1) LIMIT 25",(query,)):pool.add(r['occupation_id'])
        n=self.db.execute("SELECT count(*) FROM occupation WHERE scope='core'").fetchone()[0]
        df=collections.Counter(s for ss in hits.values() for s in ss);idf={s:1+math.log((1+n)/(1+df[s])) for s in ids};den=sum(idf.values())
        ranked=[]
        for oid in pool:
            r=self.rows('SELECT o.occupation_id,o.source_id,o.preferred_label,c.family_id,c.parent_id,c.leaf_id,c.mapping_relation FROM occupation o LEFT JOIN occupation_classification c USING(occupation_id) WHERE o.occupation_id=?',(oid,))[0]
            coverage=sum(idf[s] for s in hits[oid])/den if den else 0
            r.update(matched_skill_ids=sorted(hits[oid]),observed_skill_profile_overlap=round(coverage,6),exact_title_alias=oid in exact,retrieval_score=round(coverage+(1 if oid in exact else 0),6),evidence_ids=sorted(evidence[oid]))
            ranked.append(r)
        ranked.sort(key=lambda r:(-r['retrieval_score'],r['occupation_id']))
        return {'normalization':parsed,'candidates':ranked[:int(limit)],'scoring':'Untuned baseline: IDF-weighted observed-skill overlap + 1 for an exact title alias. Cross-source profiles have different breadth; validate ranking on real English examples. Scores are not probabilities.'}
    def compare_profiles(self,candidate,job):
        """Compare actual extracted evidence only; unknown requirements never become gaps."""
        held=[x for x in candidate.get('skills',[]) if x.get('assertion')=='possessed']
        required=[x for x in job.get('skills',[]) if x.get('assertion')=='required']
        preferred=[x for x in job.get('skills',[]) if x.get('assertion')=='preferred']
        c=self.normalize_skills(held);req=self.normalize_skills(required);pref=self.normalize_skills(preferred)
        have=set(c['resolved_skill_ids']);need=set(req['resolved_skill_ids']);want=set(pref['resolved_skill_ids'])
        return {'required_match_ratio':len(have&need)/len(need) if need else None,
         'preferred_match_ratio':len(have&want)/len(want) if want else None,
         'matched_required_skill_ids':sorted(have&need),'unobserved_required_skill_ids':sorted(need-have),'matched_preferred_skill_ids':sorted(have&want),
         'unresolved_candidate_skills':c['unresolved'],'unresolved_required_skills':req['unresolved'],'unresolved_preferred_skills':pref['unresolved'],
         'required_input_count':len(required),'resolved_required_concept_count':len(need),
         'interpretation':'An unobserved required skill is absent from parsed CV evidence, not proof that the candidate lacks it. Ratios use only resolved explicitly required/preferred concepts; no source profile becomes a job requirement.'}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--db',default=str(DEFAULT_DB));sub=ap.add_subparsers(dest='command',required=True)
    p=sub.add_parser('title');p.add_argument('title');p.add_argument('--include-conditional',action='store_true')
    p=sub.add_parser('skill');p.add_argument('skill');p=sub.add_parser('tasks');p.add_argument('skill');p.add_argument('--limit',type=int,default=12)
    p=sub.add_parser('rank');p.add_argument('--skills',nargs='+',required=True);p.add_argument('--title',default='');p.add_argument('--limit',type=int,default=10)
    p=sub.add_parser('match');p.add_argument('candidate_json');p.add_argument('job_json')
    a=ap.parse_args();kb=ITKnowledgeBase(a.db)
    if a.command=='title':out=kb.lookup_title(a.title,a.include_conditional)
    elif a.command=='skill':out=kb.skill_context(a.skill)
    elif a.command=='tasks':out=kb.task_candidates(a.skill,a.limit)
    elif a.command=='rank':out=kb.rank_occupations(a.skills,a.title,a.limit)
    elif a.command=='match':out=kb.compare_profiles(json.loads(Path(a.candidate_json).read_text()),json.loads(Path(a.job_json).read_text()))
    print(json.dumps(out,indent=2,ensure_ascii=False));kb.close()
if __name__=='__main__':main()
