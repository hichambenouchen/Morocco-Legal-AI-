import json
import time
import random
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
# التصميم
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
# Google API Key
# ============================================================

try:
    gemini_key_val = st.secrets["GOOGLE_API_KEY"]
except Exception:
    gemini_key_val = ""


# ============================================================
# الموديلات المفضلة
#
# الترتيب مهم:
# إذا كان 3.8 مضغوطاً → يجرب 3.7
# إذا 3.7 غير متاح → يجرب 3.6
# ثم 3.5
# ============================================================

PREFERRED_MODELS = [
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
]


# ============================================================
# الحصول على الموديلات المتاحة
# ============================================================

def get_available_gemini_models(api_key):

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

        with urllib.request.urlopen(
            req,
            timeout=30
        ) as response:

            data = json.loads(
                response.read().decode("utf-8")
            )

        available = []

        for model in data.get("models", []):

            full_name = model.get("name", "")

            model_name = full_name.replace(
                "models/",
                ""
            )

            supported_methods = model.get(
                "supportedGenerationMethods",
                []
            )

            if (
                "generateContent" in supported_methods
                and "flash" in model_name.lower()
            ):

                available.append(model_name)

        return available

    except urllib.error.HTTPError as e:

        error_message = e.read().decode(
            "utf-8",
            errors="replace"
        )

        raise Exception(
            f"خطأ أثناء جلب قائمة موديلات Gemini: "
            f"{e.code} - {error_message}"
        )

    except Exception as e:

        raise Exception(
            f"تعذر الاتصال بخدمة Gemini: {str(e)}"
        )


# ============================================================
# ترتيب الموديلات
# ============================================================

def build_model_priority(api_key):

    available_models = get_available_gemini_models(
        api_key
    )

    ordered_models = []

    # ------------------------------------------
    # أولاً: الموديلات التي حددناها
    # ------------------------------------------

    for preferred in PREFERRED_MODELS:

        if preferred in available_models:

            if preferred not in ordered_models:

                ordered_models.append(preferred)

    # ------------------------------------------
    # ثانياً: أي Flash آخر متاح
    # ------------------------------------------

    for model in available_models:

        if model not in ordered_models:

            ordered_models.append(model)

    return ordered_models


# ============================================================
# إرسال الطلب إلى موديل واحد
# ============================================================

def generate_with_model(
    prompt_text,
    api_key,
    model_name,
    retries=3
):

    url = (
        "https://generativelanguage.googleapis.com/"
        f"v1beta/models/{model_name}:generateContent"
    )

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

    req = urllib.request.Request(

        url,

        data=data,

        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key
        },

        method="POST"
    )

    last_error = None

    # ========================================================
    # Retry للموديل نفسه
    # ========================================================

    for attempt in range(retries):

        try:

            with urllib.request.urlopen(
                req,
                timeout=120
            ) as response:

                response_data = json.loads(
                    response.read().decode("utf-8")
                )

            candidates = response_data.get(
                "candidates",
                []
            )

            if not candidates:

                return {
                    "success": False,
                    "retryable": False,
                    "error": "لم يرجع Gemini أي نتيجة.",
                    "model": model_name
                }

            content = candidates[0].get(
                "content",
                {}
            )

            parts = content.get(
                "parts",
                []
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

            if not final_text:

                return {
                    "success": False,
                    "retryable": False,
                    "error": "Gemini رجع استجابة فارغة.",
                    "model": model_name
                }

            return {
                "success": True,
                "text": final_text,
                "model": model_name
            }

        except urllib.error.HTTPError as e:

            error_message = e.read().decode(
                "utf-8",
                errors="replace"
            )

            last_error = error_message

            # =================================================
            # 503 / 429 / 500 / 502 / 504
            # أخطاء مؤقتة → Retry
            # =================================================

            if e.code in [
                429,
                500,
                502,
                503,
                504
            ]:

                if attempt < retries - 1:

                    # Exponential Backoff
                    wait_time = (
                        2 ** attempt
                    ) + random.uniform(
                        0,
                        1
                    )

                    time.sleep(
                        wait_time
                    )

                    continue

                return {
                    "success": False,
                    "retryable": True,
                    "error": (
                        f"HTTP {e.code}: "
                        f"{error_message}"
                    ),
                    "model": model_name
                }

            # =================================================
            # 400 / 401 / 403 / 404
            # أخطاء غير مؤقتة
            # =================================================

            return {
                "success": False,
                "retryable": False,
                "error": (
                    f"HTTP {e.code}: "
                    f"{error_message}"
                ),
                "model": model_name
            }

        except Exception as e:

            last_error = str(e)

            if attempt < retries - 1:

                wait_time = (
                    2 ** attempt
                ) + random.uniform(
                    0,
                    1
                )

                time.sleep(
                    wait_time
                )

                continue

            return {
                "success": False,
                "retryable": True,
                "error": str(e),
                "model": model_name
            }

    return {
        "success": False,
        "retryable": True,
        "error": last_error,
        "model": model_name
    }


# ============================================================
# النظام الرئيسي لـ Gemini
# ============================================================

def call_gemini_api(
    prompt_text,
    api_key
):

    # ========================================================
    # الحصول على الموديلات
    # ========================================================

    try:

        models = build_model_priority(
            api_key
        )

    except Exception as e:

        return {
            "success": False,
            "text": "",
            "model": "",
            "error": str(e)
        }

    if not models:

        return {
            "success": False,
            "text": "",
            "model": "",
            "error": (
                "لم يتم العثور على أي موديل "
                "Flash يدعم generateContent."
            )
        }

    # ========================================================
    # تجربة الموديلات بالتتابع
    # ========================================================

    errors = []

    for model_name in models:

        result = generate_with_model(
            prompt_text,
            api_key,
            model_name,
            retries=3
        )

        # ----------------------------------------------------
        # نجاح
        # ----------------------------------------------------

        if result.get("success"):

            return result

        # ----------------------------------------------------
        # تسجيل الخطأ
        # ----------------------------------------------------

        errors.append(
            f"{model_name}: {result.get('error', '')}"
        )

        # ----------------------------------------------------
        # إذا كان الخطأ غير قابل لإعادة المحاولة
        # نوقف العملية
        # ----------------------------------------------------

        if not result.get(
            "retryable",
            False
        ):

            return {
                "success": False,
                "text": "",
                "model": model_name,
                "error": result.get(
                    "error",
                    "خطأ غير معروف"
                )
            }

    # ========================================================
    # جميع الموديلات فشلت
    # ========================================================

    return {
        "success": False,
        "text": "",
        "model": "",
        "error": (
            "تعذر الحصول على استجابة من جميع "
            "موديلات Gemini المتاحة.\n\n"
            + "\n".join(errors)
        )
    }


# ============================================================
# تحميل قاعدة البيانات
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
# تشغيل قاعدة المعرفة
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
# إدخال السؤال
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
            # البحث الدلالي
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
            # تجهيز النصوص القانونية
            # =================================================

            context_texts = []

            for idx, doc in enumerate(results):

                source_name = doc.metadata.get(
                    "source",
                    "مصدر رقمي"
                )

                context_texts.append(
                    f"""
النص رقم {idx + 1}:

{doc.page_content}

المصدر:
{source_name}
"""
                )

            context_combined = "\n".join(
                context_texts
            )

            # =================================================
            # Prompt القانوني
            # =================================================

            prompt_full = f"""
أنت مستشار قانوني مغربي متخصص في القانون العام
والقانون الإداري والمنازعات الإدارية والصفقات العمومية
والتنظيم القضائي والقانون الدستوري والحريات العامة.

مهمتك تحليل النازلة القانونية المقدمة من المستخدم.

قواعد إلزامية:

1. اعتمد على السياق القانوني المسترجع من قاعدة البيانات.

2. لا تخترع أي مادة قانونية أو مرجع أو حكم قضائي.

3. لا تنسب إلى قانون أو مرسوم أو قرار قضائي معلومة
   غير موجودة في السياق المسترجع.

4. إذا كان السياق غير كاف للإجابة، صرّح بذلك بوضوح.

5. إذا كان هناك شك في الجواب، لا تقدم التخمين
   على أنه حقيقة قانونية.

6. ميّز بوضوح بين الوقائع والتحليل القانوني.

7. استعمل اللغة العربية القانونية الواضحة.

8. عند وجود مصدر أو مرجع في السياق، اذكره.

9. لا تقدم الاستشارة على أنها حكم قضائي أو رأي
   ملزم صادر عن جهة رسمية.

10. ركز على القانون المغربي.

--------------------------------------------

السياق القانوني المسترجع:

{context_combined}

--------------------------------------------

وقائع المستخدم:

{user_scenario}

--------------------------------------------

صغ الاستشارة وفق الهيكلة التالية:

### أولاً: عرض الوقائع

لخص الوقائع القانونية المهمة.

### ثانياً: الإشكال القانوني

حدد المسألة أو المسائل القانونية المطروحة.

### ثالثاً: النصوص والقواعد القانونية

اذكر فقط النصوص أو القواعد التي يدعمها السياق المسترجع.

### رابعاً: التحليل القانوني

حلل الوقائع على ضوء النصوص والمعطيات المسترجعة.

### خامساً: النتيجة

قدم خلاصة واضحة ومباشرة.

### سادساً: المراجع

اذكر المصادر المتاحة في السياق.

الاستشارة القانونية:
"""

            # =================================================
            # الاتصال بـ Gemini
            # =================================================

            gemini_result = call_gemini_api(
                prompt_full,
                gemini_key_val
            )

            # =================================================
            # في حالة الخطأ
            # =================================================

            if not gemini_result.get(
                "success",
                False
            ):

                st.error(
                    "❌ حدث خطأ أثناء إصدار الاستشارة."
                )

                st.code(
                    gemini_result.get(
                        "error",
                        "خطأ غير معروف"
                    )
                )

            else:

                response_text = gemini_result["text"]
                used_model = gemini_result["model"]

                # =================================================
                # نجاح
                # =================================================

                st.success(
                    "✅ تمت صياغة الاستشارة القانونية بنجاح!"
                )

                # ------------------------------------------------
                # إظهار الموديل بشكل صغير
                # ------------------------------------------------

                st.caption(
                    f"🤖 الموديل المستعمل: {used_model}"
                )

                # =================================================
                # Tabs
                # =================================================

                tab1, tab2 = st.tabs(
                    [
                        "📋 وثيقة الاستشارة القانونية",
                        "📚 النصوص والمراجع المستند إليها"
                    ]
                )

                # =================================================
                # الاستشارة
                # =================================================

                with tab1:

                    st.markdown(
                        "### الاستشارة الرسمية"
                    )

                    st.markdown("---")

                    st.markdown(
                        response_text
                    )

                # =================================================
                # المصادر
                # =================================================

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
