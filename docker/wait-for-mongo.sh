#!/bin/sh
# Polls MongoDB until it accepts connections, then runs CMD.
# Does NOT use set -e so the retry loop survives failed ping attempts.

MONGO_URI="${MONGO_URI:-mongodb://mongo:27017}"
MAX_RETRIES=30
RETRY_INTERVAL=3

echo "Waiting for MongoDB at ${MONGO_URI} ..."

i=1
while [ "$i" -le "$MAX_RETRIES" ]; do
    python - "$MONGO_URI" <<'PYEOF'
import sys
from pymongo import MongoClient
try:
    c = MongoClient(sys.argv[1], serverSelectionTimeoutMS=3000)
    c.admin.command("ping")
    print("MongoDB is ready.")
    sys.exit(0)
except Exception as e:
    print(f"  Not ready: {e}")
    sys.exit(1)
PYEOF
    if [ $? -eq 0 ]; then
        exec "$@"
    fi
    echo "  Attempt $i/$MAX_RETRIES — retrying in ${RETRY_INTERVAL}s ..."
    i=$((i + 1))
    sleep $RETRY_INTERVAL
done

echo "MongoDB did not become ready in time. Exiting."
exit 1
