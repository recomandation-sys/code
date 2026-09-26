"""Import a manually reviewed Nesta/external skill crosswalk into a WORKING COPY.
Usage: python src/import_reviewed_crosswalk.py --db working.sqlite --csv mappings.csv
No network and no fuzzy mapping. Conflicting or unreviewed mappings are rejected.
"""
import argparse,csv,sqlite3
def main():
    p=argparse.ArgumentParser();p.add_argument('--db',required=True);p.add_argument('--csv',required=True);a=p.parse_args()
    with open(a.csv,encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
    c=sqlite3.connect(a.db);c.execute('PRAGMA foreign_keys=ON')
    try:
        with c:
            for r in rows:
                required=['namespace','external_id','skill_id','relation','review_status']
                if any(not r.get(k) for k in required):raise ValueError('Missing required crosswalk value')
                if r['review_status']!='reviewed' or r['relation']not in {'exact','equivalent'}:raise ValueError('Only reviewed exact/equivalent mappings can be imported')
                if not c.execute('SELECT 1 FROM skill WHERE skill_id=?',(r['skill_id'],)).fetchone():raise ValueError('Unknown target skill ID: '+r['skill_id'])
                old=c.execute('SELECT skill_id,relation,review_status FROM external_skill_crosswalk WHERE namespace=? AND external_id=?',(r['namespace'],r['external_id'])).fetchall()
                if old and any(x!=(r['skill_id'],r['relation'],'reviewed') for x in old):raise ValueError('Conflicting crosswalk; review and version the change explicitly')
                c.execute('INSERT OR IGNORE INTO external_skill_crosswalk(namespace,external_id,external_label,skill_id,relation,review_status) VALUES (?,?,?,?,?,?)',(r['namespace'],r['external_id'],r.get('external_label'),r['skill_id'],r['relation'],'reviewed'))
        print('Imported reviewed mappings:',len(rows))
    finally:c.close()
if __name__=='__main__':main()
