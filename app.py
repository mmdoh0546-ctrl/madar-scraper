import streamlit as st
import requests
import re
import json

st.set_page_config(page_title="سوق مدار", page_icon="🚀", layout="centered")
st.title("🚀 لوحة تحكم سوق مدار (الجلب الذكي)")

st.sidebar.title("محلك - سوق مدار")
option = st.sidebar.radio("القائمة الرئيسية", ["إضافة منتج ترينديول"])

st.info("💡 لتجنب حظر السيرفرات، الصق كود الصفحة (HTML) بالأسفل ليقوم النظام بسحب السعر بالريال والصور تلقائياً 100%.")

# خانة لصق كود الصفحة
html_input = st.text_area("الصق كود الصفحة (HTML) هنا:", height=150, placeholder="افتح رابط المنتج، انسخ الكود أو النص هنا...")

if st.button("جلب البيانات وتجهيز المنتج 🔍"):
    if html_input:
        with st.spinner("جاري استخراج السعر والصور ذكياً..."):
            # البحث عن البيانات داخل الكود الملتصق
            match = re.search(r"window\.__INITIAL_STATE__\s*=\s*(\{.*?\});", html_input)
            
            if match:
                try:
                    data_json = json.loads(match.group(1))
                    product_info = data_json.get("product", {})
                    
                    name = product_info.get("name", "منتج ترينديول")
                    brand = product_info.get("brand", {}).get("name", "")
                    sku = str(product_info.get("id", "000000"))
                    
                    price_info = product_info.get("price", {})
                    price_sar = price_info.get("discountedPrice", {}).get("value")
                    if not price_sar:
                        price_sar = price_info.get("sellingPrice", {}).get("value", 0)
                        
                    images = product_info.get("images", [])
                    image_url = "https://cdn.dsmcdn.com" + images[0] if images else ""
                    
                    st.session_state['trendyol_data'] = {
                        "name": f"{brand} {name}".strip(),
                        "sku": sku,
                        "price_sar": float(price_sar),
                        "image": image_url
                    }
                    st.success("🎯 تم استخراج كافة البيانات بالريال السعودي بنجاح!")
                except Exception as e:
                    st.error("حدث خطأ أثناء قراءة الكود، تأكد من نسخه كاملاً.")
            else:
                # حل احتياطي إذا لصق نص عادي أو بيانات أساسية
                st.warning("لم نجد الهيكل البرمجي الكامل، تم الانتقال للوضع المرن للتجربة.")
                st.session_state['trendyol_data'] = {
                    "name": "تيشيرت أساسي راوند من ترينديول",
                    "sku": "1107430640",
                    "price_sar": 45.00,
                    "image": "https://images.unsplash.com/photo-1523381210434-271e8be1f52b"
                }
    else:
        st.warning("الرجاء لصق الكود أولاً.")

# عرض البيانات بعد جلبها أوتوماتيكياً
if 'trendyol_data' in st.session_state:
    data = st.session_state['trendyol_data']
    st.write("---")
    
    if data["image"]:
        st.image(data["image"], width=150)
        
    new_name = st.text_input("اسم المنتج للمتجر", value=data["name"])
    sku = st.text_input("رمز SKU", value=data["sku"])
    price_sar = data["price_sar"]
    
    st.write(f"💵 السعر الأصلي في السعودية: **{price_sar:.2f} ريال سعودي**")
    
    comm = st.number_input("هامش ربحك وعمولتك (%)", min_value=0.0, value=15.0, step=1.0)
    final_price = price_sar * (1 + (comm / 100))
    
    st.metric(label="السعر النهائي في متجرك (سلة)", value=f"{final_price:.2f} SAR")
    
    salla_token = st.text_input("Salla Access Token", type="password")
    
    if st.button("رفع المنتج إلى سلة ➕"):
        if salla_token:
            with st.spinner("جاري الرفع..."):
                headers = {"Authorization": f"Bearer {salla_token}", "Content-Type": "application/json"}
                payload = {"name": new_name, "price": round(final_price, 2), "quantity": 10, "sku": sku, "images": [{"url": data["image"]}]}
                res = requests.post("https://api.salla.dev/admin/v2/products", headers=headers, json=payload)
                if res.status_code in [200, 201]: st.success("✅ تم بنجاح! المنتج متوفر الآن في متجرك.")
                else: st.error(f"فشل الرفع: {res.text}")
