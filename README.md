# Royal Road Scraper

This python script scrapes a given Royal Road story into a pdf-file, containing all or a selection of chapters.

## Requirements

This project uses [uv](https://docs.astral.sh/uv/) for dependency management.

```bash
uv sync
```

## Usage

```bash
uv run main.py scrape [-t TITLE] [-c CHAPTERS] [-m | --no-markdown] [-p] <URL>
```

This will scrape the given Royal Road fiction URL for its chapter list, and combine these chapters into a Markdown and/or PDF file.

### `scrape`

| Flag               | Description                                                   |
| ------------------ | ------------------------------------------------------------- |
| `-t`, `--title`    | Override the output file title (default: scraped story title) |
| `-c`, `--chapters` | Number of chapters to scrape (default: all available)         |
| `-m`, `--markdown` | Save output as a `.md` file (default: on)                     |
| `--no-markdown`    | Disable Markdown output                                       |
| `-p`, `--pdf`      | Save output as a `.pdf` file (off by default)                 |

**Example:**

```bash
uv run main.py scrape -c 10 -p https://www.royalroad.com/fiction/12345/some-story
```

Scrapes the first 10 chapters and saves both `.md` and `.pdf` output.

### `convert`

Convert an existing Markdown file to PDF without scraping.

```bash
uv run main.py convert [-o OUTPUT] <input.md>
```

| Flag             | Description                                                         |
| ---------------- | ------------------------------------------------------------------- |
| `-o`, `--output` | Output PDF filename (default: same name as input, `.pdf` extension) |

**Example:**

```bash
uv run main.py convert -o mybook.pdf book.md
```

## Notes

- Images referenced in chapters are downloaded locally into an `images/` folder before PDF conversion.
- A 1-second delay is added between chapter requests to avoid hammering the server.
- Be mindful of Royal Road's terms of service and rate limits when scraping large stories.
