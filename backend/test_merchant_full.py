import sys, os
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.path.insert(0, '.')

import pandas as pd
import tempfile, shutil

from app.services.workers.structured_processor import structured_processor
from app.core.database import get_db_connection

# 1) Convert Excel → CSV
temp_dir = tempfile.mkdtemp()
csv_path = os.path.join(temp_dir, 'tara_merchants.csv')

df = pd.read_excel('E:/Searchia/merchants/tara_merchants.xlsx')
df.to_csv(csv_path, index=False, encoding='utf-8')
print(f'Rows: {len(df)}, Cols: {df.columns.tolist()}')

# 2) Get file_id
conn = get_db_connection()
with conn.cursor() as cur:
    cur.execute("SELECT COALESCE(MAX(file_id), 0) + 1 FROM pg_supervisor")
    file_id = cur.fetchone()[0]
print(f'file_id={file_id}')

# 3) Process
result = structured_processor.process_structured_csv(csv_path, 'tara_merchants.csv', file_id)
print(f'Result: {result}')

# 4) Record in documents
with conn.cursor() as cur:
    cur.execute("""
        INSERT INTO documents (id, filename, file_type, min_role_required)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (id) DO NOTHING
    """, (file_id, 'tara_merchants.csv', 'csv', 'Analyst'))
    conn.commit()
conn.close()

# 5) Verify
conn = get_db_connection()
with conn.cursor() as cur:
    cur.execute("SELECT COUNT(*) FROM pg_supervisor WHERE file_id = %s", (file_id,))
    count = cur.fetchone()[0]
    print(f'\nIndexed chunks: {count}')
    if count > 0:
        cur.execute("SELECT content FROM pg_supervisor WHERE file_id = %s ORDER BY sequence_id LIMIT 3", (file_id,))
        for i, r in enumerate(cur.fetchall()):
            print(f'  [{i+1}] {r[0][:130]}...')
conn.close()
shutil.rmtree(temp_dir)
print('\nDone.')
