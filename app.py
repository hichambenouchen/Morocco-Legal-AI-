import os
import json
import time
import urllib.request
import urllib.error
import streamlit as st

from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings


# ============================================================
# إعداد الصفحة
# ============================================================

st.set_page_config(
    page_title="المساعد القانوني المغربي الذكي",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# التصميم CSS
# ============================================================

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

        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3,
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] label {
            color: #FFFFFF !important;
        }

        .main-title {
            color: #1A2B4C;
            font-weight: 800;
            border-bottom: 3px solid #D4AF37;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }

        .stButton > button {
            background-color: #1A2B4C;
            color: white;
            border: 2px solid #D4AF37;
            border-radius: 6px;
            font-weight: bold;
            padding: 0.5rem 1rem;
            width: 100%;
            transition: all 0.3s ease;
        }

        .stButton > button:hover {
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


# ============================================================
# جلب مفتاح Google API
# ============================================================

try:
    gemini_key_val = st.secrets["GOOGLE_API_KEY"]
except Exception:
    gemini_key_val = ""


# ============================================================
# اكتشاف موديل Gemini المتاح
# ============================================================

def get_available_gemini_model(api_key):

    url = (
        "https://generativelanguage.googleapis.com/"
        "v1beta/models"
    )

    req = urllib.request.Request(
        url,
        headers={
            "x-goog-api-key": api_key
        },
        method="GET"
    )

    try:

        with urllib.request.urlopen(req, timeout=30) as response:

            response_data = json.loads(
                response.read().decode("utf-8")
            )

        models = response_data.get("models", [])

        # الموديلات المفضلة بالترتيب
        preferred_models = [
            "gemini-3.8-flash",
            "gemini-2.5-flash",
            "gemini-2.5-flash-lite",
            "gemini-3.5-flash-lite"
        ]

        # ----------------------------------------------------
        # البحث عن موديل مفضل يدعم generateContent
        # ----------------------------------------------------

        for preferred in preferred_models:

            for model in models:

                model_name = model.get("name", "")

                supported_methods = model.get(
                    "supportedGenerationMethods",
                    []
                )

                clean_name = model_name.replace(
                    "models/",
                    ""
                )

                if (
                    clean_name == preferred
                    and
                    "generateContent" in supported_methods
                ):
                    return clean_name

        # ----------------------------------------------------
        # إذا لم نجد الموديلات السابقة،
        # نبحث عن أي Flash يدعم generateContent
        # ----------------------------------------------------

        for model in models:

            model_name = model.get("name", "")

            supported_methods = model.get(
                "supportedGenerationMethods",
                []
            )

            clean_name = model_name.replace(
                "models/",
                ""
            )

            if (
                "generateContent" in supported_methods
                and "flash" in clean_name.lower()
            ):
                return clean_name

        return None

    except urllib.error.HTTPError as e:

        error_message = e.read().decode("utf-8")

        raise Exception(
            f"فشل الحصول على قائمة موديلات Gemini: "
            f"{e.code} - {error_message}"
        )

    except Exception as e:

        raise Exception(
            f"تعذر اكتشاف موديل Gemini المتاح: {str(e)}"
        )


# ============================================================
# الاتصال بـ Gemini مع إعادة المحاولة
# ============================================================

def call_gemini_api_with_retry(
    prompt_text,
    api_key,
    retries=3,
    delay=2
):

    # --------------------------------------------------------
    # اكتشاف الموديل المتاح
    # --------------------------------------------------------

    try:

        model_name = get_available_gemini_model(
            api_key
        )

    except Exception as ex:

        return (
            "❌ تعذر تحديد موديل Gemini المتاح.\n\n"
            f"التفاصيل: {str(ex)}"
        )

    if not model_name:

        return (
            "❌ لم يتم العثور على أي موديل Gemini "
            "يدعم generateContent مع مفتاح API الحالي."
        )

    # --------------------------------------------------------
    # عنوان API
    # --------------------------------------------------------

    url = (
        "https://generativelanguage.googleapis.com/"
        f"v1beta/models/{model_name}:generateContent"
    )

    # --------------------------------------------------------
    # البيانات المرسلة إلى Gemini
    # --------------------------------------------------------

    payload = {

        "contents": [

            {
                "parts": [
                    {
                        "text": prompt_text
                    }
                ]
            }

        ],

        "generationConfig": {

            "temperature": 0.2,

            "topP": 0.9,

            "maxOutputTokens": 4096

        }

    }

    data = json.dumps(
        payload,
        ensure_ascii=False
    ).encode("utf-8")

    # --------------------------------------------------------
    # إعداد الطلب
    # --------------------------------------------------------

    req = urllib.request.Request(

        url,

        data=data,

        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key
        },

        method="POST"
    )

    # --------------------------------------------------------
    # المحاولة
    # --------------------------------------------------------

    for attempt in range(retries):

        try:

            with urllib.request.urlopen(
                req,
                timeout=120
            ) as response:

                res_data = json.loads(
                    response.read().decode("utf-8")
                )

            # ------------------------------------------------
            # استخراج النص
            # ------------------------------------------------

            candidates = res_data.get(
                "candidates",
                []
            )

            if not candidates:

                return (
                    "❌ Gemini لم يرجع أي إجابة.\n\n"
                    f"الموديل المستعمل: {model_name}\n"
                    f"الاستجابة: {json.dumps(res_data, ensure_ascii=False)}"
                )

            content = candidates[0].get(
                "content",
                {}
            )

            parts = content.get(
                "parts",
                []
            )

            if not parts:

                return (
                    "❌ Gemini رجع استجابة بدون نص."
                )

            text_parts = []

            for part in parts:

                if "text" in part:

                    text_parts.append(
                        part["text"]
                    )

            final_text = "\n".join(
                text_parts
            ).strip()

            if final_text:

                return final_text

            return (
                "❌ تعذر استخراج النص من استجابة Gemini."
            )

        # ----------------------------------------------------
        # أخطاء HTTP
        # ----------------------------------------------------

        except urllib.error.HTTPError as e:

            error_message = e.read().decode(
                "utf-8",
                errors="replace"
            )

            # 429 = تجاوز الحصة / Rate Limit
            # 500/502/503/504 = مشاكل مؤقتة بالخادم

            if e.code in [429, 500, 502, 503, 504]:

                if attempt < retries - 1:

                    time.sleep(
                        delay * (attempt + 1)
                    )

                    continue

            return (
                f"❌ خطأ Gemini API: {e.code}\n\n"
                f"الموديل: {model_name}\n\n"
                f"التفاصيل:\n{error_message}"
            )

        # ----------------------------------------------------
        # أخطاء أخرى
        # ----------------------------------------------------

        except Exception as ex:

            if attempt < retries - 1:

                time.sleep(
                    delay * (attempt + 1)
                )

                continue

            return (
                "❌ حدث خطأ غير متوقع أثناء الاتصال "
                "بـ Gemini.\n\n"
                f"الموديل: {model_name}\n"
                f"التفاصيل: {str(ex)}"
            )

    return (
        "❌ فشلت جميع محاولات الاتصال بـ Gemini."
    )


# ============================================================
# تحميل قاعدة البيانات والنماذج
# ============================================================

@st.cache_resource
def load_ai_system():

    embeddings = HuggingFaceEmbeddings(
        model_name="intfloat/multilingual-e5-base"
    )

    vector_db = Chroma(
        persist_directory="./moroccan_law_db",
        embedding_function=embeddings
    )

    return vector_db


# ============================================================
# تشغيل المنظومة
# ============================================================

with st.spinner(
    "⚖️ جاري تهيئة المنظومة القانونية واستدعاء القاعدة المعرفية..."
):

    vector_db = load_ai_system()


# ============================================================
# Sidebar
# ============================================================

with st.sidebar:

    st.image(
        "https://img.icons8.com/color/96/scales.png",
        width=70
    )

    st.markdown(
        "## إطارات العمل القضائي"
    )

    st.markdown("---")

    st.markdown("""
    **المجالات المغطاة:**

    * القانون العام والمنازعات الإدارية
    * مرسوم الصفقات العمومية 2023
    * التنظيم القضائي والمحاكم الإدارية
    * الدستور والحريات العامة
    """)

    st.markdown("---")

    st.markdown(
        """
        <p style='text-align: center;
        font-size: 12px;
        color: #D4AF37;'>
        منصة بحث واستشارات قانونية ذكية
        &copy; 2026
        </p>
        """,
        unsafe_allow_html=True
    )


# ============================================================
# الواجهة الرئيسية
# ============================================================

st.markdown(
    """
    <h1 class='main-title'>
    ⚖️ منصة الاستشارات والتحليل القانوني المغربي
    </h1>
    """,
    unsafe_allow_html=True
)

st.markdown(
    """
    منصة ذكية موجهة للباحثين والممارسين لتحليل النوازل
    القانونية، استناداً إلى قاعدة بيانات محينة تحاكي
    اجتهادات ونصوص القانون الإداري والمالي بالمملكة.
    """
)


# ============================================================
# إدخال النازلة
# ============================================================

user_scenario = st.text_area(

    "📋 **أدخل وقائع النازلة أو السؤال القانوني المراد تحليله:**",

    placeholder="اطرح سؤالك القانوني هنا...",

    height=140
)


# ============================================================
# زر الاستشارة
# ============================================================

col1, col2, col3 = st.columns(
    [1, 2, 1]
)

with col2:

    generate_btn = st.button(
        "🔍 إصدار الاستشارة القانونية",
        type="primary"
    )


# ============================================================
# معالجة الاستشارة
# ============================================================

if generate_btn:

    # --------------------------------------------------------
    # التحقق من السؤال
    # --------------------------------------------------------

    if not user_scenario.strip():

        st.warning(
            "⚠️ يرجى كتابة وقائع النازلة "
            "أو الاستشارة أولاً قبل الضغط على الزر."
        )

    # --------------------------------------------------------
    # التحقق من API Key
    # --------------------------------------------------------

    elif not gemini_key_val:

        st.error(
            "⚠️ مفتاح API غير موجود في إعدادات المنصة (Secrets)."
        )

    else:

        with st.spinner(
            "🔄 جاري البحث الدلالي وتحليل النازلة عبر النماذج الذكية..."
        ):

            # =================================================
            # البحث داخل قاعدة البيانات
            # =================================================

            try:

                results = vector_db.similarity_search(
                    user_scenario,
                    k=3
                )

            except Exception as ex:

                st.error(
                    "❌ حدث خطأ أثناء البحث في قاعدة البيانات."
                )

                st.code(
                    str(ex)
                )

                st.stop()

            # =================================================
            # تجهيز السياق القانوني
            # =================================================

            context_texts = []

            for idx, doc in enumerate(results):

                source_name = doc.metadata.get(
                    "source",
                    "مصدر رقمي"
                )

                context_texts.append(
                    f"""
- النص {idx + 1}:
{doc.page_content}

المصدر:
{source_name}
"""
                )

            context_combined = "\n".join(
                context_texts
            )

            # =================================================
            # Prompt قانوني
            # =================================================

            prompt_full = f"""
أنت مستشار قانوني مغربي متخصص في:

- القانون العام
- القانون الإداري
- المنازعات الإدارية
- الصفقات العمومية
- التنظيم القضائي
- الحريات العامة
- القانون الدستوري

مهمتك هي تحليل النازلة القانونية المقدمة من المستخدم.

قواعد مهمة جداً:

1. اعتمد أساساً على النصوص والمعطيات الموجودة في
   "السياق القانوني المسترد".

2. لا تخترع أي مادة قانونية أو حكم قضائي أو مرجع
   غير موجود في السياق.

3. إذا كان السياق غير كافٍ للإجابة الدقيقة،
   صرّح بوضوح أن المعطيات المتاحة غير كافية.

4. لا تقدم معلومة قانونية على أنها مؤكدة إذا لم
   تكن مدعومة بالمصادر المسترجعة.

5. ميّز بين:
   - الوقائع
   - المسألة القانونية
   - القاعدة القانونية
   - التحليل
   - النتيجة

6. عندما يكون المرجع أو المصدر موجوداً في السياق،
   اذكره بوضوح.

7. اجعل الجواب باللغة العربية القانونية الواضحة
   والمناسبة للسياق المغربي.

8. لا تستعمل عبارات عامة فقط، بل اربط التحليل
   بالوقائع والنصوص المسترجعة.

--------------------------------------------------

السياق القانوني المسترد من قاعدة البيانات:

{context_combined}

--------------------------------------------------

وقائع المستخدم:

{user_scenario}

--------------------------------------------------

قم الآن بصياغة الاستشارة القانونية وفق الهيكلة التالية:

### أولاً: عرض الوقائع
لخص الوقائع القانونية باختصار.

### ثانياً: الإشكال القانوني
حدد السؤال أو الإشكال القانوني الرئيسي.

### ثالثاً: القواعد والنصوص القانونية
اذكر النصوص أو المراجع الموجودة فعلاً في السياق.

### رابعاً: التحليل القانوني
حلل الوقائع على ضوء النصوص المسترجعة.

### خامساً: الخلاصة
قدم نتيجة قانونية واضحة ومختصرة.

### سادساً: المراجع
اذكر المصادر التي استندت إليها إذا كانت متوفرة.

الاستشارة القانونية:
"""

            # =================================================
            # استدعاء Gemini
            # =================================================

            response_text = call_gemini_api_with_retry(
                prompt_full,
                gemini_key_val
            )

            # =================================================
            # النتيجة
            # =================================================

            if response_text.startswith("❌"):

                st.error(
                    "حدث خطأ أثناء إصدار الاستشارة."
                )

                st.code(
                    response_text
                )

            else:

                st.success(
                    "✅ تمت صياغة الاستشارة القانونية بنجاح!"
                )

                # عرض التبويبات

                tab1, tab2 = st.tabs(
                    [
                        "📋 وثيقة الاستشارة القانونية",
                        "📚 النصوص والمراجع المستند إليها"
                    ]
                )

                # ------------------------------------------------
                # الاستشارة
                # ------------------------------------------------

                with tab1:

                    st.markdown(
                        "### الاستشارة الرسمية"
                    )

                    st.markdown("---")

                    st.markdown(
                        response_text
                    )

                # ------------------------------------------------
                # المصادر
                # ------------------------------------------------

                with tab2:

                    st.markdown(
                        "### السندات المستخرجة من قاعدة البيانات"
                    )

                    st.markdown("---")

                    if context_combined.strip():

                        st.text(
                            context_combined
                        )

                    else:

                        st.info(
                            "لم يتم العثور على نصوص قانونية "
                            "مطابقة في قاعدة البيانات."
                        )
