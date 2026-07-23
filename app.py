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
    page_title="الموسوعة القانونية المغربية الشاملة | Legal AI Agent",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------
# 2. تصميم الواجهة ودعم RTL وتكتاكت الرفع المدمج
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
        max-width: 1200px !important;
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
        padding: 28px 32px;
        color: white;
        margin-bottom: 20px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
        direction: rtl !important;
        text-align: right !important;
    }
    
    .hero-title {
        font-size: 2.1rem;
        font-weight: 900;
        margin: 0;
        color: #ffffff;
    }

    .hero-subtitle {
        font-size: 0.98rem;
        color: #cbd5e1;
        margin-top: 8px;
        line-height: 1.6;
    }

    /* تنسيق زر الإرفاق ليظهر ملتصقاً بخانة الدردشة في الأسفل */
    div[data-element-id="stPopover"] {
        position: fixed;
        bottom: 25px;
        right: 18%;
        z-index: 99999;
    }
    
    div[data-element-id="stPopover"] > button {
        border-radius: 50% !important;
        width: 45px !important;
        height: 45px !important;
        padding: 0 !important;
        font-size: 22px !important;
        background-color: #1e3a8a !important;
        color: white !important;
        border: none !important;
        box-shadow: 0 4px 10px rgba(0,0,0,0.15) !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# 3. بناء قاعدة البيانات المتجهة (ChromaDB Vector Store)
# ---------------------------------------------------------
FULL_LEGAL_CORPUS = [
    {"id": "doc1", "law": "مرسوم الصفقات العمومية - المادة 4 و 5", "category": "صفقات عمومية", "text": "تخضع الصفقات العمومية لمبادئ حرية الوصول إلى الطلبية العمومية، المساواة في التعامل مع المتنافسين، والشفافية في اختيارات صاحب المشروع. وتشمل الصفقات: صفقة أشغال، توريدات، أو خدمات."},
    {"id": "doc2", "law": "مرسوم الصفقات العمومية - المادة 16 و 17", "category": "صفقات عمومية", "text": "تتم طريقة إبرام الصفقات العمومية عن طريق طلبات العروض (مفتوح أو محدود)، المباراة، أو المسطرة التفاوضية. يعتبر طلب العروض المفتوح هو الأصل."},
    {"id": "doc3", "law": "مرسوم الصفقات العمومية - المادة 40", "category": "صفقات عمومية", "text": "يستوجب على المتنافسين تقديم ضمان مؤقت للقبول في الصفقات العمومية، ثم يتوجب على النائل إيداع ضمان نهائي لضمان تنفيذه السليم للالتزامات التعاقدية."},
    {"id": "doc4", "law": "مرسوم الصفقات العمومية - المادة 136", "category": "صفقات عمومية", "text": "يمكن للمتنافسين تقديم شكايات ورسائل طعن للجنة الصفقات العمومية أو السلطة الحكومية المعنية في حال الإخلال بقواعد المنافسة والشفافية."},
    {"id": "doc5", "law": "قانون الوظيفة العمومية - المادة 2 و 13", "category": "وظيفة عمومية", "text": "الموظف هو كل شخص يعين في وظيفة دائمة ويرسم في إحدى درجات التسلسل الإداري للإدارات التابعة للدولة. والتوظيف يتم عبر المباريات للجميع بمساواة."},
    {"id": "doc6", "law": "قانون الوظيفة العمومية - المادة 39 و 40", "category": "وظيفة عمومية", "text": "للموظف الحق في العطلة السنوية المؤدى عنها ومدتها شهر عن كل سنة عمل. كما يستفيد من رخص المرض ورخص الولادة والأمومة."},
    {"id": "doc7", "law": "قانون الوظيفة العمومية - المادة 65 و 66", "category": "وظيفة عمومية", "text": "تحدد العقوبات التأديبية في درجتين: الأولى تشمل الإنذار والتوبيخ، والثانية تشمل الإنزلاق في الدرجة، الحرمان من الترقية، أو العزل."},
    {"id": "doc8", "law": "قانون الوظيفة العمومية - المادة 73", "category": "وظيفة عمومية", "text": "إذا ارتكب الموظف خطأ جسيماً جاز توقيفه فوراً من طرف السلطة التي لها حق التأديب مع خصم أجرته باستثناء التعويضات العائلية."},
    {"id": "doc9", "law": "مدونة الشغل - المادة 13", "category": "شغل", "text": "تحدد فترة التجربة بالنسبة للعقود غير محددة المدة في: 3 أشهر للأطر وما ماثلهم، شهر ونصف للمستخدمين، و15 يوما للعمال."},
    {"id": "doc10", "law": "مدونة الشغل - المادة 61 و 62", "category": "شغل", "text": "يستحق الأجير تعويضاً عن الفصل التعسفي ما لم يرتكب خطأ جسيماً. ويجب الاستماع إليه بحضور مندوب الأجراء في أجل لا يتعدى 8 أيام."},
    {"id": "doc11", "law": "قانون الكراء التجاري (49.16) - المادة 7", "category": "كراء تجاري", "text": "يستحق المكتري تعويضاً كاملاً عن الإفراغ يعادل الضرر الحاصل عن فقدان الأصل التجاري ما لم يستند الإفراغ لعدم أداء الكراء أو البناء."},
    {"id": "doc12", "law": "القانون الجنائي - المادة 540", "category": "جنائي", "text": "يعاقب بالحبس من سنة إلى خمس سنوات وغرامة كل من استعمل الاحتيال والخداع لإيقاع شخص في الغلط وسلبه أموالاً (النصب)."},
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
# 4. دالة استخراج وتنظيف النصوص من PDF / DOCX
# ---------------------------------------------------------
def clean_arabic_text(text):
    if not text:
        return ""
    text = re.sub(r'[^\w\s\d\.\,\:\;\-\_\(\)\n\u0600-\u06FF]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def extract_text_from_file(uploaded_file):
    text = ""
    try:
        if uploaded_file.name.endswith(".pdf"):
            with pdfplumber.open(uploaded_file) as pdf:
                for page in pdf.pages:
                    extracted = page.extract_text(layout=True)
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
        st.error(f"حدث خطأ أثناء قراءة الوثيقة: {e}")
    
    return clean_arabic_text(text)

# ---------------------------------------------------------
# 5. الهيدر
# ---------------------------------------------------------
st.markdown(
    """
    <div class="hero-header">
        <div class="hero-title">⚖️ الموسوعة القانونية المغربية الذكية</div>
        <div class="hero-subtitle">وكيل قانوني معزز بمحرك بحث دلالي (ChromaDB Vector RAG) وقارئ المستندات والعقود الرسمية (SGG)</div>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("⚙️ خيارات الجلسة")
    if st.button("🗑️ مسح المحادثة وإعادة البداية", use_container_width=True):
        st.session_state.messages = [{
            "role": "assistant",
            "content": "مرحباً بك! يمكنك طرح أي استفسار قانوني، أو رفع عقد/وثيقة لمطابقتها مع التشريع المغربي."
        }]
        st.rerun()

# ---------------------------------------------------------
# 6. محرك الذكاء الاصطناعي (Groq)
# ---------------------------------------------------------
api_key = st.secrets.get("GROQ_API_KEY") or os.getenv("GROQ_API_KEY")
if not api_key:
    st.error("⚠️ GROQ_API_KEY مفقود! يرجى إضافته إلى Secrets.")
    st.stop()

client = Groq(api_key=api_key)

if "messages" not in st.session_state:
    st.session_state.messages = [{
        "role": "assistant",
        "content": "مرحباً بك! يمكنك طرح أي استفسار قانوني، أو إرفاق عقد/وثيقة عبر زر (+) الموجود في خانة الإدخال بالأسفل لمطابقتها مع التشريع المغربي والجريدة الرسمية."
    }]

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ---------------------------------------------------------
# 7. زر الإرفاق الدائري (+) وخانة السؤال في نفس المكان
# ---------------------------------------------------------
uploaded_file = None
document_context = ""

# النافذة المنبثقة من زر (+) المدمج
with st.popover("➕"):
    st.markdown("### 📎 إرفاق عقد أو وثيقة (PDF / Word)")
    uploaded_file = st.file_uploader("اختر الملف:", type=["pdf", "docx"], key="direct_file_uploader")
    if uploaded_file is not None:
        document_context = extract_text_from_file(uploaded_file)
        if document_context:
            st.success(f"تمت قراءة الملف بنجاح ({len(document_context)} حرف)")

# خانة الدردشة الرئيسية
user_input = st.chat_input("اطرح سؤالك القانوني أو اكتب استفسارك حول الملف المرفق...")

# ---------------------------------------------------------
# 8. المعالجة
# ---------------------------------------------------------
if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    retrieved_docs = semantic_search(user_input, top_k=3)
    
    formatted_context = ""
    sources_ui = []
    for idx, doc in enumerate(retrieved_docs, 1):
        formatted_context += f"[{idx}] {doc['law']}: {doc['text']}\n"
        sources_ui.append(f"• **{doc['law']}**: {doc['text']}")

    doc_instruction = ""
    if document_context:
        doc_instruction = f"""
        CRITICAL INSTRUCTION: The user HAS uploaded a document. Below is the CLEAN EXTRACTED ARABIC TEXT from the file:
        
        === START OF UPLOADED DOCUMENT TEXT ===
        {document_context[:4000]}
        === END OF UPLOADED DOCUMENT TEXT ===
        
        Analyze this document text thoroughly in accordance with Moroccan laws.
        """

    system_prompt = f"""
    You are an expert Moroccan Legal AI Advisor using Vector Search (ChromaDB) and SGG Official Legislation.
    
    {doc_instruction}

    Retrieved Statutory Legal Framework (Official Laws from Database):
    {formatted_context}
    
    Instructions:
    1. Answer in fluent, academically sound Arabic.
    2. Read and analyze the uploaded text provided above accurately.
    3. Cite exact Decree, Dahir, or Article numbers clearly.
    4. End with a professional legal disclaimer.
    """

    messages_payload = [{"role": "system", "content": system_prompt}]
    for m in st.session_state.messages:
        messages_payload.append({"role": m["role"], "content": m["content"]})

    with st.chat_message("assistant"):
        if sources_ui:
            with st.expander("📚 المراجع والمواد القانونية المطابقة (Vector RAG):"):
                for src in sources_ui:
                    st.markdown(src)

        with st.spinner("جاري تحليل الطلب والبحث الدلالي..."):
            try:
                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=messages_payload,
                    temperature=0.1,
                )
                bot_reply = response.choices[0].message.content
                st.markdown(bot_reply)
                st.session_state.messages.append({"role": "assistant", "content": bot_reply})
                st.rerun()
            except Exception as e:
                st.error(f"حدث خطأ أثناء معالجة الاستشارة: {e}")
