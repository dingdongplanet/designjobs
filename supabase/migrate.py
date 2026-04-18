"""Run schema.sql against your Supabase project."""
import os
from pathlib import Path
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

url = os.environ["SUPABASE_URL"]
key = os.environ["SUPABASE_KEY"]
client = create_client(url, key)

sql = Path(__file__).parent / "schema.sql"
print("Running migration...")
client.rpc("exec_sql", {"query": sql.read_text()}).execute()
print("Done. Schema applied.")
