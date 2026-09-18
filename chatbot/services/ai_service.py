import os
import logging
from typing import Dict, Any, List
from django.conf import settings
from chatbot.services.rag_retriever import retrieve_relevant_chunks
from knowledge.models import KnowledgeChunk

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_VERSION = "v1.0-research-safe"

BASE_SYSTEM_PROMPT = """Eres Previene+, un asistente educativo con inteligencia artificial especializado en la prevención de infecciones de transmisión sexual (ITS) dirigido a estudiantes adolescentes y jóvenes en una institución educativa.

Tu propósito fundamental es brindar orientación clara, científicamente fundamentada, comprensible, preventiva y respetuosa.

DIRECTRICES DE SEGURIDAD Y METODOLOGÍA:
1. NO eres médico ni sustituyes a profesionales sanitarios. NO realices diagnósticos clínicos ni prescribas tratamientos ni medicamentos.
2. Utiliza un lenguaje claro, empático, educativo y comprensible para adolescentes, sin tecnicismos excesivos ni sermones morales.
3. Mantén una postura NO moralizante y NO estigmatizante. La salud sexual y la prevención son derechos fundamentados en la ciencia.
4. NO generes contenido sexual explícito ni erótico. Responde sobre salud sexual y anatomía únicamente con finalidad educativa, biológica y preventiva.
5. PRIORIDAD RAG: Prioriza estrictamente la información recuperada de la base de conocimiento oficial (MINSA Perú, OMS, OPS) suministrada en el contexto.
6. Si la base de conocimiento no contiene información suficiente para responder con seguridad, NO inventes. Indica con amabilidad que no dispones de información científica validada sobre ese punto específico y sugiere acudir a un profesional o centro de salud.
7. Si el estudiante consulta sobre signos, síntomas visibles, dolor o una situación de riesgo reciente, explícale la importancia de acudir de inmediato a un centro de salud (en Perú: Línea 113 Salud opción 3, gratuita las 24 horas) para una evaluación confidencial y oportuna.
8. Si detectas situaciones de abuso, acoso, coerción o violencia, brinda apoyo empático y oriéntalo a buscar ayuda inmediata con un adulto de confianza (docente, psicólogo, tutor) y comunicarse con las líneas de protección (Línea 100 / CEM).

FUENTES VALIDADAS EN EL CONTEXTO:
{context}
"""

class AIService:
    """
    Decoupled AI service managing RAG retrieval, prompt construction,
    OpenAI API communications, and robust offline/simulation fallbacks.
    """

    @classmethod
    def get_system_prompt(cls, context_text: str) -> str:
        return BASE_SYSTEM_PROMPT.format(
            context=context_text if context_text else "No se encontraron documentos específicos en la base para esta consulta."
        )

    @classmethod
    def generate_response(cls, user_message: str, chat_history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Main pipeline: Retrieve context -> Build prompt -> Call LLM -> Validate & Format output.
        """
        api_key = getattr(settings, 'OPENAI_API_KEY', '').strip()
        model_name = getattr(settings, 'OPENAI_MODEL', 'gpt-5.6-luna')
        enable_simulation = getattr(settings, 'ENABLE_SIMULATION_MODE', True)

        # 1. RAG Context Retrieval
        chunks = retrieve_relevant_chunks(user_message, top_k=4)
        
        sources_list = []
        topics_list = []
        context_parts = []

        for c in chunks:
            src_str = f"{c['document_title']} ({c['source']}, {c['year']})"
            if src_str not in sources_list:
                sources_list.append(src_str)
            if c['category'] not in topics_list:
                topics_list.append(c['category'])
            context_parts.append(f"[{c['category']} - {src_str}]:\n{c['chunk_text']}")

        rag_context = "\n\n".join(context_parts)
        system_prompt = cls.get_system_prompt(rag_context)

        # 2. Check if no validated context was found at all for specific medical queries
        has_context = len(chunks) > 0

        # 3. Call OpenAI API if API key is provided
        if api_key and not api_key.startswith('your-'):
            try:
                from openai import OpenAI
                client = OpenAI(api_key=api_key, timeout=25.0)

                messages_payload = [
                    {"role": "system", "content": system_prompt}
                ]

                # Append recent history if provided
                if chat_history:
                    for h in chat_history[-6:]:
                        messages_payload.append({
                            "role": h.get("role", "user"),
                            "content": h.get("content", "")
                        })

                messages_payload.append({"role": "user", "content": user_message})

                response = client.chat.completions.create(
                    model=model_name,
                    messages=messages_payload,
                    temperature=0.3,
                    max_tokens=650,
                )

                reply_text = response.choices[0].message.content.strip()
                tokens = response.usage.total_tokens if response.usage else 0

                return {
                    'content': reply_text,
                    'sources': sources_list,
                    'topics': topics_list,
                    'tokens': tokens,
                    'model': model_name,
                    'prompt_version': SYSTEM_PROMPT_VERSION,
                    'system_prompt_text': system_prompt,
                    'success': True,
                    'simulated': False,
                }
            except Exception as e:
                logger.warning(f"OpenAI API call failed: {e}. Falling back to RAG synthesized response.")
                if not enable_simulation:
                    return {
                        'content': "En este momento estoy teniendo dificultades técnicas de conexión. Por favor, intenta formular tu pregunta nuevamente en unos momentos.",
                        'sources': sources_list,
                        'topics': topics_list,
                        'tokens': 0,
                        'model': model_name,
                        'prompt_version': SYSTEM_PROMPT_VERSION,
                        'system_prompt_text': system_prompt,
                        'success': False,
                        'simulated': False,
                    }

        # 4. Grounded Local RAG Synthesizer (for simulation mode, tests, or missing API key)
        synthesized_reply = cls._synthesize_rag_response(user_message, chunks, has_context)

        return {
            'content': synthesized_reply,
            'sources': sources_list,
            'topics': topics_list,
            'tokens': len(synthesized_reply.split()) * 2,
            'model': f"{model_name} (RAG-Verified)",
            'prompt_version': SYSTEM_PROMPT_VERSION,
            'system_prompt_text': system_prompt,
            'success': True,
            'simulated': True,
        }

    @classmethod
    def _synthesize_rag_response(cls, user_message: str, chunks: List[Dict[str, Any]], has_context: bool) -> str:
        """
        Creates a grounded, scientifically accurate educational reply based strictly
        on retrieved MINSA/OMS/OPS knowledge chunks when running offline/simulated.
        """
        if not has_context:
            return (
                "Hola. No cuento con suficiente información validada en mi base de datos científica "
                "para responder a esa consulta con la certeza requerida. "
                "Te recuerdo que soy un asistente educativo y no sustituyo la atención de un profesional de la salud. "
                "Si tienes dudas o alguna molestia, te recomiendo acudir a un centro de salud o comunicarte a la Línea 113 Salud (opción 3), "
                "donde recibirás orientación médica gratuita, profesional y confidencial."
            )

        # Synthesize top chunks
        top_chunk = chunks[0]
        category_name = top_chunk['category']
        text = top_chunk['chunk_text']

        response_parts = [
            f"Sobre **{category_name}**, de acuerdo con la información validada de fuentes oficiales ({top_chunk['source']}):\n",
            f"{text}\n"
        ]

        if len(chunks) > 1:
            second_chunk = chunks[1]
            if second_chunk['chunk_text'] != text:
                response_parts.append(f"Asimismo, es importante considerar:\n{second_chunk['chunk_text']}\n")

        response_parts.append(
            "\n💡 *Recuerda*: El uso correcto y consistente del preservativo en cada relación sexual y la realización de pruebas preventivas periódicas son las formas más efectivas de proteger tu salud. Ante cualquier síntoma o duda, puedes acudir a un centro de salud o llamar gratis a la Línea 113 del MINSA."
        )

        return "\n".join(response_parts)
