import base64
import imaplib
import os
import socket
import time
from email import message_from_bytes
from email.header import decode_header, make_header

from config import (
    IMAP_HOST,
    IMAP_PORT,
    IMAP_USERNAME,
    IMAP_PASSWORD,
    IMAP_MAILBOX,
    IMAP_TRASH,
    IMAP_SUBJECT,
    IMAP_OUTPUT_DIR,
    IMAP_TIMEOUT,
    IMAP_RETRY_COUNT,
    IMAP_RETRY_DELAY,
)


def print_header(title):
    print()
    print("=" * 80)
    print(title)
    print("=" * 80)


def ensure_ok(status, message):
    if status != "OK":
        raise RuntimeError(message)


def encode_imap_utf7(value):
    """Кодирует человекочитаемое имя IMAP-папки в Modified UTF-7."""
    result = []
    buffer = []

    def flush_buffer():
        if not buffer:
            return

        text = "".join(buffer)
        encoded = base64.b64encode(
            text.encode("utf-16-be")
        ).decode("ascii")
        encoded = encoded.rstrip("=").replace("/", ",")
        result.append(f"&{encoded}-")
        buffer.clear()

    for char in value:
        code = ord(char)

        if 0x20 <= code <= 0x7E:
            flush_buffer()
            result.append("&-" if char == "&" else char)
        else:
            buffer.append(char)

    flush_buffer()
    return "".join(result)


def mailbox_arg(value):
    """Готовит имя mailbox для передачи imaplib, включая имена с пробелами."""
    encoded = encode_imap_utf7(value)
    encoded = encoded.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{encoded}"'


def close_mail(mail):
    if mail is None:
        return

    try:
        mail.close()
    except Exception:
        pass

    try:
        mail.logout()
    except Exception:
        pass


def connect_mail():
    """Создаёт IMAP SSL-соединение, авторизуется и открывает рабочий mailbox."""
    mail = imaplib.IMAP4_SSL(
        IMAP_HOST,
        IMAP_PORT,
        timeout=IMAP_TIMEOUT,
    )

    try:
        status, _ = mail.login(
            IMAP_USERNAME,
            IMAP_PASSWORD,
        )
        ensure_ok(status, "Ошибка IMAP-авторизации.")

        status, _ = mail.select(
            mailbox_arg(IMAP_MAILBOX)
        )
        ensure_ok(
            status,
            f"Не удалось открыть почтовый ящик: {IMAP_MAILBOX}",
        )

        return mail

    except Exception:
        close_mail(mail)
        raise


def decode_subject(raw_headers):
    """Декодирует MIME Subject в обычную Unicode-строку."""
    message = message_from_bytes(raw_headers)
    raw_subject = message.get("Subject", "")

    try:
        return str(make_header(decode_header(raw_subject)))
    except Exception:
        return raw_subject


def extract_raw_email(data):
    for response_part in data:
        if (
            isinstance(response_part, tuple)
            and len(response_part) >= 2
            and isinstance(response_part[1], (bytes, bytearray))
        ):
            return bytes(response_part[1])

    raise RuntimeError("IMAP не вернул содержимое письма.")


def search_unseen_news(mail):
    """
    Возвращает список (uid, subject) для UNSEEN-писем, в Subject которых
    локально найдено IMAP_SUBJECT.

    Серверу не передаётся кириллический критерий SUBJECT: сначала выполняется
    UID SEARCH UNSEEN, затем заголовок Subject читается через BODY.PEEK.
    """
    status, data = mail.uid(
        "search",
        None,
        "UNSEEN",
    )
    ensure_ok(
        status,
        "Ошибка поиска непрочитанных писем в IMAP.",
    )

    if not data or not data[0]:
        return []

    uid_values = data[0].split()
    matches = []

    # UID растут по мере добавления писем в mailbox. Сортировка по числу
    # гарантирует, что сначала будет обработано самое старое письмо.
    uid_values.sort(key=lambda value: int(value))

    for uid_bytes in uid_values:
        uid = uid_bytes.decode("ascii")

        status, fetch_data = mail.uid(
            "fetch",
            uid,
            "(BODY.PEEK[HEADER.FIELDS (SUBJECT)])",
        )
        ensure_ok(
            status,
            f"Не удалось получить Subject письма UID {uid}.",
        )

        try:
            raw_headers = extract_raw_email(fetch_data)
        except RuntimeError:
            print(f"UID {uid}: Subject получить не удалось, письмо пропущено.")
            continue

        subject = decode_subject(raw_headers)

        if IMAP_SUBJECT.casefold() in subject.casefold():
            matches.append((uid, subject))

    return matches


def find_oldest_unseen():
    """Возвращает (uid, subject) самого старого подходящего UNSEEN-письма."""
    mail = None

    try:
        mail = connect_mail()
        matches = search_unseen_news(mail)

        if not matches:
            return None

        return matches[0]

    finally:
        close_mail(mail)


def cleanup_part(temp_path):
    if not temp_path or not os.path.exists(temp_path):
        return

    try:
        os.remove(temp_path)
        print(f"Временный файл удалён: {temp_path}")
    except OSError as error:
        print(f"Не удалось удалить временный файл {temp_path}: {error}")


def download_by_uid(mail, uid):
    """
    Скачивает письмо по UID через BODY.PEEK[], не выставляя флаг \\Seen.
    Сначала пишет .part, затем атомарно заменяет готовый .eml.
    """
    os.makedirs(IMAP_OUTPUT_DIR, exist_ok=True)

    filename = f"ЗГП_{uid}.eml"
    output_path = os.path.join(IMAP_OUTPUT_DIR, filename)
    temp_path = output_path + ".part"

    cleanup_part(temp_path)

    try:
        status, data = mail.uid(
            "fetch",
            str(uid),
            "(BODY.PEEK[])",
        )
        ensure_ok(
            status,
            f"Не удалось получить содержимое письма UID {uid}.",
        )

        raw_email = extract_raw_email(data)

        with open(temp_path, "wb") as file:
            file.write(raw_email)
            file.flush()
            os.fsync(file.fileno())

        os.replace(temp_path, output_path)
        return output_path

    except Exception:
        cleanup_part(temp_path)
        raise


def mark_seen_by_uid(mail, uid):
    status, _ = mail.uid(
        "store",
        str(uid),
        "+FLAGS",
        "(\\Seen)",
    )
    ensure_ok(
        status,
        f"Не удалось пометить письмо UID {uid} как прочитанное.",
    )


def move_to_trash_by_uid(mail, uid):
    """
    Реально перемещает письмо в корзину: COPY -> \\Deleted -> EXPUNGE.
    IMAP_TRASH хранится в config.py в человекочитаемом виде и здесь
    автоматически преобразуется в Modified UTF-7.
    """
    trash_arg = mailbox_arg(IMAP_TRASH)

    status, _ = mail.uid(
        "copy",
        str(uid),
        trash_arg,
    )
    ensure_ok(
        status,
        f"Не удалось скопировать письмо UID {uid} в корзину: {IMAP_TRASH}",
    )

    status, _ = mail.uid(
        "store",
        str(uid),
        "+FLAGS",
        "(\\Deleted)",
    )
    ensure_ok(
        status,
        f"Не удалось пометить письмо UID {uid} на удаление.",
    )

    status, _ = mail.expunge()
    ensure_ok(status, "Ошибка EXPUNGE.")


def download_with_retries(uid):
    """
    Пытается скачать письмо до IMAP_RETRY_COUNT раз.
    Retry относится только к скачиванию .eml.
    """
    last_error = None

    for attempt in range(1, IMAP_RETRY_COUNT + 1):
        mail = None
        print()
        print(f"Попытка скачивания {attempt}/{IMAP_RETRY_COUNT}...")

        try:
            mail = connect_mail()
            output_path = download_by_uid(mail, uid)
            print(f"Письмо скачано: {output_path}")
            return output_path

        except (
            TimeoutError,
            socket.timeout,
            imaplib.IMAP4.abort,
            imaplib.IMAP4.error,
            OSError,
            RuntimeError,
        ) as error:
            last_error = error
            print(
                f"Ошибка попытки {attempt}/{IMAP_RETRY_COUNT}: {error}"
            )

        finally:
            close_mail(mail)

        if attempt < IMAP_RETRY_COUNT:
            print(f"Повтор через {IMAP_RETRY_DELAY} сек.")
            time.sleep(IMAP_RETRY_DELAY)

    print()
    print(
        f"Все {IMAP_RETRY_COUNT} попытки для UID {uid} завершились ошибкой."
    )

    mail = None
    try:
        mail = connect_mail()
        print(
            f"Помечаем UID {uid} как прочитанное и оставляем в {IMAP_MAILBOX}..."
        )
        mark_seen_by_uid(mail, uid)
        print(f"UID {uid}: SEEN + {IMAP_MAILBOX}.")
    finally:
        close_mail(mail)

    if last_error is not None:
        print(
            f"Последняя ошибка: {type(last_error).__name__}: {last_error}"
        )

    return None


def finish_test_message(uid):
    """
    В автономном тесте успешное скачивание считается успешной обработкой,
    поэтому письмо реально переносится в корзину.
    """
    mail = None

    try:
        mail = connect_mail()
        print(f"Перемещение UID {uid} в корзину {IMAP_TRASH}...")
        move_to_trash_by_uid(mail, uid)
        print(f"Письмо UID {uid} перемещено в корзину.")
    finally:
        close_mail(mail)


def main():
    print("=" * 80)
    print("MAIL DOWNLOADER TEST")
    print("=" * 80)
    print()

    print(f"IMAP: {IMAP_HOST}:{IMAP_PORT}")
    print(f"Пользователь: {IMAP_USERNAME}")
    print(f"Mailbox: {IMAP_MAILBOX}")
    print(f"Корзина: {IMAP_TRASH}")
    print(f"Subject содержит: {IMAP_SUBJECT!r}")
    print(f"Папка .eml: {IMAP_OUTPUT_DIR}")
    print(f"Timeout: {IMAP_TIMEOUT} сек.")
    print(f"Retry: {IMAP_RETRY_COUNT}")
    print(f"Задержка retry: {IMAP_RETRY_DELAY} сек.")

    processed = 0
    failed = 0

    while True:
        print_header("ПОИСК НЕПРОЧИТАННОГО ПИСЬМА")

        found = find_oldest_unseen()

        if found is None:
            print(
                f"Непрочитанных писем с {IMAP_SUBJECT!r} "
                f"в {IMAP_MAILBOX} больше нет."
            )
            break

        uid, subject = found
        print(f"Найдено самое старое подходящее письмо: UID {uid}")
        print(f"Subject: {subject}")

        output_path = download_with_retries(uid)

        if output_path is None:
            failed += 1
            print()
            print("Письмо пропущено после неудачных попыток.")
            print(
                f"Оно осталось в {IMAP_MAILBOX} как SEEN; "
                "переходим к следующему UNSEEN."
            )
            continue

        # В production здесь будет запуск остального конвейера.
        # В автономном тесте успешное скачивание считаем успешной обработкой.
        finish_test_message(uid)
        processed += 1

        print()
        print("Тестовая обработка письма завершена успешно.")
        print(f"Локальный .eml оставлен: {output_path}")

    print_header("ГОТОВО")
    print(f"Успешно скачано и перемещено в корзину: {processed}")
    print(f"Оставлено в {IMAP_MAILBOX} как SEEN после ошибок: {failed}")
    print()
    print("Конвейер обработки .eml в тестовом модуле не запускался.")


if __name__ == "__main__":
    main()
