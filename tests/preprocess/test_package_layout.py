from app.preprocess.pdf.loader import load_pdf_pages
from app.preprocess.sources.inventory import build_source_inventory
from app.preprocess.sources.manifest import load_source_manifest
from app.preprocess.transform.chunker import chunk_pages
from app.preprocess.transform.preprocess import preprocess_manifest


def test_preprocess_public_imports_are_available() -> None:
    assert all(
        [
            load_pdf_pages,
            build_source_inventory,
            load_source_manifest,
            chunk_pages,
            preprocess_manifest,
        ]
    )
