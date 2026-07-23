import io
import os
import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from fpdf import FPDF
from groq import Groq
import streamlit as st

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
        padding-top: 1rem !important;
        padding-bottom: 5rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }

    /* تحسين زر الأسئلة السريعة */
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        font-family: 'Cairo', sans-serif !important;
    }

    /* تحسينات الشاشات الصغيرة (الهواتف) */
    @media (max-width: 768px) {
        [data-testid="stSidebar"] { display: none !important; }
        [data-testid="collapsedControl"] { display: none !important; }
        .main .block-container {
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
            max-width: 100% !important;
        }
        h1 {
            font-size: 1.4rem !important;
            line-height: 1.3 !important;
            text-align: center !important;
        }
        p, div { font-size: 0.95rem !important; }
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
# 3. دالتا إنشــاء ملفات DOCX و PDF (باستخدام FPDF خفيف ومستقر)
# ---------------------------------------------------------
def generate_docx(messages):
  doc = docx.Document()

  def set_rtl(p):
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p_pr = p._p.get_or_add_pPr()
    bidi = OxmlElement('w:bidi')
    bidi.set(qn('w:val'), '1')
    p_pr.append(bidi)

  title = doc.add_paragraph('تقرير استشارة قانونية - مدونة الشغل المغربية')
  set_rtl(title)
  title.runs[0].font.bold = True
  title.runs[0].font.size = docx.shared.Pt(16)

  doc.add_paragraph('')

  for msg in messages:
    role_name = 'المستخدم' if msg['role'] == 'user' else 'المستشار القانوني'
    p = doc.add_paragraph()
    set_rtl(p)

    run_role = p.add_run(f'[{role_name}]:\n')
    run_role.bold = True
    run_role.font.color.rgb = (
        docx.shared.RGBColor(180, 50, 50)
        if msg['role'] == 'user'
        else docx.shared.RGBColor(20, 80, 160)
    )

    p_content = doc.add_paragraph(msg['content'])
    set_rtl(p_content)
    doc.add_paragraph('-' * 40)

  buffer = io.BytesIO()
  doc.save(buffer)
  buffer.seek(0)
  return buffer.getvalue()


def generate_pdf_text(messages):
  # إنشاء ملف نصي مُصمم كبديل آمن وسريع للمستندات
  pdf_str = "==================================================\n"
  pdf_str += "⚖️ تقرير استشارة قانونية - مدونة الشغل المغربية\n"
  pdf_str += "==================================================\n\n"

  for msg in messages:
    role = "السؤال:" if msg["role"] == "user" else "الإجابة القانونية:"
    pdf_str += f"{role}\n{msg['content']}\n"
    pdf_str += "\n--------------------------------------------------\n\n"

  pdf_str += (
      "\nملاحظة: هذه الاستشارة ذات طابع أكاديمي واسترشادي ولا تغني عن"
      " الاستشارة القضائية."
  )
  return pdf_str.encode("utf-8")


# ---------------------------------------------------------
# 4. إعداد الـ API الخاص بـ Groq
# ---------------------------------------------------------
api_key = st.secrets.get("GROQ_API_KEY") or os.getenv("GROQ_API_KEY")

if not api_key:
  st.error("⚠️ لم يتم العثور على GROQ_API_KEY. يرجى إضافته في Streamlit Secrets.")
  st.stop()

client = Groq(api_key=api_key)

# ---------------------------------------------------------
# 5. قاعدة المعرفة القانونية المباشرة (مُوسّعة)
# ---------------------------------------------------------
LEGAL_KNOWLEDGE_BASE = {
    "عطلة": (
        "المادة 231 وما يليها من القانون 65.99: يستحق الأجير عطلة سنوية مؤدى"
        " عنها بعد قضائه 6 أشهر من الخدمة الفعلية. مدتها يوم ونصف يوم من العمل"
        " الفعلي عن كل شهر (يومان للأجراء أقل من 18 سنة)."
    ),
    "أمومة": (
        "المادة 152: تتمتع الأجيرة بمناسبة الحمل والولادة برخصة أمومة مدتها 14"
        " أسبوعاً. المادة 269: يستفيد الأب الأجير من رخصة مدتها 3 أيام بمناسبة"
        " كل ولادة."
    ),
    "فصل": (
        "المواد 61-65: الفصل التعسفي يوجب التعويض (تعويض الفصل، مهلة الإشعار،"
        " وتعويض عن الضرر). الأخطاء الجسيمة المرتكبة من الأجير تسقط التعويض"
        " بشرط احترام مسطرة الاستماع (المادة 62)."
    ),
    "طرد": (
        "المواد 61-65: الطرد التعسفي يوجب التعويضات القانونية المستحقة كاملة ما"
        " لم يثبت ارتكاب خطأ جسيم ومراعاة مسطرة المادة 62."
    ),
    "تجربة": (
        "المادة 13: فترة التجربة هي: 3 أشهر للأطر، شهر ونصف للمستخدمين، و15"
        " يوماً للعمال. يمكن تجديدها مرة واحدة فقط."
    ),
    "ساعات إضافية": (
        "المادة 196 وما يليها: تُؤدى الزيادة عن الساعات الإضافية بنسبة 25% بين 6"
        " صباحاً و9 ليلاً، و50% بين 9 ليلاً و6 صباحاً. وترتفع إلى 50% و100% في"
        " أيام العطل."
    ),
    "إشعار": (
        "المادة 43 وما يليها: يجب احترام أجل الإشعار (Notice) قبل إنهاء العقد"
        " غير محدد المدة، وتختلف المدة بحسب الأقدمية وفئة الأجير (من أسبوع إلى"
        " 3 أشهر)."
    ),
    "عقد": (
        "المادة 16: عقد الشغل يكون غير محدد المدة (CDD) أو محدد المدة (CDD) في"
        " حالات استثنائية محددة قانوناً (كإنجاز مشروع أو استبدال أجير)."
    ),
    "أعياد": (
        "المادة 217: يمنع شغل الأجراء في أيام الأعياد المؤدى عنها والأيام المحددة"
        " بنص تنظيمي إلا في بعض القطاعات الخاصة مع التعويض عنها."
    ),
    "حادثة شغل": (
        "القانون 18.12 المتعلق بحوادث الشغل: التصريح بالحادثة إجباري داخل أجل"
        " 48 ساعة لشركة التأمين والسلطات."
    ),
    "صحة وسلامة": (
        "المادة 281 وما يليها: يتوجب على المشغل السهر على نظافة وسلامة الأجراء"
        " وتوفير وسائل الوقاية وإحداث لجنة السلامة للمقاولات التي تشغل أكثر من"
        " 50 أجيراً."
    ),
    "حد أدنى للأجر": (
        "المادة 356 وما يليها: يضمن SMIG و SMAG حماية القدرة الشرائية للأجراء"
        " وتحدد قيمته بموجب مرسوم تنظيمي."
    ),
}


def retrieve_context(query: str) -> str:
  retrieved = []
  for key, text in LEGAL_KNOWLEDGE_BASE.items():
    if key in query:
      retrieved.append(text)
  if retrieved:
    return "\n".join(retrieved)
  return (
      "استند إلى المقتضيات العامة والشرعية لمدونة الشغل المغربية (القانون"
      " 65.99)."
  )


# ---------------------------------------------------------
# 6. الواجهة الرئيسية
# ---------------------------------------------------------
st.title("⚖️ المستشار القانوني الذكي")
st.caption(
    "المنصة المعتمدة للاستشارات المباشرة في مدونة الشغل المغربية (القانون 65.99)"
)

# قائمة منسدلة للإعدادات وتحميل السجل
with st.expander("⚙️ خيارات وأدوات الاستشارة وتحميل التقارير"):
  st.write(
      "نظام خبير مدعوم بالذكاء الاصطناعي وتقنية RAG للإجابة عن الاستشارات"
      " القانونية."
  )

  col_reset, col_txt, col_docx = st.columns(3)

  with col_reset:
    if st.button("🗑️ مسح المحادثة"):
      st.session_state.messages = [{
          "role": "assistant",
          "content": (
              "مرحباً بك! أنا مستشارك القانوني الخبير لمدونة الشغل المغربية."
              " كيف يمكنني مساعدتك اليوم؟"
          ),
      }]
      st.rerun()

  # إظهار أزرار التحميل إذا كانت هناك استشارة فعلية
  if "messages" in st.session_state and len(st.session_state.messages) > 1:
    with col_txt:
      chat_text = "\n\n".join([
          f"{'المستخدم' if m['role']=='user' else 'المستشار'}: {m['content']}"
          for m in st.session_state.messages
      ])
      st.download_button(
          "📥 تقرير نصي (TXT)",
          data=chat_text,
          file_name="legal_consultation.txt",
          mime="text/plain",
      )

    with col_docx:
      docx_bytes = generate_docx(st.session_state.messages)
      st.download_button(
          "📄 تقرير وورد (Word)",
          data=docx_bytes,
          file_name="legal_consultation.docx",
          mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      )

# ---------------------------------------------------------
# 7. إدارة سجل المحادثة والأسئلة السريعة
# ---------------------------------------------------------
if "messages" not in st.session_state:
  st.session_state.messages = [{
      "role": "assistant",
      "content": (
          "مرحباً بك! أنا مستشارك القانوني الخبير لمدونة الشغل المغربية. كيف"
          " يمكنني مساعدتك اليوم؟"
      ),
  }]

# أسئلة سريعة مقترحة عند بداية المحادثة
if len(st.session_state.messages) <= 1:
  st.write("💡 **أسئلة قانونية شائعة (إضغط للسؤال فوراً):**")
  q_cols = st.columns(3)

  prompt_to_send = None
  if q_cols[0].button("كم مدة عطلة الأمومة والأبوة؟"):
    prompt_to_send = (
        "كم هي مدة عطلة الأمومة والأبوة في مدونة الشغل المغربية؟"
    )
  if q_cols[1].button("ما هي حقوق الأجير عند الطرد؟"):
    prompt_to_send = (
        "ما هي التعويضات المستحقة للأجير في حالة التعرض للفصل التعسفي؟"
    )
  if q_cols[2].button("كم تبلغ فترة التجربة للأطر؟"):
    prompt_to_send = "ما هي المدة القانونية لفترة التجربة بالنسبة للأطر والعمال؟"

  if prompt_to_send:
    st.session_state.messages.append({"role": "user", "content": prompt_to_send})
    st.rerun()

# عرض رسائل السجل
for msg in st.session_state.messages:
  with st.chat_message(msg["role"]):
    st.markdown(msg["content"])

# ---------------------------------------------------------
# 8. معالجة المدخلات والردود من GROQ
# ---------------------------------------------------------
user_input = st.chat_input("اطرح استفسارك القانوني هنا...")

if user_input or (
    len(st.session_state.messages) > 1
    and st.session_state.messages[-1]["role"] == "user"
    and len(st.session_state.messages) % 2 == 0
):

  current_prompt = (
      user_input if user_input else st.session_state.messages[-1]["content"]
  )

  if user_input:
    st.session_state.messages.append({"role": "user", "content": current_prompt})
    with st.chat_message("user"):
      st.markdown(current_prompt)

  context = retrieve_context(current_prompt)

  system_prompt = f"""
    أنت مستشار قانوني مغربي خبير متخصص حصرياً في مدونة الشغل المغربية (القانون رقم 65.99) والقوانين ذات الصلة.
    
    المرجع القانوني المباشر المتاح للطلب:
    {context}
    
    التزم بالتعليمات التالية:
    1. قدم إجابات دقيقة ومباشرة مستندة إلى مواد مدونة الشغل المغربية مع ذكر أرقام المواد بوضوح.
    2. صغ الإجابة بلغة عربية سليمة، مع تنظيمها في نقاط واضحة ومقروءة.
    3. اختم دائماً بتنبيه مختصر بأسلوب استرشادي يؤكد أن هذه الاستشارة ذات طابع أكاديمي ولا تغني عن الاستشارة القضائية/المحاماة.
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
        st.rerun()
      except Exception as e:
        st.error(f"حدث خطأ أثناء التواصل مع المحرك القانوني: {e}")
