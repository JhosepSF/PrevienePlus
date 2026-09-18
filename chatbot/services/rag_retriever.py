from typing import List, Dict, Any
from knowledge.models import KnowledgeChunk, KnowledgeCategory
from knowledge.services import normalize_text

def retrieve_relevant_chunks(query: str, top_k: int = 4, threshold: float = 0.15) -> List[Dict[str, Any]]:
    """
    RAG Retrieval Engine:
    Finds the most relevant validated knowledge chunks from MINSA/OMS/OPS
    matching the student's query based on semantic-lexical scoring.
    """
    normalized_query = normalize_text(query)
    query_tokens = set(normalized_query.split())

    if not query_tokens:
        return []

    active_chunks = KnowledgeChunk.objects.filter(
        is_active=True,
        document__is_active=True
    ).select_related('document', 'category')

    scored_chunks = []

    for chunk in active_chunks:
        chunk_norm = normalize_text(chunk.chunk_text)
        keywords_norm = normalize_text(chunk.keywords)
        category_norm = normalize_text(chunk.category.name)

        score = 0.0
        chunk_words = set(chunk_norm.split())
        kw_words = set(keywords_norm.split())

        for token in query_tokens:
            if len(token) < 3:
                continue

            # Direct token in category name (high weight)
            if token in category_norm:
                score += 3.0

            # Direct token in keywords (high weight)
            if token in kw_words:
                score += 2.0

            # Direct token in chunk text
            if token in chunk_words:
                score += 1.0
            elif token in chunk_norm:
                score += 0.5

        # Substring / phrase bonus
        if len(normalized_query) > 5 and normalized_query in chunk_norm:
            score += 4.0

        if score > 0:
            scored_chunks.append({
                'id': chunk.id,
                'score': score,
                'category': chunk.category.name,
                'category_code': chunk.category.code,
                'document_title': chunk.document.title,
                'source': chunk.document.source_institution,
                'year': chunk.document.publication_year,
                'chunk_text': chunk.chunk_text,
            })

    # Sort by relevance score descending
    scored_chunks.sort(key=lambda x: x['score'], reverse=True)

    # Return top K chunks
    return scored_chunks[:top_k]
