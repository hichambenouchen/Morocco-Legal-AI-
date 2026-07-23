import io
import os
import re
import docx
import pypdf
import pdfplumber
import chromadb
from chromadb.utils import embedding_functions
from groq import Groq
import streamlit as st

# ---------------------------------------------------------
# 1. إعدادات الصفحة الأساسية
# ---------------------------------------------------------
st.set_page_config(
    page_title="الموسوعة القانونية المغربية | Moroccan Legal AI",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------
# 2. إدارة حالة الجلسة (Session State)
# ---------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

if "uploaded_doc_text" not in st.session_state:
    st.session_state.uploaded_doc_text = ""

if "uploaded_doc_name" not in st.session_state:
    st.session_state.uploaded_doc_name = ""

if "language" not in st.session_state:
    st.session_state.language = "العربية"

# ---------------------------------------------------------
# 3. النصوص المترجمة للواجهة
# ---------------------------------------------------------
UI_TEXTS = {
    "العربية": {
        "title": "⚖️ الموسوعة القانونية المغربية الذكية",
        "subtitle": "مساعد قانوني مغربي معزز بالتحليل الدلالي وقواعد البيانات الرسمية (ChromaDB Vector RAG)",
        "welcome": "مرحباً بك! أنا مساعدك القانوني المغربي. يمكنك طرح أي سؤال أو رفع عقد/وثيقة لمطابقتها مع التشريع المغربي.",
        "attach_btn": "➕ إرفاق",
        "attach_title": "📎 إرفاق عقد أو وثيقة (PDF / Word)",
        "attach_label": "اختر الملف:",
        "placeholder": "اطرح سؤالك القانوني هنا...",
        "file_info": "📄 الملف المرفق المعتمد حالياً:",
        "reset_btn": "🗑️ إعادة ضبط الجلسة والملفات",
        "spinner": "جاري فحص المراجع القانونية والتحليل..."
    },
    "Français": {
        "title": "⚖️ Encyclopédie Juridique Marocaine Intelligente",
        "subtitle": "Assistant juridique marocain optimisé par l'analyse sémantique (ChromaDB Vector RAG)",
        "welcome": "Bienvenue! Je suis votre assistant juridique marocain. Posez votre question ou téléchargez un document pour analyse.",
        "attach_btn": "➕ Joindre",
        "attach_title": "📎 Joindre un contrat ou un document (PDF / Word)",
        "attach_label": "Choisissez un fichier:",
        "placeholder": "Posez votre question juridique ici...",
        "file_info": "📄 Document actuellement chargé:",
        "reset_btn": "🗑️ Réinitialiser la session et les fichiers",
        "spinner": "Analyse des références juridiques en cours..."
    },
    "English": {
        "title": "⚖️ Moroccan Smart Legal AI Advisor",
        "subtitle": "Moroccan Legal Assistant powered by semantic analysis and official databases (ChromaDB Vector RAG)",
        "welcome": "Welcome! I am your Moroccan legal AI advisor. Feel free to ask any legal question or upload a document for review.",
        "attach_btn": "➕ Attach",
        "attach_title": "📎 Attach a Contract or Document (PDF / Word)",
        "attach_label": "Select file:",
        "placeholder": "Type your legal question here...",
        "file_info": "📄 Currently attached document:",
        "reset_btn": "🗑️ Reset Session & Clear Files",
        "spinner": "Analyzing legal records and processing..."
    }
}

# ---------------------------------------------------------
# 4. القائمة الجانبية (Sidebar) - اختيار اللغة والإعدادات
# ---------------------------------------------------------
with st.sidebar:
    st.header("🌐 Language / اللغة")
    selected_lang = st.selectbox(
        "اختر لغة الواجهة والتحليل:",
        options=["🇲🇦 العربية", "🇫🇷 Français", "🇬🇧 English"],
        index=0 if st.session_state.language == "العربية" else (1 if st.session_state.language == "Français" else 2),
    )
    
    if "العربية" in selected_lang:
        current_lang = "العربية"
    elif "Français" in selected_lang:
        current_lang = "Français"
    else:
        current_lang = "English"

    if st.session_state.language != current_lang:
        st.session_state.language = current_lang
        st.session_state.messages = []
        st.rerun()

    st.divider()
    st.header("⚙️ Options")
    texts = UI_TEXTS[st.session_state.language]
    if st.button(texts["reset_btn"], use_container_width=True):
        st.session_state.messages = []
        st.session_state.uploaded_doc_text = ""
        st.session_state.uploaded_doc_name = ""
        st.rerun()

# ---------------------------------------------------------
# 5. CSS ناعم وآمن لمنع تداخل الأعمدة
# ---------------------------------------------------------
is_rtl = st.session_state.language == "العربية"
direction = "rtl" if is_rtl else "ltr"
text_align = "right" if is_rtl else "left"

st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800;900&display=swap');

    /* تطبيق الخط بدون كسر اتجاه الهيكل الأساسي لـ Streamlit */
    p, h1, h2, h3, div {{
        font-family: 'Cairo', sans-serif;
    }}

    /* البطاقات الرئيسية */
    .hero-header {{
        background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 50%, #1e40af 100%);
        border-radius: 16px;
        padding: 24px;
        color: white;
        margin-bottom: 20px;
        direction: {direction};
        text-align: {text_align};
    }}
    
    .hero-title {{
        font-size: 1.8rem;
        font-weight: 800;
        margin: 0;
    }}

    .hero-subtitle {{
        font-size: 0.95rem;
        color: #cbd5e1;
        margin-top: 8px;
    }}

    /* تنسيق فقاعات المحادثة */
    .stChatMessage {{
        direction: {direction} !important;
        text-align: {text_align} !important;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# 6. بناء قاعدة البيانات المتجهة (ChromaDB)
# ---------------------------------------------------------
FULL_LEGAL_CORPUS = [
    {"id": "doc1", "law": "مرسوم الصفقات العمومية - المادة 4 و 5", "category": "صفقات عمومية", "text": "تخضع الصفقات العمومية لمبادئ حرية الوصول إلى الطلبية العمومية، المساواة في التعامل مع المتنافسين، والشفافية في اختيارات صاحب المشروع."},
    {"id": "doc2", "law": "قانون الوظيفة العمومية - اللجان المتساوية الأعضاء", "category": "وظيفة عمومية", "text": "تحدث في كل إدارة عمومية لجان إدارية متساوية الأعضاء تختص بالنظر في الترقية والعقوبات التأديبية للموظفين العموميين وتتكون من ممثلين للإدارة وممثلين للموظفين."},
    {"id": "doc3", "law": "مدونة الشغل - المادة 13", "category": "شغل", "text": "تحدد فترة التجربة بالنسبة للعقود غير محددة المدة في: 3 أشهر للأطر، شهر ونصف للمستخدمين، و15 يوما للعمال."},
    {"id": "doc4", "law": "مدونة الشغل - المادة 464 (مندوبو الأجراء)", "category": "شغل", "text": "يجب انتخاب مندوبي الأجراء في جميع المؤسسات التي تشغل اعتيادياً ما لا يقل عن عشرة أجراء دائمين."},
]

@st.cache_resource
def init_vector_db():
    chroma_client = chromadb.Client()
    emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="paraphrase-multilingual-MiniLM-L12-v2")
    collection = chroma_client.get_or_create_collection(name="moroccan_legal_db", embedding_function=emb_fn)
    
    if collection.count() == 0:
        ids = [doc["id"] for doc in FULL_LEGAL_CORPUS]
        documents = [f"{doc['law']} - {doc['text']}" for doc in FULL_LEGAL_CORPUS]
        metadatas = [{"law": doc["law"], "category": doc["category"], "text": doc["text"]} for doc in FULL_LEGAL_CORPUS]
        collection.add(ids=ids, documents=documents, metadatas=metadatas)
    return collection

vector_collection = init_vector_db()

def semantic_search(query, top_k=3):
    results = vector_collection.query(query_texts=[query], n_results=top_k)
    retrieved = []
    if results and "metadatas" in results and results["metadatas"]:
        for meta in results["metadatas"][0]:
            retrieved.append(meta)
    return retrieved

# ---------------------------------------------------------
# 7. قراءة واستخرج النصوص
# ---------------------------------------------------------
def clean_text(text):
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def extract_text_from_file(uploaded_file):
    text = ""
    try:
        if uploaded_file.name.endswith(".pdf"):
            with pdfplumber.open(uploaded_file) as pdf:
                for page in pdf.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted + "\n"
            if not text.strip():
                uploaded_file.seek(0)
                reader = pypdf.PdfReader(uploaded_file)
                for page in reader.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted + "\n"
        elif uploaded_file.name.endswith(".docx"):
            doc = docx.Document(uploaded_file)
            for p in doc.paragraphs:
                if p.text:
                    text += p.text + "\n"
    except Exception as e:
        st.error(f"Error reading file: {e}")
    return clean_text(text)

def extract_relevant_snippets(query, full_text, top_n=3, chunk_size=1200):
    if not full_text:
        return ""
    if len(full_text) <= chunk_size:
        return full_text

    chunks = [full_text[i:i+chunk_size] for i in range(0, len(full_text), chunk_size - 200)]
    keywords = [k for k in re.findall(r'\w+', query) if len(k) > 2]
    
    scored_chunks = []
    for chunk in chunks:
        score = sum(chunk.count(kw) for kw in keywords)
        if score > 0:
            scored_chunks.append((score, chunk))
            
    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    
    if scored_chunks:
        selected = [item[1] for item in scored_chunks[:top_n]]
        return "\n--- EXTRACTED SNIPPET ---\n".join(selected)
    else:
        return "NO_DIRECT_MATCH"

# ---------------------------------------------------------
# 8. عرض البانر والمحادثات
# ---------------------------------------------------------
st.markdown(
    f"""
    <div class="hero-header">
        <div class="hero-title">{texts['title']}</div>
        <div class="hero-subtitle">{texts['subtitle']}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

if not st.session_state.messages:
    st.session_state.messages.append({"role": "assistant", "content": texts["welcome"]})

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ---------------------------------------------------------
# 9. شريط الإدخال المدمج
# ---------------------------------------------------------
col_file, col_input = st.columns([2, 8], vertical_alignment="bottom")

with col_file:
    with st.popover(texts["attach_btn"], use_container_width=True):
        st.markdown(f"### {texts['attach_title']}")
        file_obj = st.file_uploader(texts["attach_label"], type=["pdf", "docx"], key="doc_uploader")
        if file_obj is not None:
            if st.session_state.uploaded_doc_name != file_obj.name:
                extracted = extract_text_from_file(file_obj)
                st.session_state.uploaded_doc_text = extracted
                st.session_state.uploaded_doc_name = file_obj.name
                st.success(f"Loaded: {file_obj.name}")

if st.session_state.uploaded_doc_name:
    st.info(f"{texts['file_info']} **{st.session_state.uploaded_doc_name}** ({len(st.session_state.uploaded_doc_text)} chars)")

with col_input:
    user_input = st.chat_input(texts["placeholder"])

# ---------------------------------------------------------
# 10. المعالجة الذكية للإجابة
# ---------------------------------------------------------
api_key = st.secrets.get("GROQ_API_KEY") or os.getenv("GROQ_API_KEY")
if not api_key:
    st.error("⚠️ GROQ_API_KEY missing in Secrets!")
    st.stop()

client = Groq(api_key=api_key)

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    doc_snippet = ""
    match_found = True
    if st.session_state.uploaded_doc_text:
        doc_snippet = extract_relevant_snippets(user_input, st.session_state.uploaded_doc_text)
        if doc_snippet == "NO_DIRECT_MATCH":
            match_found = False
            doc_snippet = ""

    retrieved_docs = semantic_search(user_input, top_k=3)
    formatted_context = "\n".join([f"- {d['law']}: {d['text']}" for d in retrieved_docs])

    doc_instruction = ""
    if st.session_state.uploaded_doc_text:
        if match_found and doc_snippet:
            doc_instruction = f"""
            ATTACHED FILE: ({st.session_state.uploaded_doc_name})
            RELEVANT EXTRACTS FROM ATTACHED FILE:
            \"\"\"
            {doc_snippet}
            \"\"\"
            """
        else:
            doc_instruction = f"""
            ATTACHED FILE: ({st.session_state.uploaded_doc_name})
            NOTE: The user's query topic WAS NOT FOUND in the uploaded document text.
            INSTRUCTION: State clearly that this specific subject is not mentioned in the uploaded file ({st.session_state.uploaded_doc_name}), then explain the correct legal rule based on Moroccan legislation.
            """

    system_prompt = f"""
    You are an expert Moroccan Legal AI Advisor.
    Target Language for Output: {st.session_state.language}
    
    {doc_instruction}

    GENERAL MOROCCAN LAW STATUTES:
    {formatted_context}

    CRITICAL RULES:
    1. Reply fully in the target language: {st.session_state.language}.
    2. NEVER repeat paragraphs or sentences. Present a clean, well-structured response.
    3. Do NOT invent concepts.
    4. Respond directly, accurately, and professionally.
    """

    messages_payload = [{"role": "system", "content": system_prompt}]
    for m in st.session_state.messages:
        messages_payload.append({"role": m["role"], "content": m["content"]})

    with st.chat_message("assistant"):
        with st.spinner(texts["spinner"]):
            try:
                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=messages_payload,
                    temperature=0.0,
                )
                bot_reply = response.choices[0].message.content
                st.markdown(bot_reply)
                st.session_state.messages.append({"role": "assistant", "content": bot_reply})
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
