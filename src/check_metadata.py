
from pathlib import Path
import boto3
import pandas as pd
from botocore import UNSIGNED
from botocore.config import Config

project = Path(__file__).resolve().parent.parent
output_dir = project / "data" / "raw"
output_dir.mkdir(parents=True, exist_ok=True)

key = "pvdaq/parquet/metrics/metrics__system_1202__part000.parquet"
local_file = output_dir / "metrics_system_1202.parquet"

s3 = boto3.client(
    "s3",
    config=Config(signature_version=UNSIGNED)
)

print("Downloading System 1202 metadata...")
s3.download_file("oedi-data-lake", key, str(local_file))

metadata = pd.read_parquet(local_file)

print("\n--- METADATA COLUMNS ---")
print(metadata.columns.tolist())

print("\n--- METADATA CONTENT ---")
print(metadata.to_string(index=False))

print("\nSaved metadata to:", local_file)
