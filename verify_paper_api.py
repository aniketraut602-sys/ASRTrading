import requests
try:
    url = "http://localhost:8000/api/trade/paper"
    payload = {
        "symbol": "NIFTY_PAPER_TEST",
        "action": "BUY",
        "quantity": 10,
        "confidence": 0.8,
        "price": 100.0,
        "confirm": True
    }
    print(f"Sending POST to {url}...")
    res = requests.post(url, json=payload, timeout=5)
    print(f"Status: {res.status_code}")
    print(f"Response: {res.text}")
except Exception as e:
    print(f"Error: {e}")
