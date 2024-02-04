import pandas as pd
import subprocess
import argparse
from io import StringIO

# Step 1: Convert Parquet to CSV in memory
def parquet_to_csv(parquet_path):
    try:
        df = pd.read_parquet(parquet_path).drop(columns=['index'])
    except Exception as e:
        pass
    finally:
        df = pd.read_parquet(parquet_path)
        
    csv_data = df.to_csv(index=False)
    return csv_data

# Step 2: Load CSV into PostgreSQL
def load_csv_to_postgres(csv_data, postgres_host, postgres_port, postgres_user, postgres_db, postgres_table):
    copy_command = f"""
    COPY {postgres_table} FROM STDIN WITH CSV HEADER DELIMITER ',';
    """

    psql_command = f"""
    psql -h {postgres_host} -p {postgres_port} -U {postgres_user} -d {postgres_db} -c "{copy_command}"
    """

    subprocess.run(psql_command, input=csv_data, text=True, shell=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load Parquet file into PostgreSQL.")
    parser.add_argument("file_path", help="Path to the input Parquet file")
    parser.add_argument("--host", default="localhost", help="PostgreSQL host")
    parser.add_argument("--port", default="5432", help="PostgreSQL port")
    parser.add_argument("--user", required=True, help="PostgreSQL user")
    parser.add_argument("--dbname", required=True, help="PostgreSQL database name")
    parser.add_argument("--table", required=True, help="PostgreSQL table name")

    args = parser.parse_args()

    parquet_path = args.file_path
    postgres_host = args.host
    postgres_port = args.port
    postgres_user = args.user
    postgres_db = args.dbname
    postgres_table = args.table

    # Step 1: Convert Parquet to CSV in memory
    csv_data = parquet_to_csv(parquet_path)

    # Step 2: Load CSV into PostgreSQL
    load_csv_to_postgres(csv_data, postgres_host, postgres_port, postgres_user, postgres_db, postgres_table)
