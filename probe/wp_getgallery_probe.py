import requests
import json

# ============================================================
# НАСТРОЙКИ
# ============================================================


WP_URL = "https://www.zanevkaorg.ru"

WP_USERNAME = "eldar"
WP_APP_PASSWORD = "W0n5 nMpu jxFt 9fr1 2uQM cqtS"

POST_ID = 103010

def get_auth():
    return (WP_USERNAME, WP_APP_PASSWORD.replace(" ", ""))


url = WP_URL.rstrip("/") + f"/wp-json/wp/v2/posts/{POST_ID}"

response = requests.get(
    url,
    auth=get_auth(),
    timeout=30
)

print("HTTP:", response.status_code)

if response.status_code != 200:
    print(response.text)
    raise SystemExit

data = response.json()

print("\n" + "=" * 80)
print("TOP-LEVEL KEYS")
print("=" * 80)

print(list(data.keys()))


print("\n" + "=" * 80)
print("TITLE")
print("=" * 80)

print(json.dumps(data.get("title"), ensure_ascii=False, indent=2))


print("\n" + "=" * 80)
print("EXCERPT")
print("=" * 80)

print(json.dumps(data.get("excerpt"), ensure_ascii=False, indent=2))


print("\n" + "=" * 80)
print("CONTENT")
print("=" * 80)

print(json.dumps(data.get("content"), ensure_ascii=False, indent=2))


print("\n" + "=" * 80)
print("CONTENT RENDERED")
print("=" * 80)

print(data.get("content", {}).get("rendered", ""))