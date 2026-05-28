import streamlit as st
import requests
from bs4 import BeautifulSoup
import json

# إعدادات الصفحة
st.set_page_config(page_title="سوق مدار - إضافة بالرابط", page_icon="🔗", layout="centered")

st.title("🔗 لوحة تحكم سوق مدار - الجلب بالرابط")
st.markdown("أدخل رابط المنتج لجلب البيانات تلقائياً، مع إمكانية التعديل اليدوي قبل الرفع.")
st.divider()

# --- 1. قسم جلب البيانات بالرابط ---
st.header("🌐 جلب بيانات المنتج")
product_url = st.text_input("أدخل رابط المنتج هنا:")

# دالة سحب البيانات الأساسية (تحتاج تخصيص حسب الموقع)
def scrape_product_data(url):
    try:
        # استخدام User-Agent وهمي لتقليل فرصة الحظر
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # --- تنبيه: هذه المحددات (Selectors) افتراضية وتحتاج تعديل حسب الموقع ---
            # مثال افتراضي لجلب العنوان من وسم <title> أو <h1>
            name_tag = soup.find('h1')
            name = name_tag.text.strip() if name_tag else "لم يتم العثور على الاسم"
            
            # إرجاع البيانات المبدئية
            return {
                "name": name,
                "sku": "", # غالباً يحتاج استخراج من الرابط أو هيكل الصفحة
                "price": 0.0, # يحتاج تحديد دقيق لوسم السعر
                "image": "", # يحتاج تحديد دقيق لوسم الصورة
                "description": url # نضع الرابط مؤقتاً في الوصف
            }
        else:
            return None
    except Exception as e:
        st.error(f"حدث خطأ أثناء الاتصال بالموقع: {e}")
        return None

# تهيئة الـ Session State للحقول إذا لم تكن موجودة
if 'form_data' not in st.session_state:
    st.session_state.form_data = {"name": "", "sku": "", "price": 0.0, "image": "", "description": ""}

if st.button("جلب البيانات من الرابط", type="secondary"):
    if product_url:
        with st.spinner("جاري قراءة الرابط..."):
            scraped_data = scrape_product_data(product_url)
            if scraped_data:
                st.session_state.form_data = scraped_data
                st.success("تم جلب البيانات المبدئية! يرجى مراجعتها وتعديلها بالأسفل.")
            else:
                st.warning("تعذر جلب البيانات. قد يكون الموقع محمي بنظام منع السحب. يمكنك إدخالها يدوياً.")
    else:
        st.error("يرجى إدخال الرابط أولاً.")

st.divider()

# --- 2. قسم المراجعة والإدخال اليدوي ---
st.header("📦 مراجعة وتعديل تفاصيل المنتج")

col1, col2 = st.columns(2)
with col1:
    prod_name = st.text_input("اسم المنتج", value=st.session_state.form_data['name'])
    prod_sku = st.text_input("رمز SKU", value=st.session_state.form_data['sku'])
with col2:
    prod_price_sar = st.number_input("السعر الأصلي (ر.س)", min_value=0.0, value=float(st.session_state.form_data['price']), step=1.0, format="%.2f")
    prod_image = st.text_input("رابط صورة المنتج (URL)", value=st.session_state.form_data['image'])

prod_desc = st.text_area("وصف المنتج كاملاً", value=st.session_state.form_data['description'], height=150)

if st.button("اعتماد وتجهيز المنتج", type="primary"):
    if prod_name and prod_price_sar > 0:
        st.session_state['product_ready'] = {
            'name': prod_name,
            'sku': prod_sku,
            'price': prod_price_sar,
            'image': prod_image,
            'description': prod_desc
        }
        st.success("تم تجهيز البيانات! مرر للأسفل للتسعير والرفع.")
    else:
        st.error("يرجى التأكد من إدخال اسم المنتج والسعر على الأقل.")

st.divider()

# --- 3. قسم العرض وتحديد الهامش والرفع ---
if 'product_ready' in st.session_state:
    st.header("💰 التسعير والرفع إلى سلة")
    
    data = st.session_state['product_ready']
    
    # مربع تحديد نسبة العمولة والربح
    margin_percent = st.number_input("نسبة العمولة وهامش الربح (%)", min_value=0.0, value=20.0, step=1.0)
    final_price = data['price'] + (data['price'] * (margin_percent / 100))
    st.info(f"**السعر النهائي للبيع في المتجر:** {final_price:.2f} ر.س")
    
    # الرفع إلى منصة سلة
    salla_token = st.text_input("أدخل Salla Access Token", type="password")
    
    if st.button("🚀 ارفع المنتج إلى متجر سلة"):
        if not salla_token:
            st.warning("يرجى إدخال الـ Token الخاص بمتجرك في سلة أولاً.")
        else:
            with st.spinner("جاري الرفع إلى سلة..."):
                url = "https://api.salla.dev/admin/v2/products"
                headers = {
                    "Authorization": f"Bearer {salla_token}",
                    "Content-Type": "application/json",
                }
                payload = {
                    "name": data['name'],
                    "price": final_price,
                    "description": data['description'],
                    "sku": data['sku'],
                    "product_type": "product",
                    "quantity": 1
                }
                if data['image']:
                    payload["images"] = [{"original": data['image']}]
                
                try:
                    response = requests.post(url, headers=headers, data=json.dumps(payload))
                    if response.status_code in [200, 201]:
                        st.success("🎉 تم رفع المنتج إلى متجرك في سلة بنجاح!")
                    else:
                        st.error(f"حدث خطأ أثناء الرفع (الكود: {response.status_code})")
                        st.json(response.json())
                except Exception as e:
                    st.error(f"حدث خطأ في الاتصال: {e}")
                                          
