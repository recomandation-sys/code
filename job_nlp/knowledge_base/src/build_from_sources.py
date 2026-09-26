"""Build the normalized IT knowledge base from the user's unpacked archive.
Usage: python src/build_from_sources.py --source-dir '/path/job taxonomy'
Python 3.10+; pandas/openpyxl are only needed for source ingestion.
"""
import argparse, collections, csv, gzip, hashlib, json, re, sqlite3, sys
from pathlib import Path
import pandas as pd
from policy import *

ROOT=Path(__file__).resolve().parents[1]
def hid(prefix,*values):return prefix+hashlib.sha256('\x1f'.join(map(str,values)).encode()).hexdigest()[:24]
def rows(path):
    with open(path,encoding='utf-8-sig',newline='') as f:
        yield from enumerate(csv.DictReader(f),start=2)
def excel(path,sheet,header=4):
    return [(i+header+2,{str(k):str(v) for k,v in r.items()}) for i,r in enumerate(pd.read_excel(path,sheet_name=sheet,header=header,dtype=str).fillna('').to_dict('records'))]
def number(x):
    try:return float(x) if x!='' else None
    except (TypeError,ValueError):return None

class Builder:
 def __init__(self,source_dir):
    self.R=Path(source_dir); self.E=next(self.R.glob('ESCO*'));self.O=self.R/'db_31_0_csv/db_31_0_csv'
    self.path=ROOT/'it_knowledge.sqlite';self.path.unlink(missing_ok=True)
    self.db=sqlite3.connect(self.path);self.db.execute('PRAGMA foreign_keys=ON');self.db.executescript((ROOT/'schema.sql').read_text())
    self.db.execute('PRAGMA journal_mode=OFF');self.db.execute('PRAGMA synchronous=OFF')
    self.seen=collections.defaultdict(set);self.files={};self.occ={};self.aliases=collections.defaultdict(list);self.skill_aliases=collections.defaultdict(set)
    self.skill_info={};self.native_software={};self.software_rows=[];self.cmr={};self.tasks={};self.descriptor_skills={}
 def put(self,table,record,unique=None):
    if unique is not None:
        if unique in self.seen[table]:return
        self.seen[table].add(unique)
    cols=list(record)
    try:self.db.execute(f'INSERT INTO {table} ({",".join(cols)}) VALUES ({",".join("?" for _ in cols)})',[record[c] for c in cols])
    except Exception as e:raise RuntimeError((table,record)) from e
 def evidence(self,path,locator,r):
    f=self.files[str(path)];key=hid('EV:',f,locator)
    self.put('evidence',dict(evidence_id=key,file_id=f,locator=str(locator),record_json=json.dumps(r,ensure_ascii=False,sort_keys=True)),key)
    return key
 def issue(self,typ,id,code,detail,severity='medium'):
    key=hid('REV:',typ,id,code)
    self.put('review_issue',dict(issue_id=key,entity_type=typ,entity_id=id,issue_type=code,severity=severity,detail=detail),key)
 def register(self):
    sources=[
     ('ONET','O*NET Database','31.0 (August 2026)','https://www.onetcenter.org/database.html','O*NET 31.0 Database, USDOL/ETA; CC BY 4.0; filtered and adapted. Not endorsed or tested by USDOL/ETA.'),
     ('ESCO','European Skills, Competences, Qualifications and Occupations','1.2.1','https://esco.ec.europa.eu/en/use-esco','European Commission ESCO; supplied English release.'),
     ('OSCA','Occupation Standard Classification for Australia','2024 v1.0; descriptions released 2025-07-28','https://www.abs.gov.au/statistics/classifications/osca-occupation-standard-classification-australia/2024-version-1-0','Australian Bureau of Statistics; supplied classification and correspondence files.'),
     ('ISCO','International Standard Classification of Occupations','ISCO-08; supplied English workbooks','https://ilostat.ilo.org/methods/concepts-and-definitions/classification-occupation/','International Labour Organization; supplied ISCO-08 definitions and index.'),
     ('TECH_V2','User IT technology runtime taxonomy','V2; supplied snapshot','', 'Original tech_id, labels, aliases, matching policy and provenance retained.'),
     ('USER_TITLES','User reviewed IT title list','supplied 1445-row snapshot','','Original row numbers and review status retained; IT scope separately audited.'),
     ('KB','Analyst-designed canonical IT knowledge model',VERSION,'','Proposed mappings and functional tags; not an official taxonomy crosswalk.')]
    for id,name,ver,url,attr in sources:self.put('source',dict(source_id=id,name=name,version=ver,url=url,attribution=attr))
    for p in sorted(self.R.rglob('*')):
        if not p.is_file():continue
        s='ONET' if p.is_relative_to(self.O) else 'ESCO' if p.is_relative_to(self.E) else 'OSCA' if p.name.startswith('OSCA') else 'ISCO' if p.name.startswith('ISCO') else 'TECH_V2' if p.name.startswith('IT_TECH') else 'USER_TITLES'
        fid=hid('FILE:',p.relative_to(self.R));self.files[str(p)]=fid
        self.put('source_file',dict(file_id=fid,source_id=s,relative_path=str(p.relative_to(self.R)),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),byte_size=p.stat().st_size,processing_note='Full file fingerprint; only relevant source records are ingested.'))
    for k,v in {'taxonomy_version':VERSION,'language':'en','schema_version':'1.0.0','snapshot_date':'2026-09-08','runtime_default_scope':'core','nesta_crosswalk_status':'not_supplied','classification_status':'analyst_proposed_not_human_validated','task_link_policy':'No direct software-task relationship is manufactured from a shared occupation.','legacy_taxonomy_status':'Not supplied; existing production mappings and H2 resolver are not changed.'}.items():self.put('metadata',dict(key=k,value=v))
    for f,(label,parents) in TREE.items():
        self.put('family',dict(family_id=f,label=label,definition='IT occupational family covering '+', '.join(p[0] for p in parents.values())+'.',taxonomy_version=VERSION))
        for p,(pl,pd,leaves) in parents.items():
            self.put('parent',dict(parent_id=p,family_id=f,label=pl,definition=pd))
            for l,ll in leaves.items():self.put('leaf',dict(leaf_id=l,parent_id=p,label=ll,definition=ll+' within '+pl+'. '+pd,scope='conditional' if l in CONDITIONAL_LEAVES else 'core'))
    for id,label in FUNCTIONAL_DOMAINS.items():self.put('domain',dict(domain_id='FUNCTION:'+id,source_id='KB',label=label,domain_type='functional_proposal',description='Analyst-defined functional grouping; not evidence of a job requirement.'))
    for d,ps in DOMAIN_PARENT_CANDIDATES.items():
        for p in ps:self.put('domain_parent_candidate',dict(domain_id='FUNCTION:'+d,parent_id=p,rule_id='domain_parent:'+d+':'+p))

 def load_occupations(self):
    # ISCO group definitions and index retain official ancestor structure.
    ip=self.R/'ISCO-08 EN Structure and definitions.xlsx'
    for n,r in excel(ip,'ISCO-08 EN Struct and defin',0):
        code=r['ISCO 08 Code'];key='ISCO:'+code;e=self.evidence(ip,f'ISCO-08 EN Struct and defin!row:{n}',r)
        self.put('occupation_group',dict(group_id=key,source_id='ISCO',native_id=code,label=r['Title EN'],level=r['Level'],description=r['Definition'],evidence_id=e),key)
    for n,r in excel(ip,'ISCO-08 EN Struct and defin',0):
        code=r['ISCO 08 Code']
        if len(code)>1 and 'ISCO:'+code[:-1] in self.seen['occupation_group']:
            self.put('occupation_group_edge',dict(child_id='ISCO:'+code,parent_id='ISCO:'+code[:-1],evidence_id=self.evidence(ip,f'ISCO-08 EN Struct and defin!row:{n}',r)),('ISCO:'+code,'ISCO:'+code[:-1]))
    # OSCA groups from descriptions, occupations are also addressable crosswalk nodes.
    p=self.R/'OSCA Category Descriptions.xlsx'
    for sheet,titlecol,desccol in [('Table 2','Occupation Title','Lead Statement'),('Table 1','Principal Title','Lead Statement')]:
        for n,r in excel(p,sheet):
            code=r['Identifier']
            if not re.fullmatch(r'\d{1,6}',code):continue
            key='OSCA_GROUP:'+code;e=self.evidence(p,f'{sheet}!row:{n}',r)
            self.put('occupation_group',dict(group_id=key,source_id='OSCA',native_id=code,label=r[titlecol],level='occupation' if len(code)==6 else str(len(code)),description=r[desccol],evidence_id=e),key)
    for (key,) in self.db.execute("SELECT group_id FROM occupation_group WHERE source_id='OSCA'").fetchall():
        code=key.split(':')[1];parent=code[:4] if len(code)==6 else code[:-1]
        if parent and 'OSCA_GROUP:'+parent in self.seen['occupation_group']:self.put('occupation_group_edge',dict(child_id=key,parent_id='OSCA_GROUP:'+parent,evidence_id=self.db.execute('SELECT evidence_id FROM occupation_group WHERE group_id=?',(key,)).fetchone()[0]),(key,parent))
    p=self.O/'occupation_data.csv'
    for n,r in rows(p):
        self.add_occ('ONET',r['O*NET-SOC Code'],r['Title'],r['Description'],None,r,p,n)
    p=self.E/'occupations_en.csv'
    for n,r in sorted(rows(p),key=lambda nr:nr[1]['modifiedDate'],reverse=True):
        gid='ISCO:'+r['iscoGroup'];gid=gid if gid in self.seen['occupation_group'] else None
        self.add_occ('ESCO',r['conceptUri'],r['preferredLabel'],r['description'],gid,r,p,n)
    p=self.R/'OSCA Category Descriptions.xlsx'
    for n,r in excel(p,'Table 1'):
        if re.fullmatch(r'\d{6}',r['Identifier']):self.add_occ('OSCA',r['Identifier'],r['Principal Title'],r['Lead Statement'],'OSCA_GROUP:'+r['Identifier'],r,p,f'Table 1!row:{n}')
    # Keep the full source concept registry for audit, but only IT and conditional profiles are loaded.
    for id,o in self.occ.items():
        if o['scope']=='reference_only':continue
        c=classify_occupation(o['preferred_label'])
        if c:
            self.put('occupation_classification',dict(occupation_id=id,**{k:c[k] for k in ('family_id','parent_id','leaf_id')},mapping_relation='parent_only' if c['leaf_id'] is None else 'equivalent_proposal',method='versioned_label_policy',review_status='proposed',rule_id=c['rule_id']))
        else:self.issue('occupation',id,'canonical_mapping_missing','IT source concept retained with full source profile; no sufficiently specific canonical label mapping.')
    # ESCO broader relations include nested occupation concepts as well as ISCO groups.
    for id,o in self.occ.items():
        if o['source_id']=='ESCO':
            self.put('occupation_group',dict(group_id=id,source_id='ESCO',native_id=o['native_id'],label=o['preferred_label'],level='occupation',description=o['description'],evidence_id=o['evidence_id']),id)
    p=self.E/'broaderRelationsOccPillar_en.csv'
    def gid(uri):return 'ISCO:'+uri.split('/C')[-1] if '/isco/C' in uri else 'ESCO:'+uri
    for n,r in rows(p):
        child,parent=gid(r['conceptUri']),gid(r['broaderUri'])
        if child in self.seen['occupation_group'] and parent in self.seen['occupation_group']:
            self.put('occupation_group_edge',dict(child_id=child,parent_id=parent,evidence_id=self.evidence(p,f'row:{n}',r)),(child,parent))
    p=self.R/'OSCA correspondence tables v2.xlsx'
    raw=pd.read_excel(p,sheet_name='Table 8',header=None,dtype=str).fillna('');last=None
    for i,rr in raw.iloc[5:].iterrows():
        vals=rr.tolist();code=vals[0]
        if re.fullmatch(r'\d{6}',code):last=code
        target=vals[2]
        if not last or not re.fullmatch(r'\d{4}',target):continue
        a,b='OSCA_GROUP:'+last,'ISCO:'+target
        if a in self.seen['occupation_group'] and b in self.seen['occupation_group']:
            note='partial' if str(vals[3]).strip()=='p' else 'unspecified correspondence; not asserted equivalent'
            self.put('source_crosswalk',dict(from_group_id=a,to_group_id=b,relationship_note=note,evidence_id=self.evidence(p,f'Table 8!row:{i+1}',{'cells':vals})),(a,b))

 def add_occ(self,s,native,label,desc,group,raw,path,row):
    id=s+':'+native;scope,reason=scope_for(s,native,label,raw);e=self.evidence(path,str(row) if isinstance(row,str) else f'row:{row}',raw)
    if id in self.occ:
        previous=self.occ[id]
        same=all(previous[k]==v for k,v in [('preferred_label',label),('description',desc),('group_id',group)])
        self.issue('occupation',id,'duplicate_source_concept','Repeated source concept URI/code; most recently modified definition retained, with all source rows recorded during ingestion. Same label/description/group: '+str(same),'low' if same else 'high')
        self.add_alias(id,label,'preferred',e)
        if s=='ESCO':
            for field in ('altLabels','hiddenLabels'):
                for a in raw[field].split('\n'):
                    if a:self.add_alias(id,a,field,e)
        return
    record=dict(occupation_id=id,source_id=s,native_id=native,preferred_label=label,description=desc,group_id=group,scope=scope,scope_reason=reason,evidence_id=e)
    self.put('occupation',record);self.occ[id]={**record,'raw':raw};self.add_alias(id,label,'preferred',e)
    if s=='ESCO':
        for field in ('altLabels','hiddenLabels'):
            for a in raw[field].split('\n'):
                if a:self.add_alias(id,a,field,e)
 def add_alias(self,id,label,kind,e):
    if not label:return
    key=hid('OA:',id,label,kind);self.put('occupation_alias',dict(alias_id=key,occupation_id=id,label=label,normalized_label=title_norm(label),alias_type=kind,evidence_id=e),key)
    self.aliases[title_norm(label)].append((id,key))

 def load_titles(self):
    for fn,col in [('job_titles.csv','Job Title'),('sample_of_reported_titles.csv','Reported Job Title')]:
        p=self.O/fn
        for n,r in rows(p):
            id='ONET:'+r['O*NET-SOC Code']
            if id not in self.occ:continue
            e=self.evidence(p,f'row:{n}',r);self.add_alias(id,r[col],fn,e)
            if 'Short Title'in r:self.add_alias(id,r['Short Title'],'short_title',e)
    p=self.R/'OSCA index of principal titles alternative titles and specialisations.xlsx'
    for n,r in excel(p,'Table 1'):
        id='OSCA:'+r['Identifier']
        if id in self.occ:self.add_alias(id,r['Description'],r['Category'],self.evidence(p,f'Table 1!row:{n}',r))
    p=self.R/'jobs_review_final_it_only_semantic_deduplicated_final.csv'
    for n,r in rows(p):
        title=r['job_title'];id='TITLE:'+r['row_number'];normalized=title_norm(title);matches=list(set(self.aliases.get(normalized,[])));method='normalized_exact'
        if not matches and '('in title:
            head=title_norm(title.split('(')[0]);matches=list(set(self.aliases.get(head,[])));method='parenthetical_head_candidate'
        core={o for o,a in matches if self.occ[o]['scope']=='core'};cond={o for o,a in matches if self.occ[o]['scope']=='conditional'};other={o for o,a in matches if self.occ[o]['scope']=='reference_only'}
        c=classify(title);scope='review';status='unresolved'
        preferred_core={o for o in core if title_norm(self.occ[o]['preferred_label'])==normalized}
        preferred_other={o for o in other if title_norm(self.occ[o]['preferred_label'])==normalized}
        preferred=[classify_occupation(self.occ[o]['preferred_label']) for o in core|cond if title_norm(self.occ[o]['preferred_label'])==normalized]
        preferred=[x for x in preferred if x]
        if preferred and len({x['parent_id'] for x in preferred})==1:
            c={**preferred[0]}
            if len({x['leaf_id'] for x in preferred})>1:c['leaf_id']=None
            c['rule_id']='preferred_source_consensus:'+c['parent_id']
        if EXCLUDE_TITLE.search(title):scope,status='excluded','outside_it_scope'
        elif CERT_TITLE.search(title):scope,status='review','credential_not_occupation'
        elif CONDITIONAL_TITLE.search(title) or (c and c['leaf_id']in CONDITIONAL_LEAVES):scope,status='conditional','needs_it_duties'
        elif preferred_core and not preferred_other:scope,status='core','preferred_source_supported_proposal'
        elif core and not other:scope,status='core','source_supported_proposal'
        elif c and c['priority']>=90 and (not matches or core):scope,status=('review','source_scope_conflict') if other else ('core','label_policy_proposal')
        elif cond and not core:scope,status='conditional','needs_it_duties'
        elif other and not core:scope,status='review','non_it_source_collision'
        if not c and core:
            cs=[classify_occupation(self.occ[o]['preferred_label']) for o in core];cs=[x for x in cs if x]
            parents={x['parent_id'] for x in cs}
            if len(parents)==1:
                c={**cs[0],'leaf_id':None,'rule_id':'source_parent_consensus','priority':0}
        if c and c['leaf_id'] is None and scope=='core':status='parent_only_proposal'
        self.put('input_title',dict(title_id=id,original_row_number=int(r['row_number']),title=title,normalized_title=normalized,provided_it_label=r['it_label'],provided_review_status=r['review_status'],scope=scope,resolution_status=status,evidence_id=self.evidence(p,f'row:{n}',r)))
        for oid,aid in matches:self.put('title_source_match',dict(title_id=id,alias_id=aid,match_method=method),(id,aid))
        if c and scope!='excluded' and not CERT_TITLE.search(title):self.put('title_classification',dict(title_id=id,**{k:c[k] for k in ('family_id','parent_id','leaf_id')},method='source_parent_consensus' if c['rule_id']=='source_parent_consensus' else 'versioned_label_policy',rule_id=c['rule_id'],review_status='proposed'))
        if scope in ('review','excluded','conditional'):self.issue('input_title',id,status,'Title: '+title+'. Source concepts: '+', '.join(sorted(core|cond|other)),'high' if scope=='excluded' or status=='source_scope_conflict' else 'medium')
        if not matches:self.issue('input_title',id,'no_source_title_match','No exact preferred/alternate title correspondence in supplied ESCO, O*NET or OSCA; any classification is an analyst proposal.')
        if len(core)>1:
            parents={self.db.execute('SELECT parent_id FROM occupation_classification WHERE occupation_id=?',(o,)).fetchone()[0] for o in core if self.db.execute('SELECT parent_id FROM occupation_classification WHERE occupation_id=?',(o,)).fetchone()}
            if len(parents)>1:self.issue('input_title',id,'multiple_source_parents','Competing source parents: '+', '.join(sorted(parents)))

 def add_skill(self,id,s,native,label,kind,desc,e,policy='SOURCE_ONLY',category=None,aliases=()):
    if id in self.skill_info:return
    rec=dict(skill_id=id,source_id=s,native_id=native,preferred_label=label,normalized_label=norm(label),kind=kind,description=desc,matching_policy=policy,provided_category=category,evidence_id=e)
    self.put('skill',rec);self.skill_info[id]=rec
    for label2,typ in [(label,'preferred')]+[(a if isinstance(a,tuple) else (a,'provided_alias')) for a in aliases if a]:
        if not label2:continue
        aid=hid('SA:',id,label2,typ);self.put('skill_alias',dict(alias_id=aid,skill_id=id,label=label2,normalized_label=norm(label2),alias_type=typ,evidence_id=e),aid)
        if s=='TECH_V2':self.skill_aliases[norm(label2)].add(id)
 def sd(self,s,d,rel,method,status,e=None):
    self.put('skill_domain',dict(skill_id=s,domain_id=d,relation=rel,method=method,review_status=status,evidence_id=e),(s,d,rel))

 def load_skills(self):
    p=self.R/'IT_TECH_TAXONOMY_V2_RUNTIME.csv'
    for n,r in rows(p):
        e=self.evidence(p,f'row:{n}',r);id=r['tech_id']
        self.add_skill(id,'TECH_V2',id,r['canonical_name'],'technology','',e,r['matching_policy'],r['category'],r['aliases'].split('|'))
        d='SUPPLIED_CATEGORY:'+r['category'];self.put('domain',dict(domain_id=d,source_id='TECH_V2',label=r['category'],domain_type='provided_technology_category',description='Original user category, retained without certifying semantic accuracy.'),d)
        self.sd(id,d,'provided_category','input_taxonomy','provided_unverified',e)
        for fun in CATEGORY_DOMAINS.get(r['category'],[]):self.sd(id,'FUNCTION:'+fun,'proposed_functional_domain','provided_category_policy','proposed',e)
        if r['category']=='OTHER_IT_TECH' and 'GITHUB_LINGUIST' in r['sources'].split('|'):
            self.sd(id,'FUNCTION:SOFTWARE_BUILD','proposed_functional_domain','provided_linguist_code_artifact_provenance','proposed',e)
    # Primary-documentation curation corrects high-impact supplied category errors and
    # joins known duplicate product IDs while preserving all original IDs and aliases.
    cp=ROOT/'config/technology_enrichment.json';cf=hid('FILE:','generated/config/technology_enrichment.json');self.files[str(cp)]=cf
    self.put('source_file',dict(file_id=cf,source_id='KB',relative_path='generated/config/technology_enrichment.json',sha256=hashlib.sha256(cp.read_bytes()).hexdigest(),byte_size=cp.stat().st_size,processing_note='Analyst curation with primary-documentation URLs, accessed 2026-09-08.'))
    by_name={norm(v['preferred_label']):id for id,v in self.skill_info.items()};redirect={}
    for product in json.loads(cp.read_text())['products']:
        ids=[by_name[norm(name)] for name in product['names'] if norm(name)in by_name]
        if not ids:continue
        representative=ids[0];e=self.evidence(cp,'product:'+product['names'][0],product)
        for id in ids:
            self.put('technology_curation',dict(skill_id=id,recommended_category=product['category'],capability=product['capability'],reason='Product purpose and identity checked against primary documentation; original supplied category retained.',source_url=product['url'],status='analyst_curated',evidence_id=e))
            for fun in product['domains']:self.sd(id,'FUNCTION:'+fun,'proposed_functional_domain','documented_technology_curation','analyst_curated',e)
            if id!=representative:
                redirect[id]=representative
                self.put('skill_crosswalk',dict(from_skill_id=id,to_skill_id=representative,relation='curated_equivalent',method='same_product_primary_documentation',review_status='reviewed',matched_label=self.skill_info[id]['preferred_label'],evidence_id=e),(id,representative))
        for id in ids:
            if self.skill_info[id]['provided_category']!=product['category']:
                self.issue('skill',id,'supplied_category_corrected','Supplied '+str(self.skill_info[id]['provided_category'])+'; documented recommendation '+product['category']+'. Use technology_curation and v_effective_skill_domains.','high')
    for label,ids in self.skill_aliases.items():self.skill_aliases[label]={redirect.get(id,id) for id in ids}
    for name,ids in self.skill_aliases.items():
        if len(ids)>1:
            for id in ids:self.issue('skill',id,'alias_collision','Shared normalized label '+repr(name)+' maps to '+', '.join(sorted(ids)))
    # All O*NET software examples remain namespaced, so unresolved products never enter TECH V2 silently.
    p=self.O/'software_skills.csv'
    for n,r in rows(p):
        label=r['Workplace Example'];id=hid('ONET_SW:',norm(label));self.native_software[norm(label)]=id
        matches=self.skill_aliases.get(norm(label),set());oid='ONET:'+r['O*NET-SOC Code'];scope=self.occ[oid]['scope']
        if not matches and scope=='reference_only':continue
        e=self.evidence(p,f'row:{n}',r)
        self.add_skill(id,'ONET',norm(label),label,'software_example','O*NET workplace software example.',e)
        cat='ONET_CATEGORY:'+r['Element ID'];self.put('domain',dict(domain_id=cat,source_id='ONET',label=r['Element Name'],domain_type='official_software_category',description='O*NET Content Model/UNSPSC software category.',evidence_id=e),cat)
        self.sd(id,cat,'official_software_category','source_asserted','source_asserted',e)
        if len(matches)==1:
            target=next(iter(matches));self.put('skill_crosswalk',dict(from_skill_id=id,to_skill_id=target,relation='exact_label',method='unique_casefolded_label_or_provided_alias',review_status='deterministic_exact',matched_label=label,evidence_id=e),(id,target))
            self.sd(target,cat,'official_software_category','exact_label_bridge','deterministic_exact',e)
            for fun,pat in DOMAIN_PATTERNS.items():
                if re.search(pat,r['Element Name'],re.I):self.sd(target,'FUNCTION:'+fun,'proposed_functional_domain','onet_category_label_policy','proposed',e)
        elif len(matches)>1:
            self.issue('skill',id,'ambiguous_tech_crosswalk','O*NET software label matches multiple TECH V2 IDs; no equivalence accepted: '+', '.join(sorted(matches)))
        if scope!='reference_only':self.put('occupation_skill',dict(occupation_id=oid,skill_id=id,relation='software_used',hot_technology=int(r['Hot Technology']=='Y'),in_demand=int(r['In Demand']=='Y'),evidence_id=e),(oid,id,'software_used'))
    # Import ESCO competencies attached to IT occupations, and their existing relation neighborhood.
    ep=self.E/'occupationSkillRelations_en.csv';relations=[];selected=set()
    for n,r in rows(ep):
        oid='ESCO:'+r['occupationUri']
        if oid in self.occ and self.occ[oid]['scope']!='reference_only':relations.append((n,r));selected.add(r['skillUri'])
    skrel=list(rows(self.E/'skillSkillRelations_en.csv'))
    # One-hop related concepts support exact crosswalks and graph context without all-sector occupation profiles.
    seed=set(selected)
    for n,r in skrel:
        if r['originalSkillUri']in seed:selected.add(r['relatedSkillUri'])
    digital=set(r['conceptUri'] for n,r in rows(self.E/'digitalSkillsCollection_en.csv'))
    selected.update(digital)
    p=self.E/'skills_en.csv'
    for n,r in rows(p):
        if r['conceptUri']not in selected:continue
        id='ESCO_SKILL:'+r['conceptUri'];e=self.evidence(p,f'row:{n}',r)
        self.add_skill(id,'ESCO',r['conceptUri'],r['preferredLabel'],'knowledge' if r['skillType']=='knowledge' else 'professional_skill',r['description'],e,aliases=[(a,'alt_label') for a in r['altLabels'].split('\n')]+[(a,'hidden_label') for a in r['hiddenLabels'].split('\n')])
        candidates=set()
        for label in [r['preferredLabel']]+r['altLabels'].split('\n'):candidates.update(self.skill_aliases.get(norm(label),set()))
        # ESCO action skills such as "use Python" are not equivalent to the technology itself.
        if len(candidates)==1:
            t=next(iter(candidates));self.put('skill_crosswalk',dict(from_skill_id=id,to_skill_id=t,relation='exact_label',method='unique_source_label_or_alias',review_status='deterministic_exact',matched_label=r['preferredLabel'],evidence_id=e),(id,t))
        elif len(candidates)>1:self.issue('skill',id,'ambiguous_tech_crosswalk','ESCO label/alias matches multiple technologies; no equivalence accepted.')
    for n,r in relations:
        id='ESCO_SKILL:'+r['skillUri']
        if id in self.skill_info:self.put('occupation_skill',dict(occupation_id='ESCO:'+r['occupationUri'],skill_id=id,relation=r['relationType'],evidence_id=self.evidence(ep,f'row:{n}',r)),('ESCO:'+r['occupationUri'],id,r['relationType']))
    p=self.E/'skillGroups_en.csv'
    for n,r in rows(p):
        id='ESCO_DOMAIN:'+r['conceptUri'];self.put('domain',dict(domain_id=id,source_id='ESCO',label=r['preferredLabel'],domain_type='official_skill_group',description=r['description'],evidence_id=self.evidence(p,f'row:{n}',r)),id)
    # Some broader relations target skills rather than skill groups: preserve these as distinct domains.
    p=self.E/'broaderRelationsSkillPillar_en.csv';br=list(rows(p))
    needed={r['broaderUri'] for n,r in br if 'ESCO_SKILL:'+r['conceptUri'] in self.skill_info or 'ESCO_DOMAIN:'+r['conceptUri']in self.seen['domain']}
    change=True
    while change:
        old=len(needed);needed.update(r['broaderUri'] for n,r in br if r['conceptUri']in needed);change=len(needed)>old
    for n,r in br:
        for uri,label in [(r['conceptUri'],r['conceptLabel']),(r['broaderUri'],r['broaderLabel'])]:
            if uri in needed:
                id='ESCO_DOMAIN:'+uri;self.put('domain',dict(domain_id=id,source_id='ESCO',label=label,domain_type='official_skill_broader_concept',description='',evidence_id=self.evidence(p,f'row:{n}',r)),id)
    for n,r in br:
        child='ESCO_SKILL:'+r['conceptUri'];parent='ESCO_DOMAIN:'+r['broaderUri'];domchild='ESCO_DOMAIN:'+r['conceptUri']
        if parent not in self.seen['domain']:continue
        e=None
        if child in self.skill_info:e=self.evidence(p,f'row:{n}',r);self.sd(child,parent,'official_broader','source_asserted','source_asserted',e)
        if domchild in self.seen['domain'] and domchild!=parent:self.put('domain_edge',dict(child_id=domchild,parent_id=parent,evidence_id=e or self.evidence(p,f'row:{n}',r)),(domchild,parent))
    p=self.E/'skillSkillRelations_en.csv'
    for n,r in skrel:
        a,b='ESCO_SKILL:'+r['originalSkillUri'],'ESCO_SKILL:'+r['relatedSkillUri']
        if a in self.skill_info and b in self.skill_info:self.put('skill_relation',dict(from_skill_id=a,to_skill_id=b,relation=r['relationType'],evidence_id=self.evidence(p,f'row:{n}',r)),(a,b,r['relationType']))
    for fn in ['digitalSkillsCollection_en.csv','digCompSkillsCollection_en.csv','transversalSkillsCollection_en.csv','languageSkillsCollection_en.csv','researchSkillsCollection_en.csv']:
        p=self.E/fn;d='ESCO_COLLECTION:'+fn
        self.put('domain',dict(domain_id=d,source_id='ESCO',label=fn.removesuffix('_en.csv'),domain_type='official_skill_collection',description='ESCO collection membership.'),d)
        for n,r in rows(p):
            s='ESCO_SKILL:'+r['conceptUri']
            if s in self.skill_info:self.sd(s,d,'collection_membership','source_asserted','source_asserted',self.evidence(p,f'row:{n}',r))

 def load_ratings(self):
    # O*NET content-model descriptors are kept separate from skills to avoid turning traits into skills.
    p=self.O/'content_model_reference.csv'
    for n,r in rows(p):
        self.cmr[r['Element ID']]=(r,self.evidence(p,f'row:{n}',r))
    for fn,kind,relation in [('essential_skills.csv','professional_skill','rated_essential_skill'),('transferable_skills.csv','professional_skill','rated_transferable_skill'),('knowledge.csv','knowledge','rated_knowledge')]:
        for n,r in rows(self.O/fn):
            native=r['Element ID'];id='ONET_SKILL:'+native
            if id not in self.skill_info:
                cr,e=self.cmr[native];self.add_skill(id,'ONET',native,cr['Element Name'],kind,cr['Description'],e)
                self.descriptor_skills[native]=id
        # Full rows loaded below, once.
    p=self.O/'content_model_reference.csv'
    for native,(r,e) in self.cmr.items():self.put('descriptor',dict(descriptor_id='ONET_DESC:'+native,source_id='ONET',native_id=native,label=r['Element Name'],description=r['Description'],skill_id=self.descriptor_skills.get(native),evidence_id=e),'ONET_DESC:'+native)
    for native,sid in self.descriptor_skills.items():
        child=None;ancestor=native.rsplit('.',1)[0]
        while ancestor and ancestor in self.cmr:
            r,e=self.cmr[ancestor];d='ONET_DOMAIN:'+ancestor
            self.put('domain',dict(domain_id=d,source_id='ONET',label=r['Element Name'],domain_type='official_content_model_group',description=r['Description'],evidence_id=e),d)
            if child is None:self.sd(sid,d,'official_broader','source_asserted','source_asserted',self.skill_info[sid]['evidence_id'])
            else:self.put('domain_edge',dict(child_id=child,parent_id=d,evidence_id=e),(child,d))
            child=d;ancestor=ancestor.rsplit('.',1)[0] if '.'in ancestor else ''
    for (did,) in self.db.execute("SELECT domain_id FROM domain WHERE domain_type='official_software_category'").fetchall():
        native=did.split(':',1)[1]
        if native in self.cmr:self.db.execute('UPDATE domain SET description=? WHERE domain_id=?',(self.cmr[native][0]['Description'],did))
        child=did;ancestor=native.rsplit('.',1)[0] if '.'in native else ''
        while ancestor and ancestor in self.cmr:
            r,e=self.cmr[ancestor];d='ONET_DOMAIN:'+ancestor
            self.put('domain',dict(domain_id=d,source_id='ONET',label=r['Element Name'],domain_type='official_content_model_group',description=r['Description'],evidence_id=e),d)
            self.put('domain_edge',dict(child_id=child,parent_id=d,evidence_id=e),(child,d))
            child=d;ancestor=ancestor.rsplit('.',1)[0] if '.'in ancestor else ''
    p=self.O/'scales_reference.csv'
    for n,r in rows(p):self.put('rating_scale',dict(scale_id=r['Scale ID'],label=r['Scale Name'],minimum=number(r['Minimum']),maximum=number(r['Maximum']),evidence_id=self.evidence(p,f'row:{n}',r)),r['Scale ID'])
    for fn in ['education_categories.csv','training_and_experience_categories.csv','work_context_categories.csv','task_categories.csv']:
        p=self.O/fn
        for n,r in rows(p):self.put('rating_category',dict(category_id=hid('CAT:',fn,n),category_domain=fn,element_id=r.get('Element ID'),scale_id=r['Scale ID'],category=r['Category'],description=r['Category Description'],evidence_id=self.evidence(p,f'row:{n}',r)))
    p=self.O/'level_scale_anchors.csv'
    for n,r in rows(p):
        if 'ONET_DESC:'+r['Element ID']in self.seen['descriptor']:self.put('scale_anchor',dict(anchor_id=hid('ANCHOR:',n),descriptor_id='ONET_DESC:'+r['Element ID'],scale_id=r['Scale ID'],value=number(r['Anchor Value']),description=r['Anchor Description'],evidence_id=self.evidence(p,f'row:{n}',r)))
    files=['essential_skills.csv','transferable_skills.csv','knowledge.csv','abilities.csv','work_styles.csv','work_activities.csv','work_context.csv','education.csv','training_and_experience.csv']
    for fn in files:
        p=self.O/fn
        for n,r in rows(p):
            oid='ONET:'+r['O*NET-SOC Code']
            if self.occ[oid]['scope']=='reference_only':continue
            desc='ONET_DESC:'+r['Element ID']
            if desc not in self.seen['descriptor']:raise ValueError(('descriptor missing',fn,desc))
            e=self.evidence(p,f'row:{n}',r)
            self.put('occupation_rating',dict(rating_id=hid('RATING:',fn,n),occupation_id=oid,descriptor_id=desc,dataset=fn.removesuffix('.csv'),scale_id=r['Scale ID'],category=r.get('Category'),value=number(r['Data Value']),sample_n=number(r.get('N')),standard_error=number(r.get('Standard Error')),ci_low=number(r.get('Lower CI Bound')),ci_high=number(r.get('Upper CI Bound')),recommend_suppress=r.get('Recommend Suppress'),not_relevant=r.get('Not Relevant'),date=r.get('Date'),domain_source=r.get('Domain Source'),evidence_id=e))
            if fn in ['essential_skills.csv','transferable_skills.csv','knowledge.csv']:
                relation={'essential_skills.csv':'rated_essential_skill','transferable_skills.csv':'rated_transferable_skill','knowledge.csv':'rated_knowledge'}[fn]
                self.put('occupation_skill',dict(occupation_id=oid,skill_id='ONET_SKILL:'+r['Element ID'],relation=relation,evidence_id=e),(oid,'ONET_SKILL:'+r['Element ID'],relation))
    for fn in ['job_zones.csv','occupation_level_metadata.csv','emerging_tasks.csv','career_interest_types.csv','specific_interest_areas.csv']:
        p=self.O/fn
        for n,r in rows(p):
            oid='ONET:'+r['O*NET-SOC Code']
            if oid in self.occ and self.occ[oid]['scope']!='reference_only':self.put('occupation_metadata',dict(metadata_id=hid('OM:',fn,n),occupation_id=oid,dataset=fn,record_json=json.dumps(r),evidence_id=self.evidence(p,f'row:{n}',r)))
    p=self.O/'job_zone_reference.csv'
    for n,r in rows(p):self.put('job_zone',dict(job_zone=int(r['Job Zone']),label=r['Name'],experience=r['Experience'],education=r['Education'],job_training=r['Job Training'],examples=r['Examples'],svp_range=r['SVP Range'],evidence_id=self.evidence(p,f'row:{n}',r)))
    p=self.O/'job_zones.csv'
    for n,r in rows(p):
        oid='ONET:'+r['O*NET-SOC Code']
        if oid in self.occ and self.occ[oid]['scope']!='reference_only':self.put('occupation_job_zone',dict(occupation_id=oid,job_zone=int(r['Job Zone']),date=r['Date'],domain_source=r['Domain Source'],evidence_id=self.evidence(p,f'row:{n}',r)))
    p=self.O/'related_occupations.csv'
    for n,r in rows(p):
        a,b='ONET:'+r['O*NET-SOC Code'],'ONET:'+r['Related O*NET-SOC Code']
        if a in self.occ and b in self.occ and self.occ[a]['scope']!='reference_only' and self.occ[b]['scope']!='reference_only':self.put('related_occupation',dict(occupation_id=a,related_occupation_id=b,tier=r['Relatedness Tier'],rank=int(r['Index']),evidence_id=self.evidence(p,f'row:{n}',r)),(a,b))

 def load_tasks(self):
    p=self.O/'task_statements.csv'
    for n,r in rows(p):
        oid='ONET:'+r['O*NET-SOC Code']
        if self.occ[oid]['scope']=='reference_only':continue
        id='ONET_TASK:'+r['Task ID'];e=self.evidence(p,f'row:{n}',r)
        self.add_task(id,'ONET',r['Task ID'],r['Task'],e)
        self.put('occupation_task',dict(occupation_id=oid,task_id=id,task_type=r['Task Type'],date=r['Date'],domain_source=r['Domain Source'],evidence_id=e),(oid,id))
    for oid,o in self.occ.items():
        if o['source_id']!='OSCA' or o['scope']=='reference_only':continue
        for i,t in enumerate(o['raw']['Main Tasks'].split(';'),1):
            if not t.strip():continue
            id='OSCA_TASK:'+o['native_id']+':'+str(i)
            self.add_task(id,'OSCA',o['native_id']+':'+str(i),t.strip(),o['evidence_id'])
            self.put('occupation_task',dict(occupation_id=oid,task_id=id,task_type='main',evidence_id=o['evidence_id']),(oid,id))
    p=self.O/'task_ratings.csv'
    for n,r in rows(p):
        oid='ONET:'+r['O*NET-SOC Code'];id='ONET_TASK:'+r['Task ID']
        if (oid,id)not in self.seen['occupation_task']:continue
        self.put('task_rating',dict(rating_id=hid('TR:',n),occupation_id=oid,task_id=id,scale_id=r['Scale ID'],category=r['Category'],value=number(r['Data Value']),sample_n=number(r['N']),recommend_suppress=r['Recommend Suppress'],evidence_id=self.evidence(p,f'row:{n}',r)))
    p=self.O/'gwas_to_iwas_to_dwas.csv'
    for n,r in rows(p):
        e=self.evidence(p,f'row:{n}',r)
        for lev in ['GWA','IWA','DWA']:
            id='ONET_ACT:'+r[lev+' Element ID'];self.put('activity',dict(activity_id=id,source_id='ONET',native_id=r[lev+' Element ID'],label=r[lev+' Element Name'],level=lev,evidence_id=e),id)
        for a,b in [('DWA','IWA'),('IWA','GWA')]:
            c,pid='ONET_ACT:'+r[a+' Element ID'],'ONET_ACT:'+r[b+' Element ID'];self.put('activity_edge',dict(child_id=c,parent_id=pid,evidence_id=e),(c,pid))
    p=self.O/'tasks_to_dwas.csv'
    for n,r in rows(p):
        oid='ONET:'+r['O*NET-SOC Code'];t='ONET_TASK:'+r['Task ID'];a='ONET_ACT:'+r['DWA Element ID']
        if (oid,t)in self.seen['occupation_task'] and a in self.seen['activity']:self.put('task_activity',dict(occupation_id=oid,task_id=t,activity_id=a,evidence_id=self.evidence(p,f'row:{n}',r)),(oid,t,a))
    for fn,prefix in [('essential_skills_to_work_activities.csv','Essential Skills'),('transferable_skills_to_work_activities.csv','Transferable Skills'),('abilities_to_work_activities.csv','Abilities'),('work_styles_to_work_activities.csv','Work Styles')]:
        p=self.O/fn
        for n,r in rows(p):
            d='ONET_DESC:'+r[prefix+' Element ID'];a='ONET_ACT:'+r['Work Activities Element ID']
            if d in self.seen['descriptor'] and a in self.seen['activity']:self.put('descriptor_activity',dict(descriptor_id=d,activity_id=a,relation='source_asserted_descriptor_gwa',evidence_id=self.evidence(p,f'row:{n}',r)),(d,a))
    for fn,prefix in [('essential_skills_to_work_context.csv','Essential Skills'),('transferable_skills_to_work_context.csv','Transferable Skills'),('abilities_to_work_context.csv','Abilities'),('work_styles_to_work_context.csv','Work Styles')]:
        p=self.O/fn
        for n,r in rows(p):
            a='ONET_DESC:'+r[prefix+' Element ID'];b='ONET_DESC:'+r['Work Context Element ID']
            if a in self.seen['descriptor'] and b in self.seen['descriptor']:self.put('descriptor_relation',dict(from_descriptor_id=a,to_descriptor_id=b,relation='source_asserted_work_context_relation',evidence_id=self.evidence(p,f'row:{n}',r)),(a,b,'source_asserted_work_context_relation'))
    # Literal task mentions are extracted as textual evidence, not certified software usage.
    # Common nouns found in the supplied SAFE lexicon are not reliable product mentions.
    ambiguous_task_words={'bucket','cartography','conduit','outlines','access','make','find','test','rest','word','excel','unity','shell','chef','puppet','flow','data','ramp','fleet','helm'}
    safe_aliases={a:next(iter(ids)) for a,ids in self.skill_aliases.items() if len(ids)==1 and a not in ambiguous_task_words and (len(a)>=4 or a in {'c++','c#','.net'}) and self.skill_info[next(iter(ids))]['matching_policy']=='SAFE'}
    token_index=collections.defaultdict(list)
    for a,id in safe_aliases.items():
        first=re.search(r'[\w]+',a)
        if first:token_index[first.group()].append((a,id,re.compile(r'(?<![\w+#.])'+re.escape(a)+r'(?![\w+#])',re.I)))
    for t,rec in self.tasks.items():
        txt=rec['description'];words=set(re.findall(r'[\w]+',txt.casefold()));checked=set()
        for w in words:
            for a,id,pat in token_index.get(w,[]):
                if (a,id)in checked:continue
                checked.add((a,id))
                for m in pat.finditer(txt):self.put('skill_task_evidence',dict(skill_id=id,task_id=t,relation='literal_mention',method='unique_SAFE_alias_token_boundary',matched_text=m.group(),start_char=m.start(),end_char=m.end(),review_status='literal_match_needs_usage_review',evidence_id=rec['evidence_id']),(id,t,m.start()))
        for fun,pat in DOMAIN_PATTERNS.items():
            if re.search(pat,txt,re.I):self.put('task_domain',dict(task_id=t,domain_id='FUNCTION:'+fun,rule_id='task_domain:'+fun,method='analyst_keyword_proposal',evidence_id=rec['evidence_id']),(t,fun))
 def add_task(self,id,s,native,text,e):
    rec=dict(task_id=id,source_id=s,native_id=native,description=text,evidence_id=e);self.put('task',rec,id);self.tasks[id]=rec

 def finish(self):
    # Do not ship unrelated all-sector occupation inventories. Retain only IT concepts and
    # non-IT concepts needed to explain a competing match against the user's reviewed titles.
    keep={r[0] for r in self.db.execute('SELECT DISTINCT a.occupation_id FROM title_source_match m JOIN occupation_alias a USING(alias_id)')}
    remove=[(id,) for id,o in self.occ.items() if o['scope']=='reference_only' and id not in keep]
    self.db.executemany('DELETE FROM occupation_alias WHERE occupation_id=?',remove)
    self.db.executemany('DELETE FROM occupation WHERE occupation_id=?',remove)
    # Every technology receives explicit coverage accounting; missing links are visible rather than guessed.
    for r in self.db.execute('SELECT skill_id,preferred_label,core_occupation_count,official_category_count,proposed_domain_count FROM v_technology_coverage').fetchall():
        id,label,oc,cat,dom=r
        if not oc:self.issue('skill',id,'no_core_occupation_link','No verified source software/skill linkage to a core IT occupation in this snapshot. Product retained for extraction; not proof of non-IT status.','low')
        if not dom:self.issue('skill',id,'functional_domain_unresolved','No supported functional-domain proposal for '+label+'. Original category remains available.','medium')
    self.issue('integration','NESTA','nesta_ids_not_supplied','No Nesta extraction output or namespace-to-canonical-ID mapping was supplied. external_skill_crosswalk is empty; use the included import adapter, not assumed ID equivalence.','high')
    self.issue('integration','LEGACY_TAXONOMY','legacy_ids_not_supplied','The previous production family/parent/leaf table was not in the archive. This is a separate proposed taxonomy version; populate legacy_taxonomy_crosswalk before production migration.','high')
    self.issue('integration','EVALUATION','gold_evaluation_not_supplied','No annotated English CV/job-offer gold set supplied. Structural validation does not estimate classification or recommendation accuracy.','high')
    self.db.commit()
    self.db.execute('CREATE VIRTUAL TABLE occupation_search USING fts5(occupation_id UNINDEXED, title, aliases, description, tokenize="unicode61")')
    self.db.execute("INSERT INTO occupation_search SELECT o.occupation_id,o.preferred_label,COALESCE(group_concat(a.label,' | '),''),o.description FROM occupation o LEFT JOIN occupation_alias a USING(occupation_id) WHERE o.scope IN ('core','conditional') GROUP BY o.occupation_id")
    self.db.execute('CREATE VIRTUAL TABLE task_search USING fts5(task_id UNINDEXED, description, tokenize="unicode61")')
    self.db.execute('INSERT INTO task_search SELECT task_id,description FROM task')
    self.db.execute('CREATE VIRTUAL TABLE skill_search USING fts5(skill_id UNINDEXED,label,aliases,description, tokenize="unicode61")')
    self.db.execute("INSERT INTO skill_search SELECT s.skill_id,s.preferred_label,COALESCE(group_concat(a.label,' | '),''),s.description FROM skill s LEFT JOIN skill_alias a USING(skill_id) GROUP BY s.skill_id")
    self.db.commit();self.db.execute('ANALYZE');self.db.execute('VACUUM')
    fk=self.db.execute('PRAGMA foreign_key_check').fetchall();integrity=self.db.execute('PRAGMA integrity_check').fetchone()[0]
    assert not fk and integrity=='ok',(fk,integrity)
    self.db.close()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source-dir',required=True);args=ap.parse_args();b=Builder(args.source_dir)
    for step in ['register','load_occupations','load_titles','load_skills','load_ratings','load_tasks','finish']:
        print(step,flush=True);getattr(b,step)()
    print('Built',b.path,flush=True)
if __name__=='__main__':main()
