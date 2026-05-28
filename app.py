import streamlit as st
import requests

st.set_page_config(page_title="سوق مدار - جلب المنتجات", page_icon="🚀", layout="centered")

st.sidebar.title("محلك - سوق مدار")

option = st.sidebar.radio(
    "القائمة الرئيسية",
    ["اللوحة الرئيسية", "إضافة منتج أمازون", "إضافة منتج نون", "إضافة منتج ترينديول", "إضافة منتج شي إن", "إضافة منتج نمشي"]
)

def scrape_product(url, platform):
    return {
        "name": f"منتج تجريبي من {platform}",
        "sku": "134751731",
        "price_sar": 21.75,
        "description": "وصف المنتج المجلوب تلقائياً من المورد.",
        "image": "https://images.unsplash.com/photo-1523381210434-271e8be1f52b"
    }

if option == "اللوحة الرئيسية":
    st.title("👋 أهلاً بك في لوحة تحكم سوق مدار")
    st.write("اختر المنصة من القائمة الجانبية للبدء في جلب المنتجات مباشرة إلى متجرك في سلة.")

elif option in ["إضافة منتج أمازون", "إضافة منتج نون", "إضافة منتج ترينديول", "إضافة منتج شي إن", "إضافة منتج نمشي"]:
    platform_name = option.replace("إضافة منتج ", "")
    st.title(f"محلك - {platform_name} 🛒")
    
    st.info("ينتهي اشتراكك في: 25-04-2028")
    
    st.subheader("بحث عن منتج")
    product_url = st.text_input("رابط المنتج", placeholder="أدخل رابط المنتج هنا...")
    
    if st.button("بحث 🔍"):
        if product_url:
            st.session_state['scraped_data'] = scrape_product(product_url, platform_name)
            st.success("تم جلب بيانات المنتج بنجاح!")
        else:
            st.warning("الرجاء إدخال رابط المنتج أولاً.")

    if 'scraped_data' in st.session_state:
        data = st.session_state['scraped_data']
        st.write("---")
        st.subheader("تفاصيل المنتج المجلوب")
        st.image(data["image"], caption="صورة المنتج المستخرجة", width=200)
        
        new_name = st.text_input("اسم المنتج", value=data["name"])
        sku = st.text_input("رمز المنتج (SKU)", value=data["sku"])
        original_price = st.number_input("السعر الأصلي (بالريال السعودي)", value=data["price_sar"])
        
        commission_percent = st.number_input("العمولة (%)", min_value=0.0, max_value=100.0, value=15.0, step=1.0)
        final_price = original_price * (1 + (commission_percent / 100))
        
        st.write(f"💰 **السعر النهائي بعد إضافة العمولة في متجرك:** {final_price:.2f} ريال سعودي")
        new_description = st.text_area("وصف المنتج", value=data["description"])
        salla_token = st.text_input("رمز وصول سلة (Access Token)", type="password", placeholder="أدخل الـ Token لمتجرك...")
        
        if st.button("➕ إضافة منتج لمتجر سلة"):
            if salla_token:
                with st.spinner("جاري إرسال المنتج إلى متجرك في سلة..."):
                    headers = {
                        "Authorization": f"Bearer {salla_token}",
                        "Content-Type": "application/json"
                    }
                    payload = {
                        "name": new_name,
                        "price": final_price,
                        "quantity": 10,
                        "description": new_description,
                        "sku": sku,
                        "images": [{"url": data["image"]}]
                    }
                    response = requests.post("https://api.salla.dev/admin/v2/products", headers=headers, json=payload)
                    if response.status_code in [200, 201]:
                        st.success("✅ تم نشر المنتج بنجاح في متجرك على سلة!")
                    else:
                        st.error(f"❌ فشل الرفع: {response.text}")
            else:
                st.error("الرجاء إدخال رمز وصول سلة (Access Token).")
