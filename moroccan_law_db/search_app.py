from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

# 1. تحميل نموذج التضمين (نفس النموذج المستخدم في بناء القاعدة)
print("جاري تحميل نموذج الذكاء الاصطناعي...")
embeddings = HuggingFaceEmbeddings(model_name="intfloat/multilingual-e5-base")

# 2. الاتصال بقاعدة البيانات المحفوظة
print("جاري الاتصال بقاعدة البيانات القانونية...")
vector_db = Chroma(
    persist_directory="./moroccan_law_db", 
    embedding_function=embeddings
)

# 3. دالة البحث الدلالي عن النصوص القانونية
def retrieve_legal_context(user_scenario, top_k=2):
    print(f"\n🔍 وقائع المستخدم: '{user_scenario}'\n")
    print("جاري البحث في المنظومة القانونية...\n")
    
    # البحث واستخراج أقرب النصوص الدلالية
    results = vector_db.similarity_search_with_score(user_scenario, k=top_k)
    
    if not results:
        print("لم يتم العثور على نصوص قانونية ذات صلة.")
        return
    
    # 4. طباعة النتائج بوضوح
    for idx, (doc, score) in enumerate(results):
        print(f"=== النتيجة القانونية رقم {idx + 1} ===")
        print(f"📖 النص المسترد: {doc.page_content}")
        print(f"⚖️ السند القانوني: {doc.metadata.get('source')} - {doc.metadata.get('article')}")
        print(f"📌 الموضوع: {doc.metadata.get('topic')}")
        print("-" * 40)

# ==========================================
# 5. اختبار النظام بوقائع افتراضية
# ==========================================

scenario = "شاركت في طلب عروض، وقامت الإدارة بإلغاء الصفقة فجأة بحجة تغير المعطيات الاقتصادية وارتفاع الأسعار. هل يحق لها ذلك؟"
retrieve_legal_context(scenario)