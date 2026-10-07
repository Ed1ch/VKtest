import base64
import imaplib

from config import (
    IMAP_HOST,
    IMAP_PORT,
    IMAP_USERNAME,
    IMAP_PASSWORD,
    IMAP_TIMEOUT,
)


def decode_imap_utf7(value):
    result = ""
    i = 0

    while i < len(value):
        if value[i] != "&":
            result += value[i]
            i += 1
            continue

        end = value.find("-", i)

        if end == -1:
            result += value[i:]
            break

        if end == i + 1:
            result += "&"
        else:
            encoded = value[i + 1:end]
            encoded = encoded.replace(",", "/")

            padding = "=" * (
                (-len(encoded)) % 4
            )

            raw = base64.b64decode(
                encoded + padding
            )

            result += raw.decode("utf-16-be")

        i = end + 1

    return result


mail = imaplib.IMAP4_SSL(
    IMAP_HOST,
    IMAP_PORT,
    timeout=IMAP_TIMEOUT,
)

try:
    mail.login(
        IMAP_USERNAME,
        IMAP_PASSWORD,
    )

    status, folders = mail.list()

    print(f"LIST status: {status}")
    print()

    for folder in folders:
        raw = folder.decode(
            "ascii",
            errors="replace",
        )

        print("RAW:")
        print(raw)

        # Последняя часть строки LIST — имя mailbox.
        # Для нашей диагностики достаточно убрать кавычки
        # и декодировать всю строку: служебные части ASCII
        # останутся без изменений.
        print("DECODED:")
        print(decode_imap_utf7(raw))
        print()

finally:
    mail.logout()