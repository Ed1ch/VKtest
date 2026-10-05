from config import EML_FILE
from eml_parser import extract_attachments
from news_parser import read_docx


email_data = extract_attachments(
    EML_FILE
)

for document in email_data["documents"]:

    if document["filename"] == "семья.docx":

        result = read_docx(
            document["data"]
        )

        print("=" * 80)
        print("TITLE:")
        print(result["title"])

        print("=" * 80)
        print("EXCERPT:")
        print(result["excerpt"])

        print("=" * 80)
        print("HTML:")
        print(result["content"])