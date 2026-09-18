from django.core.management.base import BaseCommand
from django.utils import timezone
from accounts.models import User, StudentProfile, ResearchGroup, StudyStage, UserRole
from evaluations.models import (
    Dimension, Assessment, AssessmentType, Question, QuestionType,
    AnswerOption, StudentAssessment, StudentResponse
)
from knowledge.models import KnowledgeCategory, KnowledgeDocument
from chatbot.models import ChatSession, ChatMessage, MessageRole, InterventionConfigLog
from research.models import ResearchSetting

class Command(BaseCommand):
    help = 'Carga datos de demostración e información validada de MINSA/OMS/OPS para Previene+'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Iniciando carga de datos de demostración y base de conocimiento..."))

        # 1. Create or update Admin / Researcher User
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'investigador@previeneplus.edu.pe',
                'role': UserRole.ADMIN,
                'is_staff': True,
                'is_superuser': True,
            }
        )
        admin_user.set_password('admin123')
        admin_user.save()
        self.stdout.write(self.style.SUCCESS("[OK] Administrador creado: usuario 'admin', clave 'admin123'"))

        # 2. Research Global Settings
        ResearchSetting.get_settings()
        self.stdout.write(self.style.SUCCESS("[OK] Configuracion de investigacion inicializada."))

        # 3. Create Dimensions
        dim1, _ = Dimension.objects.get_or_create(
            code='DIM_1_KNOWLEDGE',
            defaults={
                'name': 'Dimensión 1: Conocimientos sobre prevención de ITS',
                'description': 'Evalúa los conceptos científicos, vías de transmisión, medidas de protección y reconocimiento de infecciones de transmisión sexual.',
                'order': 1
            }
        )
        dim2, _ = Dimension.objects.get_or_create(
            code='DIM_2_PRACTICE',
            defaults={
                'name': 'Dimensión 2: Prácticas preventivas frente a ITS',
                'description': 'Evalúa las conductas de autocuidado, comunicación asertiva, uso correcto del preservativo y búsqueda de atención en salud.',
                'order': 2
            }
        )
        self.stdout.write(self.style.SUCCESS("[OK] Dimensiones de evaluacion configuradas."))

        # 4. Create Assessments (Pretest and Postest)
        pretest_inst, _ = Assessment.objects.get_or_create(
            assessment_type=AssessmentType.PRETEST,
            defaults={
                'title': 'Cuestionario de Evaluación Inicial (Pretest) de ITS',
                'instructions': 'Lee atentamente cada pregunta y selecciona la opción que mejor represente tus conocimientos y prácticas. Tus respuestas son totalmente anónimas y confidenciales.',
                'is_active': True
            }
        )

        postest_inst, _ = Assessment.objects.get_or_create(
            assessment_type=AssessmentType.POSTEST,
            defaults={
                'title': 'Cuestionario de Evaluación Final (Postest) de ITS',
                'instructions': 'Responde las siguientes preguntas tras la etapa educativa. Esta información permitirá medir el aprendizaje alcanzado.',
                'is_active': True
            }
        )
        self.stdout.write(self.style.SUCCESS("[OK] Instrumentos Pretest y Postest creados."))

        # 5. Populate Questions Pool for both assessments
        questions_data = [
            # Dimensión 1: Conocimientos
            {
                'dim': dim1,
                'text': '¿Cuál de las siguientes afirmaciones sobre las Infecciones de Transmisión Sexual (ITS) es científicamente correcta?',
                'type': QuestionType.MULTIPLE_CHOICE,
                'weight': 1.0,
                'options': [
                    ('Muchas ITS pueden cursar sin ningún síntoma visible durante meses o años.', 1.0, True),
                    ('Solo las personas con múltiples parejas pueden contraer una ITS.', 0.0, False),
                    ('Lavarse con agua caliente después de una relación sexual previene todas las ITS.', 0.0, False),
                    ('Las ITS solo se transmiten si hay dolor o ardor evidente.', 0.0, False),
                ]
            },
            {
                'dim': dim1,
                'text': '¿Cuál es el método preventivo de barrera que ha demostrado científicamente reducir de forma más eficaz la transmisión de ITS y del VIH durante el acto sexual?',
                'type': QuestionType.MULTIPLE_CHOICE,
                'weight': 1.0,
                'options': [
                    ('El uso correcto y consistente del preservativo (condón de látex o poliuretano).', 1.0, True),
                    ('La píldora anticonceptiva oral.', 0.0, False),
                    ('El método del ritmo o calendario.', 0.0, False),
                    ('La interrupción del coito antes de la eyaculación.', 0.0, False),
                ]
            },
            {
                'dim': dim1,
                'text': '¿El Virus del Papiloma Humano (VPH) cuenta con una vacuna preventiva recomendada en el esquema nacional de vacunación del MINSA?',
                'type': QuestionType.TRUE_FALSE,
                'weight': 1.0,
                'options': [
                    ('Verdadero. La vacuna contra el VPH protege contra los tipos de virus causantes de cáncer de cuello uterino y verrugas genitales.', 1.0, True),
                    ('Falso. No existe ninguna vacuna para prevenir el VPH.', 0.0, False),
                ]
            },
            {
                'dim': dim1,
                'text': 'Sobre el Virus de la Inmunodeficiencia Humana (VIH), señale la opción correcta:',
                'type': QuestionType.MULTIPLE_CHOICE,
                'weight': 1.0,
                'options': [
                    ('El VIH se transmite por relaciones sexuales sin protección, vía sanguínea o de madre a hijo, pero NO por abrazos, besos o compartir cubiertos.', 1.0, True),
                    ('El VIH se puede contagiar a través de picaduras de mosquitos o sudor.', 0.0, False),
                    ('El VIH y el SIDA son exactamente la misma etapa médica desde el primer día.', 0.0, False),
                    ('No existen pruebas de descarte gratuitas en el sistema de salud público.', 0.0, False),
                ]
            },
            {
                'dim': dim1,
                'text': '¿Qué debe hacer una persona si nota una llaga, lesión, secreción inusual o tiene sospecha de haber estado expuesta a una ITS?',
                'type': QuestionType.MULTIPLE_CHOICE,
                'weight': 1.0,
                'options': [
                    ('Acudir de inmediato a un centro de salud o llamar a la Línea 113 para recibir orientación médica profesional.', 1.0, True),
                    ('Automedicarse con antibióticos recomendados por amigos o internet.', 0.0, False),
                    ('Esperar un par de semanas a ver si la molestia desaparece sola.', 0.0, False),
                    ('Aplicar remedios caseros como alcohol o vinagre en la zona afectada.', 0.0, False),
                ]
            },
            # Dimensión 2: Prácticas Preventivas
            {
                'dim': dim2,
                'text': 'Antes de abrir un preservativo, ¿con qué frecuencia verificas que el empaque esté sellado, tenga aire (efecto almohadilla) y la fecha de vencimiento esté vigente?',
                'type': QuestionType.LIKERT,
                'weight': 1.0,
                'options': [
                    ('Siempre (Práctica altamente segura)', 1.0, True),
                    ('Casi siempre', 0.75, False),
                    ('A veces', 0.50, False),
                    ('Casi nunca o Nunca', 0.0, False),
                ]
            },
            {
                'dim': dim2,
                'text': 'Si tu pareja propusiera tener relaciones sexuales sin preservativo, ¿qué tan seguro(a) estás de tu capacidad para comunicarle asertivamente la necesidad de protegerse antes de consentir?',
                'type': QuestionType.LIKERT,
                'weight': 1.0,
                'options': [
                    ('Totalmente seguro(a) de exigir y usar protección', 1.0, True),
                    ('Probablemente exigiría protección', 0.75, False),
                    ('Dudaría en conversarlo por temor o vergüenza', 0.25, False),
                    ('Aceptaría sin protección para no incomodar', 0.0, False),
                ]
            },
            {
                'dim': dim2,
                'text': '¿Qué tan dispuesto(a) estás a acudir periódicamente a un centro de salud o solicitar consejería médica para realizarte pruebas preventivas de descarte de ITS/VIH?',
                'type': QuestionType.LIKERT,
                'weight': 1.0,
                'options': [
                    ('Completamente dispuesto(a) y consciente de su importancia preventiva', 1.0, True),
                    ('Dispuesto(a) si un profesional o docente me orienta', 0.75, False),
                    ('Poco dispuesto(a) por temor o desinformación', 0.25, False),
                    ('Nada dispuesto(a)', 0.0, False),
                ]
            },
        ]

        # Insert questions for both Pretest and Postest
        for inst in [pretest_inst, postest_inst]:
            # Clear old if needed
            inst.questions.all().delete()
            for idx, qdata in enumerate(questions_data, start=1):
                q = Question.objects.create(
                    assessment=inst,
                    dimension=qdata['dim'],
                    question_text=qdata['text'],
                    question_type=qdata['type'],
                    weight=qdata['weight'],
                    order=idx,
                    is_active=True
                )
                for o_idx, opt in enumerate(qdata['options'], start=1):
                    AnswerOption.objects.create(
                        question=q,
                        option_text=opt[0],
                        score_value=opt[1],
                        is_correct=opt[2],
                        order=o_idx
                    )
        self.stdout.write(self.style.SUCCESS("[OK] Banco de preguntas y opciones configurado para Pretest y Postest."))

        # 6. Validated Knowledge Categories & Documents
        categories_data = [
            ('Concepto y Generalidades de ITS', 'concepto-its', 'Definición, clasificación y generalidades sobre las infecciones de transmisión sexual según MINSA y OMS.', 'bi-info-circle'),
            ('VIH y SIDA', 'vih-sida', 'Mecanismos de transmisión, pruebas de descarte, TARV y medidas de prevención.', 'bi-heart-pulse'),
            ('Virus del Papiloma Humano (VPH)', 'vph', 'Tipos de VPH, prevención mediante vacunación, despistaje y cuidados.', 'bi-shield-shaded'),
            ('Sífilis y Gonorrea', 'sifilis-gonorrea', 'Signos clínicos de alarma, diagnóstico oportuno y tratamiento con base médica.', 'bi-capsule'),
            ('Uso Correcto del Preservativo', 'preservativo', 'Protocolo paso a paso para el uso efectivo y almacenamiento del condón masculino y femenino.', 'bi-shield-check'),
            ('Mitos y Creencias Falsas', 'mitos-its', 'Desmitificación científica de creencias erróneas sobre la transmisión y prevención de ITS.', 'bi-lightbulb'),
            ('Servicios de Salud y Orientación', 'servicios-salud', 'Información sobre centros de salud del MINSA, Línea 113 Salud y consejería confidencial.', 'bi-geo-alt'),
        ]

        cat_objs = {}
        for name, code, desc, icon in categories_data:
            cat, _ = KnowledgeCategory.objects.get_or_create(
                code=code,
                defaults={'name': name, 'description': desc, 'icon': icon}
            )
            cat_objs[code] = cat
        self.stdout.write(self.style.SUCCESS("[OK] Categorias de conocimiento creadas."))

        documents_data = [
            {
                'cat': cat_objs['concepto-its'],
                'title': 'Guía Técnica: Prevención y Manejo Integral de las Infecciones de Transmisión Sexual',
                'source': 'Ministerio de Salud del Perú (MINSA)',
                'year': 2024,
                'ref': 'Norma Técnica de Salud NTS N° 198-MINSA/DGIESP',
                'content': (
                    "Las Infecciones de Transmisión Sexual (ITS) son un grupo de patologías infecciosas causadas por bacterias, "
                    "virus, hongos o parásitos que se transmiten predominantemente mediante contacto sexual sin protección "
                    "(vaginal, anal u oral).\n\n"
                    "Es fundamental destacar que una gran proporción de personas con una ITS pueden ser totalmente ASINTOMÁTICAS "
                    "(no presentar ningún dolor, ardor ni lesión visible). Por ello, la ausencia de síntomas no descarta una infección. "
                    "El método de prevención más eficaz y accesible en la actividad sexual es el uso correcto y consistente del preservativo."
                )
            },
            {
                'cat': cat_objs['vih-sida'],
                'title': 'Documento Técnico: Información Preventiva sobre el VIH/SIDA para Escolares y Jóvenes',
                'source': 'Organización Panamericana de la Salud (OPS/OMS)',
                'year': 2023,
                'ref': 'Directrices sobre Prevención del VIH en Poblaciones Jóvenes - OPS',
                'content': (
                    "El VIH (Virus de la Inmunodeficiencia Humana) ataca el sistema inmunitario. Si no se trata, puede evolucionar a SIDA. "
                    "El VIH se transmite únicamente por tres vías confirmadas: 1) Relaciones sexuales sin preservativo con una persona con carga viral detectable; "
                    "2) Contacto directo con sangre infectada (como compartir agujas); 3) Transmisión vertical (madre a hijo durante el embarazo, parto o lactancia).\n\n"
                    "El VIH NO se transmite por abrazos, apretones de manos, besos, compartir vasos, platos, cubiertos, ropa o usar los mismos baños. "
                    "En los centros de salud del MINSA en el Perú, las pruebas rápidas de despistaje de VIH son GRATUITAS, voluntarias y confidenciales."
                )
            },
            {
                'cat': cat_objs['vph'],
                'title': 'Prevención del Cáncer de Cuello Uterino y VPH en Población Escolar',
                'source': 'Ministerio de Salud del Perú (MINSA)',
                'year': 2024,
                'ref': 'Esquema Nacional de Vacunación - RM N° 884-2023/MINSA',
                'content': (
                    "El Virus del Papiloma Humano (VPH) es una de las ITS más comunes en el mundo. La mayoría de infecciones son transitorias, "
                    "pero ciertos tipos de alto riesgo oncogénico pueden provocar cáncer de cuello uterino, de pene, ano o garganta.\n\n"
                    "El Estado Peruano aplica la VACUNA CONTRA EL VPH de forma gratuita a niñas, niños y adolescentes en edad escolar. "
                    "La vacuna es altamente segura y eficaz para prevenir las lesiones precancerosas causadas por los tipos más peligrosos del virus."
                )
            },
            {
                'cat': cat_objs['preservativo'],
                'title': 'Manual de Uso Correcto del Preservativo de Látex',
                'source': 'Organización Mundial de la Salud (OMS)',
                'year': 2023,
                'ref': 'Manual Técnico de Métodos de Barrera - OMS',
                'content': (
                    "El preservativo es el único método que ofrece DOBLE PROTECCIÓN: previene embarazos no planificados y protege contra la mayoría de ITS, incluido el VIH.\n\n"
                    "Pasos esenciales para su uso correcto:\n"
                    "1. Verificar siempre la fecha de vencimiento y que el sobre tenga aire (burbuja intacta).\n"
                    "2. Abrir el sobre con la yema de los dedos, NUNCA con los dientes ni tijeras.\n"
                    "3. Colocarlo sobre el pene erecto antes de cualquier contacto genital.\n"
                    "4. Presionar la punta del condón para expulsar el aire acumulado y desenrollarlo hasta la base.\n"
                    "5. Usar solo lubricantes a base de agua; nunca usar vaselina, cremas o aceites porque rompen el látex.\n"
                    "6. Retirar inmediatamente después de la eyaculación sujetando la base y desecharlo en la basura, nunca en el inodoro."
                )
            },
            {
                'cat': cat_objs['mitos-its'],
                'title': 'Mitos y Realidades en Salud Sexual y Reproductiva para Adolescentes',
                'source': 'UNFPA / MINSA Perú',
                'year': 2024,
                'ref': 'Guía Pedagógica de Educación Sexual Integral',
                'content': (
                    "MITO 1: 'Si mi pareja se ve limpia y saludable, no puede tener una ITS'. REALIDAD: La gran mayoría de ITS no presentan síntomas visibles en etapas iniciales.\n\n"
                    "MITO 2: 'La primera relación sexual no contagia ITS ni produce embarazo'. REALIDAD: El riesgo biológico es exactamente el mismo en cualquier relación sexual sin protección.\n\n"
                    "MITO 3: 'Lavar la zona genital con jabón o limón previene infecciones'. REALIDAD: Ningún lavado posterior elimina los patógenos y puede causar quemaduras o irritación severa en las mucosas."
                )
            },
            {
                'cat': cat_objs['servicios-salud'],
                'title': 'Acceso a Servicios de Salud y Consejería Gratuita en el Perú',
                'source': 'Ministerio de Salud del Perú (MINSA)',
                'year': 2024,
                'ref': 'Portal de Orientación Sanitaria 113 Salud',
                'content': (
                    "Cualquier estudiante o adolescente en el Perú tiene derecho a recibir orientación confidencial y gratuita en salud sexual en cualquier establecimiento de salud del MINSA.\n\n"
                    "La LÍNEA 113 SALUD del MINSA brinda atención telefónica gratuita las 24 horas del día, los 365 días del año (marcando el 113 desde cualquier celular o teléfono fijo, opción 3 para Salud Sexual y Reproductiva).\n\n"
                    "Ante situaciones de vulneración de derechos o violencia, la LÍNEA 100 del MIMP ofrece auxilio legal y psicológico confidencial."
                )
            },
        ]

        for doc_data in documents_data:
            doc, _ = KnowledgeDocument.objects.get_or_create(
                title=doc_data['title'],
                defaults={
                    'category': doc_data['cat'],
                    'source_institution': doc_data['source'],
                    'publication_year': doc_data['year'],
                    'reference_url': doc_data['ref'],
                    'full_content': doc_data['content'],
                    'summary': doc_data['content'][:200] + '...',
                    'is_active': True
                }
            )
        self.stdout.write(self.style.SUCCESS("[OK] Documentos y fragmentos de conocimiento sincronizados para RAG."))

        # 7. Create Sample Students for Experimental and Control Groups
        # Experimental group: EXP-001 to EXP-008
        # Control group: CTR-001 to CTR-008
        created_students = 0

        # Sample Experimental Students
        for i in range(1, 9):
            code = f"EXP-{str(i).zfill(3)}"
            user, _ = User.objects.get_or_create(
                username=f"student_{code.lower().replace('-', '_')}",
                defaults={'role': UserRole.STUDENT, 'is_active': True}
            )
            profile, _ = StudentProfile.objects.get_or_create(
                student_code=code,
                defaults={
                    'user': user,
                    'group': ResearchGroup.EXPERIMENTAL,
                    'stage': StudyStage.INTERVENTION if i <= 5 else StudyStage.PRETEST,
                    'consent_given': True,
                    'consent_timestamp': timezone.now(),
                    'is_active': True
                }
            )
            created_students += 1

            # Give first 3 students completed Pretests & Sample Chat sessions
            if i <= 3:
                # Pretest
                sa_pre, _ = StudentAssessment.objects.get_or_create(
                    student=profile,
                    assessment=pretest_inst,
                    assessment_type=AssessmentType.PRETEST,
                    defaults={
                        'started_at': timezone.now(),
                        'completed_at': timezone.now(),
                        'score_dimension_1': 3.0,
                        'score_dimension_2': 2.0,
                        'total_score': 5.0,
                        'is_submitted': True
                    }
                )
                # Chat session
                sess, _ = ChatSession.objects.get_or_create(
                    student=profile,
                    defaults={
                        'started_at': timezone.now(),
                        'total_messages': 4,
                        'duration_seconds': 240,
                        'is_active': True
                    }
                )
                ChatMessage.objects.get_or_create(
                    session=sess,
                    role=MessageRole.USER,
                    content="¿Cómo se transmite el VIH y cómo se previene?",
                    defaults={'created_at': timezone.now()}
                )
                ChatMessage.objects.get_or_create(
                    session=sess,
                    role=MessageRole.ASSISTANT,
                    content="El VIH se transmite principalmente por relaciones sexuales sin preservativo...",
                    defaults={
                        'sources_used': 'OPS/OMS - Información Preventiva sobre el VIH/SIDA',
                        'topics_detected': 'VIH y SIDA, Preservativo',
                        'tokens_used': 120,
                        'created_at': timezone.now()
                    }
                )
                InterventionConfigLog.objects.get_or_create(
                    student=profile,
                    session=sess,
                    app_version='1.0.0-research',
                    model_name='gpt-5.6-luna (RAG-Verified)',
                    defaults={
                        'system_prompt_version': 'v1.0-research-safe',
                        'system_prompt_text': 'System Prompt Base v1.0',
                        'knowledge_chunks_count': 12,
                        'recorded_at': timezone.now()
                    }
                )

        # Sample Control Students
        for i in range(1, 9):
            code = f"CTR-{str(i).zfill(3)}"
            user, _ = User.objects.get_or_create(
                username=f"student_{code.lower().replace('-', '_')}",
                defaults={'role': UserRole.STUDENT, 'is_active': True}
            )
            profile, _ = StudentProfile.objects.get_or_create(
                student_code=code,
                defaults={
                    'user': user,
                    'group': ResearchGroup.CONTROL,
                    'stage': StudyStage.POSTEST if i <= 4 else StudyStage.PRETEST,
                    'consent_given': True,
                    'consent_timestamp': timezone.now(),
                    'is_active': True
                }
            )
            created_students += 1

            if i <= 3:
                # Pretest
                StudentAssessment.objects.get_or_create(
                    student=profile,
                    assessment=pretest_inst,
                    assessment_type=AssessmentType.PRETEST,
                    defaults={
                        'started_at': timezone.now(),
                        'completed_at': timezone.now(),
                        'score_dimension_1': 2.0,
                        'score_dimension_2': 1.75,
                        'total_score': 3.75,
                        'is_submitted': True
                    }
                )

        self.stdout.write(self.style.SUCCESS(f"[OK] Creados {created_students} participantes de prueba (EXP-001...EXP-008, CTR-001...CTR-008)."))
        self.stdout.write(self.style.SUCCESS("\n[OK] Inicializacion completada con exito!"))
        self.stdout.write(self.style.NOTICE("Puedes iniciar sesion como:"))
        self.stdout.write(self.style.NOTICE("  - Administrador: usuario 'admin', clave 'admin123'"))
        self.stdout.write(self.style.NOTICE("  - Estudiante Experimental: codigo 'EXP-001'"))
        self.stdout.write(self.style.NOTICE("  - Estudiante Control: codigo 'CTR-001'"))

