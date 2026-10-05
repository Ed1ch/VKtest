import re
import requests

from config import (
    VK_ACCESS_TOKEN,
    VK_API_VERSION,
    VK_API_TIMEOUT,
)


def vk_api(method, params):

    api_url = (
        f"https://api.vk.com/method/{method}"
    )

    params = {
        **params,
        "v": VK_API_VERSION,
        "access_token": VK_ACCESS_TOKEN,
    }

    response = requests.get(
        api_url,
        params=params,
        timeout=VK_API_TIMEOUT
    )

    response.raise_for_status()

    data = response.json()

    if "error" in data:
        raise RuntimeError(
            f"Ошибка VK API: {data['error']}"
        )

    return data.get(
        "response",
        {}
    )


def get_vk_post(post_url):

    match = re.search(
        r"wall(-?\d+)_(\d+)",
        post_url
    )

    if not match:
        raise ValueError(
            "В ссылке не найден фрагмент вида "
            "wall-188414783_53864"
        )

    owner_id = match.group(1)
    post_id = match.group(2)

    response = vk_api(
        "wall.getById",
        {
            "posts":
                f"{owner_id}_{post_id}",
            "extended": 1,
        }
    )

    items = response.get(
        "items",
        []
    )

    if not items:
        raise RuntimeError(
            "VK API не вернуло информацию о посте."
        )

    return items[0]


def find_video_recursive(obj):

    if isinstance(obj, dict):

        attachments = obj.get(
            "attachments"
        )

        if isinstance(
            attachments,
            list
        ):

            for attachment in attachments:

                if not isinstance(
                    attachment,
                    dict
                ):
                    continue

                if attachment.get(
                    "type"
                ) == "video":

                    video = attachment.get(
                        "video"
                    )

                    if isinstance(
                        video,
                        dict
                    ):
                        return video

        for key, value in obj.items():

            if key == "attachments":
                continue

            result = find_video_recursive(
                value
            )

            if result is not None:
                return result

    elif isinstance(obj, list):

        for item in obj:

            result = find_video_recursive(
                item
            )

            if result is not None:
                return result

    return None


def get_vk_video_from_post(post_url):

    post = get_vk_post(
        post_url
    )

    video_from_post = find_video_recursive(
        post
    )

    if video_from_post is None:

        raise RuntimeError(
            "В посте и его вложенных "
            "copy_history не найдено видео."
        )

    owner_id = video_from_post.get(
        "owner_id"
    )

    video_id = video_from_post.get(
        "id"
    )

    if owner_id is None or video_id is None:

        raise RuntimeError(
            "У найденного видео отсутствуют "
            "owner_id или id."
        )

    response = vk_api(
        "video.get",
        {
            "videos":
                f"{owner_id}_{video_id}",
            "extended": 1,
        }
    )

    items = response.get(
        "items",
        []
    )

    if not items:

        raise RuntimeError(
            "VK API не вернуло информацию о видео."
        )

    video = items[0]

    images = video.get(
        "image",
        []
    )

    preview_url = None
    preview_width = None
    preview_height = None

    if images:

        images_720 = [
            image
            for image in images
            if image.get("width") == 720
        ]

        if images_720:

            best_image = max(
                images_720,
                key=lambda x:
                    x.get("height", 0)
            )

        else:

            best_image = min(
                images,
                key=lambda x:
                    abs(
                        x.get("width", 0)
                        - 720
                    )
            )

        preview_url = best_image.get(
            "url"
        )

        preview_width = best_image.get(
            "width"
        )

        preview_height = best_image.get(
            "height"
        )

    return {
        "post_owner_id":
            post.get("owner_id"),

        "post_id":
            post.get("id"),

        "owner_id":
            owner_id,

        "video_id":
            video_id,

        "title":
            video.get("title"),

        "description":
            video.get("description"),

        "duration":
            video.get("duration"),

        "player":
            video.get("player"),

        "preview":
            preview_url,

        "preview_width":
            preview_width,

        "preview_height":
            preview_height,

        "raw":
            video,
    }