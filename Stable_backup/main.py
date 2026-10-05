import html
import mimetypes

import requests

from config import EML_FILE

from eml_parser import extract_attachments
from eml_links import extract_vk_links

from news_parser import build_news

from image_manager import (
    upload_media,
    upload_media_bytes,
)

from wordpress import create_post

from vk_video import (
    get_vk_video_from_post,
)


def download_vk_preview(url):

    response = requests.get(
        url,
        timeout=30
    )

    response.raise_for_status()

    content_type = response.headers.get(
        "Content-Type",
        "image/jpeg"
    )

    extension = (
        mimetypes.guess_extension(
            content_type.split(";")[0]
        )
        or ".jpg"
    )

    return (
        response.content,
        content_type,
        extension
    )


def process_vk(news, vk_info):

    if not vk_info:
        return

    url = vk_info["url"]

    print(
        f"VK URL: {url}"
    )

    # -------------------------
    # Получаем данные видео
    # -------------------------

    vk_data = get_vk_video_from_post(
        url
    )

    news["vk_data"] = vk_data

    # -------------------------
    # Embed
    # -------------------------

    player = vk_data.get(
        "player"
    )

    if player:

        news["vk_embed"] = (
            f'<iframe '
            f'src="{html.escape(player)}" '
            f'width="853" '
            f'height="480" '
            f'frameborder="0" '
            f'allowfullscreen></iframe>'
        )

    # -------------------------
    # VK preview
    # -------------------------
    #
    # Если у новости нет обычной
    # featured-картинки, preview
    # VK становится featured image.
    # -------------------------

    if (
        not news.get("featured_image")
        and vk_data.get("preview")
    ):

        print(
            "Загрузка VK preview..."
        )

        preview_data, mime_type, extension = (
            download_vk_preview(
                vk_data["preview"]
            )
        )

        media = upload_media_bytes(
            preview_data,
            "vk_preview" + extension,
            mime_type
        )

        news["featured_media_id"] = (
            media["wp_id"]
        )


def process_images(news):

    featured_image = news.get(
        "featured_image"
    )

    if featured_image:

        media = upload_media(
            featured_image
        )

        news["featured_media_id"] = (
            media["wp_id"]
        )

    gallery_images = news.get(
        "gallery_images",
        []
    )

    gallery_media_ids = []

    for image_path in gallery_images:

        media = upload_media(
            image_path
        )

        gallery_media_ids.append(
            media["wp_id"]
        )

    news["gallery_media_ids"] = (
        gallery_media_ids
    )


def main():

    print("=" * 80)
    print("EML → WORDPRESS")
    print("=" * 80)

    print()
    print(
        f"EML: {EML_FILE}"
    )

    # -------------------------
    # EML
    # -------------------------

    email_data = extract_attachments(
        EML_FILE
    )

    documents = email_data["documents"]
    images = email_data["images"]

    print(
        f"DOCX найдено: {len(documents)}"
    )

    print(
        f"Изображений найдено: {len(images)}"
    )

    # -------------------------
    # Новости
    # -------------------------

    news_list = build_news(
        documents,
        images
    )

    print(
        f"Новостей собрано: {len(news_list)}"
    )

    # -------------------------
    # VK ссылки из EML
    # -------------------------
    #
    # email_links.py сам:
    #
    # 1. ищет имена DOCX
    # 2. ищет их в Subject/text/html
    # 3. ищет VK wall перед найденным именем
    # 4. удаляет дубли
    # 5. сообщает ошибку,
    #    если имя найдено без ссылки
    #
    # Поэтому здесь не нужно
    # ничего дополнительно искать.
    # -------------------------

    vk_links = extract_vk_links(
        email_data,
        documents
    )

    vk_by_document = {
        item["document"]: item
        for item in vk_links
    }

    print()

    if vk_links:

        print("=" * 80)
        print("VK ССЫЛКИ")
        print("=" * 80)

        for item in vk_links:

            print()
            print(
                f'DOCX: {item["document"]}'
            )

            print(
                f'URL:  {item["url"]}'
            )

            print(
                f'Источник: {item["source"]}'
            )

    else:

        print(
            "VK ссылок, привязанных к DOCX, не найдено."
        )

    # -------------------------
    # Обработка новостей
    # -------------------------

    for number, news in enumerate(
        news_list,
        start=1
    ):

        print()
        print("=" * 80)
        print(
            f"NEWS #{number}: "
            f"{news['title']}"
        )
        print("=" * 80)

        try:

            # -------------------------
            # 1. Изображения
            # -------------------------

            print(
                "\n[1] Обработка изображений..."
            )

            process_images(
                news
            )

            # -------------------------
            # 2. VK
            # -------------------------

            print(
                "\n[2] Поиск VK..."
            )

            document_filename = (
                news["document_filename"]
            )

            vk_info = vk_by_document.get(
                document_filename
            )

            if vk_info:

                print(
                    f"Найдена VK-ссылка для "
                    f"{document_filename}"
                )

                process_vk(
                    news,
                    vk_info
                )

            else:

                print(
                    "VK-ссылка для этой новости "
                    "не найдена."
                )

            # -------------------------
            # 3. WordPress
            # -------------------------

            print(
                "\n[3] Создание записи..."
            )

            post = create_post(
                news
            )

            print(
                "\nГотово:"
            )

            print(
                f"ID: {post['id']}"
            )

            print(
                f"URL: {post.get('link')}"
            )

            print(
                f"Статус: {post.get('status')}"
            )

        except Exception as e:

            print(
                "\nОШИБКА:"
            )

            print(e)

    print()
    print("=" * 80)
    print("ГОТОВО")
    print("=" * 80)


if __name__ == "__main__":
    main()

