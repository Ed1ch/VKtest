import requests


# ============================================================
# НАСТРОЙКИ
# ============================================================


WP_URL = "https://www.zanevkaorg.ru"

WP_USERNAME = "eldar"
WP_APP_PASSWORD = "W0n5 nMpu jxFt 9fr1 2uQM cqtS"

TITLE = "Осень – не время грустить!"

EXCERPT = (
    "Приглашаем жителей и гостей муниципалитета на октябрьские события, "
    "подготовленные культурно-досуговыми центрами при поддержке администрации "
    "Заневского городского поселения."
)

CONTENT = (
    "<p>"
    "Приглашаем жителей и гостей муниципалитета на октябрьские события, "
    "подготовленные культурно-досуговыми центрами при поддержке администрации "
    "Заневского городского поселения. "
    "Взрослых и детей ждут уютные встречи в семейных клубах, игровые программы, "
    "творческие мастер-классы, а также отчётные концерты местных коллективов. "
    "Делитесь афишами, берите с собой близких и зовите соседей!"
    "</p>"
    "\n"
    '[gallery columns="3" size="medium" ids="103009,103008,103007,103006,103005"]'
)

FEATURED_MEDIA_ID = 103005


def get_auth():
    return (
        WP_USERNAME,
        WP_APP_PASSWORD.replace(" ", "")
    )


url = WP_URL.rstrip("/") + "/wp-json/wp/v2/posts"

payload = {
    "title": TITLE,
    "content": CONTENT,
    "excerpt": EXCERPT,
    "status": "draft",
    "featured_media": FEATURED_MEDIA_ID,
}

response = requests.post(
    url,
    auth=get_auth(),
    json=payload,
    timeout=30
)

print("HTTP:", response.status_code)

if response.status_code not in (200, 201):
    print(response.text)
    raise SystemExit

data = response.json()

print("POST ID:", data["id"])
print("EDIT URL:")
print(f"{WP_URL}/wp-admin/post.php?post={data['id']}&action=edit")

print()
print("TITLE:", data["title"]["rendered"])
print("LINK:", data["link"])
print("FEATURED MEDIA:", data["featured_media"])