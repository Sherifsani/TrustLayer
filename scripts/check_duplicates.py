import sqlite3
from pprint import pprint

con = sqlite3.connect('dev.db')
con.row_factory = sqlite3.Row
cur = con.cursor()

print('Total users:', cur.execute('SELECT COUNT(*) FROM users').fetchone()[0])

for col in ('nin_hash','bvn_hash','email'):
    print('\nChecking duplicates in', col)
    rows = cur.execute(f"SELECT {col} as val, COUNT(*) as cnt FROM users GROUP BY {col} HAVING cnt>1 ORDER BY cnt DESC").fetchall()
    if not rows:
        print('  None')
        continue
    for r in rows:
        val = r['val']
        cnt = r['cnt']
        print(f'  {val!r} -> {cnt}')
        sample = cur.execute(f"SELECT id, user_handle, email, phone, bvn_hash, nin_hash FROM users WHERE {col}=?", (val,)).fetchall()
        for s in sample[:10]:
            pprint(dict(s))

con.close()
print('\nDone')
