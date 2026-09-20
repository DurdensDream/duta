import os

APP_DB_DSN = os.environ.get("APP_DB_DSN", "postgresql://duta:duta@localhost:5434/duta")
CRM_DB_DSN = os.environ.get("CRM_DB_DSN", "postgresql://duta_ro:duta_ro_pw@localhost:5433/talentbase")

KESTREL_BASE_URL = os.environ.get("KESTREL_BASE_URL", "http://localhost:8100")
KESTREL_CLIENT_ID = os.environ.get("KESTREL_CLIENT_ID", "meridian-pilot")
KESTREL_CLIENT_SECRET = os.environ.get("KESTREL_CLIENT_SECRET", "kestrel-pilot-secret-2026")

JOBWIRE_DROPZONE = os.environ.get("JOBWIRE_DROPZONE", "./data/dropzone")

TEMPORAL_ADDRESS = os.environ.get("TEMPORAL_ADDRESS", "localhost:7233")
TEMPORAL_TASK_QUEUE = os.environ.get("TEMPORAL_TASK_QUEUE", "duta-pilot")

# Kestrel emits timestamps in mixed timezone spellings and compares `updated_since` as a raw
# string (verified against the staged vendor). A -05:00 record can be string-excluded even when
# its UTC instant is newer than the watermark. Defense: rewind the watermark by this overlap on
# every pull and let schema-level idempotency eat the re-reads. 6h > the worst offset seen (-05:00).
KESTREL_WATERMARK_OVERLAP_HOURS = int(os.environ.get("KESTREL_WATERMARK_OVERLAP_HOURS", "6"))
