import streamlit as st
import requests
import json

# إعدادات الصفحة الأساسية
st.set_page_config(page_title="سوق مدار - إضافة المنتجات", page_icon="🛒", layout="centered")

st.title("🛒 لوحة تحكم سوق مدار - إضافة المنتجات")
st.markdown("أدخل تفاصيل المنتج يدوياً لتجنب مشاكل حظر السيرفرات وضمان دقة البيانات.")
st.divider()

# --- 1. قسم إدخال البيانات ---
st.header("📦 تفاصيل المنتج")

col1, col2 = st.columns(2)
with col1:
    prod_name = st.text_input("اسم المنتج")
    prod_sku = st.text_input("رمز SKU")
with col2:
    prod_price_sar = st.number_input("السعر الأصلي (ر.س)", min_value=0.0, step=1.0, format="%.2f")
    prod_image = st.text_input("رابط صورة المنتج (URL)")

prod_desc = st.text_area("وصف المنتج كاملاً", height=150)

# زر تجهيز المنتج وحفظه في الـ Session State
if st.button("تجهيز المنتج", type="primary"):
    if prod_name and prod_price_sar > 0:
        st.session_state['product_data'] = {
            'name': prod_name,
            'sku': prod_sku,
            'price': prod_price_sar,
            'image': prod_image,
            'description': prod_desc
        }
        st.success("تم تجهيز بيانات المنتج وحفظها بنجاح! مرر للأسفل لاستكمال التسعير.")
    else:
        st.error("يرجى التأكد من إدخال اسم المنتج والسعر على الأقل.")

st.divider()

# --- 2. قسم العرض وتحديد الهامش وحساب السعر ---
# لن يظهر هذا القسم إلا إذا تم حفظ البيانات بنجاح
if 'product_data' in st.session_state:
    st.header("💰 تسعير المنتج")
    
    data = st.session_state['product_data']
    
    # عرض البيانات المؤكدة
    st.info(f"**المنتج:** {data['name']} | **السعر الأصلي:** {data['price']} ر.س")
    
    # مربع تحديد نسبة العمولة والربح
    margin_percent = st.number_input("نسبة العمولة وهامش الربح (%)", min_value=0.0, value=20.0, step=1.0)
    
    # حساب السعر النهائي
    final_price = data['price'] + (data['price'] * (margin_percent / 100))
    
    st.success(f"**السعر النهائي للبيع في المتجر:** {final_price:.2f} ر.س")
    
    st.divider()

    # --- 3. قسم الرفع إلى منصة سلة ---
    st.header("🚀 الرفع إلى متجر سلة")
    
    # إدخال التوكن الخاص بسلة (مخفي لحماية البيانات)
    salla_token = st.text_input("أدخل Salla Access Token", type="password")
    
    if st.button("ارفع المنتج إلى سلة"):
        if not salla_token:
            st.warning("يرجى إدخال الـ Token الخاص بمتجرك في سلة أولاً.")
        else:
            with st.spinner("جاري رفع المنتج إلى سوق مدار..."):
                # رابط Salla API الرسمي لإضافة المنتجات (V2)
                url = "https://api.salla.dev/admin/v2/products"
                
                headers = {
                    "Authorization": f"Bearer {salla_token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
                
                # تجهيز هيكل البيانات المطلوب من سلة
                payload = {
                    "name": data['name'],
                    "price": final_price,
                    "description": data['description'],
                    "sku": data['sku'],
                    "product_type": "product", # نوع المنتج الافتراضي
                    "quantity": 1 # يمكنك تعديل الكمية الافتراضية إذا أردت
                }
                
                # إضافة الصورة إذا كان الرابط موجوداً
                if data['image']:
                    payload["images"] = [{"original": data['image']}]
                
                try:
                    response = requests.post(url, headers=headers, data=json.dumps(payload))
                    
                    # التحقق من حالة الطلب
                    if response.status_code in [200, 201]:
                        st.success("🎉 تم رفع المنتج إلى متجرك في سلة بنجاح!")
                        # تفريغ البيانات إذا أردت إضافة منتج جديد (اختياري)
                        # del st.session_state['product_data'] 
                    else:
                        st.error(f"حدث خطأ أثناء الرفع (الكود: {response.status_code})")
                        # عرض تفاصيل الخطأ القادمة من سيرفر سلة لفهم المشكلة
                        st.json(response.json())
                
                except Exception as e:
                    st.error(f"حدث خطأ في الاتصال: {e}")
                    
