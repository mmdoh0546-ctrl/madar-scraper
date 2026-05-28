import streamlit as st
import requests

# إعدادات واجهة سوق مدار
st.set_page_config(page_title="سوق مدار", page_icon="🚀", layout="centered")
st.title("🚀 لوحة تحكم سوق مدار (إضافة المنتجات)")

st.sidebar.title("محلك - سوق مدار")
option = st.sidebar.radio("القائمة الرئيسية", ["إضافة منتج ترينديول"])

st.info("💡 أدخل بيانات المنتج الأساسية بالأسفل، وسيظهر لك مربع العمولة وزر الرفع لمتجرك في سلة بأسفل الصفحة تلقائيًا.")

# الخطوة 1: إدخال البيانات المباشرة بدون تعقيد الروابط
prod_name = st.text_input("اسم المنتج (اكتب الاسم أو الصقه من ترينديول):")
prod_id = st.text_input("رقم المنتج ID (الرقم الموجود بعد p- في الرابط):", placeholder="مثال: 1107430640")
price_sar = st.number_input("السعر الحالي في ترينديول السعودية (بالريال):", min_value=0.0, value=0.0, step=1.0)

if st.button("تجهيز بيانات المنتج 🔍"):
    if prod_name and price_sar > 0:
        # حفظ البيانات في ذاكرة الصفحة لتظهر بالأسفل
        st.session_state['manual_product'] = {
            "name": prod_name,
            "sku": prod_id if prod_id else "TR-000",
            "price_sar": float(price_sar)
        }
        st.success("🎯 تم تجهيز المنتج بنجاح! انزل للأسفل لتحديد عمولتك ورفعه لـ سلة.")
    else:
        st.warning("الرجاء كتابة اسم المنتج والسعر أولاً للتجهيز.")

# --- الخطوة 2: تظهر في الأسفل فقط بعد الضغط على التجهيز (حسب طلبك) ---
if 'manual_product' in st.session_state:
    data = st.session_state['manual_product']
    st.write("---")
    st.subheader("📋 مراجعة الأسعار والرفع إلى سلة")
    
    # عرض البيانات الحالية
    st.write(f"📦 المنتج: **{data['name']}**")
    st.write(f"🔢 رمز SKU: **{data['sku']}**")
    st.write(f"💵 السعر الأصلي: **{data['price_sar']:.2f} ريال سعودي**")
    
    # مربع العموله (تتحكم بالجرام والنسبة)
    comm = st.number_input("نسبة عمولتك وهامش ربحك (%)", min_value=0.0, value=15.0, step=1.0)
    
    # حساب السعر النهائي المباشر
    final_price = data['price_sar'] * (1 + (comm / 100))
    st.metric(label="💰 السعر النهائي الذي سيظهر في متجرك (سلة)", value=f"{final_price:.2f} SAR")
    
    # مربع الـ Token الخاص بمتجرك
    salla_token = st.text_input("أدخل رمز وصول سلة (Salla Access Token)", type="password", placeholder="ضع الـ Token الخاص بمتجرك للرفع...")
    
    # زر رفع المنتج في أسفل الصفحة تماماً كما طلبت
    if st.button("➕ ارفع المنتج الآن إلى متجري في سلة"):
        if salla_token:
            with st.spinner("جاري إرسال المنتج إلى سلة..."):
                headers = {"Authorization": f"Bearer {salla_token}", "Content-Type": "application/json"}
                payload = {
                    "name": data['name'], 
                    "price": round(final_price, 2), 
                    "quantity": 10, 
                    "sku": data['sku'],
                    "images": [{"url": "https://images.unsplash.com/photo-1523381210434-271e8be1f52b"}] # صورة مؤقتة حتى نربط الصور لاحقاً
                }
                res = requests.post("https://api.salla.dev/admin/v2/products", headers=headers, json=payload)
                if res.status_code in [200, 201]: 
                    st.success("✅ مبروك! المنتج نزل رسميًا في متجرك على سلة بالربح الجديد!")
                else: 
                    st.error(f"❌ فشل الرفع لـ سلة. تفاصيل الخطأ: {res.text}")
        else:
            st.error("الرجاء وضع الـ Salla Token أولاً لتتمكن من رفع المنتج.")
            
