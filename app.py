import streamlit as st
import requests
from bs4 import BeautifulSoup
import json
import re

# إعدادات واجهة النظام
st.set_page_config(page_title="مستخرج منتجات ترنديوول", layout="centered")
st.title("🇹🇷 نظام جلب منتجات ترنديوول الذكي")
st.write("ضع رابط المنتج من Trendyol، حدد عمولتك، واجلب البيانات حية فوراً.")

# دالة الجلب البرمجية الخاصة بترنديوول
def fetch_trendyol_product(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7" # لإقناع الموقع أن الطلب طبيعي
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return {"error": f"فشل الاتصال بالموقع. كود الخطأ: {response.status_code}"}
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # البحث عن بيانات المنتج المخفية داخل الـ Scripts (تقنية سريعة ومستقرة جداً لترنديوول)
        script_tags = soup.find_all('script', type='application/ld+json')
        
        product_data = None
        for script in script_tags:
            if '"@type": "Product"' in script.string:
                product_data = json.loads(script.string)
                break
                
        if product_data:
            # استخراج البيانات الأساسية
            title = product_data.get("name", "عنوان غير متوفر")
            # استخراج السعر وتحويله لرقم عشري
            price = float(product_data.get("offers", {}).get("price", 0))
            currency = product_data.get("offers", {}).get("priceCurrency", "TRY")
            # استخراج الصور (يأخذ الصورة الأولى كصورة رئيسية)
            images = product_data.get("image", [])
            image_url = images[0] if isinstance(images, list) and images else images
            
            return {
                "title": title,
                "price": price,
                "currency": currency,
                "image_url": image_url
            }
        else:
            # طريقة احتياطية في حال لم تتوفر البيانات المخفية
            title_tag = soup.find('h1', {'class': 'pr-new-br'})
            price_tag = soup.find('span', {'class': 'prc-dsc'})
            img_tag = soup.find('img', {'class': 'base-product-image'})
            
            if title_tag:
                return {
                    "title": title_tag.text.strip(),
                    "price": float(re.sub(r'[^\d.]', '', price_tag.text.replace(',', '.'))) if price_tag else 0.0,
                    "currency": "TRY",
                    "image_url": img_tag['src'] if img_tag else ""
                }
            
            return {"error": "لم نتمكن من العثور على بيانات المنتج. تأكد من أن الرابط لمنتج محدد وليس لقسم."}
            
    except Exception as e:
        return {"error": f"حدث خطأ أثناء الجلب: {str(e)}"}

# --- واجهة المستخدم التفاعلية ---

# 1. المدخلات
product_url = st.text_input("🔗 ألصق رابط منتج ترنديوول هنا:", "")
commission = st.number_input("💰 حدد قيمة عمولتك المتغيرة لهذا المنتج (بالريال):", min_value=0.0, value=20.0, step=1.0)

# 2. زر المعالجة
if st.button("🚀 جلب وتسعير المنتج حياً"):
    if not product_url:
        st.warning("رجاءً ضع الرابط أولاً!")
    elif "trendyol.com" not in product_url:
        st.error("الرابط المدخل لا يبدو أنه ينتمي لموقع ترنديوول!")
    else:
        with st.spinner("جاري الاتصال بترنديوول وسحب البيانات الفيدرالية للمنتج..."):
            result = fetch_trendyol_product(product_url)
            
            if "error" in result:
                st.error(result["error"])
            else:
                st.success("تم جلب البيانات الحقيقية بنجاح!")
                st.markdown("---")
                
                # حساب السعر النهائي (ملاحظة: سعر ترنديوول الأصلي بالليرة التركية TRY)
                original_price_try = result["price"]
                
                # هنا يمكنك مستقبلاً وضع سعر الصرف الفعلي للريال (كمثال نفترض 1 ليرة = 0.11 ريال)
                price_in_sar = round(original_price_try * 0.11, 2) 
                final_price = price_in_sar + commission
                
                # 3. عرض النتائج المستخرجة حياً
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    if result["image_url"]:
                        st.image(result["image_url"], caption="الصورة الأصلية من ترنديوول", use_container_width=True)
                    else:
                        st.warning("لم يتم العثور على صورة")
                
                with col2:
                    st.subheader("📋 البيانات المستخرجة:")
                    st.write(f"**الاسم الأصلي:** {result['title']}")
                    st.write(f"**السعر في ترنديوول:** {original_price_try} {result['currency']}")
                    st.write(f"**السعر التقريبي بالريال السعودي:** {price_in_sar} ريال")
                    st.info(f"**عمولتك المحددة:** {commission} ريال")
                    st.metric(label="💵 السعر النهائي المقترح للبيع في سلة", value=f"{final_price} ريال")
                
                st.markdown("---")
                st.button("➕ إضافة المنتج إلى متجر سلة (جاهز للربط المستقبلي)")
