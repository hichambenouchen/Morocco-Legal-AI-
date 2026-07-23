import io
import os
import re
import math
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
    page_title="المستشار القانوني الذكي الشامل | JurisConsult AI Morocco",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------
# 2. تصميم CSS احترافي
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
        max-width: 1150px !important;
    }

    /* Hero Header Styling */
    .hero-header {
        background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 100%);
        border-radius: 16px;
        padding: 28px 32px;
        color: white;
        margin-bottom: 25px;
        box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.25);
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    .hero-title {
        font-size: 2.3rem;
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

    .rag-badge {
        background-color: #3b82f6;
        color: white;
        font-size: 0.75rem;
        padding: 4px 10px;
        border-radius: 20px;
        font-weight: 600;
        margin-right: 10px;
        vertical-align: middle;
    }

    /* Quick Action Buttons */
    .stButton>button {
        border-radius: 10px !important;
        border: 1px solid #e2e8f0 !important;
        transition: all 0.2s ease !important;
    }

    .stButton>button:hover {
        border-color: #2563eb !important;
        color: #2563eb !important;
        background-color: #f8fafc !important;
    }

    /* Chat Styling */
    .stChatMessage {
        border-radius: 14px !important;
        padding: 15px !important;
        margin-bottom: 12px !important;
        box-shadow: 0 2px 5px rgba(0,0,0,0.03);
    }

    /* Mobile Responsive */
    @media (max-width: 768px) {
        [data-testid="stSidebar"] { display: none !important; }
        [data-testid="collapsedControl"] { display: none !important; }
        .hero-header {
            padding: 20px;
            text-align: center;
        }
        .hero-title {
            font-size: 1.6rem;
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
# 3. محول اللغات الثلاثي
# ---------------------------------------------------------
if "lang" not in st.session_state:
    st.session_state.lang = "ar"

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

TEXTS = {
    "ar": {
        "title": "المستشار القانوني المغربي الشامل",
        "subtitle": "نظام استرجاع سياقي ذكي (Full RAG) يغطي مدونة الشغل، مدونة الأسرة، القانون الجنائي، الالتزامات والعقود، والمسطرة المدنية",
        "welcome": "مرحباً بك! أنا مستشارك القانوني المغربي المعتمد بنظام RAG الشامل. اطرح أي استفسار قانوني وسأقوم بالبحث المباشر والمطابقة مع نصوص القوانين المغربية.",
        "input_placeholder": "اطرح سؤالك القانوني (مثال: حقوق الأجير، الطلاق والنفقة، الكراء، العقوبات...)",
        "quick_questions": "💡 استفسارات شائعة في مختلف القوانين:",
        "q1": "ما هي حقوق الأجير عند الفصل التعسفي حسب مدونة الشغل؟",
        "q2": "ما هي أنواع الطلاق وإجراءات النفقة في مدونة الأسرة؟",
        "q3": "ما هي الشروط القانونية لإنهاء عقد الكراء السكني؟",
        "tools": "🛠️ أدوات إدارة الجلسة وتحميل التقارير",
        "reset": "🗑️ مسح المحادثة",
        "download_txt": "📥 تقرير نصي (TXT)",
        "download_word": "📄 تقرير وورد (DOCX)",
        "rag_sources": "📚 النصوص والمواد القانونية المسترجعة تلقائياً لاستفسارك:",
    },
    "fr": {
        "title": "JurisConsult Maroc - Full RAG AI",
        "subtitle": "Système de Recherche Juridique Intelligente (Code du Travail, Code de la Famille, Code Pénal, DOC, Procédure Civile)",
        "welcome": "Bonjour ! Je suis votre assistant juridique marocain propulsé par RAG. Posez votre question pour une analyse comparative directe des textes de loi marocains.",
        "input_placeholder": "Posez votre question (Licenciement, Divorce, Bruit/Voisinage, Contrats, Baux...)",
        "quick_questions": "💡 Exemples de questions juridiques :",
        "q1": "Quelles sont les indemnités de licenciement abusif ?",
        "q2": "Quelles sont les conditions du divorce et de la pension alimentaire ?",
        "q3": "Comment résilier légalement un contrat de bail d'habitation ?",
        "tools": "🛠️ Outils & Téléchargement du Rapport",
        "reset": "🗑️ Réinitialiser",
        "download_txt": "📥 Rapport (TXT)",
        "download_word": "📄 Rapport Word (DOCX)",
        "rag_sources": "📚 Articles juridiques extraits pour cette requête :",
    },
    "en": {
        "title": "Moroccan Comprehensive Legal RAG AI",
        "subtitle": "Advanced Full RAG Legal Search covering Labor Law, Family Law, Penal Code, DOC, and Civil Procedure",
        "welcome": "Welcome! I am your Moroccan AI Legal Advisor powered by Full RAG. Ask any legal query and I will retrieve directly relevant Moroccan statutes.",
        "input_placeholder": "Type your legal question (Employment, Family, Tenancy, Contracts, Criminal...)",
        "quick_questions": "💡 Frequent Law Queries:",
        "q1": "What compensation is due for wrongful termination under Labor Code?",
        "q2": "What are the rules regarding divorce and child support under Moudawana?",
        "q3": "What are the legal steps to terminate a residential lease contract?",
        "tools": "🛠️ Session Tools & Document Downloads",
        "reset": "🗑️ Reset Conversation",
        "download_txt": "📥 Export Report (TXT)",
        "download_word": "📄 Export Report (DOCX)",
        "rag_sources": "📚 Retrieved Statutory Legal Context:",
    },
}

current_texts = TEXTS[st.session_state.lang]

# ---------------------------------------------------------
# 4. الهيدر الرئيسي
# ---------------------------------------------------------
st.markdown(
    f"""
    <div class="hero-header">
        <div class="hero-title">
            ⚖️ {current_texts['title']} <span class="rag-badge">Full RAG Engine 2.0</span>
        </div>
        <div class="hero-subtitle">{current_texts['subtitle']}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# 5. قاعدة المعرفة المتكاملة ومحرك RAG
# ---------------------------------------------------------
FULL_LEGAL_CORPUS = [
    # --- مدونة الشغل (القانون 65.99) ---
    {"law": "مدونة الشغل - المادة 13", "category": "شغل", "text": "تحدد فترة التجربة بالنسبة للعقود غير محددة المدة في: 3 أشهر للأطر وما ماثلهم، شهر ونصف للمستخدمين، و15 يوما للعمال. يمكن تجديد فترة التجربة مرة واحدة فقط."},
    {"law": "مدونة الشغل - المادة 61", "category": "شغل", "text": "يستحق الأجير المرتبط بعقد غير محدد المدة تعويضا عن الفصل التعسفي، ما لم يرتكب خطأ جسيما. ويشمل التعويض: التعويض عن الفصل، التعويض عن مهلة الإشعار، والتعويض عن الضرر."},
    {"law": "مدونة الشغل - المادة 62", "category": "شغل", "text": "قبل فصل الأجير، يجب أن تتاح له فرصة الدفاع عن نفسه باستماعه من طرف المشغل أو من ينيبه بحضور مندوب الأجراء أو الممثل النقابي في أجل لا يتعدى 8 أيام من تاريخ ثبوت الفعل."},
    {"law": "مدونة الشغل - المادة 152", "category": "شغل", "text": "تتمتع الأجيرة بمناسبة الحمل والولادة برخصة أمومة مدتها 14 أسبوعاً متصلة مؤدى عنها. كما يستفيد الأب الأجير من رخصة مدتها 3 أيام بمناسبة كل ولادة."},
    {"law": "مدونة الشغل - المادة 196", "category": "شغل", "text": "تعتبر ساعات إضافية الساعات الفائضة عن النشاط العادي للأجير، وتؤدى بقسط يزيد بـ 25% نهاراً و50% ليلاً، وترتفع إلى 50% نهارا و100% ليلا في الأعياد والعطل."},
    {"law": "مدونة الشغل - المادة 231", "category": "شغل", "text": "يستحق الأجير عطلة سنوية مؤدى عنها قدرها يوم ونصف يوم من العمل الفعلي عن كل شهر من الخدمة الفعلية بعد قضائه 6 أشهر متصلة في المقاولة."},

    # --- مدونة الأسرة (القانون 70.03) ---
    {"law": "مدونة الأسرة - المادة 4", "category": "أسرة", "text": "الزواج هو ميثاق تراض وترابط شرعي بين رجل وامرأة على وجه الدوام غايته الإحصان والعفاف وإنشاء أسرة مستقرة برعاية الزوجين."},
    {"law": "مدونة الأسرة - المادة 78", "category": "أسرة", "text": "الطلاق حل ميثاق الزوجية يمارسه الزوج والزوجة، كل بحسب شروطه تحت مراقبة القاضي ووفق أحكام المدونة."},
    {"law": "مدونة الأسرة - المادة 84", "category": "أسرة", "text": "تشتمل مستحقات الزوجة عند الطلاق على: الصداق المسمى إن كان مؤجلاً، ونفقة العدة، والمتعة التي تراعي مدة الزوجية والوضع المالي للزوج."},
    {"law": "مدونة الأسرة - المادة 163", "category": "أسرة", "text": "الحضانة هي حفظ الولد مما يضره والقيم بفرضه ورعايته. وتمنح الحضانة للأم، ثم للأب، ثم لأم الأم، مع مراعاة مصلحة المحضون الفضلى."},
    {"law": "مدونة الأسرة - المادة 189", "category": "أسرة", "text": "تشتمل النفقة على الغذاء والكسوة والعلاج والتعليم للمحضون وما يعتبر من الضروريات، وتراعى فيها سعة الملتزم بها وحال الملتزم له."},

    # --- قانون الالتزامات والعقود (DOC) والكراء ---
    {"law": "قانون الالتزامات والعقود - المادة 230", "category": "عقود", "text": "الالتزامات التعاقدية المنشأة على وجه صحيح تقوم مقام القانون بالنسبة إلى من أنشأوها، ولا تجوز إلغاؤها إلا بتراضيهما أو في الحالات التي ينص عليها القانون."},
    {"law": "قانون الكراء السكني (67.12) - المادة 12", "category": "كراء", "text": "يلتزم المكري بتسليم المحل للمكتري وهو في حالة صالحة للاستعمال، ويضمن المكري للمكتري التعرضات والاستحقاقات التي تعكر انتفاعه بالمحل."},
    {"law": "قانون الكراء السكني (67.12) - المادة 44", "category": "كراء", "text": "لا ينتهي عقد الكراء بقوة القانون إلا بعد الإشعار بالإفراغ وتوجيه إنذار المكري للمكتري بأجل لا يقل عن شهرين مع استناد الإفراغ لسبب مشروع قانوناً."},
    {"law": "قانون الالتزامات والعقود - المادة 77", "category": "عقود", "text": "كل فعل يجرمه القانون يأتيه الإنسان عن علم واختيار ومن غير أن يسمح به القانون، أحدث ضرراً مادياً أو معنوياً للغير، يلتزم مرتكبه بتعويض هذا الضرر."},

    # --- القانون الجنائي المغربي ---
    {"law": "القانون الجنائي - المادة 2", "category": "جنائي", "text": "لا يسوغ لأحد أن يعتذر بجهل التشريع الجنائي، ولا يعاقب أحد على فعل لم يكن يعتبر جريمة بمقتضى القانون وقت ارتكابه."},
    {"law": "القانون الجنائي - المادة 505", "category": "جنائي", "text": "من اختلس عمداً مالاً مملوكاً للغير يعتبر سارقاً، ويعاقب بالسجن من سنة إلى خمس سنوات وغرامة مالية."},
    {"law": "القانون الجنائي - المادة 540", "category": "جنائي", "text": "يعاقب بالحبس من سنة إلى خمس سنوات وغرامة كل من استعمل الاحتيال والخداع لإيقاع شخص في الغلط وسلبه أموالاً أو ممتلكات."},

    # --- قانون المسطرة المدنية ---
    {"law": "قانون المسطرة المدنية - المادة 32", "category": "مسطرة", "text": "تُقدم الدعوى أمام المحكمة الابتدائية بمقال مكتوب أو بتصريح شفوي يدلي به المدعي أمام كتابة ضبط المحكمة."},
    {"law": "قانون المسطرة المدنية - المادة 134", "category": "مسطرة", "text": "تحدد آجال الاستئناف في ثلاثين يوماً من تاريخ التبليغ الرسمي للحكم المطعون فيه، ما لم ينص القانون على خلاقه."},
]

def clean_and_tokenize(text):
    text = re.sub(r'[^\w\s]', '', text.lower())
    return set(text.split())

def tfidf_similarity_search(query, top_k=3):
    query_tokens = clean_and_tokenize(query)
    if not query_tokens:
        return FULL_LEGAL_CORPUS[:top_k]

    scored_docs = []
    for doc in FULL_LEGAL_CORPUS:
        doc_tokens = clean_and_tokenize(doc["text"] + " " + doc["law"] + " " + doc["category"])
        intersection = query_tokens.intersection(doc_tokens)
        score = len(intersection) / (math.sqrt(len(query_tokens)) * math.sqrt(len(doc_tokens)) + 1e-5)
        
        for q_token in query_tokens:
            if q_token in doc["category"]:
                score += 0.5
        
        scored_docs.append((score, doc))

    scored_docs.sort(key=lambda x: x[0], reverse=True)
    retrieved = [doc for score, doc in scored_docs[:top_k] if score > 0]
    
    if not retrieved:
        retrieved = FULL_LEGAL_CORPUS[:top_k]
    
    return retrieved

# ---------------------------------------------------------
# 6. دالة إنشاء تقرير Word المتقدم
# ---------------------------------------------------------
def generate_docx(messages):
    doc = docx.Document()

    def set_rtl(p):
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        p_pr = p._p.get_or_add_pPr()
        bidi = OxmlElement('w:bidi')
        bidi.set(qn('w:val'), '1')
        p_pr.append(bidi)

    title = doc.add_paragraph("Rapport de Consultation Juridique RAG - Droit Marocain")
    if st.session_state.lang == "ar":
        set_rtl(title)
        title.runs[0].text = "تقرير استشارة قانونية شاملة - التشريع المغربي (Full RAG)"

    title.runs[0].font.bold = True
    title.runs[0].font.size = docx.shared.Pt(15)

    for msg in messages:
        role_name = "المستخدم / User" if msg["role"] == "user" else "المستشار القانوني / JurisConsult RAG"
        p = doc.add_paragraph()
        if st.session_state.lang == "ar":
            set_rtl(p)

        run_role = p.add_run(f"[{role_name}]:\n")
        run_role.bold = True

        p_content = doc.add_paragraph(msg["content"])
        if st.session_state.lang == "ar":
            set_rtl(p_content)
        doc.add_paragraph("-" * 45)

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()

# ---------------------------------------------------------
# 7. إعداد مفتاح API ومحرك Groq
# ---------------------------------------------------------
api_key = st.secrets.get("GROQ_API_KEY") or os.getenv("GROQ_API_KEY")
if not api_key:
    st.error("⚠️ GROQ_API_KEY Missing! Please add it to Streamlit secrets.")
    st.stop()

client = Groq(api_key=api_key)

# ---------------------------------------------------------
# 8. أدوات التحميل وإعادة الضبط
# ---------------------------------------------------------
with st.expander(current_texts["tools"]):
    col_reset, col_txt, col_docx = st.columns(3)

    with col_reset:
        if st.button(current_texts["reset"]):
            st.session_state.messages = [{"role": "assistant", "content": current_texts["welcome"]}]
            st.rerun()

    if "messages" in st.session_state and len(st.session_state.messages) > 1:
        with col_txt:
            chat_text = "\n\n".join([f"{'User' if m['role']=='user' else 'Legal RAG AI'}: {m['content']}" for m in st.session_state.messages])
            st.download_button(current_texts["download_txt"], data=chat_text, file_name="rag_legal_consultation.txt", mime="text/plain")

        with col_docx:
            docx_bytes = generate_docx(st.session_state.messages)
            st.download_button(current_texts["download_word"], data=docx_bytes, file_name="rag_legal_consultation.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

# ---------------------------------------------------------
# 9. إدارة سجل الرسائل والأسئلة السريعة
# ---------------------------------------------------------
if "messages" not in st.session_state or len(st.session_state.messages) == 0 or st.session_state.messages[0]["content"] not in [TEXTS[k]["welcome"] for k in TEXTS]:
    st.session_state.messages = [{"role": "assistant", "content": current_texts["welcome"]}]

if len(st.session_state.messages) <= 1:
    st.markdown(f"**{current_texts['quick_questions']}**")
    q_cols = st.columns(3)

    prompt_to_send = None
    if q_cols[0].button(f"📌 {current_texts['q1']}"):
        prompt_to_send = current_texts["q1"]
    if q_cols[1].button(f"📌 {current_texts['q2']}"):
        prompt_to_send = current_texts["q2"]
    if q_cols[2].button(f"📌 {current_texts['q3']}"):
        prompt_to_send = current_texts["q3"]

    if prompt_to_send:
        st.session_state.messages.append({"role": "user", "content": prompt_to_send})
        st.rerun()

# عرض المحادثة
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ---------------------------------------------------------
# 10. معالجة الإدخال بنظام RAG الشامل
# ---------------------------------------------------------
user_input = st.chat_input(current_texts["input_placeholder"])

if user_input or (len(st.session_state.messages) > 1 and st.session_state.messages[-1]["role"] == "user" and len(st.session_state.messages) % 2 == 0):

    current_prompt = user_input if user_input else st.session_state.messages[-1]["content"]

    if user_input:
        st.session_state.messages.append({"role": "user", "content": current_prompt})
        with st.chat_message("user"):
            st.markdown(current_prompt)

    # استرجاع النصوص ذات الصلة عبر محرك RAG
    retrieved_docs = tfidf_similarity_search(current_prompt, top_k=3)
    
    formatted_context = ""
    sources_ui = []
    for idx, doc in enumerate(retrieved_docs, 1):
        formatted_context += f"[{idx}] {doc['law']}: {doc['text']}\n"
        sources_ui.append(f"• **{doc['law']}**: {doc['text']}")

    lang_instruction = {
        "ar": "أجب باللغة العربية الفصحى بصياغة قانونية رصينة وموضوعية. استشهد بالمواد القانونية المسترجعة أدناه.",
        "fr": "Répondez en français juridique rigoureux. Citez les articles de loi marocains extraits ci-dessous.",
        "en": "Answer in precise legal English. Cite the extracted Moroccan statutory articles below."
    }[st.session_state.lang]

    system_prompt = f"""
    You are an expert Moroccan Senior Legal Counsel with full mastery of Moroccan Laws (Labor Code, Moudawana Family Law, Penal Code, DOC, Civil Procedure).
    
    Retrieved Statutory Context (RAG):
    {formatted_context}
    
    Language Requirement: {lang_instruction}
    
    Instructions:
    1. Base your legal reasoning primarily on the retrieved context above and Moroccan jurisprudence.
    2. Explicitly cite the specific law and article numbers in your explanation.
    3. Structure your response clearly with headings, bullet points, and an academic legal disclaimer at the end.
    """

    messages_payload = [{"role": "system", "content": system_prompt}]
    for m in st.session_state.messages:
        messages_payload.append({"role": m["role"], "content": m["content"]})

    with st.chat_message("assistant"):
        # إظهار المصادر المسترجعة للمستخدم لشفافية كاملة
        with st.expander(current_texts["rag_sources"]):
            for src in sources_ui:
                st.markdown(src)

        with st.spinner("جاري استرجاع النصوص القانونية ومطابقة القوانين..." if st.session_state.lang == "ar" else "Retrieving Moroccan legal context..."):
            try:
                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=messages_payload,
                    temperature=0.2,
                )
                bot_reply = response.choices[0].message.content
                st.markdown(bot_reply)
                st.session_state.messages.append({"role": "assistant", "content": bot_reply})
                st.rerun()
            except Exception as e:
                st.error(f"Error executing RAG completion: {e}")
