import time

import requests


URL = "http://127.0.0.1:8000/api/v1/scan/history/GDXU"


def main():
    """Run the manual cache benchmark against an already-running local API."""
    start_miss = time.time()
    res_miss = requests.get(URL, timeout=30).json()
    end_miss = time.time()
    print("--- Call 1 (Cache Miss) ---")
    print(f"Source Type: {res_miss.get('source')}")
    print(f"Execution Latency: {(end_miss - start_miss) * 1000:.2f} ms\n")

    time.sleep(0.5)
    start_hit = time.time()
    res_hit = requests.get(URL, timeout=30).json()
    end_hit = time.time()
    print("--- Call 2 (Cache Hit) ---")
    print(f"Source Type: {res_hit.get('source')}")
    print(f"Execution Latency: {(end_hit - start_hit) * 1000:.2f} ms")


if __name__ == "__main__":
    main()
