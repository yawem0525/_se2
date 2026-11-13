import json
import urllib.request

class CloudflareAppClient:
    def __init__(self, base_url: str = "https://your-app.your-subdomain.workers.dev"):
        self.base_url = base_url.rstrip("/")

    def call_endpoint(self, path: str = "/api/health") -> dict:
        url = f"{self.base_url}{path}"
        req = urllib.request.Request(url, headers={"User-Agent": "cf-app-client/0.1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
