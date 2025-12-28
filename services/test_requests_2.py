import time
import requests

URL = "http://localhost:8002/predict"

with open("log.txt", "a", encoding="utf-8") as f:
    for i in range(40):
        params = {"x": str(i), "y": "-16"}

        t0 = time.perf_counter()
        try:
            r = requests.get(URL, params=params, timeout=10)
            dt = time.perf_counter() - t0
            print(f"i={i} status={r.status_code} latency={dt:.4f}s body={r.text}", file=f)
        except Exception as e:
            dt = time.perf_counter() - t0
            print(f"i={i} error={type(e).__name__}: {e} latency={dt:.4f}s", file=f)

        if i == 30:
            time.sleep(30)
        time.sleep(2)
