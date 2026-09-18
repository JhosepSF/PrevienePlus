from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from knowledge.models import KnowledgeCategory, KnowledgeDocument

@login_required
def knowledge_index_view(request):
    """
    Overview of verified knowledge categories and documents available to researchers.
    """
    categories = KnowledgeCategory.objects.prefetch_related('documents').filter(documents__is_active=True).distinct()
    context = {
        'categories': categories,
    }
    return render(request, 'knowledge/index.html', context)

@login_required
def document_detail_view(request, doc_id):
    """
    Detail view of a specific validated knowledge document.
    """
    document = get_object_or_404(KnowledgeDocument, pk=doc_id)
    context = {
        'document': document,
    }
    return render(request, 'knowledge/document_detail.html', context)
