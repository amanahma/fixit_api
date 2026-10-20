#!/usr/bin/env python3
"""Cross-platform smoke test for Fixit API."""

import json
import sys
import urllib.request


def main() -> None:
    base_url = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://localhost:8000"
    print(f"Testing deployed service at {base_url} ...")

    # 1. Health check
    print(f"GET {base_url}/health")
    with urllib.request.urlopen(f"{base_url}/health", timeout=15) as resp:
        data = json.loads(resp.read().decode())
        print("  Response:", data)
        assert data.get("status") == "ok", f"Unexpected health status: {data}"

    # 2. Serviceability check
    print(f"GET {base_url}/serviceability/110001")
    with urllib.request.urlopen(f"{base_url}/serviceability/110001", timeout=15) as resp:
        data = json.loads(resp.read().decode())
        print("  Response:", data)
        assert data.get("serviceable") is True, f"Pincode 110001 should be serviceable: {data}"

    print("\nAll smoke tests passed!")


if __name__ == "__main__":
    main()
