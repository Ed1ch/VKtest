import os
import re
import email
from email import policy
from email.parser import BytesParser
from io import BytesIO

from docx import Document


EML_FILE = r"ЗГП.eml"


def extract_docx_attachments(eml_path):
    """Извлекает DOCX-вложения из EML."""

    with open(eml_path, "rb") as f:
        msg = BytesParser(policy=policy.default).parse(f)

    documents = []

    for part in msg.walk():
        filename = part.get_filename()

        if not filename:
            continue

        if filename.lower().endswith(".docx"):
            data = part.get_payload(decode=True)

            if data:
                documents.append((filename, data))

    return documents


def read_docx(data):
    """Извлекает непустые абзацы из DOCX."""

    document = Document(BytesIO(data))

    paragraphs = []

    for paragraph in document.paragraphs:
        text = paragraph.text.strip()

        if text:
            paragraphs.append(text)

    return paragraphs


def split_news(paragraphs):
    """
    Правила:
    1. Первый абзац = title.
    2. Первое предложение после title = excerpt.
    3. Title в content не включается.
    4. Excerpt остаётся частью content.
    """

    if not paragraphs:
        raise ValueError("Документ не содержит текста.")

    title = paragraphs[0]

    content = "\n\n".join(paragraphs[1:]).strip()

    if not content:
        raise ValueError("После title нет текста.")

    # Ищем первое предложение.
    # Учитываем . ! ? и русские варианты с последующими кавычками/скобками.
    match = re.search(
        r".+?(?:[.!?]+(?:[»”\"]+)?(?:\s|$))",
        content,
        flags=re.DOTALL
    )

    if match:
        excerpt = match.group(0).strip()
    else:
        # Если предложение не удалось определить,
        # используем весь оставшийся текст.
        excerpt = content

    return {
        "title": title,
        "excerpt": excerpt,
        "content": content,
    }


def main():

    print("EML → DOCX → NEWS")
    print("==================")
    print(f"Файл: {EML_FILE}\n")

    if not os.path.exists(EML_FILE):
        print(f"ОШИБКА: файл не найден: {EML_FILE}")
        return

    documents = extract_docx_attachments(EML_FILE)

    print(f"Найдено DOCX-вложений: {len(documents)}\n")

    if not documents:
        print("DOCX-вложения не найдены.")
        return

    for number, (filename, data) in enumerate(documents, start=1):

        print("=" * 70)
        print(f"ДОКУМЕНТ #{number}: {filename}")
        print("=" * 70)

        try:
            paragraphs = read_docx(data)
            news = split_news(paragraphs)

            print("\nTITLE:")
            print(news["title"])

            print("\nEXCERPT:")
            print(news["excerpt"])

            print("\nCONTENT:")
            print(news["content"])

            print("\nКоличество абзацев:", len(paragraphs))
            print("Размер DOCX:", len(data), "байт")

        except Exception as e:
            print(f"\nОШИБКА обработки {filename}:")
            print(e)


if __name__ == "__main__":
    main()