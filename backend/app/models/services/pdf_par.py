import fitz  # PyMuPDF
from typing import List

def extract_chunks(file_path: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """Extract text from PDF and split into overlapping chunks."""
    doc = fitz.open(file_path)
    full_text = ""

    for page in doc:
        full_text += page.get_text()

    doc.close()

    # Split into chunks with overlap
    words = full_text.split()
    chunks = []

    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        if chunk.strip():
            chunks.append(chunk)

    return chunks
