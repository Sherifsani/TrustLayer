"""One-time cleanup: delete all reports that are not 'active'."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(".env.local")
load_dotenv()

from db.session import SessionLocal
from api.models.db_models import Report

db = SessionLocal()
try:
    to_delete = db.query(Report).filter(Report.status != "active").all()
    count = len(to_delete)
    for r in to_delete:
        db.delete(r)
    db.commit()
    print(f"Deleted {count} non-active report(s).")
finally:
    db.close()
