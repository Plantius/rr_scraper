import logging
import re
from pathlib import Path

from markdown_pdf import MarkdownPdf, Section

from app.config import PDF_BATCH_SIZE
from app.utils import open_text
from export.images import embed_images_locally
from export.markdown import build_toc

logger = logging.getLogger(__name__)


def save_as_pdf(
    title: str, manifest, output_path: str, batch_size: int = PDF_BATCH_SIZE
):
    """
    Convert cached chapters to a PDF. Chapters are grouped into batches and
    added as separate fitz Sections so the whole book's markdown/HTML is
    never held in memory at once - important for 100k+ line books.
    """
    pdf = MarkdownPdf()

    header_md = f"# {title}\n\n{build_toc(manifest)}"
    pdf.add_section(Section(embed_images_locally(header_md)))

    batch = []
    for i, (_, _, filepath) in enumerate(manifest, start=1):
        chapter_md = embed_images_locally(filepath.read_text(encoding="utf-8"))
        batch.append(chapter_md)

        if len(batch) >= batch_size or i == len(manifest):
            section_md = "\n\n---\n\n".join(batch)
            pdf.add_section(Section(section_md))
            logger.info(f"Added batch ending at chapter {i}/{len(manifest)} to PDF")
            batch = []

    pdf.save(output_path)
    logger.info(f"PDF file saved to {output_path}")


def convert_md_to_pdf(
    input_file: str, output_file: str | None = None, batch_size: int = PDF_BATCH_SIZE
):
    """Convert an existing Markdown file (optionally .md.gz) to a PDF, splitting
    on chapter/section breaks ('---' on its own line) so large files aren't
    loaded as one giant Section."""
    input_path = Path(input_file)
    if not input_path.exists():
        logger.error(f"File {input_path} does not exist.")
        return

    if output_file:
        output_path = Path(output_file)
    else:
        stem = input_path.with_suffix("") if input_path.suffix == ".gz" else input_path
        output_path = stem.with_suffix(".pdf")

    pdf = MarkdownPdf()
    with open_text(input_path, "r") as f:
        full_text = f.read()
    parts = re.split(r"\n---\n", full_text)

    batch = []
    for i, part in enumerate(parts, start=1):
        batch.append(embed_images_locally(part))
        if len(batch) >= batch_size or i == len(parts):
            pdf.add_section(Section("\n\n---\n\n".join(batch)))
            logger.info(f"Added batch ending at part {i}/{len(parts)} to PDF")
            batch = []

    pdf.save(output_path)
    logger.info(f"PDF file saved to {output_path}")
