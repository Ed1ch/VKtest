import os
from email import policy
from email.parser import BytesParser


EML_FILE = r"ЗГП.eml"

PREVIEW_LENGTH = 2000


def print_part(part, level=0):

    indent = "  " * level

    content_type = part.get_content_type()
    filename = part.get_filename()
    charset = part.get_content_charset()
    transfer_encoding = part.get(
        "Content-Transfer-Encoding"
    )

    print()
    print(
        f"{indent}CONTENT-TYPE: {content_type}"
    )

    print(
        f"{indent}FILENAME: {filename}"
    )

    print(
        f"{indent}CHARSET: {charset}"
    )

    print(
        f"{indent}TRANSFER-ENCODING: "
        f"{transfer_encoding}"
    )

    # Если это контейнер multipart,
    # рекурсивно показываем его содержимое.
    if part.is_multipart():

        print(
            f"{indent}MULTIPART: "
            f"{len(part.get_payload())} частей"
        )

        for child in part.iter_parts():

            print_part(
                child,
                level + 1
            )

        return

    # Нас интересуют прежде всего текстовые части.
    if content_type.startswith("text/"):

        try:
            text = part.get_content()

        except Exception as e:

            print(
                f"{indent}ОШИБКА ДЕКОДИРОВАНИЯ: {e}"
            )

            return

        print()
        print(
            f"{indent}----- НАЧАЛО ТЕКСТА -----"
        )

        print(
            text[:PREVIEW_LENGTH]
        )

        if len(text) > PREVIEW_LENGTH:

            print(
                f"\n{indent}..."
                f"ещё {len(text) - PREVIEW_LENGTH} "
                f"символов"
            )

        print(
            f"{indent}------ КОНЕЦ ТЕКСТА ------"
        )


def main():

    print("=" * 80)
    print("EML MIME DEBUG")
    print("=" * 80)

    print()
    print(
        f"Файл: {os.path.abspath(EML_FILE)}"
    )

    if not os.path.exists(EML_FILE):

        print()
        print(
            "ОШИБКА: файл не найден."
        )

        return

    with open(
        EML_FILE,
        "rb"
    ) as f:

        msg = BytesParser(
            policy=policy.default
        ).parse(f)

    print()
    print(
        "Корневой Content-Type:",
        msg.get_content_type()
    )

    print()
    print("=" * 80)
    print("СТРУКТУРА MIME")
    print("=" * 80)

    print_part(msg)

    print()
    print("=" * 80)
    print("ПОИСК VK")
    print("=" * 80)

    # Ищем непосредственно в декодированном
    # текстовом содержимом MIME-частей.
    found = []

    for part in msg.walk():

        if not part.get_content_type().startswith(
            "text/"
        ):
            continue

        try:
            text = part.get_content()
        except Exception:
            continue

        if "vk" in text.lower():

            found.append(
                (
                    part.get_content_type(),
                    text
                )
            )

    if not found:

        print()
        print(
            "В текстовых MIME-частях "
            "строка 'vk' НЕ найдена."
        )

    else:

        print()
        print(
            f"Текстовых частей с 'vk': "
            f"{len(found)}"
        )

        for number, (content_type, text) in enumerate(
            found,
            start=1
        ):

            print()
            print(
                f"--- MIME #{number}: "
                f"{content_type} ---"
            )

            # Показываем строки, содержащие vk.
            for line in text.splitlines():

                if "vk" in line.lower():

                    print(line)


if __name__ == "__main__":
    main()