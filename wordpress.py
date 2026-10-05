import requests

from config import (
    WP_URL,
    WP_USERNAME,
    WP_APP_PASSWORD,
    WP_API_TIMEOUT,
    POST_STATUS,
    GALLERY_COLUMNS,
    GALLERY_SIZE,
)


def get_auth():
    return (
        WP_USERNAME,
        WP_APP_PASSWORD
    )


def create_post(news):

    content = build_post_content(
        news
    )

    payload = {
        "title": news["title"],
        "content": content,
        "excerpt": news["excerpt"],
        "status": POST_STATUS,
    }

    featured = news.get(
        "featured_media_id"
    )

    if featured:
        payload["featured_media"] = featured

    url = (
        f"{WP_URL}/wp-json/wp/v2/posts"
    )

    response = requests.post(
        url,
        auth=get_auth(),
        json=payload,
        timeout=WP_API_TIMEOUT
    )

    response.raise_for_status()

    return response.json()


def build_post_content(news):

    parts = []

    # ---------------------------------
    # Основной текст из Pandoc
    # ---------------------------------

    content = news.get(
        "content",
        ""
    ).strip()

    if content:
        parts.append(
            content
        )

    # ---------------------------------
    # Галерея
    # ---------------------------------

    gallery_ids = news.get(
        "gallery_media_ids",
        []
    )

    if gallery_ids:

        ids = ",".join(
            str(media_id)
            for media_id in gallery_ids
        )

        parts.append(
            f'[gallery '
            f'columns="{GALLERY_COLUMNS}" '
            f'size="{GALLERY_SIZE}" '
            f'ids="{ids}"]'
        )

    # ---------------------------------
    # VK video
    # ---------------------------------

    vk_embed = news.get(
        "vk_embed"
    )

    if vk_embed:
        parts.append(
            vk_embed
        )

    return "\n\n".join(
        parts
    )
