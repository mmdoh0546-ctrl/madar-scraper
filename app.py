import streamlit as st
import requests

# إعدادات واجهة سوق مدار
st.set_page_config(page_title="سوق مدار", page_icon="🚀", layout="centered")
st.title("🚀 لوحة تحكم سوق مدار (إضافة المنتجات الكاملة)")

st.sidebar.title("محلك - سوق مدار")
option = st.sidebar.radio("القائمة الرئيسية", ["إضافة منتج"])

st.info("💡 أدخل تفاصيل المنتج بالأسفل، وسيظهر لك مربع العمولة وزر الرفع لمتجرك في سلة بأسفل الصفحة تلقائياً بكامل الوصف والصور.")

# الخطوة 1: إدخال البيانات المباشرة لضمان عدم الحظر
prod_name = st.text_input("اسم المنتج (اكتب الاسم المناسب لمتجرك):")
prod_sku = st.text_input("رمز المنتج SKU (أو رقم المنتج من ترينديول):")
prod_desc = st.text_area("وصف المنتج وتفاصيله:")
prod_image = st.text_input("رابط صورة المنتج المباشر:")
price_sar = st.number_input("السعر الأصلي في ترينديول (بالريال السعودي):", min_value=0.0, value=0.0, step=1.0)

if st.button("تجهيز وحفظ بيانات المنتج 🔍"):
    if prod_name and price_sar > 0:
        st.session_state['manual_ready'] = True
        st.session_state['m_name'] = prod_name
        st.session_state['m_sku'] = prod_sku if prod_sku else "TR-000"
        st.session_state['m_desc'] = prod_desc
        st.session_state['m_image'] = prod_image if prod_image else "https://images.unsplash.com/photo-1523381210434-271e8be1f52b"
        st.session_state['m_price'] = float(price_sar)
        st.success("🎯 تم تجهيز المنتج بنجاح! راجع البيانات بالأسفل لتحديد عمولتك ورفعه.")
    else:
        st.warning("الرجاء كتابة اسم المنتج والسعر أولاً للتجهيز.")

# --- الخطوة 2: تظهر في الأسفل فقط بعد الضعم على التجهيز (حسب طلبك) ---
if st.session_state.get('manual_ready', False):
    st.write("---")
    st.subheader("📋 مراجعة الأسعار والرفع النهائي إلى سلة")
    
    # عرض الصورة المدخلة للتأكيد
    if st.session_state['m_image']:
        st.image(st.session_state['m_image'], width=130, caption="صورة المنتج")
    
    # مربع العمولة (تتحكم به كما تريد)
    comm = st.number_input("نسبة عمولتك وهامش ربحك لمتجرك (%)", min_value=0.0, value=15.0, step=1.0)
    
    # حساب السعر النهائي المباشر
    final_price = st.session_state['m_price'] * (1 + (comm / 100))
    st.metric(label="💰 السعر النهائي الذي سيظهر في متجرك (سلة)", value=f"{final_price:.2f} SAR")
    
    # مربع الـ Token الخاص بمتجرك في سلة
    salla_token = st.text_input("أدخل رمز وصول سلة (Salla Access Token)", type="password", placeholder="ضع الـ Token الخاص بمتجرك للرفع...")
    
    # زر رفع المنتج في أسفل الصفحة تماماً ومعه الوصف والصورة والاسم والسعر الجديد
    if st.button("➕ ارفع المنتج الآن بكامل تفاصيله وصورته إلى سلة"):
        if salla_token:
            with st.spinner("جاري إرسال المنتج بالكامل إلى سلة..."):
                headers = {"Authorization": f"Bearer {salla_token}", "Content-Type": "application/json"}
                payload = {
                    "name": st.session_state['m_name'], 
                    "price": round(final_price, 2), 
                    "quantity": 10, 
                    "sku": st.session_state['m_sku'],
                    "description": st.session_state['m_desc'],
                    "images": [{"url": st.session_state['m_image']}]
                }
                res = requests.post("https://api.salla.dev/admin/v2/products", headers=headers, json=payload)
                if res.status_code in [200, 201]: 
                    st.success("✅ كفو ممدوح! المنتج نزل رسميًا بكامل تفاصيله، وصفه، وصورته في متجرك على سلة بالربح الجديد!")
                    st.session_state['manual_ready'] = False  # تفريغ الذاكرة لمنتج جديد
                else: 
                    st.error(f"❌ فشل الرفع لـ سلة. تفاصيل الخطأ: {res.text}")
        else:
            st.error("الرجاء وضع الـ Salla Token أولاً لتتمكن من رفع المنتج.")
