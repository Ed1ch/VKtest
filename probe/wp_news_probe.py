import os
import mimetypes
import re
import requests

from news_probe import (
    EML_FILE,
    extract_attachments,
    build_news,
)


# ============================================================
# WORDPRESS
# ============================================================

WP_URL = "https://www.zanevkaorg.ru"

WP_USERNAME = "eldar"
WP_APP_PASSWORD = "W0n5 nMpu jxFt 9fr1 2uQM cqtS"


# ============================================================
# AUTH
# ============================================================

def get_auth():
    return (
        WP_USERNAME,
        WP_APP_PASSWORD.replace(" ", "")
    )


# ============================================================
# TRANSLITERATION
# ============================================================

TRANSLIT = {
    "а": "a",  "б": "b",  "в": "v",  "г": "g",
    "д": "d",  "е": "e",  "ё": "e",  "ж": "zh",
    "з": "z",  "и": "i",  "й": "j",  "к": "k",
    "л": "l",  "м": "m",  "н": "n",  "о": "o",
    "п": "p",  "р": "r",  "с": "s",  "т": "t",
    "у": "u",  "ф": "f",  "х": "h",  "ц": "c",
    "ч": "ch", "ш": "sh", "щ": "sch",
    "ъ": "",   "ы": "y",  "ь": "",
    "э": "e",  "ю": "yu", "я": "ya",
}


def transliterate_filename(filename):
    """
    Делает имя файла безопасным для HTTP-заголовка.

    Например:
        октябрь1.jpg -> oktyabr1.jpg
        80 лет.jpg   -> 80_let.jpg
    """

    result = []

    for char in filename:

        lower = char.lower()

        if lower in TRANSLIT:
            replacement = TRANSLIT[lower]

            if char.isupper():
                replacement = replacement.capitalize()

            result.append(replacement)

        elif char.isascii():
            result.append(char)

        elif char.isspace():
            result.append("_")

        else:
            result.append("_")

    filename = "".join(result)

    filename = re.sub(r"_+", "_", filename)

    return filename


# ============================================================
# WORDPRESS MEDIA
# ============================================================

def upload_media(image_path):
    """
    Загружает изображение в WordPress Media Library.

    Возвращает:
        {
            "id": 123,
            "source_url": "https://..."
        }
    """

    filename = os.path.basename(image_path)
    safe_filename = transliterate_filename(filename)

    mime_type = mimetypes.guess_type(filename)[0]

    if not mime_type:
        mime_type = "application/octet-stream"

    url = WP_URL.rstrip("/") + "/wp-json/wp/v2/media"

    headers = {
        "Content-Disposition": f'attachment; filename="{safe_filename}"',
        "Content-Type": mime_type,
    }

    print()
    print("  Загрузка изображения:")
    print(f"    {filename}")
    print(f"    → {safe_filename}")

    with open(image_path, "rb") as f:

        response = requests.post(
            url,
            auth=get_auth(),
            headers=headers,
            data=f,
            timeout=60,
        )

    print(f"    HTTP: {response.status_code}")

    if response.status_code not in (200, 201):
        print(response.text)
        raise RuntimeError(
            f"Ошибка загрузки изображения: {filename}"
        )

    data = response.json()

    media_id = data["id"]
    source_url = data["source_url"]

    print(f"    Media ID: {media_id}")
    print(f"    URL: {source_url}")

    return {
        "id": media_id,
        "source_url": source_url,
    }


# ============================================================
# CONTENT
# ============================================================

def build_post_content(news):
    """
    Формирует тело WordPress-поста.

    Правила:
      - title сюда НЕ попадает
      - excerpt остаётся частью content
      - каждый исходный абзац становится <p>
      - при наличии 2+ изображений добавляется
        классическая WordPress gallery
    """

    paragraphs = [
        paragraph.strip()
        for paragraph in news["content"].split("\n\n")
        if paragraph.strip()
    ]

    html_parts = []

    for paragraph in paragraphs:
        html_parts.append(
            f"<p>{paragraph}</p>"
        )

    gallery_images = news["gallery_images"]

    if gallery_images:
        media_ids = [
            str(image["wp_id"])
            for image in gallery_images
        ]

        ids = ",".join(media_ids)

        gallery_shortcode = (
            f'[gallery columns="3" size="medium" ids="{ids}"]'
        )

        html_parts.append(gallery_shortcode)

    return "\n".join(html_parts)


# ============================================================
# WORDPRESS POST
# ============================================================

def create_post(news):
    """
    Создаёт черновик WordPress.
    """

    content = build_post_content(news)

    featured_media = 0

    if news["featured_image"]:
        featured_media = news["featured_image"]["wp_id"]

    payload = {
        "title": news["title"],
        "content": content,
        "excerpt": news["excerpt"],
        "status": "draft",
        "featured_media": featured_media,
    }

    url = WP_URL.rstrip("/") + "/wp-json/wp/v2/posts"

    print()
    print("  Создание WordPress-поста...")
    print(f"    Title: {news['title']}")
    print(f"    Featured media: {featured_media}")

    response = requests.post(
        url,
        auth=get_auth(),
        json=payload,
        timeout=60,
    )

    print(f"    HTTP: {response.status_code}")

    if response.status_code not in (200, 201):
        print(response.text)
        raise RuntimeError(
            f"Ошибка создания поста: {news['title']}"
        )

    data = response.json()

    post_id = data["id"]

    print(f"    POST ID: {post_id}")
    print(
        f"    EDIT: "
        f"{WP_URL}/wp-admin/post.php?post={post_id}&action=edit"
    )

    return data


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 80)
    print("EML → WORDPRESS NEWS PROBE")
    print("=" * 80)

    print()
    print(f"EML: {EML_FILE}")
    print(f"WordPress: {WP_URL}")

    if not os.path.exists(EML_FILE):
        print()
        print(f"ОШИБКА: файл не найден: {EML_FILE}")
        return

    # --------------------------------------------------------
    # 1. Читаем EML
    # --------------------------------------------------------

    documents, images = extract_attachments(EML_FILE)

    print()
    print(f"DOCX найдено: {len(documents)}")
    print(f"Изображений найдено: {len(images)}")

    # --------------------------------------------------------
    # 2. Формируем новости
    # --------------------------------------------------------

    news_list = build_news(
        documents,
        images
    )

    print()
    print(f"Новостей собрано: {len(news_list)}")

    # --------------------------------------------------------
    # 3. Обрабатываем каждую новость
    # --------------------------------------------------------

    for number, news in enumerate(news_list, start=1):

        print()
        print("=" * 80)
        print(f"NEWS #{number}")
        print("=" * 80)

        print()
        print("TITLE:")
        print(news["title"])

        print()
        print("EXCERPT:")
        print(news["excerpt"])

        print()
        print("CONTENT:")
        print(news["content"])

        # ----------------------------------------------------
        # Загружаем featured image
        # ----------------------------------------------------

        if news["featured_image"]:

            uploaded = upload_media(
                news["featured_image"]
            )

            news["featured_image"] = {
                "path": news["featured_image"],
                "wp_id": uploaded["id"],
                "source_url": uploaded["source_url"],
            }

        # ----------------------------------------------------
        # Загружаем gallery
        # ----------------------------------------------------

        if news["gallery_images"]:

            uploaded_gallery = []

            for image_path in news["gallery_images"]:

                uploaded = upload_media(
                    image_path
                )

                uploaded_gallery.append({
                    "path": image_path,
                    "wp_id": uploaded["id"],
                    "source_url": uploaded["source_url"],
                })

            news["gallery_images"] = uploaded_gallery

        # ----------------------------------------------------
        # Создаём пост
        # ----------------------------------------------------

        create_post(news)

    print()
    print("=" * 80)
    print("ГОТОВО")
    print("=" * 80)


if __name__ == "__main__":
    main()