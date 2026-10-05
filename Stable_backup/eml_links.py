import html
import os
import re


# =========================
# VK WALL URL
# =========================

VK_WALL_RE = re.compile(
    r'https?://[^\s<>"\']*wall-?\d+_\d+',
    re.IGNORECASE
)


# =========================
# НОРМАЛИЗАЦИЯ ИМЕНИ
# =========================

def normalize_name(name):
    """
    Нормализует имя DOCX или ключ поиска.

    Например:

        "атмосфера.docx" -> "атмосфера"
        "АТМОСФЕРА"       -> "атмосфера"
        "Октябрь.docx"    -> "октябрь"

    Убираются:
        - расширение
        - лишние пробелы
        - HTML entities
    """

    name = html.unescape(name)

    name = os.path.splitext(name)[0]

    name = name.strip().lower()

    # Разные виды пробелов превращаем
    # в обычный пробел.
    name = re.sub(
        r'\s+',
        ' ',
        name
    )

    return name


# =========================
# HTML → TEXT
# =========================

def html_to_text(value):
    """
    Превращает HTML-тело письма в текст.

    Важно:
    href VK-ссылки сохраняется как текст,
    поскольку в нашем письме URL присутствует
    непосредственно внутри <a>.
    """

    value = re.sub(
        r'<[^>]+>',
        ' ',
        value
    )

    value = html.unescape(value)

    value = re.sub(
        r'\s+',
        ' ',
        value
    )

    return value.strip()


# =========================
# ИСТОЧНИКИ ПИСЬМА
# =========================

def build_search_text(email_data):
    """
    Формирует единый текст для поиска.

    Используются:

        Subject
        text/plain
        text/html

    Возвращает список источников, чтобы потом
    можно было нормально диагностировать,
    где именно было найдено совпадение.
    """

    sources = []

    subject = email_data.get(
        "subject",
        ""
    )

    if subject:
        sources.append({
            "name": "Subject",
            "text": subject,
        })

    text = email_data.get(
        "text",
        ""
    )

    if text:
        sources.append({
            "name": "text/plain",
            "text": text,
        })

    html_source = email_data.get(
        "html",
        ""
    )

    if html_source:

        sources.append({
            "name": "text/html",
            "text": html_to_text(
                html_source
            ),
        })

    return sources


# =========================
# ПОИСК VK ССЫЛОК
# =========================

def find_vk_links(text):
    """
    Возвращает VK wall-ссылки
    с их позициями в тексте.
    """

    return list(
        VK_WALL_RE.finditer(text)
    )


# =========================
# БЛИЖАЙШАЯ VK ССЫЛКА ПЕРЕД ИМЕНЕМ
# =========================

def find_previous_vk_link(
    text,
    position
):
    """
    Ищет ближайшую VK wall-ссылку,
    расположенную ПЕРЕД указанной позицией.

    Например:

        URL1
        текст
        АТМОСФЕРА
        URL2
        текст
        ОКТЯБРЬ

    Для АТМОСФЕРА будет найдена URL1.
    Для ОКТЯБРЬ будет найдена URL2.
    """

    matches = list(
        VK_WALL_RE.finditer(
            text,
            0,
            position
        )
    )

    if not matches:
        return None

    return matches[-1]


# =========================
# ПОИСК ИМЕНИ DOCX
# =========================

def find_document_occurrences(
    text,
    documents
):
    """
    Ищет нормализованные имена всех DOCX
    в переданном тексте.

    Возвращает список найденных совпадений.
    """

    occurrences = []

    normalized_documents = []

    for document in documents:

        filename = document["filename"]

        normalized = normalize_name(
            filename
        )

        if not normalized:
            continue

        normalized_documents.append({
            "filename": filename,
            "normalized": normalized,
        })

    # Более длинные имена ищем первыми.
    #
    # Это предотвращает ситуацию, когда,
    # например, "октябрь" перехватывает
    # более длинное имя "октябрь 2026".
    normalized_documents.sort(
        key=lambda x: len(x["normalized"]),
        reverse=True
    )

    for document in normalized_documents:

        pattern = re.compile(
            re.escape(
                document["normalized"]
            ),
            re.IGNORECASE
        )

        for match in pattern.finditer(text):

            occurrences.append({
                "filename": document["filename"],
                "normalized": document["normalized"],
                "start": match.start(),
                "end": match.end(),
            })

    return occurrences


# =========================
# ОСНОВНАЯ ОБРАБОТКА
# =========================

def extract_vk_links(
    email_data,
    documents
):
    """
    Находит VK-ссылки и сопоставляет их
    с DOCX по именам файлов.

    Алгоритм:

        DOCX name
            ↓
        поиск имени в Subject/text/html
            ↓
        ближайшая VK-ссылка ПЕРЕД именем
            ↓
        DOCX ↔ VK URL

    Если имя DOCX найдено, но перед ним
    нет VK-ссылки, генерируется ошибка.

    Одинаковые пары DOCX + VK URL
    удаляются.
    """

    sources = build_search_text(
        email_data
    )

    # Уникальные пары:
    #
    # (filename, url)
    #
    unique_pairs = {}

    errors = []

    # -------------------------
    # Обрабатываем каждый источник
    # -------------------------

    for source in sources:

        source_name = source["name"]
        text = source["text"]

        if not text:
            continue

        # -------------------------
        # Ищем имена DOCX
        # -------------------------

        occurrences = find_document_occurrences(
            text,
            documents
        )

        # -------------------------
        # Для каждого имени
        # ищем VK перед ним
        # -------------------------

        for occurrence in occurrences:

            filename = occurrence["filename"]
            position = occurrence["start"]

            vk_match = find_previous_vk_link(
                text,
                position
            )

            if vk_match is None:

                errors.append(
                    {
                        "document": filename,
                        "source": source_name,
                        "message": (
                            f'Найдено имя DOCX '
                            f'"{filename}", '
                            f'но перед ним не найдена '
                            f'VK wall-ссылка.'
                        ),
                    }
                )

                continue

            url = vk_match.group(0)

            key = (
                filename.lower(),
                url.lower(),
            )

            if key not in unique_pairs:

                unique_pairs[key] = {
                    "document": filename,
                    "url": url,
                    "source": source_name,
                }

    # -------------------------
    # Если есть ошибки,
    # прекращаем обработку
    # -------------------------

    if errors:

        lines = [
            "Не удалось сопоставить все VK-ссылки "
            "с DOCX."
        ]

        for error in errors:

            lines.append(
                f'\nDOCX: {error["document"]}'
            )

            lines.append(
                f'Источник: {error["source"]}'
            )

            lines.append(
                f'Ошибка: {error["message"]}'
            )

        raise RuntimeError(
            "\n".join(lines)
        )

    return list(
        unique_pairs.values()
    )