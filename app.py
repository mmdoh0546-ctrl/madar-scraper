import streamlit as st
import requests
import re
import json

# إعدادات الصفحة
st.set_page_config(page_title="سوق مدار - جلب المنتجات", page_icon="🚀", layout="centered")

st.sidebar.title("محلك - سوق مدار")

option = st.sidebar.radio(
    "القائمة الرئيسية",
    ["اللوحة الرئيسية", "إضافة منتج ترينديول", "إضافة منتج أمازون", "إضافة منتج نون", "إضافة منتج شي إن", "إضافة منتج نمشي"]
)

# --- محرك كشط ترينديول الذكي (يدعم الروابط السعودية والتركية) ---
def scrape_trendyol(url):
    try:
        # تنظيف الرابط إذا كان يحتوي على النسخة العربية أو الموجهة للسعودية
        clean_url = url
        if "/ar/" in url:
            clean_url = url.replace("/ar/", "/")
        elif "/en/" in url:
            clean_url = url.replace("/en/", "/")
            
        # إرسال ترويسات تحاكي متصفح حقيقي من داخل تركيا لتجنب الحظر جغرافياً
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "tr-TR,tr;q=0.9",
            "Cookie": "countryCode=TR; languageCode=tr;" # إجبار السيرفر على إعطائنا البيانات التركية الأصلية بالليرة
        }
        
        response = requests.get(clean_url, headers=headers, timeout=15)
        if response.status_code != 200:
            return {"error": f"فشل الاتصال بموقع ترينديول. كود الخطأ: {response.status_code}"}
            
        html_content = response.text
        
        # البحث عن بيانات المنتج داخل كود الصفحة
        match = re.search(r"window\.__INITIAL_STATE__\s*=\s*(\{.*?\});", html_content)
        
        if match:
            data_json = json.loads(match.group(1))
            product_info = data_json.get("product", {})
            
            name = product_info.get("name", "منتج ترينديول")
            brand = product_info.get("brand", {}).get("name", "")
            full_name = f"{brand} {name}".strip()
            
            sku = str(product_info.get("id", "000000"))
            
            # جلب السعر بالليرة التركية
            price_tl = product_info.get("price", {}).get("discountedPrice", {}).get("value", 0)
            if not price_tl:
                price_tl = product_info.get("price", {}).get("sellingPrice", {}).get("value", 0)
                
            # جلب الصور
            images = product_info.get("images", [])
            image_url = "https://cdn.dsmcdn.com" + images[0] if images else "https://images.unsplash.com/photo-1523381210434-271e8be1f52b"
            
            # الوصف أو الخصائص
            attributes = product_info.get("attributes", [])
            desc = "🛡️ منتج أصلي من ترينديول تركيا.\n\nالمواصفات:\n"
            for attr in attributes:
                key = attr.get("key", {}).get("name", "")
                val = attr.get("value", {}).get("name", "")
                if key and val:
                    desc += f"- {key}: {val}\n"
            
            return {
                "name": full_name,
                "sku": sku,
                "price_tl": float(price_tl),
                "description": desc,
                "image": image_url,
                "error": None
            }
        else:
            return {"error": "لم نتمكن من قراءة هيكل الصفحة. ترينديول يفرض حماية مؤقتة، جرب رابط منتج آخر أو أعد المحاولة بعد ثوانٍ."}
            
    except Exception as e:
        return {"error": f"حدث خطأ غير متوقع: {str(e)}"}

# --- محاكاة باقي المنصات مؤقتاً ---
def scrape_placeholder(url, platform):
    return {
        "name": f"منتج تجريبي من {platform}",
        "sku": "134751731",
        "price_tl": 150.0,
        "description": "وصف افتراضي للمنصات الأخرى.",
        "image": "https://images.unsplash.com/photo-1523381210434-271e8be1f52b",
        "error": None
    }

# --- واجهات الصفحات ---
if option == "اللوحة الرئيسية":
    st.title("👋 أهلاً بك في لوحة تحكم سوق مدار")
    st.write("اختر المنصة من القائمة الجانبية للبدء في جلب المنتجات الحقيقية مباشرة إلى متجرك في سلة.")

elif option in ["إضافة منتج ترينديول", "إضافة منتج أمازون", "إضافة منتج نون", "إضافة منتج شي إن", "إضافة منتج نمشي"]:
    platform_name = option.replace("إضافة منتج ", "")
    st.title(f"محلك - {platform_name} 🛒")
    st.info("ينتهي اشتراكك في: 25-04-2028")
    
    st.subheader("بحث عن منتج برابط مباشر")
    product_url = st.text_input("رابط المنتج", placeholder="أدخل رابط المنتج هنا...")
    
    if st.button("جلب البيانات الحقيقية 🔍"):
        if product_url:
            with st.spinner("جاري كشط وفحص البيانات وتحويل العملة من تركيا..."):
                if platform_name == "ترينديول":
                    result = scrape_trendyol(product_url)
                else:
                    result = scrape_placeholder(product_url, platform_name)
                
                if result.get("error"):
                    st.error(result["error"])
                else:
                    st.session_state['scraped_data'] = result
                    st.success("تم جلب وتجهيز بيانات ترينديول الحقيقية بنجاح!")
        else:
            st.warning("الرجاء إدخال رابط المنتج أولاً.")

    # عرض البيانات والتعديل عليها
    if 'scraped_data' in st.session_state:
        data = st.session_state['scraped_data']
        st.write("---")
        st.subheader("📋 البيانات المستخرجة من تركيا")
        
        st.image(data["image"], caption="صورة المنتج الأساسية", width=200)
        
        new_name = st.text_input("اسم المنتج (يمكنك تعديله وتعريبه)", value=data["name"])
        sku = st.text_input("رمز المنتج (SKU)", value=data["sku"])
        
        price_tl = data["price_tl"]
        st.write(f"💵 السعر الأصلي في تركيا: **{price_tl:.2f} ليرة تركية**")
        
        # حقول الحساب المالي والتحويل للريال
        st.subheader("💰 الحساب المالي والعمولة")
        col1, col2 = st.columns(2)
        with col1:
            exchange_rate = st.number_input("سعر صرف الليرة التركية مقابل الريال", value=0.11, format="%.3f")
        with col2:
            commission_percent = st.number_input("هامش ربحك وعمولتك (%)", min_value=0.0, value=20.0, step=1.0)
            
        # تحويل العملة وحساب السعر النهائي
        price_in_sar = price_tl * exchange_rate
        final_price_sar = price_in_sar * (1 + (commission_percent / 100))
        
        st.metric(label="السعر النهائي المقترح لمتجرك
