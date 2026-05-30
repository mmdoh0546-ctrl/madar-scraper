import streamlit as st
import requests
from bs4 import BeautifulSoup
import re

# --- إعدادات واجهة النظام ---
st.set_page_config(page_title="نظام سحب المنتجات | سوق مدار", layout="centered", page_icon="🛍️")
st.title("🛍️ نظام سحب المنتجات لمتجر سوق مدار")
st.write("أدخل رابط المنتج من Trendyol لجلب (العنوان، الوصف، الصور، والسعر) مع حساب العمولة الديناميكي.")

def fetch_trendyol_product(url):
    # 1. استخراج رقم المنتج من الرابط (السحر يبدأ هنا)
    match = re.search(r'-p-(\d+)', url)
    if not match:
        return {"error": "تأكد من أن الرابط كامل ويحتوي على رقم المنتج (ينتهي عادة بـ -p-أرقام)."}
    
    product_id = match.group(1)
    
    # 2. الاتصال بواجهة ترينديول البرمجية (API) المخفية لتخطي الحظر
    api_url = f"https://public.trendyol.com/discovery-web-productgw-service/api/productDetail/{product_id}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(api_url, headers=headers, timeout=15)
        if response.status_code != 200:
            return {"error": f"تم حظر الطلب من المورد أو المنتج غير متاح. كود: {response.status_code}"}
        
        data = response.json()
        
        # تحديد موقع البيانات داخل الرد
        result = data.get("result", data)
        
        # استخراج العنوان مع اسم الماركة
        brand = result.get("brand", {}).get("name", "")
        name = result.get("name", "منتج بدون اسم")
        title = f"{brand} {name}".strip()
        
        # استخراج السعر
        price = 0.0
        price_info = result.get("price", {}).get("sellingPrice") or result.get("price", {}).get("discountedPrice", {})
        if price_info:
            price = float(price_info.get("value", 0.0))
        
        # استخراج الصور عالية الجودة
        images = []
        for img in result.get("images", []):
            img_url = img.get("url", "")
            if img_url:
                if not img_url.startswith("http"):
                    img_url = f"https://cdn.dsmcdn.com{img_url}"
                images.append(img_url)
        
        # استخراج الوصف وتنظيفه من أكواد HTML
        description = ""
        desc_list = result.get("contentDescriptions", [])
        if desc_list:
            raw_html = desc_list[0].get("description", "")
            # استخدام BeautifulSoup لتنظيف النص برمجياً وجعله مقروءاً
            soup = BeautifulSoup(raw_html, "html.parser")
            description = soup.get_text(separator="\n").strip()
        else:
            description = "لا يوجد وصف تفصيلي لهذا المنتج من المورد."
            
        return {
            "title": title,
            "price": price,
            "description": description,
            "images": images
        }
        
    except Exception as e:
        return {"error": f"حدث خطأ أثناء معالجة بيانات المورد: {str(e)}"}

# --- واجهة المستخدم التفاعلية ---
st.write("---")
product_url = st.text_input("🔗 ألصق رابط المنتج هنا:")

st.subheader("⚙️ إعدادات التسعير والعمولة")
col_type, col_val = st.columns(2)

with col_type:
    commission_type = st.radio("نوع العمولة:", ["مبلغ ثابت", "نسبة مئوية (%)"])
with col_val:
    if commission_type == "مبلغ ثابت":
        commission_value = st.number_input("مقدار الإضافة:", min_value=0.0, value=20.0, step=1.0)
    else:
        commission_value = st.number_input("النسبة المئوية للربح (%):", min_value=0.0, value=15.0, step=1.0)

if st.button("🚀 جلب وتحليل بيانات المنتج", use_container_width=True):
    if not product_url:
        st.warning("الرجاء وضع الرابط أولاً.")
    else:
        with st.spinner("جاري الاتصال السري بخوادم المورد لتخطي الحماية..."):
            result = fetch_trendyol_product(product_url)
            
            if "error" in result:
                st.error(result["error"])
            else:
                st.success("تم سحب بيانات المنتج بنجاح وبدقة عالية!")
                
                original_price = result['price']
                if commission_type == "مبلغ ثابت":
                    final_price = original_price + commission_value
                else:
                    final_price = original_price + (original_price * (commission_value / 100))
                
                st.write("---")
                st.subheader(result['title'])
                
                price_col1, price_col2 = st.columns(2)
                # السعر المستخرج غالباً ما يكون بالليرة التركية (TRY)
                price_col1.metric("السعر من المورد", f"{original_price:.2f}")
                price_col2.metric("السعر النهائي للعميل", f"{final_price:.2f}", delta=f"ربحك: {(final_price - original_price):.2f}")
                
                with st.expander("📝 عرض وصف المنتج", expanded=True):
                    # عرض النص كما هو بالمسافات والأسطر
                    st.text(result['description'])
                
                st.subheader("📸 صور المنتج")
                if result['images']:
                    cols = st.columns(3)
                    for i, img_url in enumerate(result['images']):
                        cols[i % 3].image(img_url, use_container_width=True)
                else:
                    st.warning("لم يتم العثور على صور لهذا المنتج.")
                
                st.write("---")
                if st.button("🛒 إضافة المنتج إلى متجر سوق مدار", type="primary", use_container_width=True):
                    st.info("البيانات ممتازة وجاهزة! سيتم تفعيل هذا الزر لاحقاً لرفع المنتج بضغطة زر إلى سلة ليظهر فوراً على قالب مزايا.")
        
