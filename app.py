import os
import streamlit as st
from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate

# إعداد الصفحة وتصميم الهوية البصرية
st.set_page_config(
    page_title="المساعد القانوني المغربي الذكي",
    page_icon="⚖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# تخصيص التصميم عبر CSS
st.markdown("""
    <style>
        .main {
            background-color: #F8F9FA;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        [data-testid="stSidebar"] {
            background-color: #1A2B4C;
            color: #ffffff;
        }
        [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3, [data-testid="stSidebar"] p, [data-testid="stSidebar"] label {
            color: #FFFFFF !important;
        }
        .main-title {
            color: #1A2B4C;
            font-weight: 800;
            border-bottom: 3px solid #D4AF37;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }
        .stButton>button {
            background-color: #1A2B4C;
            color: white;
            border: 2px solid #D4AF37;
            border-radius: 6px;
            font-weight: bold;
            padding: 0.5rem 1rem;
            width: 100%;
            transition: all 0.3s ease;
        }
        .stButton>button:hover {
            background-color: #D4AF37;
            color: #1A2B4C;
            border-color: #1A2B4C;
        }
        .stTextArea textarea {
            border: 2px solid #1A2B4C;
            border-radius: 8px;
            background-color: #FFFFFF;
        }
    </style>
""", unsafe_allow_html=True)

# جلب المفتاح بأمان من خزينة Streamlit السحابية
try:
    GROQ_KEY = st.secrets["GROQ_API_KEY"]
except Exception:
    GROQ_KEY = ""

os.environ["GROQ_API_KEY"] = GROQ_KEY

# تحميل النماذج وقاعدة البيانات مع التخزين المؤقت
@st.cache_resource
def load_ai_system():
    embeddings = HuggingFaceEmbeddings(model_name="intfloat/multilingual-e5-base")
    vector_db = Chroma(persist_directory="./moroccan_law_db", embedding_function=embeddings)
    
    llm = ChatGroq(model_name="llama-3.1-8b-instant", temperature=0.1, groq_api_key=GROQ_KEY)
    
    template = """
    أنت مستشار قانوني مغربي خبير في القانون العام والمنازعات الإدارية والصفقات العمومية.
    قم بتحليل وقائع المستخدم بالاستناد حصراً على النصوص والمعطيات القانونية المستبردة في السياق أدناه.
    إذا كانت المعطيات لا تحتوي على الإجابة الدقيقة، اعتذر بلطف.

    السياق القانوني المسترد:
    {context}

    وقائع المستخدم:
    {question}

    قم بصياغة استشارة قانونية دقيقة ومنهجية مع تحديد السند أو المرجع إن وجد في السياق.
    الاستشارة:
    """
    prompt = PromptTemplate(template=template, input_variables=["context", "question"])
    chain = prompt | llm
    return vector_db, chain

with st.spinner("⚖️ جاري تهيئة المنظومة القانونية واستدعاء القواعد..."):
    vector_db, legal_chain = load_ai_system()

# --- الشريط الجانبي (Sidebar) ---
with st.sidebar:
    st.image("https://img.icons8.com/color/96/scales.png", width=70)
    st.markdown("## إطارات العمل القضائي")
    st.markdown("---")
    st.markdown("""
    **المجالات المغطاة:**
    * القانون العام والمنازعات الإدارية
    * مرسوم الصفقات العمومية 2023
    * التنظيم القضائي والمحاكم الإدارية
    * الدستور والحريات العامة
    """)
    st.markdown("---")
    st.markdown("<p style='text-align: center; font-size: 12px; color: #D4AF37;'>منصة بحث واستشارات قانونية ذكية &copy; 2026</p>", unsafe_allow_html=True)

# --- الواجهة الرئيسية ---
st.markdown("<h1 class='main-title'>⚖️ منصة الاستشارات والتحليل القانوني المغربي</h1>", unsafe_allow_html=True)
st.markdown("منصة ذكية موجهة للباحثين والممارسين لتحليل النوازل القانونية، استناداً إلى قاعدة بيانات محينة تحاكي اجتهادات ونصوص القانون الإداري والمالي بالمملكة.")

# نموذج إدخال الوقائع
user_scenario = st.text_area(
    "📋 **أدخل وقائع النازلة أو السؤال القانوني المراد تحليله:**",
    placeholder="اطرح سؤالك القانوني هنا...",
    height=140
)

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    generate_btn = st.button("🔍 إصدار الاستشارة القانونية", type="primary")

if generate_btn:
    if not user_scenario.strip():
        st.warning("⚠️ يرجى كتابة وقائع النازلة أو الاستشارة أولاً قبل الضغط على الزر.")
    else:
        with st.spinner("🔄 جاري البحث الدلالي في النصوص وتحليل النوازل القانونية..."):
            results = vector_db.similarity_search(user_scenario, k=3)
            
            context_texts = []
            for idx, doc in enumerate(results):
                source_name = doc.metadata.get('source', 'مصدر رقمي')
                context_texts.append(f"- النص {idx+1}: {doc.page_content} (المصدر: {source_name})")
            
            context_combined = "\n".join(context_texts)
            
            response = legal_chain.invoke({"context": context_combined, "question": user_scenario})
            
            st.success("✅ تمت صياغة الاستشارة القانونية بنجاح!")
            
            tab1, tab2 = st.tabs(["📋 وثيقة الاستشارة القانونية", "📚 النصوص والمراجع المستند إليها"])
            
            with tab1:
                st.markdown("### الاستشارة الرسمية")
                st.markdown("---")
                st.markdown(response.content)
                
            with tab2:
                st.markdown("### السندات المستخرجة من قاعدة البيانات")
                st.markdown("---")
                st.text(context_combined)
