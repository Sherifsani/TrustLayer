import sqlite3
from uuid import UUID

con = sqlite3.connect('dev.db')
con.row_factory = sqlite3.Row
cur = con.cursor()

user_id_str = '6bfcb4a2-6f24-465a-9b1c-15a70c3d3bfa'
cur.execute("""
SELECT user_id, business_id, granted_signals, revoked 
FROM consents 
WHERE user_id = ?
""", (user_id_str,))

rows = cur.fetchall()
print(f"Found {len(rows)} consent records:")
for row in rows:
    print(f"  {row['business_id']:<30} signals={row['granted_signals']:<50} revoked={row['revoked']}")

cur.close()
con.close()
