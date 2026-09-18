import re
import unicodedata

def normalize_text(text: str) -> str:
    """Normalizes text by removing accents, punctuation and lowercasing."""
    if not text:
        return ""
    # Lowercase
    text = text.lower()
    # Normalize unicode
    nfkd_form = unicodedata.normalize('NFKD', text)
    text = "".join([c for c in nfkd_form if not unicodedata.combining(c)])
    # Remove extra symbols
    text = re.sub(r'[^\w\s]', ' ', text)
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def extract_keywords(text: str) -> str:
    """Extracts informative keywords from text excluding common Spanish stopwords."""
    stopwords = {
        'de', 'la', 'que', 'el', 'en', 'y', 'a', 'los', 'del', 'se', 'las', 'por',
        'un', 'para', 'con', 'no', 'una', 'su', 'al', 'lo', 'como', 'mas', 'pero',
        'sus', 'le', 'ya', 'o', 'este', 'si', 'porque', 'esta', 'son', 'entre',
        'cuando', 'muy', 'sin', 'sobre', 'tambien', 'me', 'hasta', 'hay', 'donde',
        'quien', 'desde', 'todo', 'nos', 'durante', 'todos', 'uno', 'les', 'ni',
        'contra', 'otros', 'ese', 'eso', 'ante', 'ellos', 'e', 'esto', 'mi', 'antes',
        'algunos', 'que', 'unos', 'yo', 'otro', 'otras', 'otra', 'el', 'tanto', 'esa',
        'estos', 'mucho', 'quienes', 'nada', 'muchos', 'cual', 'poco', 'ella', 'estar',
        'estas', 'algunas', 'algo', 'nosotros', 'mi', 'mis', 'tus', 'suya', 'nuestras'
    }
    normalized = normalize_text(text)
    words = [w for w in normalized.split() if len(w) > 2 and w not in stopwords]
    # Unique preserve order
    seen = set()
    unique_words = []
    for w in words:
        if w not in seen:
            seen.add(w)
            unique_words.append(w)
    return ", ".join(unique_words[:40])

def sync_document_chunks(document):
    """
    Splits a KnowledgeDocument into readable chunks (by paragraphs or double newlines)
    and saves them as KnowledgeChunks for RAG retrieval.
    """
    from knowledge.models import KnowledgeChunk
    
    # Deactivate existing chunks
    KnowledgeChunk.objects.filter(document=document).delete()

    raw_paragraphs = [p.strip() for p in document.full_content.split('\n\n') if p.strip()]
    if not raw_paragraphs:
        raw_paragraphs = [document.full_content.strip()]

    chunks_to_create = []
    for idx, para in enumerate(raw_paragraphs, start=1):
        if len(para) < 20:
            continue
        kw = extract_keywords(para)
        chunks_to_create.append(KnowledgeChunk(
            document=document,
            category=document.category,
            chunk_text=para,
            keywords=kw,
            order=idx,
            is_active=document.is_active
        ))

    if chunks_to_create:
        KnowledgeChunk.objects.bulk_create(chunks_to_create)
