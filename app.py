import streamlit as st
import requests
import re

st.set_page_config(page_title="سوق مدار", page_icon="🚀", layout="centered")
st.sidebar.title("محلك - سوق مدار")

option = st.sidebar.radio(
    "القائمة الرئيسية",
    ["اللوحة الرئيسية", "إضافة منتج ترينديول", "إضافة منتج أمازون", "إضافة منتج نون", "إضافة منتج شي إن", "إضافة منتج نمشي"]
)

def scrape_trendyol_saudi(url):
    try:
        # استخراج رقم المنتج بدقة بناءً على الرابط الذي أرسلته يا ممدوح
        match = re.search(r"-p-(\d+)", url)
        if not match:
            return {"error": "تأكد من أن الرابط يحتوي على معرف المنتج الصحيح المسبوق بـ (-p-)"}
            
        product_id = match.group(1)
        
        # رابط الـ API الرسمي والمباشر للمنتجات
        api_url = f"https://public-mdc.trendyol.com/discovery-web-product-service/api/productDetail/{product_id}"
        
        # الترويسات السحرية لإجبار السيرفر على إرسال البيانات بالريال السعودي وبكامل التفاصيل
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "ar-SA,ar;q=0.9",
            "x-currency": "SAR",
            "x-countrycode": "SA",
            "x-languagecode": "ar"
        }
        
        response = requests.get(api_url, headers=headers, timeout=12)
        
        if response.status_code == 200:
            data = response.json()
            result_data = data.get("result", {})
            
            if not result_data:
                return {"error": "لم نجد بيانات لهذا المنتج، قد يكون غير متوفر حالياً."}
                
            name = result_data.get("name", "منتج ترينديول")
            brand = result_data.get("brand", {}).get("name", "")
            sku = str(result_data.get("id", product_id))
            
            # جلب السعر بالريال السعودي مباشرة من الـ API
            price_info = result_data.get("price", {})
            price_sar = price_info.get("discountedPrice", {}).get("value")
            if not price_sar:
                price_sar = price_info.get("sellingPrice", {}).get("value", 0)
                
            # جلب الصورة الأساسية للمنتج
            images = result_data.get("images", [])
            image_url = "https://cdn.dsmcdn.com" + images[0] if images else "https://images.unsplash.com/photo-1523381210434-271e8be1f52b"
            
            return {
                "name": f"{brand} {name}".strip(),
                "sku": sku,
                "price_sar": float(price_sar),
                "image": image_url,
                "error": None
            }
        else:
            return {"error": f"تعذر جلب البيانات من المورد. كود الخطأ: {response.status_code}"}
            
    except Exception as e:
        return {"error": f"حدث خطأ برمي غير متوقع: {str(e)}"}

if option == "اللوحة الرئيسية":
    st.title("👋 لوحة تحكم سوق مدار")
    st.write("اختر المنصة من القائمة الجانبية للبدء.")

elif option in ["إضافة منتج ترينديول", "إضافة منتج أمازون", "إضافة منتج نون", "إضافة منتج شي إن", "إضافة منتج نمشي"]:
    platform_name = option.replace("إضافة منتج ", "")
    st.title(f"محلك - {platform_name} 🛒")
    
    product_url = st.text_input("رابط المنتج من ترينديول السعودية")
    
    if st.button("جلب البيانات 🔍"):
        if product_url:
            with st.spinner("جاري قراءة الرابط وسحب السعر بالريال السعودي..."):
                if platform_name == "ترينديول":
                    result = scrape_trendyol_saudi(product_url)
                else:
                    result = {"name": "تجريبي", "sku": "123", "price_sar": 100.0, "image": "https://images.unsplash.com/photo-1523381210434-271e8be1f52b", "error": None}
                
                if result.get("error"):
                    st.error(result["error"])
                else:
                    st.session_state['scraped_data'] = result
                    st.success("تم جلب تفاصيل المنتج بنجاح باهر!")
        else:
            st.warning("الرجاء إدخال الرابط أولاً.")

    if 'scraped_data' in st.session_state:
        data = st.session_state['scraped_data']
        st.write("---")
        st.image(data["image"], width=200)
        
        new_name = st.text_input("الاسم المقترح للمنتج", value=data["name"])
        sku = st.text_input("رمز المنتج (SKU)", value=data["sku"])
        price_sar = data["price_sar"]
        
        st.write(f"💵 السعر الحالي في ترينديول السعودية: **{price_sar:.2f} ريال سعودي**")
        
        comm = st.number_input("هامش ربحك وعمولتك لمتجرك (%)", min_value=0.0, value=15.0, step=1.0)
        
        # حساب السعر النهائي المباشر بالريال
        final_price = price_sar * (1 + (comm / 100))
        
        st.metric(label="السعر النهائي المقترح للرفع إلى سلة", value=f"{final_price:.2f} SAR")
        
        salla_token = st.text_input("Salla Token", type="password", placeholder="ضع الـ Token الخاص بمتجرك هنا...")
        
        if st.button("رفع المنتج فوراً إلى سلة"):
            if salla_token:
                with st.spinner("جاري التصدير لمتجرك..."):
                    headers = {"Authorization": f"Bearer {salla_token}", "Content-Type": "application/json"}
                    payload = {"name": new_name, "price": round(final_price, 2), "quantity": 10, "sku": sku, "images": [{"url": data["image"]}]}
                    res = requests.post("https://api.salla.dev/admin/v2/products", headers=headers, json=payload)
                    if res.status_code in [200, 201]: 
                        st.success("✅ مبروك! المنتج نزل في متجرك على سلة بالسعر وعمولتك الجديدة!")
                    else: 
                        st.error(f"فشل الرفع: {res.text}")
                        
