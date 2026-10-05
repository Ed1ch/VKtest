import requests


# ============================================================
# НАСТРОЙКИ WORDPRESS
# ============================================================

WP_URL = "https://www.zanevkaorg.ru"

WP_USERNAME = "eldar"

WP_APP_PASSWORD = "W0n5 nMpu jxFt 9fr1 2uQM cqtS"


# ============================================================
# СОЗДАНИЕ ЧЕРНОВИКА
# ============================================================

def create_test_draft():

    api_url = f"{WP_URL.rstrip('/')}/wp-json/wp/v2/posts"

    # Данные новой записи
    post_data = {
        "title": "TEST",
        "content": "TEST",
        "status": "draft"
    }

    # WordPress REST API использует Basic Auth:
    # логин + Application Password
    response = requests.post(
        api_url,
        json=post_data,
        auth=(WP_USERNAME, WP_APP_PASSWORD),
        timeout=15
    )

    print(f"HTTP статус: {response.status_code}")

    # Если WordPress вернул ошибку
    if not response.ok:
        print("\nОтвет WordPress:")
        print(response.text)

        response.raise_for_status()

    result = response.json()

    print("\n========== ГОТОВО ==========")

    print(f"ID записи: {result.get('id')}")
    print(f"Статус: {result.get('status')}")
    print(f"Название: {result.get('title', {}).get('rendered')}")
    print(f"Ссылка: {result.get('link')}")

    return result


# ============================================================
# ЗАПУСК
# ============================================================

if __name__ == "__main__":

    print("WordPress REST API → TEST draft")
    print("--------------------------------")

    try:
        create_test_draft()

    except requests.exceptions.ConnectionError:
        print("\nОШИБКА: не удалось подключиться к WordPress.")

    except requests.exceptions.Timeout:
        print("\nОШИБКА: WordPress не ответил за 15 секунд.")

    except requests.exceptions.HTTPError:
        print("\nОШИБКА HTTP при обращении к WordPress.")

    except Exception as e:
        print(f"\nОШИБКА: {e}")