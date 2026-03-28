from core.constants import TEXT_SOURCES


def test_document_caption_is_in_text_sources():
    assert ("documentMessage", "caption") in TEXT_SOURCES
