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
# 1. إعدادات الصفحة
# ---------------------------------------------------------
st.set_page_config(
    page_title="الموسوعة القانونية المغربية | Legal AI Agent",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------
# 2. إدارة حالة الجلسة (Session State) - حاسمة لمنع التوقف
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
# 3. تصميم الواجهة ودعم RTL واللغات
# ---------------------------------------------------------
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
        margin-bottom: 20px;
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
# 4. بناء قاعدة البيانات المتجهة (ChromaDB)
# ---------------------------------------------------------
FULL_LEGAL_CORPUS = [
    {"id": "doc1", "law": "مرسوم الصفقات العمومية - المادة 4 و 5", "category": "صفقات عمومية", "text": "تخضع الصفقات العمومية لمبادئ حرية الوصول إلى الطلبية العمومية، المساواة في التعامل مع المتنافسين، والشفافية في اختيارات صاحب المشروع."},
    {"id": "doc2", "law": "مرسوم الصفقات العمومية - المادة 16 و 17", "category": "صفقات عمومية", "text": "تتم طريقة إبرام الصفقات العمومية عن طريق طلبات العروض (مفتوح أو محدود)، المباراة، أو المسطرة التفاوضية."},
    {"id": "doc3", "law": "قانون الوظيفة العمومية - المادة 2 و 13", "category": "وظيفة عمومية", "text": "الموظف هو كل شخص يعين في وظيفة دائمة ويرسم في إحدى درجات التسلسل الإداري للإدارات التابعة للدولة."},
    {"id": "doc4", "law": "مدونة الشغل - المادة 13", "category": "شغل", "text": "تحدد فترة التجربة بالنسبة للعقود غير محددة المدة في: 3 أشهر للأطر وما ماثلهم، شهر ونصف للمستخدمين، و15 يوما للعمال."},
    {"id": "doc5", "law": "مدونة الشغل - المادة 61 و 62", "category": "شغل", "text": "يستحق الأجير تعويضاً عن الفصل التعسفي ما لم يرتكب خطأ جسيماً. ويجب الاستماع إليه بحضور مندوب الأجراء."},
    {"id": "doc6", "law": "قانون الكراء التجاري (49.16) - المادة 7", "category": "كراء تجاري", "text": "يستحق المكتري تعويضاً كاملاً عن الإفراغ يعادل الضرر الحاصل عن فقدان الأصل التجاري."},
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
# 5. استخراج النصوص من الملفات
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

# ---------------------------------------------------------
# 6. القائمة الجانبية: تحديد اللغة وإعادة الضبط
# ---------------------------------------------------------
with st.sidebar:
    st.header("🌐 إعدادات اللغة / Langue")
    lang_choice = st.radio("اختر لغة الإجابة / Langue المعتمدة:", ["العربية", "Français"], index=0 if st.session_state.language == "العربية" else 1)
    st.session_state.language = lang_choice

    st.divider()

    st.header("⚙️ خيارات الجلسة")
    if st.button("🗑️ إعادة ضبط الجلسة", use_container_width=True):
        st.session_state.messages = []
        st.session_state.uploaded_doc_text = ""
        st.session_state.uploaded_doc_name = ""
        st.rerun()

# ---------------------------------------------------------
# 7. الهيدر وتهيئة المحادثة הראשوية
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
# 8. شريط رفع الملفات وتثبيته في Session State
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
# 9. محرك الذكاء الاصطناعي والمعالجة
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

    retrieved_docs = semantic_search(user_input, top_k=3)
    formatted_context = "\n".join([f"- {d['law']}: {d['text']}" for d in retrieved_docs])

    doc_context_instruction = ""
    if st.session_state.uploaded_doc_text:
        doc_context_instruction = f"""
        USER UPLOADED DOCUMENT TEXT:
        \"\"\"
        {st.session_state.uploaded_doc_text[:4000]}
        \"\"\"
        Analyze this document text directly to answer the user request.
        """

    system_prompt = f"""
    You are an expert Moroccan Legal AI Advisor.
    Language to respond in: {st.session_state.language}
    
    {doc_context_instruction}

    Retrieved Moroccan Statutory Laws:
    {formatted_context}

    Instructions:
    1. Answer strictly in {st.session_state.language}.
    2. If the user asks about the attached document, analyze its text provided above.
    3. Cite relevant legal articles or dahirs where appropriate.
    4. Provide professional legal guidance.
    """

    messages_payload = [{"role": "system", "content": system_prompt}]
    for m in st.session_state.messages:
        messages_payload.append({"role": m["role"], "content": m["content"]})

    with st.chat_message("assistant"):
        with st.spinner("جاري التحليل واستخراج الإجابة..."):
            try:
                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=messages_payload,
                    temperature=0.15,
                )
                bot_reply = response.choices[0].message.content
                st.markdown(bot_reply)
                st.session_state.messages.append({"role": "assistant", "content": bot_reply})
                st.rerun()
            except Exception as e:
                st.error(f"حدث خطأ: {e}")
