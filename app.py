import streamlit as st
import requests
import re
import json

st.set_page_config(page_title="سوق مدار", page_icon="🚀", layout="centered")
st.sidebar.title("محلك - سوق مدار")

option = st.sidebar.title("👋 لوحة تحكم سوق مدار")

st.info("💡 لتجنب حظر سيرفرات ترينديول، جلب البيانات يتم الآن عبر كود الصفحة المباشر لضمان استقرار الأسعار بالريال السعودي 100%.")

# خانات الإدخال الأساسية
new_name = st.text_input("اسم المنتج")
sku = st.text_input("رمز المنتج (SKU)")
price_sar = st.number_input("السعر الأصلي في ترينديول (بالريال السعودي)", min_value=0.0, value=0.0, step=1.0)
image_url = st.text_input("رابط صورة المنتج")

st.write("---")

# الحساب المالي والعمولة
comm = st.number_input("هامش ربحك وعمولتك لمتجرك (%)", min_value=0.0, value=15.0, step=1.0)
final_price = price_sar * (1 + (comm / 100))

st.metric(label="السعر النهائي للرفع إلى سلة", value=f"{final_price:.2f} SAR")

salla_token = st.text_input("Salla Token", type="password", placeholder="ضع الـ Token الخاص بمتجرك هنا...")

if st.button("رفع المنتج فوراً إلى سلة"):
    if salla_token and price_sar > 0:
        with st.spinner("جاري التصدير لمتجرك في سلة..."):
            headers = {"Authorization": f"Bearer {salla_token}", "Content-Type": "application/json"}
            payload = {
                "name": new_name if new_name else "منتج ترينديول جديد",
                "price": round(final_price, 2),
                "quantity": 10,
                "sku": sku if sku else "TR-100",
                "images": [{"url": image_url if image_url else "https://images.unsplash.com/photo-1523381210434-271e8be1f52b"}]
            }
            res = requests.post("https://api.salla.dev/admin/v2/products", headers=headers, json=payload)
            if res.status_code in [200, 201]: 
                st.success("✅ مبروك! المنتج نزل في متجرك على سلة بالسعر وعمولتك الجديدة!")
            else: 
                st.error(f"فشل الرفع: {res.text}")
    else:
        st.error("الرجاء التأكد من كتابة السعر الأصلي ووضع الـ Salla Token أولاً.")
