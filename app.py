import streamlit as st
import requests
from bs4 import BeautifulSoup
import re

# إعدادات واجهة النظام
st.set_page_config(page_title="مستخرج منتجات ترنديوول", layout="centered")
st.title("🇹🇷 نظام جلب منتجات ترنديوول الذكي")
st.write("ضع رابط المنتج من Trendyol، حدد عمولتك، واجلب البيانات حية فوراً.")

def fetch_trendyol_product(url):
    # إرسال هيدرز تجعل السيرفر يظن أن الطلب من متصفح حقيقي لتجنب الحظر
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            return {"error": f"فشل الاتصال بالموقع. كود الاستجابة: {response.status_code}"}
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. جلب العنوان من كود الصفحة
        title_element = soup.find('h1', {'class': 'pr-new-br'})
        title = title_element.text.strip() if title_element else "منتج ترنديوول"
        
        # 2. جلب السعر من كود الصفحة
        price_element = soup.find('span', {'class': 'prc-dsc'})
        if not price_element:
            price_element = soup.find('div', {'class': 'product-price'})
            
        if price_element:
            # تنظيف النص لاستخراج الرقم فقط
            price_text = price_element.text.replace('.', '').replace(',', '.')
            price_numbers = re.findall(r"[-+]?\d*\.\d+|\d+", price_text)
            price = float(price_numbers[0]) if price_numbers else 0.0
        else:
            price = 0.0
            
        # 3. جلب رابط الصورة
        img_element = soup.find('img', {'class': 'base-product-image'})
        image_url = img_element['src'] if img_element and 'src' in img_element.attrs else ""
        
        return {
            "title": title,
            "price": price,
            "image_url": image_url
        }
        
    except Exception as e:
        return {"error": f"حدث خطأ أثناء قراءة الرابط: {str(e)}"}

# --- واجهة المستخدم ---
product_url = st.text_input("🔗 ألصق رابط منتج ترنديوول هنا:", "")
commission = st.number_input("💰 حدد قيمة عمولتك المتغيرة لهذا المنتج (بالريال):", min_value=0.0, value=20.0, step=1.0)

if st.button("🚀 جلب وتسعير المنتج حياً"):
    if not product_url:
        st.warning("رجاءً ضع الرابط أولاً!")
    else:
        with st.spinner("جاري جلب البيانات من ترنديوول..."):
            result = fetch_trendyol_product(product_url)
            
            if "error" in result:
                st.error(result["error"])
            else:
                st.success("تم الجلب!")
                st.markdown("---")
                
                # حساب السعر بالريال (سعر الصرف الافتراضي 0.11 لليرة)
                price_in_sar = round(result["price"] * 0.11, 2)
                final_price = price_in_sar + commission
                
                col1, col2 = st.columns()
                with col1:
                    if result["image_url"]:
                        st.image(result["image_url"], use_container_width=True)
                with col2:
                    st.subheader("📋 تفاصيل المنتج:")
                    st.write(f"**الاسم:** {result['title']}")
                    st.write(f"**السعر بالليرة:** {result['price']} TRY")
                    st.write(f"**السعر بالريال:** {price_in_sar} ريال")
                    st.metric(label="💵 السعر النهائي مع عمولتك", value=f"{final_price} ريال")
                    
