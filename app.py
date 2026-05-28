import streamlit as st
import requests
import re

st.set_page_config(page_title="سوق مدار", page_icon="🚀", layout="centered")
st.sidebar.title("محلك - سوق مدار")

option = st.sidebar.radio(
    "القائمة الرئيسية",
    ["اللوحة الرئيسية", "إضافة منتج ترينديول", "إضافة منتج أمازون", "إضافة منتج نون", "إضافة منتج شي إن", "إضافة منتج نمشي"]
)

def scrape_trendyol_api(url):
    try:
        # استخراج رقم المنتج (ID) الذكي من الرابط السعودي
        match_id = re.search(r"-p-(\d+)", url)
        if not match_id:
            # محاولة أخرى إذا كان الرابط بصيغة مختلفة
            match_id = re.search(r"/(\d+)\?", url)
            
        if not match_id:
            return {"error": "لم نتمكن من العثور على رقم المنتج في الرابط. تأكد من نسخ رابط منتج صحيح."}
            
        product_id = match_id.group(1)
        
        # استدعاء الـ API المباشر لترينديول (النسخة الدولية المخصصة للخليج)
        api_url = f"https://public-mdc.trendyol.com/discovery-web-product-service/api/productDetail/{product_id}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept-Language": "ar-SA"
        }
        
        response = requests.get(api_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            content = data.get("result", {})
            
            name = content.get("name", "منتج ترينديول")
            brand = content.get("brand", {}).get("name", "")
            sku = str(content.get("id", product_id))
            
            # جلب السعر السعودي المباشر من الـ API
            price_info = content.get("price", {})
            price_sar = price_info.get("discountedPrice", {}).get("value")
            if not price_sar:
                price_sar = price_info.get("sellingPrice", {}).get("value", 0)
            
            # جلب الصور
            images = content.get("images", [])
            image_url = "https://cdn.dsmcdn.com" + images[0] if images else "https://images.unsplash.com/photo-1523381210434-271e8be1f52b"
            
            return {
                "name": f"{brand} {name}".strip(),
                "sku": sku,
                "price_sar": float(price_sar),
                "image": image_url,
                "error": None
            }
        else:
            return {"error": f"ترينديول رفض الطلب السريع. كود الخطأ: {response.status_code}"}
            
    except Exception as e:
        return {"error": f"حدث خطأ أثناء الاتصال بالـ API: {str(e)}"}

if option == "اللوحة الرئيسية":
    st.title("👋 لوحة تحكم سوق مدار")
    st.write("اختر المنصة من القائمة الجانبية للبدء.")

elif option in ["إضافة منتج ترينديول", "إضافة منتج أمازون", "إضافة منتج نون", "إضافة منتج شي إن", "إضافة منتج نمشي"]:
    platform_name = option.replace("إضافة منتج ", "")
    st.title(f"محلك - {platform_name} 🛒")
    
    product_url = st.text_input("رابط المنتج من ترينديول السعودية")
    
    if st.button("جلب البيانات 🔍"):
        if product_url:
            with st.spinner("جاري سحب السعر السعودي عبر الـ API الحقيقي..."):
                if platform_name == "ترينديول":
                    result = scrape_trendyol_api(product_url)
                else:
                    result = {"name": "تجريبي", "sku": "123", "price_sar": 100.0, "image": "https://images.unsplash.com/photo-1523381210434-271e8be1f52b", "error": None}
                
                if result.get("error"):
                    st.error(result["error"])
                else:
                    st.session_state['scraped_data'] = result
                    st.success("تم الجلب بنجاح تام!")
        else:
            st.warning("أدخل الرابط أولاً.")

    if 'scraped_data' in st.session_state:
        data = st.session_state['scraped_data']
        st.write("---")
        st.image(data["image"], width=200)
        
        new_name = st.text_input("الاسم", value=data["name"])
        sku = st.text_input("SKU", value=data["sku"])
        price_sar = data["price_sar"]
        
        st.write(f"السعر الحقيقي على ترينديول السعودية: {price_sar:.2f} ريال سعودي")
        
        comm = st.number_input("نسبة عمولتك وهامش ربحك %", min_value=0.0, value=15.0, step=1.0)
        
        final_price = price_sar * (1 + (comm / 100))
        
        st.metric(label="السعر النهائي لمتجرك في سلة", value=f"{final_price:.2f} SAR")
        
        salla_token = st.text_input("Salla Token", type="password")
        
        if st.button("رفع إلى سلة"):
            if salla_token:
                with st.spinner("جاري الرفع..."):
                    headers = {"Authorization": f"Bearer {salla_token}", "Content-Type": "application/json"}
                    payload = {"name": new_name, "price": round(final_price, 2), "quantity": 10, "sku": sku, "images": [{"url": data["image"]}]}
                    res = requests.post("https://api.salla.dev/admin/v2/products", headers=headers, json=payload)
                    if res.status_code in [200, 201]: st.success("تم الرفع بنجاح!")
                    else: st.error(f"فشل الرفع: {res.text}")
