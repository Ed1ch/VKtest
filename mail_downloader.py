import imaplib
import os


from config import (
    IMAP_HOST,
    IMAP_PORT,
    IMAP_USERNAME,
    IMAP_PASSWORD,
    IMAP_MAILBOX,
    IMAP_TRASH,
    IMAP_SUBJECT,
    IMAP_OUTPUT_DIR,
    IMAP_OUTPUT_FILE,
)


def download_news_email():
    """
    Находит последнее письмо с указанным Subject,
    сохраняет его как .eml и перемещает в корзину.

    Возвращает путь к сохранённому .eml.
    """

    os.makedirs(IMAP_OUTPUT_DIR, exist_ok=True)

    output_path = os.path.join(
        IMAP_OUTPUT_DIR,
        IMAP_OUTPUT_FILE,
    )

    mail = imaplib.IMAP4_SSL(
        IMAP_HOST,
        IMAP_PORT,
    )

    try:
        mail.login(
            IMAP_USERNAME,
            IMAP_PASSWORD,
        )

        status, _ = mail.select(IMAP_MAILBOX)

        if status != "OK":
            raise RuntimeError(
                f"Не удалось открыть почтовый ящик: {IMAP_MAILBOX}"
            )

        # Ищем письма с точным Subject.
        status, data = mail.search(
            None,
            "SUBJECT",
            f'"{IMAP_SUBJECT}"',
        )

        if status != "OK":
            raise RuntimeError(
                "Ошибка поиска писем."
            )

        message_ids = data[0].split()

        if not message_ids:
            print(
                f'Писем с темой "{IMAP_SUBJECT}" не найдено.'
            )
            return None

        # Берём последнее найденное письмо.
        message_id = message_ids[-1]

        status, data = mail.fetch(
            message_id,
            "(RFC822)",
        )

        if status != "OK":
            raise RuntimeError(
                "Не удалось получить письмо."
            )

        raw_email = None

        for response_part in data:
            if isinstance(response_part, tuple):
                raw_email = response_part[1]
                break

        if raw_email is None:
            raise RuntimeError(
                "IMAP не вернул содержимое письма."
            )

        # Сохраняем оригинальный RFC822 без изменений.
        with open(output_path, "wb") as f:
            f.write(raw_email)

        print(f"Письмо сохранено: {output_path}")

        # Перемещаем письмо в корзину.
        status, _ = mail.copy(
            message_id,
            IMAP_TRASH,
        )

        if status != "OK":
            raise RuntimeError(
                f"Не удалось скопировать письмо в корзину: "
                f"{IMAP_TRASH}"
            )

        # Помечаем оригинал на удаление.
        status, _ = mail.store(
            message_id,
            "+FLAGS",
            "\\Deleted",
        )

        if status != "OK":
            raise RuntimeError(
                "Не удалось пометить исходное письмо на удаление."
            )

        # Физически удаляем оригинал из INBOX.
        mail.expunge()

        print(
            f'Письмо с темой "{IMAP_SUBJECT}" '
            f"перемещено в корзину."
        )

        return output_path

    finally:
        try:
            mail.close()
        except Exception:
            pass

        mail.logout()


if __name__ == "__main__":
    download_news_email()