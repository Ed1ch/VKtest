import os
import mimetypes
import requests


# ============================================================
# НАСТРОЙКИ
# ============================================================

WP_URL = "https://www.zanevkaorg.ru"

WP_USERNAME = "eldar"
WP_APP_PASSWORD = "W0n5 nMpu jxFt 9fr1 2uQM cqtS"

IMAGES_DIR = r"extracted_images"

# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

def get_auth():
    """
    HTTP Basic Auth для WordPress.
    """

    password = WP_APP_PASSWORD.replace(" ", "")

    return (WP_USERNAME, password)


def make_safe_filename(filename):
    """
    Создаёт ASCII-имя для передачи в HTTP-заголовке.

    Кириллические символы заменяются на безопасные
    латинские варианты.
    """

    replacements = {
        "а": "a",
        "б": "b",
        "в": "v",
        "г": "g",
        "д": "d",
        "е": "e",
        "ё": "e",
        "ж": "zh",
        "з": "z",
        "и": "i",
        "й": "y",
        "к": "k",
        "л": "l",
        "м": "m",
        "н": "n",
        "о": "o",
        "п": "p",
        "р": "r",
        "с": "s",
        "т": "t",
        "у": "u",
        "ф": "f",
        "х": "kh",
        "ц": "ts",
        "ч": "ch",
        "ш": "sh",
        "щ": "sch",
        "ъ": "",
        "ы": "y",
        "ь": "",
        "э": "e",
        "ю": "yu",
        "я": "ya",
    }

    base, extension = os.path.splitext(filename)

    result = []

    for char in base:

        lower = char.lower()

        if lower in replacements:

            replacement = replacements[lower]

            if char.isupper():
                replacement = replacement.capitalize()

            result.append(replacement)

        elif char.isascii() and (
            char.isalnum()
            or char in ("-", "_", ".")
        ):

            result.append(char)

        else:
            result.append("_")

    safe_base = "".join(result)

    # Убираем повторяющиеся "_"
    while "__" in safe_base:
        safe_base = safe_base.replace("__", "_")

    safe_base = safe_base.strip("_")

    if not safe_base:
        safe_base = "image"

    return safe_base + extension.lower()


def upload_image(image_path):
    """
    Загружает одно изображение в WordPress.

    Возвращает:

    {
        "filename": оригинальное имя,
        "upload_filename": имя, использованное HTTP,
        "id": ID Media,
        "url": URL
    }
    """

    original_filename = os.path.basename(image_path)

    upload_filename = make_safe_filename(
        original_filename
    )

    mime_type, _ = mimetypes.guess_type(
        original_filename
    )

    if not mime_type:
        mime_type = "application/octet-stream"

    url = (
        WP_URL.rstrip("/")
        + "/wp-json/wp/v2/media"
    )

    headers = {
        "Content-Disposition":
            f'attachment; filename="{upload_filename}"',

        "Content-Type": mime_type,
    }

    print()
    print(f"Оригинал: {original_filename}")
    print(f"Передача: {upload_filename}")
    print(f"MIME:     {mime_type}")

    try:

        with open(image_path, "rb") as f:

            response = requests.post(
                url,
                headers=headers,
                data=f,
                auth=get_auth(),
                timeout=60,
            )

    except Exception as e:

        print("ОШИБКА соединения:")
        print(e)

        return None

    print(f"HTTP:     {response.status_code}")

    if response.status_code not in (200, 201):

        print("ОШИБКА WordPress:")

        try:
            print(response.json())

        except Exception:
            print(response.text)

        return None

    try:

        data = response.json()

    except Exception as e:

        print("ОШИБКА разбора ответа WordPress:")
        print(e)
        print(response.text)

        return None

    result = {
        "filename": original_filename,
        "upload_filename": upload_filename,
        "id": data.get("id"),
        "url": data.get("source_url"),
    }

    print(f"ID:       {result['id']}")
    print(f"URL:      {result['url']}")

    return result


def find_images(root_dir):
    """
    Рекурсивно находит изображения.
    """

    extensions = {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".gif",
    }

    images = []

    for root, dirs, files in os.walk(root_dir):

        for filename in files:

            extension = os.path.splitext(
                filename
            )[1].lower()

            if extension not in extensions:
                continue

            path = os.path.join(
                root,
                filename
            )

            images.append(path)

    return sorted(images)


# ============================================================
# MAIN
# ============================================================

def main():

    print("WORDPRESS MEDIA PROBE")
    print("=====================")
    print()

    print(f"WordPress: {WP_URL}")
    print(f"Каталог:   {IMAGES_DIR}")
    print()

    if not os.path.exists(IMAGES_DIR):

        print(
            f"ОШИБКА: каталог не найден: "
            f"{IMAGES_DIR}"
        )

        return

    images = find_images(IMAGES_DIR)

    print(
        f"Найдено изображений: {len(images)}"
    )

    print()

    if not images:

        print("Изображения не найдены.")
        return

    results = []

    for number, image_path in enumerate(
        images,
        start=1
    ):

        print("=" * 70)
        print(f"IMAGE #{number}")
        print("=" * 70)

        print(
            f"Файл: {image_path}"
        )

        result = upload_image(
            image_path
        )

        if result:
            results.append(result)

    print()
    print("=" * 70)
    print("ИТОГ")
    print("=" * 70)

    print(
        f"Найдено:   {len(images)}"
    )

    print(
        f"Загружено: {len(results)}"
    )

    print(
        f"Ошибок:    "
        f"{len(images) - len(results)}"
    )

    print()

    for result in results:

        print(
            f"{result['filename']}"
            f" -> ID {result['id']}"
            f" -> {result['url']}"
        )

    print()
    print("Готово.")


if __name__ == "__main__":
    main()