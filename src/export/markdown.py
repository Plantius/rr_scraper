import logging

from app.utils import open_text

logger = logging.getLogger(__name__)


def build_toc(manifest) -> str:
    toc_lines = ["## Table of Contents\n"]
    for title, slug, _ in manifest:
        toc_lines.append(f"- [{title}](#{slug})")
    return "\n".join(toc_lines)


def save_as_markdown(title: str, manifest, output_path: str):
    """Stream cached chapter files into a single markdown file without
    holding the whole book in memory at once."""
    with open_text(output_path, "w") as out:
        out.write(f"# {title}\n\n")
        out.write(build_toc(manifest))
        for _, _, filepath in manifest:
            out.write("\n\n---\n\n")
            out.write(filepath.read_text(encoding="utf-8"))
    logger.info(f"Markdown file saved to {output_path}")
