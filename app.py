import streamlit as st
import requests
from bs4 import BeautifulSoup
import json
import re

# إعدادات واجهة النظام
st.set_page_config(page_title="مستخرج منتجات ترينديول", layout="centered")
st.title("🇹🇷 نظام جلب منتجات ترينديول الذكي")
st.write("حدد عمولتك واجلب البيانات حية فوراً. ضع رابط المنتج من Trendyol.")

# دالة الجلب البرمجية الخاصة بترينديول
def fetch_trendyol_product(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return {"error": f"فشل الاتصال بالموقع. كود الخطأ: {response.status_code}"}
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # البحث عن بيانات المنتج المخفية
        script_tags = soup.find_all('script', type='application/ld+json')
        product_data = None
        
        for script in script_tags:
            if '"@type": "Product"' in script.string or '"@type":"Product"' in script.string:
                try:
                    product_data = json.loads(script.string)
                    break
                except:
                    continue
        
        if product_data:
            title = product_data.get("name", "عنوان غير متوفر")
            
            # استخراج السعر
            offers = product_data.get("offers", {})
            if isinstance(offers, list):
                offers = offers[0]
            price = float(offers.get("price", 0.0))
            currency = offers.get("priceCurrency", "TRY")
            
            # استخراج الصور
            images = product_data.get("image", [])
            image_url = images[0] if isinstance(images, list) and images else images
            
            return {
                "title": title,
                "price": price,
                "currency": currency,
                "image_url": image_url
            }
        else:
            return {"error": "لم نتمكن من العثور على بيانات المنتج. تأكد من أن الرابط لمنتج محدد."}
            
    except Exception as e:
        return {"error": f"حدث خطأ أثناء الجلب: {str(e)}"}

# واجهة المستخدم التفاعلية
st.write("---")
product_url = st.text_input("🔗 ألصق رابط منتج ترينديول هنا:")
commission = st.number_input("💰 حدد قيمة عمولتك المتغيرة لهذا المنتج (بالريال):", min_value=0.0, value=20.0, step=1.0)

if st.button("🚀 جلب وتسعير المنتج حياً"):
    if not product_url:
        st.warning("الرجاء وضع الرابط أولاً.")
    elif "trendyol.com" not in product_url:
        st.error("الرابط المدخل لا يبدو أنه ينتمي لموقع ترينديول.")
    else:
        with st.spinner("جاري جلب البيانات من المورد..."):
            result = fetch_trendyol_product(product_url)
            
            if "error" in result:
                st.error(result["error"])
            else:
                st.success("تم جلب البيانات بنجاح!")
                
                # تقسيم الشاشة لعرض الصورة بجانب التفاصيل
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    if result["image_url"]:
                        st.image(result["image_url"], use_container_width=True)
                    else:
                        st.write("لا توجد صورة")
                        
                with col2:
                    st.subheader(result["title"])
                    st.write(f"**السعر الأصلي للمورد:** {result['price']} {result['currency']}")
                    
                    # يمكنك لاحقاً إضافة كود لتحويل العملة من الليرة إلى الريال قبل إضافة العمولة
                    final_price = result['price'] + commission 
                    st.info(f"**السعر النهائي للعميل:** {final_price}")
                    
                st.write("---")
                # زر الإضافة المستقبلي
                if st.button("🛒 إضافة المنتج إلى المتجر (قريباً)"):
                    st.info("سيتم تفعيل هذا الزر لاحقاً لرفع المنتج أوتوماتيكياً عبر Salla API.")
