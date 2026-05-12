import sqlite3

con = sqlite3.connect('dev.db')
cur = con.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE name LIKE '_alembic_tmp_%'")
rows = cur.fetchall()
print('tmp tables:', rows)
if rows:
    for r in rows:
        name = r[0]
        print('dropping', name)
        cur.execute(f"DROP TABLE IF EXISTS {name}")
    con.commit()
else:
    print('no temp tables')
cur.close()
con.close()
print('done')
