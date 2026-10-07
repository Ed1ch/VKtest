import html
import mimetypes
import os
import requests

from config import OUTPUT_DIR

from mail_downloader import (
    download_news_email,
    mark_email_failed,
    mark_email_processed,
)

from eml_parser import extract_attachments
from eml_links import (
    extract_vk_links,
    extract_vk_links_from_docx,
)
from news_parser import build_news

from image_manager import (
    upload_media,
    upload_media_bytes,
)

from wordpress import create_post

from vk_video import (
    get_vk_video_from_post,
)


LOCK_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    ".main.lock",
)


def acquire_process_lock():
    """
    Захватывает системный lock для единственного экземпляра main.py.

    Сам файл .main.lock может оставаться на диске после завершения.
    Важен не факт его существования, а системная блокировка файла,
    которая автоматически освобождается ОС при завершении процесса.
    """
    lock_file = open(
        LOCK_FILE,
        "a+",
        encoding="utf-8",
    )

    lock_file.seek(0, os.SEEK_END)

    if lock_file.tell() == 0:
        lock_file.write("0")
        lock_file.flush()

    lock_file.seek(0)

    try:
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(
                lock_file.fileno(),
                msvcrt.LK_NBLCK,
                1,
            )
        else:
            import fcntl

            fcntl.flock(
                lock_file.fileno(),
                fcntl.LOCK_EX | fcntl.LOCK_NB,
            )

    except (OSError, IOError):
        lock_file.close()
        return None

    return lock_file


def release_process_lock(lock_file):
    if lock_file is None:
        return

    try:
        lock_file.seek(0)

        if os.name == "nt":
            import msvcrt

            msvcrt.locking(
                lock_file.fileno(),
                msvcrt.LK_UNLCK,
                1,
            )
        else:
            import fcntl

            fcntl.flock(
                lock_file.fileno(),
                fcntl.LOCK_UN,
            )
    finally:
        lock_file.close()


def download_vk_preview(url):
    response = requests.get(
        url,
        timeout=30
    )

    response.raise_for_status()

    content_type = response.headers.get(
        "Content-Type",
        "image/jpeg"
    )

    extension = (
        mimetypes.guess_extension(
            content_type.split(";")[0]
        )
        or ".jpg"
    )

    return (
        response.content,
        content_type,
        extension
    )


def process_vk(
    news,
    vk_info,
    force_preview_as_featured=False
):
    if not vk_info:
        return

    url = vk_info["url"]

    print(f"VK URL: {url}")

    vk_data = get_vk_video_from_post(url)

    news["vk_data"] = vk_data

    player = vk_data.get("player")

    if player:
        news["vk_embed"] = (
            f'<iframe '
            f'src="{html.escape(player)}" '
            f'width="640" '
            f'height="360" '
            f'frameborder="0" '
            f'allowfullscreen></iframe>'
        )

    preview = vk_data.get("preview")

    if not preview:
        return

    use_preview = (
        force_preview_as_featured
        or not news.get("featured_image")
    )

    if not use_preview:
        return

    print("Загрузка VK preview...")

    preview_data, mime_type, extension = (
        download_vk_preview(preview)
    )

    media = upload_media_bytes(
        preview_data,
        "vk_preview" + extension,
        mime_type
    )

    news["featured_media_id"] = media["wp_id"]


def process_images(news):
    featured_image = news.get(
        "featured_image"
    )

    if featured_image:
        media = upload_media(
            featured_image
        )

        news["featured_media_id"] = (
            media["wp_id"]
        )

    gallery_images = news.get(
        "gallery_images",
        []
    )

    gallery_media_ids = []

    for image_path in gallery_images:
        media = upload_media(
            image_path
        )

        gallery_media_ids.append(
            media["wp_id"]
        )

    news["gallery_media_ids"] = (
        gallery_media_ids
    )


def cleanup_working_files(eml_path):
    """Удаляет временные файлы конкретной итерации."""
    if eml_path:
        try:
            if os.path.isfile(eml_path):
                os.remove(eml_path)
                print(
                    f"Удалён локальный EML: {eml_path}"
                )
        except OSError as error:
            print(
                f"Не удалось удалить {eml_path}: {error}"
            )

    if os.path.isdir(OUTPUT_DIR):
        for filename in os.listdir(
            OUTPUT_DIR
        ):
            path = os.path.join(
                OUTPUT_DIR,
                filename,
            )

            try:
                if os.path.isfile(path):
                    os.remove(path)
            except OSError as error:
                print(
                    f"Не удалось удалить {path}: {error}"
                )


def process_email(eml_path):
    """
    Запускает существующий конвейер для одного EML.

    Возвращает True, только если все критические этапы всех новостей
    завершились успешно. Ошибка VK является некритичной.
    """
    print(f"EML: {eml_path}")

    email_data = extract_attachments(
        eml_path
    )

    documents = email_data["documents"]
    images = email_data["images"]

    print(
        f"DOCX найдено: {len(documents)}"
    )

    print(
        f"Изображений найдено: {len(images)}"
    )

    news_list = build_news(
        documents,
        images
    )

    print(
        f"Новостей собрано: {len(news_list)}"
    )

    vk_links = extract_vk_links(
        email_data,
        documents
    )

    vk_by_document = {
        item["document"]: item
        for item in vk_links
    }

    vk_links_from_docx = (
        extract_vk_links_from_docx(
            documents
        )
    )

    vk_by_document_from_docx = {
        item["document"]: item
        for item in vk_links_from_docx
    }

    print()
    print("=" * 80)
    print("VK ССЫЛКИ ИЗ ПИСЬМА")
    print("=" * 80)

    if vk_links:
        for item in vk_links:
            print()
            print(
                f'DOCX: {item["document"]}'
            )
            print(
                f'URL:  {item["url"]}'
            )
            print(
                f'Источник: {item["source"]}'
            )
    else:
        print(
            "VK ссылок, привязанных к DOCX "
            "в письме, не найдено."
        )

    print()
    print("=" * 80)
    print("VK ССЫЛКИ ИЗ DOCX")
    print("=" * 80)

    if vk_links_from_docx:
        for item in vk_links_from_docx:
            print()
            print(
                f'DOCX: {item["document"]}'
            )
            print(
                f'URL:  {item["url"]}'
            )
            print(
                f'Источник: {item["source"]}'
            )
    else:
        print(
            "VK wall-ссылок непосредственно "
            "в DOCX не найдено."
        )

    email_ok = True

    for number, news in enumerate(
        news_list,
        start=1
    ):
        print()
        print("=" * 80)
        print(
            f"NEWS #{number}: "
            f"{news['title']}"
        )
        print("=" * 80)

        try:
            print(
                "\n[1] Обработка изображений..."
            )

            process_images(news)

            print(
                "\n[2] Поиск VK..."
            )

            document_filename = (
                news["document_filename"]
            )

            vk_info = (
                vk_by_document_from_docx.get(
                    document_filename
                )
            )

            force_preview_as_featured = False

            if vk_info:
                print(
                    f"Найдена VK-ссылка "
                    f"внутри DOCX: "
                    f"{document_filename}"
                )
                print(
                    f'URL: {vk_info["url"]}'
                )
                force_preview_as_featured = True

            else:
                vk_info = vk_by_document.get(
                    document_filename
                )

                if vk_info:
                    print(
                        f"Найдена VK-ссылка "
                        f"в письме для "
                        f"{document_filename}"
                    )
                else:
                    print(
                        "VK-ссылка для этой новости "
                        "не найдена."
                    )

            if vk_info:
                try:
                    process_vk(
                        news,
                        vk_info,
                        force_preview_as_featured
                    )
                except Exception as error:
                    print(
                        "\nПРЕДУПРЕЖДЕНИЕ VK:"
                    )
                    print(error)
                    print(
                        "Новость будет опубликована "
                        "без VK-видео/preview."
                    )

            print(
                "\n[3] Создание записи..."
            )

            post = create_post(news)

            print(
                "\nГотово:"
            )
            print(
                f"ID: {post['id']}"
            )
            print(
                f"URL: {post.get('link')}"
            )
            print(
                f"Статус: {post.get('status')}"
            )

        except Exception as error:
            email_ok = False

            print(
                "\nОШИБКА:"
            )
            print(error)
            print(
                "Новость не обработана полностью. "
                "Переходим к следующей новости письма."
            )

    return email_ok


def run_pipeline():
    print("=" * 80)
    print("MAIL → EML → WORDPRESS")
    print("=" * 80)

    processed_emails = 0
    failed_emails = 0

    while True:
        print()
        print("=" * 80)
        print("ПОИСК СЛЕДУЮЩЕГО ПИСЬМА")
        print("=" * 80)

        downloaded = download_news_email()

        if downloaded is None:
            print(
                "Непрочитанных ЗГП-писем "
                "для обработки больше нет."
            )
            break

        uid, eml_path, subject = downloaded

        print()
        print("=" * 80)
        print(
            f"ОБРАБОТКА ПИСЬМА UID {uid}"
        )
        print("=" * 80)
        print(
            f"Subject: {subject}"
        )
        print(
            "Состояние IMAP: SEEN. "
            "Повторно автоматически письмо не подхватится."
        )

        email_ok = False

        try:
            email_ok = process_email(
                eml_path
            )

        except Exception as error:
            print()
            print(
                "КРИТИЧЕСКАЯ ОШИБКА ОБРАБОТКИ ПИСЬМА:"
            )
            print(error)
            email_ok = False

        finally:
            cleanup_working_files(
                eml_path
            )

        try:
            if email_ok:
                mark_email_processed(
                    uid
                )
                processed_emails += 1
            else:
                mark_email_failed(
                    uid
                )
                failed_emails += 1

        except Exception as error:
            print()
            print(
                "КРИТИЧЕСКАЯ ОШИБКА IMAP:"
            )
            print(error)
            print(
                "Не удалось надёжно завершить изменение "
                "состояния письма. Работа остановлена."
            )
            raise

    print()
    print("=" * 80)
    print("ГОТОВО")
    print("=" * 80)
    print(
        f"Успешно обработано писем: "
        f"{processed_emails}"
    )
    print(
        f"Оставлено в INBOX как SEEN "
        f"после ошибок: {failed_emails}"
    )


def main():
    lock_file = acquire_process_lock()

    if lock_file is None:
        print("=" * 80)
        print("MAIL → EML → WORDPRESS")
        print("=" * 80)
        print()
        print(
            "Другой экземпляр main.py уже работает. "
            "Этот запуск завершён без обработки писем."
        )
        return

    try:
        print(
            f"Process lock получен: {LOCK_FILE}"
        )
        run_pipeline()

    finally:
        release_process_lock(
            lock_file
        )


if __name__ == "__main__":
    main()
