import streamlit as st
import requests
from bs4 import BeautifulSoup
import json
import re

# --- إعدادات واجهة النظام ---
st.set_page_config(page_title="نظام سحب المنتجات | سوق مدار", layout="centered", page_icon="🛍️")
st.title("🛍️ نظام سحب المنتجات لمتجر سوق مدار")
st.write("أدخل رابط المنتج من Trendyol لجلب (العنوان، الوصف، الصور، والسعر) مع حساب العمولة الديناميكي.")

# --- دالة الجلب البرمجية المتطورة ---
def fetch_trendyol_product(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ar,en-US;q=0.9,en;q=0.8"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            return {"error": f"المورد يرفض الاتصال حالياً. كود: {response.status_code}"}
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        title = ""
        price = 0.0
        currency = "SAR"
        description = ""
        images = []

        # 1. استخراج العنوان
        meta_title = soup.find('meta', property='og:title')
        if meta_title: title = meta_title.get('content', '')

        # 2. استخراج الوصف (تم حل المشكلة البرمجية هنا)
        meta_desc = soup.find('meta', attrs={'name': 'description'}) or soup.find('meta', property='og:description')
        if meta_desc: description = meta_desc.get('content', '')
        
        # 3. استخراج الصورة الأساسية
        meta_image = soup.find('meta', property='og:image')
        if meta_image: images.append(meta_image.get('content', ''))

        # 4. استخراج السعر
        meta_price = soup.find('meta', property='product:price:amount')
        if meta_price: 
            price = float(meta_price.get('content', 0.0))
        else:
            price_tag = soup.find('span', class_='prc-dsc') or soup.find('div', class_='product-price')
            if price_tag:
                price_str = re.sub(r'[^\d.]', '', price_tag.text.replace(',', '.'))
                if price_str: price = float(price_str)

        # 5. استخراج باقي الصور
        img_urls = re.findall(r'https://cdn\.dsmcdn\.com/[^"\'\s]+\.jpg', response.text)
        for img in img_urls:
            if 'productmedia' in img or 'mnresize' in img:
                high_res_img = img.replace('/mnresize/128/192/', '/mnresize/1200/1800/')
                images.append(high_res_img)
        
        images = list(dict.fromkeys(images))

        if not title:
            return {"error": "لم يتم العثور على بيانات المنتج، قد يكون الرابط خاطئاً أو الموقع يطلب تحقق."}

        return {
            "title": title,
            "price": price,
            "currency": currency,
            "description": description,
            "images": images
        }
            
    except requests.exceptions.RequestException as e:
        return {"error": "فشل الاتصال بالإنترنت أو انتهت مهلة الطلب."}
    except Exception as e:
        return {"error": f"حدث خطأ غير متوقع أثناء معالجة البيانات: {str(e)}"}

# --- واجهة المستخدم التفاعلية ---
st.write("---")
product_url = st.text_input("🔗 ألصق رابط المنتج هنا:")

st.subheader("⚙️ إعدادات التسعير والعمولة")
col_type, col_val = st.columns(2)

with col_type:
    commission_type = st.radio("نوع العمولة:", ["مبلغ ثابت (ريال)", "نسبة مئوية (%)"])
with col_val:
    if commission_type == "مبلغ ثابت (ريال)":
        commission_value = st.number_input("مقدار الإضافة (بالريال):", min_value=0.0, value=20.0, step=1.0)
    else:
        commission_value = st.number_input("النسبة المئوية للربح (%):", min_value=0.0, value=15.0, step=1.0)

if st.button("🚀 جلب وتحليل بيانات المنتج", use_container_width=True):
    if not product_url:
        st.warning("الرجاء وضع الرابط أولاً.")
    else:
        with st.spinner("جاري سحب البيانات والصور من المورد..."):
            result = fetch_trendyol_product(product_url)
            
            if "error" in result:
                st.error(result["error"])
            else:
                st.success("تم سحب بيانات المنتج بنجاح!")
                
                original_price = result['price']
                if commission_type == "مبلغ ثابت (ريال)":
                    final_price = original_price + commission_value
                else:
                    final_price = original_price + (original_price * (commission_value / 100))
                
                st.write("---")
                st.subheader(result['title'])
                
                price_col1, price_col2 = st.columns(2)
                price_col1.metric("السعر من المورد", f"{original_price:.2f} SAR")
                price_col2.metric("السعر النهائي للعميل", f"{final_price:.2f} SAR", delta=f"ربحك: {(final_price - original_price):.2f} SAR")
                
                with st.expander("📝 عرض وصف المنتج", expanded=True):
                    st.write(result['description'] if result['description'] else "لا يوجد وصف مرفق مع هذا المنتج.")
                
                st.subheader("📸 صور المنتج")
                if result['images']:
                    cols = st.columns(3)
                    for i, img_url in enumerate(result['images']):
                        cols[i % 3].image(img_url, use_container_width=True)
                else:
                    st.warning("لم يتم العثور على صور واضحة لهذا المنتج.")
                
                st.write("---")
                if st.button("🛒 إضافة المنتج إلى متجر سوق مدار", type="primary", use_container_width=True):
                    st.info("البيانات جاهزة! سيتم تفعيل هذا الزر قريباً لرفع (العنوان، السعر النهائي، الوصف، والصور) دفعة واحدة إلى Salla API.")
                    
