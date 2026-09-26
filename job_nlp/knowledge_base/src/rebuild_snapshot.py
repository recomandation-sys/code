"""Rebuild the delivered database without pandas, Excel, internet or the original RAR.
Usage: python src/rebuild_snapshot.py --output /tmp/it_knowledge.sqlite
Only the standard library is required. The output must not already exist.
"""
import argparse,gzip,json,sqlite3,tempfile,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def rebuild(output):
    output=Path(output)
    if output.exists():raise FileExistsError('Output already exists: '+str(output))
    staging=tempfile.TemporaryDirectory(prefix='it_kb_build_')
    staged=Path(staging.name)/'knowledge.sqlite'
    c=sqlite3.connect(staged);c.execute('PRAGMA foreign_keys=ON');c.executescript((ROOT/'schema.sql').read_text())
    c.execute('BEGIN');c.execute('PRAGMA defer_foreign_keys=ON')
    sql={}
    with gzip.open(ROOT/'data/normalized_snapshot.jsonl.gz','rt',encoding='utf-8') as f:
        for line in f:
            item=json.loads(line);table=item['table'];r=item['row']
            key=(table,tuple(r))
            if key not in sql:sql[key]='INSERT INTO "'+table+'" ('+','.join('"'+x+'"' for x in r)+') VALUES ('+','.join('?' for _ in r)+')'
            c.execute(sql[key],list(r.values()))
    c.commit();c.executescript((ROOT/'search_indexes.sql').read_text());c.commit();c.execute('ANALYZE')
    assert not c.execute('PRAGMA foreign_key_check').fetchall()
    assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    c.close()
    # Stage random-access SQLite writes locally; publish a complete sequential file.
    try:
        with staged.open('rb') as src, output.open('xb') as dst:
            shutil.copyfileobj(src,dst,1024*1024)
    finally:
        staging.cleanup()
    return output
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();print(rebuild(a.output))
