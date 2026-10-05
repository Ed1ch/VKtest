import re
import requests


# =========================
# НАСТРОЙКИ
# =========================

ACCESS_TOKEN = "92a2029b92a2029b92a2029b4091e63a36992a292a2029bf862fc683c8f4c9eca7451d4"
API_VERSION = "5.199"


# =========================
# VK API
# =========================

def vk_api(method, params):

    api_url = f"https://api.vk.com/method/{method}"

    params = {
        **params,
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

    if "error" in data:
        raise RuntimeError(
            f"Ошибка VK API: {data['error']}"
        )

    return data.get("response", {})


# =========================
# ПОЛУЧЕНИЕ ПОСТА
# =========================

def get_vk_post(post_url):

    # Ищем:
    # wall-188414783_53864
    # wall188414783_53864
    #
    # owner_id может быть отрицательным.

    match = re.search(
        r'wall(-?\d+)_(\d+)',
        post_url
    )

    if not match:
        raise ValueError(
            "В ссылке не найден фрагмент вида wall-188414783_53864\n"
            "Например: https://vk.ru/wall-188414783_53864"
        )

    owner_id = match.group(1)
    post_id = match.group(2)

    print(f"wall owner_id: {owner_id}")
    print(f"post_id: {post_id}")

    response = vk_api(
        "wall.getById",
        {
            "posts": f"{owner_id}_{post_id}",
            "extended": 1
        }
    )

    items = response.get("items", [])

    if not items:
        raise RuntimeError(
            "VK API не вернуло информацию о посте."
        )

    return items[0]


# =========================
# РЕКУРСИВНЫЙ ПОИСК VIDEO
# =========================

def find_video_recursive(obj):

    """
    Рекурсивно ищет первое вложение типа video.

    Проверяются:
      - attachments
      - copy_history
      - любые вложенные dict/list

    Это позволяет находить видео не только
    непосредственно в посте, но и в репостах.
    """

    if isinstance(obj, dict):

        # Сначала проверяем attachments.
        attachments = obj.get("attachments")

        if isinstance(attachments, list):

            for attachment in attachments:

                if not isinstance(attachment, dict):
                    continue

                if attachment.get("type") == "video":

                    video = attachment.get("video")

                    if isinstance(video, dict):
                        return video

        # Затем рекурсивно идём по остальным данным.
        for key, value in obj.items():

            if key == "attachments":
                continue

            result = find_video_recursive(value)

            if result is not None:
                return result

    elif isinstance(obj, list):

        for item in obj:

            result = find_video_recursive(item)

            if result is not None:
                return result

    return None


# =========================
# ПОЛУЧЕНИЕ ДАННЫХ ВИДЕО
# =========================

def get_vk_video_from_post(post_url):

    # =========================
    # 1. Получаем пост
    # =========================

    post = get_vk_post(post_url)

    # =========================
    # 2. Ищем video рекурсивно
    # =========================

    video_from_post = find_video_recursive(post)

    if video_from_post is None:

        raise RuntimeError(
            "В посте и его вложенных copy_history "
            "не найдено видео."
        )

    owner_id = video_from_post.get("owner_id")
    video_id = video_from_post.get("id")

    if owner_id is None or video_id is None:

        raise RuntimeError(
            "У найденного видео отсутствуют owner_id или id."
        )

    print(f"video owner_id: {owner_id}")
    print(f"video_id: {video_id}")

    # =========================
    # 3. Получаем полную информацию
    #    через video.get
    # =========================

    response = vk_api(
        "video.get",
        {
            "videos": f"{owner_id}_{video_id}",
            "extended": 1
        }
    )

    items = response.get("items", [])

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
    # ПРЕВЬЮ 720px
    # =========================

    images = video.get("image", [])

    preview_url = None
    preview_width = None
    preview_height = None

    if images:

        # Сначала ищем именно width = 720.
        images_720 = [
            image
            for image in images
            if image.get("width") == 720
        ]

        if images_720:

            # Если таких несколько, берём
            # изображение с максимальной высотой.
            best_image = max(
                images_720,
                key=lambda x: x.get("height", 0)
            )

        else:

            # Fallback:
            # выбираем изображение с шириной,
            # наиболее близкой к 720.
            best_image = min(
                images,
                key=lambda x: abs(x.get("width", 0) - 720)
            )

        preview_url = best_image.get("url")
        preview_width = best_image.get("width")
        preview_height = best_image.get("height")

    return {
        # Пост
        "post_owner_id": post.get("owner_id"),
        "post_id": post.get("id"),

        # Видео
        "owner_id": owner_id,
        "video_id": video_id,
        "title": video.get("title"),
        "description": video.get("description"),
        "duration": video.get("duration"),

        # Embed
        "player": player_url,

        # Preview
        "preview": preview_url,
        "preview_width": preview_width,
        "preview_height": preview_height,

        # Полный объект VK
        "raw": video
    }


# =========================
# ЗАПУСК
# =========================

if __name__ == "__main__":

    print("VK Wall Post → Video Embed + Preview")
    print("-------------------------------------")

    post_url = input(
        "Вставь ссылку на пост VK: "
    ).strip()

    try:

        result = get_vk_video_from_post(post_url)

        print("\n========== РЕЗУЛЬТАТ ==========")

        print("\nПост:")
        print(
            f'{result["post_owner_id"]}_{result["post_id"]}'
        )

        print("\nВидео:")
        print(
            f'{result["owner_id"]}_{result["video_id"]}'
        )

        print("\nНазвание:")
        print(result["title"])

        print("\nEmbed / player:")
        print(result["player"])

        print("\nПревью:")
        print(result["preview"])

        print("\nРазмер preview:")
        print(
            f'{result["preview_width"]} × '
            f'{result["preview_height"]}'
        )

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

