import re
import unicodedata


def chunk_text(file_path: str) -> list:
    with open(file_path, "r") as f:
        text = f.read()


def clean_extracted_text(text: str) -> str:
    """
    Applies a series of robust post-processing steps to text extracted from PDFs
    to clean up common parsing artifacts for NLP tasks.

    Args:
        text (str): The raw text string extracted from a PDF.

    Returns:
        str: The cleaned text string.
    """
    if not isinstance(text, str):
        return ""

    # 0. Optional: Remove common chunk identifier prefixes (e.g., '0: ', '1: ')
    #    Adjust or remove if your parser doesn't add these.
    text = re.sub(r"^\d+:\s*\'?", "", text)

    # 1. Normalize Unicode characters:
    #    NFKC handles ligatures (ﬁ -> fi, ﬀ -> ff), different dashes, smart quotes, etc.
    text = unicodedata.normalize("NFKC", text)

    # 2. Handle hyphenated words broken across lines:
    #    This is the critical part for 'sub-\njects'.
    #    It now looks for a letter, a hyphen, followed by ANY sequence of one or more
    #    whitespace characters (which covers spaces, newlines, tabs, etc.),
    #    and then another letter. It joins them directly.
    #    This is more aggressive and should catch cases like 'sub-\njects', 'mod-\nels',
    #    and 'evalu-\nate' regardless of specific whitespace types.
    text = re.sub(r"([a-zA-Z])-\s+([a-zA-Z])", r"\1\2", text)

    # 3. Remove non-breaking spaces and zero-width spaces, replacing with regular spaces.
    text = text.replace("\xa0", " ").replace("\u200b", "")

    # 4. Normalize newlines:
    #    a. Replace single newlines (soft wraps within paragraphs) with a single space.
    #       This is for stitching sentences together.
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)

    #    b. Consolidate multiple newlines into at most two newlines.
    #       This preserves clear paragraph breaks while removing excessive blank lines.
    text = re.sub(r"\n{2,}", "\n\n", text)

    # 5. Collapse any sequence of whitespace characters (spaces, tabs, remaining newlines after step 4)
    #    into a single space. This standardizes all internal spacing.
    text = re.sub(r"\s+", " ", text)

    # 6. Remove leading and trailing whitespace from the entire string.
    text = text.strip()

    return text
