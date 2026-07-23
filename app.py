import io
import os
import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from groq import Groq
import streamlit as st

# ---------------------------------------------------------
# 1. إعدادات الصفحة الأساسية
# ---------------------------------------------------------
st.set_page_config(
    page_title="المستشار القانوني الذكي | JurisConsult AI",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------
# 2. تصميم CSS احترافي وفاخر (Professional Legal Theme)
# ---------------------------------------------------------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&family=Inter:wght@400;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'Cairo', 'Inter', sans-serif !important;
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 6rem !important;
        max-width: 1100px !important;
    }

    /* الهيدر الاحترافي الفاخر */
    .hero-header {
        background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 100%);
        border-radius: 16px;
        padding: 25px 30px;
        color: white;
        margin-bottom: 25px;
        box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.25);
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    .hero-title {
        font-size: 2.2rem;
        font-weight: 800;
        margin: 0;
        color: #ffffff;
        display: flex;
        align-items: center;
        gap: 12px;
    }

    .hero-subtitle {
        font-size: 1rem;
        color: #93c5fd;
        margin-top: 8px;
        font-weight: 400;
    }

    /* أزرار اختيار اللغة */
    .lang-container {
        display: flex;
        gap: 10px;
        margin-bottom: 15px;
    }

    /* بطاقات الأسئلة السريعة والأدوات */
    .quick-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 15px;
        transition: all 0.3s ease;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    
    .quick-card:hover {
        border-color: #3b82f6;
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.12);
        transform: translateY(-2px);
    }

    /* تحسين تصميم الشات */
    .stChatMessage {
        border-radius: 14px !important;
        padding: 15px !important;
        margin-bottom: 12px !important;
        box-shadow: 0 2px 5px rgba(0,0,0,0.03);
    }

    /* التجاوب للهواتف المحمولة */
    @media (max-width: 768px) {
        [data-testid="stSidebar"] { display: none !important; }
        [data-testid="collapsedControl"] { display: none !important; }
        .hero-header {
            padding: 18px 20px;
            text-align: center;
        }
        .hero-title {
            font-size: 1.5rem;
            justify-content: center;
        }
        .hero-subtitle {
            font-size: 0.85rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# 3. إدارة خيار اللغة (Language Switcher)
# ---------------------------------------------------------
if "lang" not in st.session_state:
  st.session_state.lang = "ar"

# شريط اختيار اللغات العلوي
col_lang1, col_lang2, col_space = st.columns([2, 3, 5])
with col_lang1:
  st.caption("🌐 **اختيار لغة الاستشارة / Language:**")
with col_lang2:
  selected_lang = st.radio(
      "Language",
      options=["العربية 🇲🇦", "Français 🇫🇷", "English 🇬🇧"],
      horizontal=True,
      label_visibility="collapsed",
  )
  if "🇲🇦" in selected_lang:
    st.session_state.lang = "ar"
  elif "🇫🇷" in selected_lang:
    st.session_state.lang = "fr"
  else:
    st.session_state.lang = "en"

# النصوص بحسب اللغة المختارة
TEXTS = {
    "ar": {
        "title": "المستشار القانوني الذكي",
        "subtitle": (
            "المنصة المعتمدة للاستشارات الذكية في مدونة الشغل المغربية (القانون"
            " 65.99)"
        ),
        "welcome": (
            "مرحباً بك! أنا مستشارك القانوني الخبير في مدونة الشغل المغربية."
            " كيف يمكنني مساعدتك اليوم؟"
        ),
        "input_placeholder": "اطرح استفسارك القانوني هنا...",
        "quick_questions": "💡 أسئلة قانونية شائعة بنقرة واحدة:",
        "q1": "كم مدة عطلة الأمومة والأبوة؟",
        "q2": "ما هي حقوق الأجير عند الفصل التعسفي؟",
        "q3": "ما هي المدة القانونية لفترة التجربة؟",
        "tools": "🛠️ أدوات الاستشارة وتحميل التقارير",
        "reset": "🗑️ مسح المحادثة",
        "download_txt": "📥 تقرير (TXT)",
        "download_word": "📄 تقرير وورد (DOCX)",
        "dir": "rtl",
    },
    "fr": {
        "title": "JurisConsult Maroc IA",
        "subtitle": (
            "Assistant Juridique Intelligent pour le Code du Travail Marocain"
            " (Loi 65.99)"
        ),
        "welcome": (
            "Bonjour! Je suis votre assistant juridique expert en Code du"
            " Travail marocain. Comment puis-je vous aider aujourd'hui?"
        ),
        "input_placeholder": "Posez votre question juridique ici...",
        "quick_questions": "💡 Questions fréquentes en un clic :",
        "q1": "Quelle est la durée du congé de maternité ?",
        "q2": "Quels sont les indemnités de licenciement abusif ?",
        "q3": "Quelle est la durée de la période d'essai ?",
        "tools": "🛠️ Outils & Téléchargement",
        "reset": "🗑️ Réinitialiser",
        "download_txt": "📥 Rapport (TXT)",
        "download_word": "📄 Rapport Word (DOCX)",
        "dir": "ltr",
    },
    "en": {
        "title": "Moroccan Legal AI Assistant",
        "subtitle": (
            "Smart Legal Advisory Platform for Moroccan Labor Code (Law 65.99)"
        ),
        "welcome": (
            "Hello! I am your expert legal assistant for the Moroccan Labor"
            " Code. How can I help you today?"
        ),
        "input_placeholder": "Ask your legal question here...",
        "quick_questions": "💡 Frequent Legal Questions:",
        "q1": "What is the duration of maternity/paternity leave?",
        "q2": "What are the compensation rights for unfair dismissal?",
        "q3": "What is the legal duration of the probation period?",
        "tools": "🛠️ Consultation Tools & Downloads",
        "reset": "🗑️ Reset Chat",
        "download_txt": "📥 Report (TXT)",
        "download_word": "📄 Word Report (DOCX)",
        "dir": "ltr",
    },
}

current_texts = TEXTS[st.session_state.lang]

# ---------------------------------------------------------
# 4. الهيدر البصري الاحترافي (Hero Banner)
# ---------------------------------------------------------
st.markdown(
    f"""
    <div class="hero-header">
        <div class="hero-title">⚖️ {current_texts['title']}</div>
        <div class="hero-subtitle">{current_texts['subtitle']}</div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# 5. دالة إنشاء ملف Word منظم
# ---------------------------------------------------------
def generate_docx(messages):
  doc = docx.Document()

  def set_rtl(p):
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p_pr = p._p.get_or_add_pPr()
    bidi = OxmlElement('w:bidi')
    bidi.set(qn('w:val'), '1')
    p_pr.append(bidi)

  title = doc.add_paragraph('Rapport de Consultation Juridique - Droit du Travail')
  if st.session_state.lang == 'ar':
    set_rtl(title)
    title.runs[0].text = (
        'تقرير استشارة قانونية - مدونة الشغل المغربية (القانون 65.99)'
    )

  title.runs[0].font.bold = True
  title.runs[0].font.size = docx.shared.Pt(15)

  for msg in messages:
    role_name = 'المستخدم / User' if msg['role'] == 'user' else 'المستشار القانوني / JurisConsult'
    p = doc.add_paragraph()
    if st.session_state.lang == 'ar':
      set_rtl(p)

    run_role = p.add_run(f'[{role_name}]:\n')
    run_role.bold = True

    p_content = doc.add_paragraph(msg['content'])
    if st.session_state.lang == 'ar':
      set_rtl(p_content)
    doc.add_paragraph('-' * 45)

  buffer = io.BytesIO()
  doc.save(buffer)
  buffer.seek(0)
  return buffer.getvalue()


# ---------------------------------------------------------
# 6. إعداد Groq API وقاعدة المعرفة
# ---------------------------------------------------------
api_key = st.secrets.get('GROQ_API_KEY') or os.getenv('GROQ_API_KEY')
if not api_key:
  st.error('⚠️ GROQ_API_KEY Missing!')
  st.stop()

client = Groq(api_key=api_key)

LEGAL_KNOWLEDGE_BASE = {
    'عطلة': (
        'المادة 231: رخصة سنوية يوم ونصف عن كل شهر. Congé annuel payé: 1.5'
        ' jour par mois.'
    ),
    'أمومة': (
        'المادة 152: رخصة أمومة 14 أسبوعاً. Congé de maternité: 14 semaines.'
        ' Congé de paternité: 3 jours.'
    ),
    'فصل': (
        'المواد 61-65: التعويض عن الفصل التعسفي والإنذار. Licenciement abusif:'
        ' indemnités de préavis et dommages-intérêts.'
    ),
    'طرد': (
        'المواد 61-65: التعويض عن الفصل التعسفي والإنذار. Licenciement abusif:'
        ' indemnités de préavis et dommages-intérêts.'
    ),
    'تجربة': (
        'المادة 13: فترة التجربة: الأطر 3 أشهر، المستخدمون 1.5 شهر، العمال 15'
        ' يوماً. Période d'essai: Cadres 3 mois, Employés 1.5 mois, Ouvriers'
        ' 15 jours.'
    ),
    'ساعات إضافية': (
        'المادة 196: زيادة 25% نهاراً و50% ليلاً. Heures supplémentaires:'
        ' majoration de 25% à 50%.'
    ),
}


def retrieve_context(query: str) -> str:
  retrieved = [
      text for key, text in LEGAL_KNOWLEDGE_BASE.items() if key in query.lower()
  ]
  return (
      '\n'.join(retrieved)
      if retrieved
      else 'المقتضيات العامة لمدونة الشغل المغربية (Loi 65.99).'
  )


# ---------------------------------------------------------
# 7. قسم الأدوات والتحميل المنسق
# ---------------------------------------------------------
with st.expander(current_texts['tools']):
  col_reset, col_txt, col_docx = st.columns(3)

  with col_reset:
    if st.button(current_texts['reset']):
      st.session_state.messages = [
          {'role': 'assistant', 'content': current_texts['welcome']}
      ]
      st.rerun()

  if 'messages' in st.session_state and len(st.session_state.messages) > 1:
    with col_txt:
      chat_text = '\n\n'.join([
          f"{'User' if m['role']=='user' else 'Legal AI'}: {m['content']}"
          for m in st.session_state.messages
      ])
      st.download_button(
          current_texts['download_txt'],
          data=chat_text,
          file_name='legal_consultation.txt',
          mime='text/plain',
      )

    with col_docx:
      docx_bytes = generate_docx(st.session_state.messages)
      st.download_button(
          current_texts['download_word'],
          data=docx_bytes,
          file_name='legal_consultation.docx',
          mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      )

# ---------------------------------------------------------
# 8. إدارة المحادثة والأسئلة السريعة
# ---------------------------------------------------------
if (
    'messages' not in st.session_state
    or len(st.session_state.messages) == 0
    or st.session_state.messages[0]['content']
    not in [TEXTS[k]['welcome'] for k in TEXTS]
):
  st.session_state.messages = [
      {'role': 'assistant', 'content': current_texts['welcome']}
  ]

if len(st.session_state.messages) <= 1:
  st.markdown(f"**{current_texts['quick_questions']}**")
  q_cols = st.columns(3)

  prompt_to_send = None
  if q_cols[0].button(f"📌 {current_texts['q1']}"):
    prompt_to_send = current_texts['q1']
  if q_cols[1].button(f"📌 {current_texts['q2']}"):
    prompt_to_send = current_texts['q2']
  if q_cols[2].button(f"📌 {current_texts['q3']}"):
    prompt_to_send = current_texts['q3']

  if prompt_to_send:
    st.session_state.messages.append({'role': 'user', 'content': prompt_to_send})
    st.rerun()

# عرض المحادثات
for msg in st.session_state.messages:
  with st.chat_message(msg['role']):
    st.markdown(msg['content'])

# ---------------------------------------------------------
# 9. معالجة الردود بلغة المستخدم المختارة
# ---------------------------------------------------------
user_input = st.chat_input(current_texts['input_placeholder'])

if user_input or (
    len(st.session_state.messages) > 1
    and st.session_state.messages[-1]['role'] == 'user'
    and len(st.session_state.messages) % 2 == 0
):

  current_prompt = (
      user_input if user_input else st.session_state.messages[-1]['content']
  )

  if user_input:
    st.session_state.messages.append({'role': 'user', 'content': current_prompt})
    with st.chat_message('user'):
      st.markdown(current_prompt)

  context = retrieve_context(current_prompt)

  # تخصيص لغة الإجابة بحسب الخيار المختار
  lang_instruction = {
      'ar': (
          'أجب باللغة العربية الفصحى مع الاستشهاد بمواد مدونة الشغل المغربية'
          ' (القانون 65.99).'
      ),
      'fr': (
          'Répondez en Français professionnel en citant les articles du Code'
          ' du Travail Marocain (Loi 65.99).'
      ),
      'en': (
          'Answer in professional English referencing articles of the Moroccan'
          ' Labor Code (Law 65.99).'
      ),
  }[st.session_state.lang]

  system_prompt = f"""
    You are an expert Moroccan Legal Assistant specializing in the Moroccan Labor Code (Law 65.99).
    Context: {context}
    Language Rule: {lang_instruction}
    Provide structured, accurate, and professional legal answers with disclaimer at the end.
    """

  messages_payload = [{'role': 'system', 'content': system_prompt}]
  for m in st.session_state.messages:
    messages_payload.append({'role': m['role'], 'content': m['content']})

  with st.chat_message('assistant'):
    with st.spinner('...' if st.session_state.lang != 'ar' else 'جاري التحليل القانوني...'):
      try:
        response = client.chat.completions.create(
            model='llama-3.3-70b-versatile',
            messages=messages_payload,
            temperature=0.2,
        )
        bot_reply = response.choices[0].message.content
        st.markdown(bot_reply)
        st.session_state.messages.append(
            {'role': 'assistant', 'content': bot_reply}
        )
        st.rerun()
      except Exception as e:
        st.error(f'Error: {e}')
