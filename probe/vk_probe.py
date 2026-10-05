
import re
import requests


# =========================
# НАСТРОЙКИ
# =========================

ACCESS_TOKEN = "92a2029b92a2029b92a2029b4091e63a36992a292a2029bf862fc683c8f4c9eca7451d4"
API_VERSION = "5.199"


# =========================
# ПОЛУЧЕНИЕ ДАННЫХ ИЗ VK
# =========================

def get_vk_video(video_url):

    # Ищем в ссылке фрагмент:
    # video-188414783_456241485
    #
    # Домен ссылки не имеет значения.

    match = re.search(
        r'video(-?\d+)_(\d+)',
        video_url
    )

    if not match:
        raise ValueError(
            "В ссылке не найден фрагмент вида video*_*\n"
            "Например: video-188414783_456241485"
        )

    owner_id = match.group(1)
    video_id = match.group(2)

    print(f"owner_id: {owner_id}")
    print(f"video_id: {video_id}")

    # =========================
    # VK API
    # =========================

    api_url = "https://api.vk.com/method/video.get"

    params = {
        "videos": f"{owner_id}_{video_id}",
        "extended": 1,
        "v": API_VERSION,
        "access_token": ACCESS_TOKEN
    }

    response = requests.get(
        api_url,
        params=params,
        timeout=15
    )

    response.raise_for_status()

    data = response.json()

    # Проверяем ошибку VK API
    if "error" in data:
        raise RuntimeError(
            f"Ошибка VK API: {data['error']}"
        )

    items = data.get("response", {}).get("items", [])

    if not items:
        raise RuntimeError(
            "VK API не вернуло информацию о видео."
        )

    video = items[0]

    # =========================
    # EMBED / PLAYER
    # =========================

    player_url = video.get("player")

    # =========================
    # ПРЕВЬЮ
    # =========================

    images = video.get("image", [])

    preview_url = None

    if images:
        # Выбираем изображение с максимальным разрешением
        best_image = max(
            images,
            key=lambda x: x.get("width", 0) * x.get("height", 0)
        )

        preview_url = best_image.get("url")

    return {
        "owner_id": owner_id,
        "video_id": video_id,
        "title": video.get("title"),
        "description": video.get("description"),
        "duration": video.get("duration"),
        "player": player_url,
        "preview": preview_url,
        "raw": video
    }


# =========================
# ЗАПУСК
# =========================

if __name__ == "__main__":

    print("VK Video → Embed + Preview")
    print("--------------------------------")

    video_url = input(
        "Вставь ссылку на видео VK: "
    ).strip()

    try:

        result = get_vk_video(video_url)

        print("\n========== РЕЗУЛЬТАТ ==========")

        print("\nНазвание:")
        print(result["title"])

        print("\nEmbed / player:")
        print(result["player"])

        print("\nПревью:")
        print(result["preview"])

        print("\nHTML iframe:")

        if result["player"]:

            print(
                f'<iframe src="{result["player"]}" '
                f'width="853" height="480" '
                f'frameborder="0" allowfullscreen></iframe>'
            )

        else:
            print("VK не вернул player.")

    except Exception as e:

        print("\nОШИБКА:")
        print(e)
