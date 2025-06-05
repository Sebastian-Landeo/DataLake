#!/usr/bin/env python3
import os
import tempfile
import pandas as pd
import pyarrow.parquet as pq
import pyarrow as pa
import psycopg2
from minio import Minio
from minio.error import S3Error

endpoint     = os.getenv("MINIO_ENDPOINT", "minio:9000")
access_key   = os.getenv("MINIO_ACCESS_KEY", "admin")
secret_key   = os.getenv("MINIO_SECRET_KEY", "admin123")
secure_flag  = (os.getenv("MINIO_SECURE", "false").lower() == "true")

raw_bucket    = os.getenv("RAW_BUCKET", "datalake")
raw_prefix    = os.getenv("RAW_PREFIX", "raw/")
silver_prefix = os.getenv("SILVER_PREFIX", "silver/")
raw_filename  = os.getenv("RAW_FILENAME", "stress_sleep.csv")

pg_host       = os.getenv("PG_HOST", "superset-db")
pg_port       = int(os.getenv("PG_PORT", "5432"))
pg_db         = os.getenv("PG_DB", "superset")
pg_user       = os.getenv("PG_USER", "superset")
pg_pass       = os.getenv("PG_PASS", "superset")
pg_table      = os.getenv("PG_TABLE", "stress_sleep_silver")

# Initialize MinIO client
client = Minio(
    endpoint,
    access_key=access_key,
    secret_key=secret_key,
    secure=secure_flag
)

def ensure_bucket(name):
    existing = [b.name for b in client.list_buckets()]
    if name not in existing:
        client.make_bucket(name)

# 1) Ensure bucket exists
ensure_bucket(raw_bucket)

# 2) Check & download raw CSV
raw_object = raw_prefix + raw_filename
try:
    client.stat_object(raw_bucket, raw_object)
except S3Error:
    print(f"ERROR: '{raw_object}' not found in bucket '{raw_bucket}'.")
    exit(1)

local_csv = tempfile.NamedTemporaryFile(suffix=".csv", delete=False).name
client.fget_object(raw_bucket, raw_object, local_csv)

# 3) Load CSV into Pandas
df = pd.read_csv(local_csv)

# 4) Transform to silver
#    a) Find the exact “sleep hours” column by matching its prefix
sleep_candidates = [c for c in df.columns if c.startswith("How many hours of actual sleep")]
if not sleep_candidates:
    raise KeyError("Could not find any column starting with 'How many hours of actual sleep'.")
sleep_col = sleep_candidates[0]

#    b) Drop rows where Age, Gender, or the sleep hours column is missing
df_silver = df.dropna(subset=["Age", "Gender", sleep_col])

#    c) Rename that long header to something simpler
df_silver = df_silver.rename(columns={sleep_col: "avg_sleep_hours"})

# 5) Write silver Parquet locally
silver_tmp_dir = tempfile.mkdtemp(prefix="silver_")
silver_parquet = silver_tmp_dir + "/stress_sleep_silver.parquet"
table = pa.Table.from_pandas(df_silver)
pq.write_table(table, silver_parquet)

# 6) Upload silver Parquet back to MinIO
silver_object = silver_prefix + "stress_sleep_silver.parquet"
client.fput_object(raw_bucket, silver_object, silver_parquet)

# 7) Load silver Parquet into Postgres
conn = psycopg2.connect(
    host=pg_host,
    port=pg_port,
    dbname=pg_db,
    user=pg_user,
    password=pg_pass
)
conn.autocommit = True
cur = conn.cursor()
 
# Drop+create table
cur.execute(f"DROP TABLE IF EXISTS {pg_table};")

# Build schema from df_silver dtypes using simple unique column names col_0, col_1, ...
def pd_to_pg(dtype):
    if pd.api.types.is_integer_dtype(dtype):
        return "INTEGER"
    if pd.api.types.is_float_dtype(dtype):
        return "DOUBLE PRECISION"
    return "TEXT"

original_columns = df_silver.columns.tolist()
col_defs = []
original_to_safe = {}

for idx, col in enumerate(original_columns):
    safe_name = f"col_{idx}"
    original_to_safe[col] = safe_name
    pg_type = pd_to_pg(df_silver[col].dtype)
    col_defs.append(f'"{safe_name}" {pg_type}')

schema_sql = ", ".join(col_defs)
cur.execute(f"CREATE TABLE {pg_table} ({schema_sql});")

# Insert rows
safe_cols = [original_to_safe[c] for c in original_columns]
col_list = ", ".join(f'"{c}"' for c in safe_cols)
placeholders = ", ".join(["%s"] * len(safe_cols))
insert_sql = f"INSERT INTO {pg_table} ({col_list}) VALUES ({placeholders});"
for _, row in df_silver.iterrows():
    values = [row[c] for c in original_columns]
    cur.execute(insert_sql, values)

cur.close()
conn.close()

print("✅ datalake pipeline finished successfully.")

