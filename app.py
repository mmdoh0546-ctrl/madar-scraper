import streamlit as st
import requests
from bs4 import BeautifulSoup

# إعدادات الصفحة
st.set_page_config(page_title="سوق مدار - تجربة السحب المباشر", page_icon="⚡", layout="centered")

st.title("⚡ تجربة جلب المنتجات (بدون ربط API)")
st.markdown("هذه النسخة مخصصة لاختبار سحب البيانات من الروابط مباشرة دون الحاجة لأي مفاتيح أو ربط مع سلة.")
st.divider()

# تهيئة الـ Session State لحفظ البيانات
if 'scraped_data' not in st.session_state:
    st.session_state.scraped_data = {"name": "", "sku": "", "price": 0.0, "image": "", "description": ""}

# --- قسم جلب البيانات ---
st.header("🌐 سحب بيانات المنتج")
product_url = st.text_input("أدخل رابط المنتج (مثل ترينديول):")

if st.button("جلب البيانات", type="primary"):
    if product_url:
        with st.spinner("جاري محاولة قراءة الرابط..."):
            try:
                # استخدام User-Agent لمحاكاة متصفح حقيقي وتجنب الحظر السريع
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
                    "Accept-Language": "ar,en-US;q=0.9,en;q=0.8"
                }
                
                response = requests.get(product_url, headers=headers, timeout=15)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # محاولة استخراج العنوان (نجلب أي وسم h1 في الصفحة)
                    title_tag = soup.find('h1')
                    title = title_tag.text.strip() if title_tag else "لم نتمكن من سحب الاسم"
                    
                    # حفظ البيانات المستخرجة مبدئياً
                    st.session_state.scraped_data = {
                        "name": title,
                        "sku": "SKU-AUTO", # افتراضي للتجربة
                        "price": 0.0,      # السعر يحتاج تخصيص حسب الموقع
                        "image": "",       # الصورة تحتاج تخصيص
                        "description": f"تم جلب البيانات من: {product_url}"
                    }
                    st.success("تم الاتصال بالرابط بنجاح! راجع البيانات المستخرجة في الأسفل.")
                
                elif response.status_code == 403:
                    st.error("السيرفر (مثل ترينديول) رفض الطلب (خطأ 403 - حظر). الموقع يمنع السحب المباشر.")
                else:
                    st.error(f"حدث خطأ أثناء محاولة الاتصال. كود الخطأ: {response.status_code}")
                    
            except Exception as e:
                st.error(f"فشل الاتصال بالرابط: {e}")
    else:
        st.warning("يرجى إدخال الرابط أولاً.")

st.divider()

# --- قسم عرض البيانات وتعديلها ---
st.header("📦 البيانات المستخرجة (يمكنك تعديلها)")

col1, col2 = st.columns(2)
with col1:
    prod_name = st.text_input("اسم المنتج", value=st.session_state.scraped_data['name'])
    prod_sku = st.text_input("رمز SKU", value=st.session_state.scraped_data['sku'])
with col2:
    prod_price_sar = st.number_input("السعر الأصلي (ر.س)", min_value=0.0, value=float(st.session_state.scraped_data['price']), step=1.0)
    prod_image = st.text_input("رابط صورة المنتج", value=st.session_state.scraped_data['image'])

prod_desc = st.text_area("وصف المنتج", value=st.session_state.scraped_data['description'], height=150)

st.divider()

# --- قسم التسعير النهائي ---
st.header("💰 تسعير المنتج")
margin_percent = st.number_input("نسبة العمولة وهامش الربح (%)", min_value=0.0, value=20.0, step=1.0)

final_price = prod_price_sar + (prod_price_sar * (margin_percent / 100))
st.info(f"**السعر النهائي للبيع في المتجر:** {final_price:.2f} ر.س")

st.success("💡 هذا الكود للتجربة فقط. زر 'الرفع إلى سلة' مخفي حالياً حتى تتأكد من عمل السحب.")
