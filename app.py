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
# 1. إعدادات الصفحة والتصميم
# ---------------------------------------------------------
st.set_page_config(
    page_title="الموسوعة القانونية المغربية | Legal AI Agent",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800;900&display=swap');

    html, body, [class*="css"] {
        font-family: 'Cairo', sans-serif !important;
    }

    #MainMenu, footer, header {visibility: hidden;}

    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 7rem !important;
        max-width: 1100px !important;
    }

    .stChatMessage, .stChatMessage p, .stMarkdown, .stMarkdown p, .stMarkdown div {
        direction: rtl !important;
        text-align: right !important;
    }

    .stChatMessage {
        flex-direction: row-reverse !important;
        gap: 12px !important;
    }

    .hero-header {
        background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 50%, #1e40af 100%);
        border-radius: 18px;
        padding: 24px 28px;
        color: white;
        margin-bottom: 15px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
        direction: rtl !important;
        text-align: right !important;
    }
    
    .hero-title {
        font-size: 1.8rem;
        font-weight: 900;
        margin: 0;
        color: #ffffff;
    }

    .hero-subtitle {
        font-size: 0.95rem;
        color: #cbd5e1;
        margin-top: 6px;
    }

    /* تنسيق زر الإرفاق */
    div[data-element-id="stPopover"] > button {
        border-radius: 12px !important;
        height: 44px !important;
        border: 1px solid #cbd5e1 !important;
        background-color: #f8fafc !important;
        color: #1e293b !important;
        font-weight: bold !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
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
# 3. شريط اختيار اللغات العلوي مع الأيقونات 🌐
# ---------------------------------------------------------
lang_col1, lang_col2 = st.columns([8, 2])

with lang_col2:
    selected_lang = st.selectbox(
        "🌐 اللغة / Langue",
        options=["🇲🇦 العربية", "🇫🇷 Français"],
        index=0 if st.session_state.language == "العربية" else 1,
        key="lang_selector"
    )
    # تحديث متغير اللغة
    st.session_state.language = "العربية" if "العربية" in selected_lang else "Français"

# ---------------------------------------------------------
# 4. بناء قاعدة البيانات المتجهة (ChromaDB)
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
# 5. استخراج النصوص وتقسيمها
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
        st.error(f"خطأ في قراءة الملف: {e}")
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
        return "\n--- فقرة مطابقة ---\n".join(selected)
    else:
        return "NO_DIRECT_MATCH"

# ---------------------------------------------------------
# 6. القائمة الجانبية (Sidebar)
# ---------------------------------------------------------
with st.sidebar:
    st.header("⚙️ خيارات الجلسة")
    if st.button("🗑️ إعادة ضبط الجلسة والملفات", use_container_width=True):
        st.session_state.messages = []
        st.session_state.uploaded_doc_text = ""
        st.session_state.uploaded_doc_name = ""
        st.rerun()

# ---------------------------------------------------------
# 7. الهيدر والترحيب
# ---------------------------------------------------------
st.markdown(
    """
    <div class="hero-header">
        <div class="hero-title">⚖️ الموسوعة القانونية المغربية الذكية</div>
        <div class="hero-subtitle">Assistant Juridique Marocain المعزز بالجريدة الرسمية والتحليل الدلالي (ChromaDB Vector RAG)</div>
    </div>
    """,
    unsafe_allow_html=True,
)

if not st.session_state.messages:
    welcome_msg = "مرحباً بك! أنا مساعدك القانوني المغربي. يمكنك طرح أي سؤال أو رفع عقد/وثيقة لمطابقتها مع التشريع المغربي." if st.session_state.language == "العربية" else "Bienvenue! Je suis votre assistant juridique marocain. Posez votre question ou téléchargez un document."
    st.session_state.messages.append({"role": "assistant", "content": welcome_msg})

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ---------------------------------------------------------
# 8. شريط الإدخال المدمج
# ---------------------------------------------------------
col_file, col_input = st.columns([1.5, 8.5], vertical_alignment="bottom")

with col_file:
    with st.popover("➕ إرفاق", use_container_width=True):
        st.markdown("### 📎 إرفاق عقد أو وثيقة (PDF / Word)")
        file_obj = st.file_uploader("اختر الملف:", type=["pdf", "docx"], key="doc_uploader")
        if file_obj is not None:
            if st.session_state.uploaded_doc_name != file_obj.name:
                extracted = extract_text_from_file(file_obj)
                st.session_state.uploaded_doc_text = extracted
                st.session_state.uploaded_doc_name = file_obj.name
                st.success(f"تم تحميل وقراءة: {file_obj.name}")

if st.session_state.uploaded_doc_name:
    st.info(f"📄 الملف المرفق المعتمد حالياً: **{st.session_state.uploaded_doc_name}** ({len(st.session_state.uploaded_doc_text)} حرف)")

with col_input:
    placeholder_text = "اطرح سؤالك القانوني هنا..." if st.session_state.language == "العربية" else "Posez votre question juridique ici..."
    user_input = st.chat_input(placeholder_text)

# ---------------------------------------------------------
# 9. معالجة السؤال والتحليل الذكي
# ---------------------------------------------------------
api_key = st.secrets.get("GROQ_API_KEY") or os.getenv("GROQ_API_KEY")
if not api_key:
    st.error("⚠️ GROQ_API_KEY مفقود في Secrets!")
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
    Language: {st.session_state.language}
    
    {doc_instruction}

    GENERAL MOROCCAN LAW STATUTES:
    {formatted_context}

    CRITICAL RULES:
    1. NEVER repeat paragraphs or sentences. Present a clean, well-structured response.
    2. Do NOT invent concepts (e.g., do NOT attribute Public Sector terms like "اللجان المتساوية الأعضاء" to the Private Sector Code "modouana" unless making a legal distinction).
    3. Respond directly, accurately, and professionally in {st.session_state.language}.
    """

    messages_payload = [{"role": "system", "content": system_prompt}]
    for m in st.session_state.messages:
        messages_payload.append({"role": m["role"], "content": m["content"]})

    with st.chat_message("assistant"):
        with st.spinner("جاري فحص المراجع القانونية والتحليل..."):
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
                st.error(f"حدث خطأ: {e}")
