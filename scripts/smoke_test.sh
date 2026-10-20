#!/usr/bin/env bash
set -e

BASE_URL="${1:-http://localhost:8000}"
# Strip trailing slash if present
BASE_URL="${BASE_URL%/}"

echo "==> Testing Health: ${BASE_URL}/health"
curl -fsS "${BASE_URL}/health"
echo ""

echo "==> Testing Serviceability for pincode 110001 (New Delhi)"
curl -fsS "${BASE_URL}/serviceability/110001"
echo ""

echo "==> Smoke test passed successfully!"
