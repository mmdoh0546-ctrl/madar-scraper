import streamlit as st
import requests
import json

st.set_page_config(page_title="سوق مدار - إضافة المنتجات الاحترافية", page_icon="⚡", layout="centered")

st.title("⚡ لوحة تحكم سوق مدار - الجلب الآلي والآمن")
st.markdown("استخدم الرابط لجلب البيانات عبر API وسيط، مع إمكانية التعديل اليدوي لتجنب الأخطاء.")
st.divider()

# --- إعدادات مفاتيح الربط ---
with st.sidebar:
    st.header("🔑 إعدادات الربط")
    rapidapi_key = st.text_input("أدخل مفتاح RapidAPI", type="password")
    salla_token = st.text_input("أدخل Salla Access Token", type="password")
    st.info("لا يتم حفظ هذه المفاتيح وتُستخدم فقط أثناء تشغيل الأداة.")

# تهيئة الـ Session State
if 'scraped_data' not in st.session_state:
    st.session_state.scraped_data = {"name": "", "sku": "", "price": 0.0, "image": "", "description": ""}

# --- 1. قسم جلب البيانات ---
st.header("🌐 سحب بيانات المنتج")
product_url = st.text_input("أدخل رابط المنتج (من شي إن أو غيره):")

if st.button("جلب البيانات", type="secondary"):
    if not rapidapi_key:
        st.error("يرجى إدخال مفتاح RapidAPI من القائمة الجانبية أولاً.")
    elif product_url:
        with st.spinner("جاري سحب البيانات بأمان..."):
            # مثال لطلب API من RapidAPI (يجب تعديل الرابط حسب الـ API الذي تشترك فيه)
            api_url = "https://shein-data-api.p.rapidapi.com/product-details"
            headers = {
                "X-RapidAPI-Key": rapidapi_key,
                "X-RapidAPI-Host": "shein-data-api.p.rapidapi.com"
            }
            querystring = {"url": product_url}
            
            try:
                # هذا مجرد محاكاة، شكل الاستجابة يختلف حسب الـ API المختار
                response = requests.get(api_url, headers=headers, params=querystring)
                
                if response.status_code == 200:
                    data = response.json()
                    # تعبئة البيانات في الـ Session State
                    st.session_state.scraped_data = {
                        "name": data.get('title', 'بدون اسم'),
                        "sku": data.get('sku', 'SKU-000'),
                        "price": float(data.get('price', {}).get('usd', 0.0)) * 3.75, # تحويل تقريبي للريال
                        "image": data.get('images', [''])[0] if data.get('images') else '',
                        "description": data.get('description', '')
                    }
                    st.success("تم سحب البيانات بنجاح! راجعها بالأسفل.")
                else:
                    st.error(f"حدث خطأ في الجلب: {response.status_code} - تأكد من صلاحية مفتاح الـ API.")
            except Exception as e:
                st.error(f"خطأ في الاتصال بالسيرفر: {e}")
    else:
        st.warning("يرجى إدخال رابط المنتج.")

st.divider()

# --- 2. قسم المراجعة والإدخال اليدوي ---
st.header("📦 مراجعة وتعديل البيانات")
col1, col2 = st.columns(2)
with col1:
    prod_name = st.text_input("اسم المنتج", value=st.session_state.scraped_data['name'])
    prod_sku = st.text_input("رمز SKU", value=st.session_state.scraped_data['sku'])
with col2:
    prod_price_sar = st.number_input("السعر الأصلي (ر.س)", min_value=0.0, value=st.session_state.scraped_data['price'], step=1.0)
    prod_image = st.text_input("رابط صورة المنتج", value=st.session_state.scraped_data['image'])

prod_desc = st.text_area("وصف المنتج", value=st.session_state.scraped_data['description'], height=150)

st.divider()

# --- 3. التسعير والرفع إلى سلة ---
st.header("💰 التسعير والرفع")
margin_percent = st.number_input("نسبة العمولة وهامش الربح (%)", min_value=0.0, value=20.0, step=1.0)

final_price = prod_price_sar + (prod_price_sar * (margin_percent / 100))
st.info(f"**السعر النهائي للبيع في المتجر:** {final_price:.2f} ر.س")

if st.button("🚀 ارفع المنتج إلى سلة", type="primary"):
    if not salla_token:
        st.error("يرجى إدخال Salla Access Token من القائمة الجانبية.")
    elif prod_name and final_price > 0:
        with st.spinner("جاري الرفع إلى سلة..."):
            salla_url = "https://api.salla.dev/admin/v2/products"
            headers = {
                "Authorization": f"Bearer {salla_token}",
                "Content-Type": "application/json",
            }
            payload = {
                "name": prod_name,
                "price": final_price,
                "description": prod_desc,
                "sku": prod_sku,
                "product_type": "product",
                "quantity": 1
            }
            if prod_image:
                payload["images"] = [{"original": prod_image}]
            
            try:
                res = requests.post(salla_url, headers=headers, data=json.dumps(payload))
                if res.status_code in [200, 201]:
                    st.success("🎉 تم الرفع بنجاح!")
                else:
                    st.error(f"خطأ من سلة: {res.text}")
            except Exception as e:
                st.error(f"فشل الاتصال بسلة: {e}")
    else:
        st.warning("تأكد من وجود اسم للمنتج وسعر صحيح قبل الرفع.")
        
