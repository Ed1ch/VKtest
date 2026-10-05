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
    Убирает расширение и конечную цифру из имени изображения.

    Например:
        октябрь1.jpg -> октябрь
        октябрь2.jpg -> октябрь
        80 лет.jpg   -> 80 лет
    """
    base = os.path.splitext(name)[0]
    base = re.sub(r"\d+$", "", base)
    return base.strip()


def extract_attachments(eml_path):
    """Извлекает DOCX и изображения из EML."""

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


def read_docx(data):
    """Читает непустые абзацы DOCX."""

    document = Document(BytesIO(data))

    paragraphs = []

    for paragraph in document.paragraphs:
        text = paragraph.text.strip()

        if text:
            paragraphs.append(text)

    return paragraphs


def split_news(paragraphs):
    """
    Разбирает документ:

    paragraph[0] -> title
    первое предложение после title -> excerpt
    весь остальной текст после title -> content
    """

    if not paragraphs:
        raise ValueError("Документ не содержит текста.")

    title = paragraphs[0]

    content = "\n\n".join(paragraphs[1:]).strip()

    if not content:
        raise ValueError("После title нет текста.")

    match = re.search(
        r".+?(?:[.!?]+(?:[»”\"]+)?(?:\s|$))",
        content,
        flags=re.DOTALL
    )

    if match:
        excerpt = match.group(0).strip()
    else:
        excerpt = content

    return {
        "title": title,
        "excerpt": excerpt,
        "content": content,
    }


def natural_image_sort(images):
    """Сортирует изображения: image, image1, image2 ... image10."""

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
    """Сохраняет изображение в папку конкретной новости."""

    news_dir = os.path.join(OUTPUT_DIR, news_name)

    os.makedirs(news_dir, exist_ok=True)

    path = os.path.join(news_dir, image["filename"])

    with open(path, "wb") as f:
        f.write(image["data"])

    return path


def build_news(documents, images):
    """
    Формирует итоговую структуру новостей.

    Результат для каждой новости:

    {
        "title": "...",
        "excerpt": "...",
        "content": "...",
        "featured_image": "...",
        "gallery_images": [...],
        "gallery_columns": 3
    }
    """

    images_by_news = {}

    for image in images:
        news_name = normalize_name(image["filename"])

        if news_name not in images_by_news:
            images_by_news[news_name] = []

        images_by_news[news_name].append(image)

    news_list = []

    for document in documents:

        paragraphs = read_docx(document["data"])

        parsed = split_news(paragraphs)

        doc_filename = document["filename"]
        doc_base = os.path.splitext(doc_filename)[0]

        news_images = images_by_news.get(doc_base, [])

        news_images = natural_image_sort(news_images)

        featured_image = None
        gallery_images = []
        gallery_columns = None

        if len(news_images) == 1:

            featured_image = save_image(
                news_images[0],
                doc_base
            )

        elif len(news_images) > 1:

            featured_image = save_image(
                news_images[0],
                doc_base
            )

            for image in news_images:

                path = save_image(
                    image,
                    doc_base
                )

                gallery_images.append(path)

            gallery_columns = 3

        news = {
            "title": parsed["title"],
            "excerpt": parsed["excerpt"],
            "content": parsed["content"],
            "featured_image": featured_image,
            "gallery_images": gallery_images,
            "gallery_columns": gallery_columns,
        }

        news_list.append(news)

    return news_list


def print_news(news_list):

    print()
    print("=" * 80)
    print("ИТОГОВАЯ СТРУКТУРА НОВОСТЕЙ")
    print("=" * 80)

    for number, news in enumerate(news_list, start=1):

        print()
        print("-" * 80)
        print(f"NEWS #{number}")
        print("-" * 80)

        print()
        print("TITLE:")
        print(news["title"])

        print()
        print("EXCERPT:")
        print(news["excerpt"])

        print()
        print("CONTENT:")
        print(news["content"])

        print()
        print("FEATURED IMAGE:")
        print(news["featured_image"])

        print()
        print("GALLERY:")

        if news["gallery_images"]:

            print(f"  columns: {news['gallery_columns']}")

            for image in news["gallery_images"]:
                print(f"  - {image}")

        else:
            print("  none")


def main():

    print("EML → NEWS DATA")
    print("================")
    print(f"Файл: {EML_FILE}")
    print()

    if not os.path.exists(EML_FILE):
        print(f"ОШИБКА: файл не найден: {EML_FILE}")
        return

    documents, images = extract_attachments(EML_FILE)

    print(f"DOCX найдено: {len(documents)}")
    print(f"Изображений найдено: {len(images)}")

    if not documents:
        print("DOCX не найдены.")
        return

    news_list = build_news(
        documents,
        images
    )

    print(f"Новостей собрано: {len(news_list)}")

    print_news(news_list)

    print()
    print("=" * 80)
    print("Готово.")
    print("=" * 80)


if __name__ == "__main__":
    main()