import streamlit as st
import requests
import re
import json

st.set_page_config(page_title="سوق مدار", page_icon="🚀", layout="centered")
st.sidebar.title("محلك - سوق مدار")

option = st.sidebar.radio(
    "القائمة الرئيسية",
    ["اللوحة الرئيسية", "إضافة منتج ترينديول", "إضافة منتج أمازون", "إضافة منتج نون", "إضافة منتج شي إن", "إضافة منتج نمشي"]
)

def scrape_trendyol_saudi(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "ar-SA,ar;q=0.9,en-US;q=0.8"
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            return {"error": f"خطأ اتصال: {response.status_code}"}
            
        # البحث عن كود البيانات في الصفحة السعودية
        match = re.search(r"window\.__INITIAL_STATE__\s*=\s*(\{.*?\});", response.text)
        if match:
            data_json = json.loads(match.group(1))
            product_info = data_json.get("product", {})
            
            name = product_info.get("name", "منتج ترينديول")
            brand = product_info.get("brand", {}).get("name", "")
            sku = str(product_info.get("id", "000000"))
            
            # جلب السعر المباشر (وهو بالريال السعودي لأن الرابط سعودي)
            price_sar = product_info.get("price", {}).get("discountedPrice", {}).get("value", 0)
            if not price_sar:
                price_sar = product_info.get("price", {}).get("sellingPrice", {}).get("value", 0)
                
            images = product_info.get("images", [])
            image_url = "https://cdn.dsmcdn.com" + images[0] if images else "https://images.unsplash.com/photo-1523381210434-271e8be1f52b"
            
            return {
                "name": f"{brand} {name}".strip(),
                "sku": sku,
                "price_sar": float(price_sar),
                "image": image_url,
                "error": None
            }
        else:
            return {"error": "لم نتمكن من قراءة هيكل الصفحة السعودية الحالية."}
    except Exception as e:
        return {"error": str(e)}

if option == "اللوحة الرئيسية":
    st.title("👋 لوحة تحكم سوق مدار")
    st.write("اختر المنصة من القائمة الجانبية للبدء.")

elif option in ["إضافة منتج ترينديول", "إضافة منتج أمازون", "إضافة منتج نون", "إضافة منتج شي إن", "إضافة منتج نمشي"]:
    platform_name = option.replace("إضافة منتج ", "")
    st.title(f"محلك - {platform_name} 🛒")
    
    product_url = st.text_input("رابط المنتج من ترينديول السعودية")
    
    if st.button("جلب البيانات 🔍"):
        if product_url:
            with st.spinner("جاري جلب السعر السعودي..."):
                if platform_name == "ترينديول":
                    result = scrape_trendyol_saudi(product_url)
                else:
                    result = {"name": "تجريبي", "sku": "123", "price_sar": 100.0, "image": "https://images.unsplash.com/photo-1523381210434-271e8be1f52b", "error": None}
                
                if result.get("error"):
                    st.error(result["error"])
                else:
                    st.session_state['scraped_data'] = result
                    st.success("تم الجلب بنجاح!")
        else:
            st.warning("أدخل الرابط أولاً.")

    if 'scraped_data' in st.session_state:
        data = st.session_state['scraped_data']
        st.write("---")
        st.image(data["image"], width=200)
        
        new_name = st.text_input("الاسم", value=data["name"])
        sku = st.text_input("SKU", value=data["sku"])
        price_sar = data["price_sar"]
        
        st.write(f"السعر الأصلي على ترينديول: {price_sar:.2f} ريال سعودي")
        
        comm = st.number_input("نسبة عمولتك وهامش ربحك %", min_value=0.0, value=15.0, step=1.0)
        
        # حساب السعر النهائي مباشرة بناءً على السعر السعودي الأصلي
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
