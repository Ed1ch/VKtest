# AGENTS.md

## Project

VKTest is a Python application that processes incoming email news (`.eml`), extracts text, images and VK links/attachments, processes VK content through the VK API, and publishes the resulting content to WordPress.

Repository:

https://github.com/Ed1ch/VKtest

Additional LLM context:

```text
gpt_context/
```

The Markdown files in `gpt_context/` contain project-specific context and previous architectural decisions.

## Source of truth

When working on the project, use this priority:

1. Current source code in the repository
2. Relevant documentation in `gpt_context/`
3. Current conversation
4. Do not assume that old chat context reflects the current code

Before making non-trivial changes, inspect the relevant existing code and context.

## Architecture

The main processing flow is approximately:

```text
Email
  ↓
main.py
  ↓
download .eml
  ↓
EML parsing
  ↓
extract links / images / VK objects
  ↓
VK API processing
  ↓
prepare WordPress content
  ↓
WordPress API
  ↓
cleanup temporary files
```

Important temporary directories:

```text
downloaded_eml/
extracted_images/
```

## Main modules

* `main.py`
  Main orchestration loop. Processes one unread email at a time and coordinates the pipeline.

* `eml_parser.py`
  Parses `.eml` files and extracts text, HTML and attachments/images.

* `eml_links.py`
  Finds and processes links and VK-related objects in email content.

* VK-related modules
  Communicate with VK API and process VK objects, including videos and nested `attachments`.

* WordPress-related modules
  Prepare and publish the resulting content through WordPress API.

* `wp_probe.py`
  Diagnostic utility for testing WordPress API behavior.

* `config.py`
  Runtime configuration. Secrets and local configuration must not be committed to Git.

## Error handling

A failure while processing one news item must **not terminate the entire processing loop**.

The intended structure is:

```python
while there are unread messages:
    download one message

    try:
        process message
    except Exception:
        log/report error

    finally:
        remove downloaded .eml
        clean extracted_images/
```

Cleanup must happen even when processing fails.

## Development rules

* Prefer small, targeted changes over unnecessary rewrites.
* Preserve existing behavior unless the task explicitly requires changing it.
* Do not duplicate functionality that already exists in another module.
* Do not silently change the architecture.
* Before adding a new helper/module, check whether existing code already provides the required functionality.
* Keep modules responsible for their own domain.
* Do not hardcode credentials, tokens or other secrets.
* Keep temporary files out of Git.
* Update relevant `gpt_context/*.md` documentation when an architectural decision or important behavior changes.
* Do not invent APIs, data structures or project behavior. Inspect the actual code first.
* When uncertain, state the uncertainty rather than guessing.

## VK-specific notes

VK objects may occur inside nested `attachments`. Do not assume that relevant objects exist only at the top level.

For VK videos, the pipeline may need:

* `owner_id`
* `video_id`
* VK API metadata
* embed information
* preview image

Preserve recursive attachment handling when modifying VK processing.

## WordPress

WordPress communication is performed through its API.

`wp_probe.py` can be used to diagnose API availability, authentication and endpoint behavior before modifying the main publishing pipeline.

## Git

GitHub is the canonical repository for the source code.

Normal small code changes should still be committed when they represent a meaningful repository state. Do not create artificial commits solely to document trivial edits.

Never commit secrets or local-only configuration.

## Environment

Current development environment:

```text
Windows
Python 3.13.15
pip 26.2.1
```

The project should remain compatible with the existing Windows-based development environment unless a task explicitly requires otherwise.
