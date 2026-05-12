import sqlite3
from pprint import pprint

con = sqlite3.connect('dev.db')
con.row_factory = sqlite3.Row
cur = con.cursor()

# find emails with duplicates
dups = cur.execute("SELECT email, COUNT(*) as c FROM users GROUP BY email HAVING c>1").fetchall()
if not dups:
    print('No duplicate emails found')
else:
    for d in dups:
        email = d['email']
        rows = cur.execute("SELECT id, user_handle, created_at FROM users WHERE email=? ORDER BY user_handle IS NOT NULL DESC, created_at ASC", (email,)).fetchall()
        keeper = rows[0]['id']
        others = [r['id'] for r in rows[1:]]
        print(f"Merging {len(others)} duplicates for {email}, keeping {keeper}")
        # reassign references
        for t in ('consents','squad_events','trust_scores','reports'):
            for oid in others:
                cur.execute(f"UPDATE {t} SET user_id=? WHERE user_id=?", (keeper, oid))
        # delete duplicate users
        for oid in others:
            cur.execute("DELETE FROM users WHERE id=?", (oid,))
    con.commit()
    print('Merge complete')

cur.close()
con.close()
