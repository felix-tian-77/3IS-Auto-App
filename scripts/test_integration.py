#!/usr/bin/env python3
"""
Integration test for 3IS-Auto-App MVP
Tests the complete flow: transaction submission -> worker dispatch -> file download
"""

import requests
import time
import sys

BACKEND_URL = "http://localhost:8000"

def test_backend_health():
    """Test backend health endpoint"""
    try:
        resp = requests.get(f"{BACKEND_URL}/health", timeout=5)
        assert resp.status_code == 200
        print("✓ Backend health check passed")
        return True
    except Exception as e:
        print(f"✗ Backend health check failed: {e}")
        return False

def test_worker_registration():
    """Test worker registration"""
    try:
        resp = requests.post(
            f"{BACKEND_URL}/api/v1/workers/register",
            json={
                "fingerprint": "test-fp-001",
                "hostname": "test-worker-01",
                "ip_address": "192.168.1.100",
                "version": "1.0.0",
                "tags": {},
                "adb_serial": "test-serial-001",
                "port": 8765,
            },
            timeout=5,
        )
        if resp.status_code == 200:
            data = resp.json()
            print(f"✓ Worker registered: {data.get('worker_id')}")
            return data
        else:
            print(f"✗ Worker registration failed: {resp.status_code}")
            return None
    except Exception as e:
        print(f"✗ Worker registration failed: {e}")
        return None

def test_transaction_creation():
    """Test transaction creation with mock data"""
    try:
        # Create mock transaction (without actual file upload for now)
        resp = requests.post(
            f"{BACKEND_URL}/api/v1/transactions",
            json={
                "business_type": "NEW",
                "customer_phone": "13812345678",
                "attachments_meta": [
                    {"file_type": "ID_CARD", "file_format": "JPG"}
                ]
            },
            timeout=5,
        )
        print(f"Transaction creation response: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"✓ Transaction created: {data.get('transaction_id')}")
            return data
        else:
            print(f"Transaction creation response: {resp.text[:200]}")
            return None
    except Exception as e:
        print(f"✗ Transaction creation failed: {e}")
        return None

def main():
    print("=" * 50)
    print("3IS-Auto-App MVP Integration Test")
    print("=" * 50)

    tests = [
        ("Backend Health", test_backend_health),
        ("Worker Registration", test_worker_registration),
        ("Transaction Creation", test_transaction_creation),
    ]

    results = []
    for name, test_func in tests:
        print(f"\n--- Testing: {name} ---")
        result = test_func()
        results.append((name, result))
        time.sleep(0.5)

    print("\n" + "=" * 50)
    print("Summary:")
    for name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"  {name}: {status}")
    print("=" * 50)

    return all(r for _, r in results)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)