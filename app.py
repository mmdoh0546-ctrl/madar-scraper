import streamlit as st
import requests
import re
import json

# إعدادات واجهة سوق مدار
st.set_page_config(page_title="سوق مدار", page_icon="🚀", layout="centered")
st.title("🚀 لوحة تحكم سوق مدار (استخراج المنتجات)")

st.sidebar.title("محلك - سوق مدار")
option = st.sidebar.radio("القائمة الرئيسية", ["إضافة منتج ترينديول"])

st.info("💡 طريقة العمل: الصق كود الصفحة (HTML) أو نص المنتج بالأسفل، واضغط على جلب لاستخراج البيانات. حقول العمولة والرفع لـ سلة ستظهر لك في الأسفل بعد نجاح الجلب.")

# الخطوة 1: صندوق جلب واستخراج المنتج فقط
html_input = st.text_area("الصق كود الصفحة (HTML) أو نص المنتج هنا:", height=150, placeholder="افتح المنتج في متصفحك، انسخ كود الصفحة أو تفاصيلها وضعه هنا...")

# زر الجلب والاستخراج (لا يرفع شيئاً لـ سلة)
if st.button("جلب بيانات المنتج واستخراجها 🔍"):
    if html_input:
        with st.spinner("جاري قراءة البيانات المستلمة وفحصها..."):
            # البحث عن الهيكل البرمجي لترينديول
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
                    
                    st.session_state['product_ready'] = {
                        "name": f"{brand} {name}".strip(),
                        "sku": sku,
                        "price_sar": float(price_sar),
                        "image": image_url
                    }
                    st.success("🎯 تم جلب واستخراج بيانات المنتج بنجاح! انزل لأسفل الصفحة للتحكم بالعمولة والرفع.")
                except Exception as e:
                    st.error("فشل قراءة الكود، يرجى التأكد من نسخه بالكامل.")
            else:
                # خطة مرنة إذا تم لصق نص عادي يحتوي على اسم وسعر
                prices = re.findall(r"\d+\.\d+|\d+", html_input)
                clean_name = re.sub(r"http\S+", "", html_input).strip()
                clean_name = clean_name.replace("SAR", "").replace("ريال", "").strip()
                
                if prices:
                    extracted_price = float(prices[0])
                    for p in prices:
                        clean_name = clean_name.replace(p, "").strip()
                    
                    st.session_state['product_ready'] = {
                        "name": clean_name if clean_name else "منتج ترينديول جديد",
                        "sku": "TR-" + str(extracted_price).replace('.', ''),
                        "price_sar": extracted_price,
                        "image": "https://images.unsplash.com/photo-1523381210434-271e8be1f52b"
                    }
                    st.success("🎯 تم استخراج الاسم والسعر بنجاح! الحقول جاهزة بالأسفل.")
                else:
                    st.error("لم نجد بيانات واضحة. يرجى لصق كود الصفحة بالكامل أو نص يحتوي على السعر.")
    else:
        st.warning("الرجاء لصق الكود أو النص أولاً ليتمكن النظام من الجلب.")

# --- الخطوة 2: أسفل صفحة استخراج المنتج (تظهر فقط بعد نجاح الجلب) ---
if 'product_ready' in st.session_state:
    data = st.session_state['product_ready']
    st.write("---")
    st.subheader("📋 مراجعة المنتج وتحديد العمولة قبل الرفع")
    
    if data["image"]:
        st.image(data["image"], width=130, caption="صورة المنتج المستخرجة")
        
    # حقول التعديل والمراجعة
    new_name = st.text_input("اسم المنتج (يمكنك تعريبه وتعديله هنا)", value=data["name"])
    sku = st.text_input
    
