import os

from eml_parser import extract_attachments
from eml_links import extract_vk_links


EML_FILE = r"ЗГП.eml"


def main():

    print("=" * 80)
    print("EMAIL → VK LINKS")
    print("=" * 80)

    if not os.path.exists(EML_FILE):
        print()
        print(f"ОШИБКА: файл не найден: {EML_FILE}")
        return

    # -------------------------
    # Читаем EML
    # -------------------------

    email_data = extract_attachments(
        EML_FILE
    )

    documents = email_data["documents"]

    print()
    print(f"Subject: {email_data['subject']}")
    print(f"DOCX: {len(documents)}")

    for document in documents:
        print(
            f"  - {document['filename']}"
        )

    # -------------------------
    # Ищем VK
    # -------------------------

    try:

        links = extract_vk_links(
            email_data,
            documents
        )

    except Exception as e:

        print()
        print("=" * 80)
        print("ОШИБКА СОПОСТАВЛЕНИЯ")
        print("=" * 80)
        print()
        print(e)
        return

    # -------------------------
    # Результат
    # -------------------------

    print()
    print("=" * 80)
    print("НАЙДЕННЫЕ VK ССЫЛКИ")
    print("=" * 80)

    if not links:

        print()
        print("VK wall-ссылки не найдены.")

        return

    for number, item in enumerate(
        links,
        start=1
    ):

        print()
        print(f"LINK #{number}")
        print("-" * 80)

        print(
            f"DOCX:   {item['document']}"
        )

        print(
            f"VK URL: {item['url']}"
        )

        print(
            f"Источник: {item['source']}"
        )

    print()
    print("=" * 80)
    print("Готово.")
    print("=" * 80)


if __name__ == "__main__":
    main()