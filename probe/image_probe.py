import os
import re
from io import BytesIO
from email import policy
from email.parser import BytesParser

from docx import Document


EML_FILE = r"ЗГП.eml"
OUTPUT_DIR = r"extracted_images"

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".gif",
}


def normalize_name(name):
    """
    Приводит имя файла к базовому имени новости.

    Например:
        "октябрь.jpg"   -> "октябрь"
        "октябрь1.jpg"  -> "октябрь"
        "октябрь2.jpg"  -> "октябрь"
        "80 лет.jpg"    -> "80 лет"
    """

    base = os.path.splitext(name)[0]

    # Убираем номер в конце имени:
    # новость1 -> новость
    # новость2 -> новость
    # новость10 -> новость
    base = re.sub(r"\d+$", "", base)

    return base.strip()


def extract_attachments(eml_path):
    """
    Извлекает DOCX и изображения из EML.
    """

    with open(eml_path, "rb") as f:
        msg = BytesParser(policy=policy.default).parse(f)

    documents = []
    images = []

    for part in msg.walk():

        filename = part.get_filename()

        if not filename:
            continue

        filename = os.path.basename(filename)
        extension = os.path.splitext(filename)[1].lower()

        data = part.get_payload(decode=True)

        if not data:
            continue

        if extension == ".docx":
            documents.append({
                "filename": filename,
                "data": data,
            })

        elif extension in IMAGE_EXTENSIONS:
            images.append({
                "filename": filename,
                "data": data,
            })

    return documents, images


def get_news_titles(documents):
    """
    Получает название новости из первого непустого
    абзаца каждого DOCX.
    """

    news = []

    for document in documents:

        doc = Document(BytesIO(document["data"]))

        title = None

        for paragraph in doc.paragraphs:

            text = paragraph.text.strip()

            if text:
                title = text
                break

        if title:
            news.append({
                "title": title,
                "doc_filename": document["filename"],
            })

    return news


def natural_image_sort(images):
    """
    Сортировка:

        октябрь.jpg
        октябрь1.jpg
        октябрь2.jpg
        ...
        октябрь10.jpg

    вместо обычной сортировки:

        октябрь.jpg
        октябрь1.jpg
        октябрь10.jpg
        октябрь2.jpg
    """

    def sort_key(image):

        filename = image["filename"]
        base = os.path.splitext(filename)[0]

        match = re.search(r"(\d+)$", base)

        if match:
            number = int(match.group(1))
        else:
            number = 0

        return number

    return sorted(images, key=sort_key)


def save_image(image, news_name):
    """
    Сохраняет изображение в папку соответствующей новости.
    """

    news_dir = os.path.join(OUTPUT_DIR, news_name)

    os.makedirs(news_dir, exist_ok=True)

    path = os.path.join(
        news_dir,
        image["filename"]
    )

    with open(path, "wb") as f:
        f.write(image["data"])

    return path


def main():

    print("EML → NEWS → IMAGES")
    print("===================")
    print(f"Файл: {EML_FILE}")
    print()

    if not os.path.exists(EML_FILE):
        print(f"ОШИБКА: файл не найден: {EML_FILE}")
        return

    documents, images = extract_attachments(EML_FILE)

    print(f"DOCX найдено: {len(documents)}")
    print(f"Изображений найдено: {len(images)}")
    print()

    if not documents:
        print("DOCX не найдены.")
        return

    news = get_news_titles(documents)

    print(f"Новостей найдено: {len(news)}")
    print()

    # Группируем изображения по имени новости
    images_by_news = {}

    for image in images:

        news_name = normalize_name(image["filename"])

        if news_name not in images_by_news:
            images_by_news[news_name] = []

        images_by_news[news_name].append(image)

    # Создаём структуру новостей
    for item in news:

        title = item["title"]

        # Ищем изображения по имени DOCX.
        doc_base = os.path.splitext(
            item["doc_filename"]
        )[0]

        news_images = images_by_news.get(
            doc_base,
            []
        )

        news_images = natural_image_sort(news_images)

        print("=" * 70)
        print(f"NEWS: {title}")
        print(f"DOCX: {item['doc_filename']}")
        print(f"IMAGES: {len(news_images)}")

        if not news_images:

            print("FEATURED: none")
            print("GALLERY: no")

        elif len(news_images) == 1:

            image = news_images[0]

            path = save_image(image, doc_base)

            print(f"FEATURED: {image['filename']}")
            print("GALLERY: no")
            print(f"SAVED: {path}")

        else:

            featured = news_images[0]

            print(f"FEATURED: {featured['filename']}")
            print("GALLERY: 3 columns")
            print("GALLERY ITEMS:")

            for number, image in enumerate(news_images, start=1):

                path = save_image(image, doc_base)

                print(
                    f"  {number}. "
                    f"{image['filename']}"
                )

                print(
                    f"     SAVED: {path}"
                )

    print()
    print("=" * 70)
    print("Готово.")
    print(f"Изображения сохранены в: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()