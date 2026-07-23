import os
import streamlit as st
from groq import Groq

# ---------------------------------------------------------
# 1. إعدادات الصفحة الأساسية
# ---------------------------------------------------------
st.set_page_config(
    page_title="المستشار القانوني الذكي - مدونة الشغل المغربية",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------
# 2. تنسيق الواجهة وخط القاهرة وتجاوب الشاشات (CSS)
# ---------------------------------------------------------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Cairo', sans-serif !important;
        direction: rtl;
        text-align: right;
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 5rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }

    /* تحسينات الشاشات الصغيرة (الهواتف) */
    @media (max-width: 768px) {
        [data-testid="stSidebar"] {
            display: none !important;
        }
        [data-testid="collapsedControl"] {
            display: none !important;
        }
        .main .block-container {
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
            max-width: 100% !important;
        }
        h1 {
            font-size: 1.5rem !important;
            line-height: 1.3 !important;
            text-align: center !important;
        }
        p, div {
            font-size: 0.95rem !important;
        }
        .stChatMessage {
            padding: 10px !important;
            border-radius: 10px !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# 3. إعداد الـ API الخاص بـ Groq
# ---------------------------------------------------------
api_key = st.secrets.get("GROQ_API_KEY") or os.getenv("GROQ_API_KEY")

if not api_key:
    st.error("⚠️ لم يتم العثور على GROQ_API_KEY. يرجى إضافته في Streamlit Secrets.")
    st.stop()

client = Groq(api_key=api_key)

# ---------------------------------------------------------
# 4. قاعدة المعرفة القانونية (RAG Engine)
# ---------------------------------------------------------
LEGAL_KNOWLEDGE_BASE = {
    "عطلة": "المادة 231 وما يليها من القانون 65.99: يستحق الأجير عطلة سنوية مؤدى عنها بعد قضائه 6 أشهر من الخدمة الفعلية. مدتها يوم ونصف يوم من العمل الفعلي عن كل شهر (يومان للأجراء أقل من 18 سنة).",
    "أمومة": "المادة 152: تتمتع الأجيرة بمناسبة الحمل والولادة برخصة أمومة مدتها 14 أسبوعاً (15 أسبوعاً في بعض الحالات). المادة 269: يستفيد الأب الأجير من رخصة مدتها 3 أيام بمناسبة كل ولادة.",
    "فصل": "المواد 61-65: الفصل التعسفي يوجب التعويض (تعويض الفصل، مهلة الإشعار، وتعويض عن الضرر). الأخطاء الجسيمة المرتكبة من الأجير تسقط التعويض بشرط احترام مسطرة الاستماع (المادة 62).",
    "طرد": "المواد 61-65: الفصل التعسفي يوجب التعويض (تعويض الفصل، مهلة الإشعار، وتعويض عن الضرر). الأخطاء الجسيمة المرتكبة من الأجير تسقط التعويض بشرط احترام مسطرة الاستماع (المادة 62).",
    "تجربة": "المادة 13: فترة التجربة هي: 3 أشهر للأطر، شهر ونصف للمستخدمين، و15 يوماً للعمال. يمكن تجديدها مرة واحدة فقط.",
    "ساعات إضافية": "المادة 196 وما يليها: تُؤدى الزيادة عن الساعات الإضافية بنسبة 25% بين 6 صباحاً و9 ليلاً، و50% بين 9 ليلاً و6 صباحاً. وترتفع النسبة إلى 50% و100% إذا أنجزت في يوم العطلة الأسبوعية.",
    "حادثة شغل": "القانون 18.12 المتعلق بحوادث الشغل: يجب على المشغل التصريح بالحادثة لشركة التأمين والسلطات المحلية داخل أجل 48 ساعة من وقوعها.",
    "صحة وسلامة": "المادة 281 وما يليها: يتوجب على المشغل السهر على نظافة وسالمة الأجراء وتوفير وسائل الوقاية. وإحداث لجنة السلامة والصحة للمقاولات التي تشغل أكثر من 50 أجيراً (المادة 336).",
    "حد أدنى للأجر": "المادة 356 وما يليها: يضمن SMIG و SMAG حماية القدرة الشرائية للأجراء وتحدد قيمته بموجب مرسوم تنظيمي يتجدد دورياً.",
}

def retrieve_context(query: str) -> str:
    retrieved = []
    for key, text in LEGAL_KNOWLEDGE_BASE.items():
        if key in query:
            retrieved.append(text)
    if retrieved:
        return "\n".join(retrieved)
    return "لا توجد نصوص مباشرة محددة في الكلمات المفتاحية، استند إلى الأحكام العامة لمدونة الشغل المغربية (القانون 65.99)."

# ---------------------------------------------------------
# 5. الواجهة الرئيسية
# ---------------------------------------------------------
st.title("⚖️ المستشار القانوني الذكي")
st.subheader("مدونة الشغل المغربية (القانون 65.99)")

# قسم المعلومات المنسدل (بديل القائمة الجانبية للهواتف)
with st.expander("ℹ️ عن التطبيق والإعدادات"):
    st.write(
        """
    نظام خبير مدعوم بالذكاء الاصطناعي وتقنية RAG للإجابة عن الاستشارات التشريعية 
    الخاصة بمدونة الشغل المغربية مع استشهاد دقيق بالمواد والمقتضيات القانونية.
    """
    )

# ---------------------------------------------------------
# 6. إدارة سجل المحادثة (Chat History)
# ---------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "مرحباً بك! أنا مستشارك القانوني الخبير لمدونة الشغل المغربية. كيف يمكنني مساعدتك اليوم؟",
        }
    ]

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ---------------------------------------------------------
# 7. معالجة المدخلات والردود
# ---------------------------------------------------------
if user_input := st.chat_input("اطرح استفسارك القانوني هنا..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    context = retrieve_context(user_input)

    system_prompt = f"""
    أنت مستشار قانوني مغربي خبير متخصص حصرياً في مدونة الشغل المغربية (القانون رقم 65.99) والقوانين ذات الصلة.
    
    المرجع القانوني المباشر المتاح للطلب:
    {context}
    
    التزم بالتعليمات التالية:
    1. قدم إجابات دقيقة ومباشرة مستندة إلى مواد مدونة الشغل المغربية.
    2. صغ الإجابة بلغة عربية سليمة، مع تنظيمها في نقاط واضحة.
    3. إذا كانت المسألة تحتمل التقدير القضائي، وضح ذلك للمستخدم بأسلوب استرشادي.
    """

    messages_payload = [{"role": "system", "content": system_prompt}]
    for m in st.session_state.messages:
        messages_payload.append({"role": m["role"], "content": m["content"]})

    with st.chat_message("assistant"):
        with st.spinner("جاري التحليل والمطابقة القانونية..."):
            try:
                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=messages_payload,
                    temperature=0.2,
                )
                bot_reply = response.choices[0].message.content
                st.markdown(bot_reply)
                st.session_state.messages.append(
                    {"role": "assistant", "content": bot_reply}
                )
            except Exception as e:
                st.error(f"حدث خطأ أثناء التواصل مع المحرك القانوني: {e}")
