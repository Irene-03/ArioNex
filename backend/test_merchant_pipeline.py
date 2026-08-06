import sys, os
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdin.reconfigure(encoding='utf-8')
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')
sys.path.insert(0, '.')

from app.services.workers.structured_processor import structured_processor
from app.core.database import get_db_connection

# 1) Convert Excel → CSV first (same as upload_logic.py does)
import pandas as pd
import tempfile, shutil

temp_dir = tempfile.mkdtemp()
excel_path = 'E:/Searchia/merchants/tara_merchants.xlsx'
csv_path = os.path.join(temp_dir, 'tara_merchants.csv')
filename = 'tara_merchants.csv'

df = pd.read_excel(excel_path)
df.to_csv(csv_path, index=False, encoding='utf-8')
print(f'Converted Excel ({df.shape[0]} rows, {df.shape[1]} cols) → CSV')

# 2) Get next file_id
conn = get_db_connection()
with conn.cursor() as cur:
    cur.execute("SELECT COALESCE(MAX(file_id), 0) + 1 FROM pg_supervisor")
    file_id = cur.fetchone()[0]
print(f'Using file_id={file_id}')

# 3) Run structured processor
result = structured_processor.process_structured_csv(csv_path, filename, file_id)
print(f'Pipeline result: {result}')

# 4) Record in documents table
with conn.cursor() as cur:
    cur.execute("""
        INSERT INTO documents (id, filename, file_type, min_role_required)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (id) DO NOTHING
    """, (file_id, filename, 'csv', 'Analyst'))
    conn.commit()
conn.close()

# 5) Verify
conn = get_db_connection()
with conn.cursor() as cur:
    cur.execute("SELECT COUNT(*) FROM pg_supervisor WHERE file_id = %s", (file_id,))
    count = cur.fetchone()[0]
    print(f'\nChunks in pg_supervisor for file_id={file_id}: {count}')
    if count > 0:
        cur.execute("SELECT content FROM pg_supervisor WHERE file_id = %s ORDER BY sequence_id LIMIT 3", (file_id,))
        for i, row in enumerate(cur.fetchall()):
            print(f'  Chunk {i+1}: {row[0][:120]}...')
conn.close()

# Clean up
shutil.rmtree(temp_dir)
