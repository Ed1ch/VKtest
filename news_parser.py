import os
import re
import shutil
import subprocess
import tempfile

from docx import Document
from io import BytesIO

from eml_parser import save_image


def normalize_match_words(filename):
    """
    Приводит имя файла к набору значимых слов для сопоставления.

    Правила нормализации изолированы здесь, чтобы их можно было
    расширять по результатам ручного тестирования.
    """
    base = os.path.splitext(filename)[0].casefold()

    base = re.sub(r"[_-]+", " ", base)
    base = re.sub(r"\d+", " ", base)
    base = re.sub(r"[^a-zа-яё\s]", " ", base)
    base = re.sub(r"\s+", " ", base).strip()

    return set(base.split())


def get_numeric_only_name(filename):
    """
    Возвращает имя как число, если до расширения находятся только цифры.
    """
    base = os.path.splitext(filename)[0].strip()

    if re.fullmatch(r"\d+", base):
        return base

    return None


def names_match(document_filename, image_filename):
    """
    Определяет, относится ли изображение к документу.

    Для текстовых имён все слова документа должны присутствовать
    в нормализованном имени изображения. Для чисто числовых имён
    используется точное сравнение числа.
    """
    doc_words = normalize_match_words(document_filename)
    image_words = normalize_match_words(image_filename)

    if doc_words:
        return doc_words.issubset(image_words)

    doc_number = get_numeric_only_name(document_filename)
    image_number = get_numeric_only_name(image_filename)

    return (
        doc_number is not None
        and image_number is not None
        and doc_number == image_number
    )


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


def normalize_html_whitespace(html_content):
    """
    Убирает физические переводы строк и лишние пробелы
    из HTML, не изменяя структуру тегов.
    """

    return re.sub(
        r"\s+",
        " ",
        html_content
    ).strip()


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


def html_to_plain_text(html_content):
    """
    Преобразует HTML в обычный текст для excerpt.
    """

    import html

    text = html_content

    # Абзацы превращаем в разделители текста.
    text = re.sub(
        r"<p\b[^>]*>",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"</p\s*>",
        "\n\n",
        text,
        flags=re.IGNORECASE
    )

    # Переносы строк HTML.
    text = re.sub(
        r"<br\s*/?>",
        "\n",
        text,
        flags=re.IGNORECASE
    )

    # Удаляем остальные HTML-теги.
    text = re.sub(
        r"<[^>]+>",
        "",
        text
    )

    # HTML entities: &quot;, &amp;, &nbsp; и т.д.
    text = html.unescape(text)

    # Неразрывные пробелы превращаем в обычные.
    text = text.replace(
        "\xa0",
        " "
    )

    # Убираем лишние пробелы.
    text = re.sub(
        r"[ \t]+",
        " ",
        text
    )

    # Нормализуем пустые строки.
    text = re.sub(
        r"\n\s*\n+",
        "\n\n",
        text
    )

    return text.strip()


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

    title = re.sub(
        r"\s+",
        " ",
        paragraphs[0]
    ).strip()

    html_content = convert_docx_to_html(data)

    if not html_content:
        raise ValueError(
            "Pandoc не вернул HTML."
        )

    return title, html_content



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
        r"\s+",
        " ",
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

    # Убираем физические переводы строк
    # и лишние пробелы из HTML.
    html_content = normalize_html_whitespace(
        html_content
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

    news_list = []

    for document in documents:

        parsed = read_docx(
            document["data"]
        )

        doc_filename = document["filename"]

        doc_base = os.path.splitext(
            doc_filename
        )[0]

        news_images = [
            image
            for image in images
            if names_match(
                doc_filename,
                image["filename"]
            )
        ]

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
