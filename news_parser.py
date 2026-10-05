import os
import re
import shutil
import subprocess
import tempfile

from docx import Document
from io import BytesIO

from eml_parser import save_image


def normalize_name(name):
    base = os.path.splitext(name)[0]

    base = re.sub(
        r"\d+$",
        "",
        base
    )

    return base.strip()


def check_pandoc():
    """
    Проверяет наличие Pandoc в PATH.
    """

    if not shutil.which("pandoc"):
        raise RuntimeError(
            "Pandoc не найден.\n"
            "Установите Pandoc и убедитесь, что он доступен "
            "из командной строки.\n\n"
            "Windows: pandoc.org/installing.html\n"
            "Debian: sudo apt install pandoc"
        )


def convert_docx_to_html(data):
    """
    Конвертирует DOCX в HTML через Pandoc.
    """

    check_pandoc()

    with tempfile.NamedTemporaryFile(
        suffix=".docx",
        delete=False
    ) as temp_file:

        temp_path = temp_file.name

        temp_file.write(data)

    try:

        result = subprocess.run(
            [
                "pandoc",
                temp_path,
                "--from=docx",
                "--to=html",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

        if result.returncode != 0:

            error = result.stderr.strip()

            raise RuntimeError(
                "Ошибка Pandoc при конвертации DOCX:\n"
                + error
            )

        return result.stdout.strip()

    finally:

        try:
            os.remove(temp_path)
        except OSError:
            pass


def extract_title_and_content(data):
    """
    Получает title из первого непустого абзаца DOCX,
    а остальной документ конвертирует Pandoc в HTML.
    """

    document = Document(
        BytesIO(data)
    )

    paragraphs = [
        paragraph.text.strip()
        for paragraph in document.paragraphs
        if paragraph.text.strip()
    ]

    if not paragraphs:
        raise ValueError(
            "Документ не содержит текста."
        )

    title = paragraphs[0]

    html_content = convert_docx_to_html(data)

    if not html_content:
        raise ValueError(
            "Pandoc не вернул HTML."
        )

    return title, html_content


def html_to_plain_text(html_content):
    """
    Упрощённо удаляет HTML-теги для построения excerpt.
    """

    text = re.sub(
        r"<br\s*/?>",
        "\n",
        html_content,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"</p\s*>",
        "\n\n",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"<[^>]+>",
        "",
        text
    )

    # HTML entities
    import html

    text = html.unescape(text)

    text = re.sub(
        r"[ \t]+",
        " ",
        text
    )

    text = re.sub(
        r"\n\s*\n+",
        "\n\n",
        text
    )

    return text.strip()


def build_excerpt(html_content):
    """
    Берёт первое предложение из текста статьи.
    """

    plain_content = html_to_plain_text(
        html_content
    )

    if not plain_content:
        return ""

    match = re.search(
        r".+?(?:[.!?]+(?:[»”\"]+)?(?:\s|$))",
        plain_content,
        flags=re.DOTALL
    )

    if match:
        return match.group(0).strip()

    return plain_content


def read_docx(data):
    """
    Возвращает title, HTML и excerpt.
    """

    title, html_content = extract_title_and_content(
        data
    )

    # Первый абзац уже является title.
    # Убираем его из HTML-контента Pandoc,
    # чтобы WordPress не дублировал заголовок.
    html_content = re.sub(
    r"^\s*<p>.*?</p>\s*",
    "",
    html_content,
    count=1,
    flags=re.IGNORECASE | re.DOTALL
    )

    if not html_content.strip():
        raise ValueError(
            "После title нет текста."
        )

    excerpt = build_excerpt(
        html_content
    )

    return {
        "title": title,
        "excerpt": excerpt,
        "content": html_content,
    }


def natural_image_sort(images):

    def sort_key(image):

        filename = image["filename"]

        base = os.path.splitext(
            filename
        )[0]

        match = re.search(
            r"(\d+)$",
            base
        )

        if match:
            number = int(
                match.group(1)
            )
        else:
            number = 0

        return number

    return sorted(
        images,
        key=sort_key
    )


def build_news(documents, images):

    images_by_news = {}

    for image in images:

        news_name = normalize_name(
            image["filename"]
        )

        images_by_news.setdefault(
            news_name,
            []
        ).append(image)

    news_list = []

    for document in documents:

        parsed = read_docx(
            document["data"]
        )

        doc_filename = document["filename"]

        doc_base = os.path.splitext(
            doc_filename
        )[0]

        news_images = images_by_news.get(
            doc_base,
            []
        )

        news_images = natural_image_sort(
            news_images
        )

        featured_image = None
        gallery_images = []

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

                gallery_images.append(
                    path
                )

        news_list.append({

            "document_filename":
                document["filename"],

            "title":
                parsed["title"],

            "excerpt":
                parsed["excerpt"],

            "content":
                parsed["content"],

            "featured_image":
                featured_image,

            "gallery_images":
                gallery_images,

            "gallery_columns":
                3,
        })

    return news_list
