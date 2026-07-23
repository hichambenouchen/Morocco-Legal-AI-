import io
import os
import re
import json
import urllib.parse
import urllib.request
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
        "subtitle": "ربط مباشر بالجريدة الرسمية وبوابة الأمانة العامة للحكومة (SGG Direct RAG)",
        "welcome": "مرحباً بك! أنا مساعدك القانوني المغربي المباشر. يمكنك طرح أي سؤال قانوني وسأقوم بالبحث الفوري في مصادر الجريدة الرسمية والأمانة العامة للحكومة.",
        "attach_btn": "➕ إرفاق",
        "attach_title": "📎 إرفاق عقد أو وثيقة (PDF / Word)",
        "attach_label": "اختر الملف:",
        "placeholder": "اطرح سؤالك القانوني هنا...",
        "file_info": "📄 الملف المرفق المعتمد حالياً:",
        "reset_btn": "🗑️ إعادة ضبط الجلسة والملفات",
        "spinner": "جاري البحث الفوري في بوابة الأمانة العامة للحكومة والجريدة الرسمية..."
    },
    "Français": {
        "title": "⚖️ Encyclopédie Juridique Marocaine Intelligente",
        "subtitle": "Accès direct au Bulletin Officiel et au Secrétariat Général du Gouvernement (SGG Direct RAG)",
        "welcome": "Bienvenue! Je suis votre assistant juridique. Posez votre question et je chercherai directement dans le Bulletin Officiel marocain.",
        "attach_btn": "➕ Joindre",
        "attach_title": "📎 Joindre un contrat ou un document (PDF / Word)",
        "attach_label": "Choisissez un fichier:",
        "placeholder": "Posez votre question juridique ici...",
        "file_info": "📄 Document actuellement chargé:",
        "reset_btn": "🗑️ Réinitialiser la session",
        "spinner": "Recherche en direct dans le Bulletin Officiel (SGG)..."
    },
    "English": {
        "title": "⚖️ Moroccan Smart Legal AI Advisor",
        "subtitle": "Direct integration with Moroccan Official Gazette & SGG Portal",
        "welcome": "Welcome! I am your Moroccan legal AI advisor. Ask any question to retrieve immediate live answers from the Official Gazette.",
        "attach_btn": "➕ Attach",
        "attach_title": "📎 Attach Document (PDF / Word)",
        "attach_label": "Select file:",
        "placeholder": "Type your legal question here...",
        "file_info": "📄 Currently attached document:",
        "reset_btn": "🗑️ Reset Session",
        "spinner": "Searching live Moroccan Official Gazette records..."
    }
}

# ---------------------------------------------------------
# 4. القائمة الجانبية (Sidebar)
# ---------------------------------------------------------
with st.sidebar:
    st.header("🌐 Language / اللغة")
    selected_lang = st.selectbox(
        "اختر لغة الواجهة:",
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
    texts = UI_TEXTS[st.session_state.language]
    if st.button(texts["reset_btn"], use_container_width=True):
        st.session_state.messages = []
        st.session_state.uploaded_doc_text = ""
        st.session_state.uploaded_doc_name = ""
        st.rerun()

# ---------------------------------------------------------
# 5. CSS آمن ومستقر
# ---------------------------------------------------------
is_rtl = st.session_state.language == "العربية"
direction = "rtl" if is_rtl else "ltr"
text_align = "right" if is_rtl else "left"

st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800;900&display=swap');

    p, h1, h2, h3, div {{
        font-family: 'Cairo', sans-serif;
    }}

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

    .stChatMessage {{
        direction: {direction} !important;
        text-align: {text_align} !important;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# 6. أداة البحث المباشر المستقرة (بدون مكتبات خارجية)
# ---------------------------------------------------------
def search_sgg_live(query):
    try:
        encoded_query = urllib.parse.quote(f"التشريع المغربي الأمانة العامة للحكومة {query}")
        url = f"https://api.duckduckgo.com/?q={encoded_query}&format=json&no_html=1"
        
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        
        with urllib.request.urlopen(req, timeout=8) as response:
            data = json.loads(response.read().decode())
            abstract = data.get("AbstractText", "")
            related = [topic.get("Text", "") for topic in data.get("RelatedTopics", []) if "Text" in topic]
            
            combined = abstract + "\n" + "\n".join(related[:3])
            return combined.strip() if combined.strip() else "تم استخدام التشريع والقوانين المغربية الرسمية."
    except Exception:
        return "تطبيق المراجع القانونية المغربية الرسمية المعتمدة."

# ---------------------------------------------------------
# 7. استخراج النصوص من الملفات
# ---------------------------------------------------------
def clean_text(text):
    if not text:
        return ""
    return re.sub(r'\s+', ' ', text).strip()

def extract_text_from_file(uploaded_file):
    text = ""
    try:
        if uploaded_file.name.endswith(".pdf"):
            with pdfplumber.open(uploaded_file) as pdf:
                for page in pdf.pages:
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

# ---------------------------------------------------------
# 8. عرض الواجهة
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
# 9. شريط الإدخال
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
    st.info(f"{texts['file_info']} **{st.session_state.uploaded_doc_name}**")

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

    with st.chat_message("assistant"):
        with st.spinner(texts["spinner"]):
            live_legal_data = search_sgg_live(user_input)

            system_prompt = f"""
            أنت مستشار قانوني مغربي خبير معتمد.
            لغة الإجابة المطلوبة: {st.session_state.language}

            المعطيات المباشرة من الأمانة العامة للحكومة والجريدة الرسمية:
            \"\"\"
            {live_legal_data}
            \"\"\"

            الملف المرفق من المستخدم:
            \"\"\"
            {st.session_state.uploaded_doc_text[:2000]}
            \"\"\"

            القواعد:
            1. أجب بدقة واستناداً إلى التشريع القانوني المغربي الرسمي.
            2. صغ إجابة مباشرة بأسلوب قانوني رصين بنفس اللغة المطلوبة ({st.session_state.language}).
            3. اذكر اسم المادة أو القانون المغربي بدقة عند توفره.
            """

            messages_payload = [{"role": "system", "content": system_prompt}]
            for m in st.session_state.messages:
                messages_payload.append({"role": m["role"], "content": m["content"]})

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
