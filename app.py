import streamlit as st
import cloudscraper
from bs4 import BeautifulSoup
import requests
import json

# إعدادات الصفحة
st.set_page_config(page_title="سوق مدار - السحب المتقدم", page_icon="🛡️", layout="centered")

st.title("🛡️ لوحة تحكم سوق مدار - الجلب المتقدم")
st.markdown("يستخدم هذا الإصدار تقنية تخطي الحماية (Cloudscraper) لسحب البيانات، مع الإبقاء على التعديل اليدوي والرفع لسلة.")
st.divider()

# تهيئة البيانات المؤقتة
if 'scraped_data' not in st.session_state:
    st.session_state.scraped_data = {"name": "", "sku": "", "price": 0.0, "image": "", "description": ""}

# --- 1. قسم جلب البيانات وتخطي الحماية ---
st.header("🌐 سحب بيانات المنتج")
product_url = st.text_input("أدخل رابط المنتج (مثل ترينديول):")

if st.button("جلب البيانات", type="primary"):
    if product_url:
        with st.spinner("جاري تخطي الحماية وقراءة الرابط..."):
            try:
                # إنشاء أداة تخطي الحماية لتشبه متصفح كروم على ويندوز
                scraper = cloudscraper.create_scraper(browser={
                    'browser': 'chrome',
                    'platform': 'windows',
                    'desktop': True
                })
                
                response = scraper.get(product_url, timeout=20)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # محاولة استخراج العنوان (من وسم title أو h1)
                    title = soup.title.string if soup.title else ""
                    if not title:
                        h1_tag = soup.find('h1')
                        title = h1_tag.text.strip() if h1_tag else "لم يتم العثور على الاسم"
                    
                    # محاولة استخراج الصورة الأساسية
                    img_tag = soup.find('meta', property='og:image')
                    img_url = img_tag['content'] if img_tag else ""
                    
                    st.session_state.scraped_data = {
                        "name": title.replace(" - Trendyol", ""), # تنظيف الاسم
                        "sku": "SKU-AUTO",
                        "price": 0.0, 
                        "image": img_url,
                        "description": f"رابط المصدر: {product_url}"
                    }
                    st.success("تم تخطي الحماية وسحب البيانات الأساسية بنجاح! راجعها بالأسفل.")
                else:
                    st.error(f"الموقع لا يزال يرفض الطلب. كود الخطأ: {response.status_code}")
                    
            except Exception as e:
                st.error(f"حدث خطأ أثناء محاولة الاتصال: {e}")
    else:
        st.warning("يرجى إدخال الرابط أولاً.")

st.divider()

# --- 2. قسم عرض البيانات وتعديلها ---
st.header("📦 البيانات (مراجعة وتعديل)")

col1, col2 = st.columns(2)
with col1:
    prod_name = st.text_input("اسم المنتج", value=st.session_state.scraped_data['name'])
    prod_sku = st.text_input("رمز SKU", value=st.session_state.scraped_data['sku'])
with col2:
    prod_price_sar = st.number_input("السعر الأصلي (ر.س)", min_value=0.0, value=float(st.session_state.scraped_data['price']), step=1.0)
    prod_image = st.text_input("رابط صورة المنتج", value=st.session_state.scraped_data['image'])

prod_desc = st.text_area("وصف المنتج", value=st.session_state.scraped_data['description'], height=150)

st.divider()

# --- 3. التسعير والرفع إلى منصة سلة ---
st.header("💰 التسعير والرفع")
margin_percent = st.number_input("نسبة العمولة وهامش الربح (%)", min_value=0.0, value=20.0, step=1.0)

final_price = prod_price_sar + (prod_price_sar * (margin_percent / 100))
st.info(f"**السعر النهائي للبيع في المتجر:** {final_price:.2f} ر.س")

salla_token = st.text_input("أدخل Salla Access Token للرفع", type="password")

if st.button("🚀 ارفع المنتج إلى متجر سلة"):
    if not salla_token:
        st.warning("يرجى إدخال الـ Token الخاص بمتجرك في سلة أولاً.")
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
                    st.success("🎉 تم رفع المنتج إلى متجرك في سلة بنجاح!")
                else:
                    st.error(f"حدث خطأ من سيرفر سلة: {res.text}")
            except Exception as e:
                st.error(f"فشل الاتصال بسلة: {e}")
    else:
        st.warning("تأكد من وجود اسم للمنتج وسعر صحيح قبل الرفع.")
        
