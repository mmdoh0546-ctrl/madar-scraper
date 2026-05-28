import streamlit as st
import requests
import re
import json

# إعدادات واجهة سوق مدار
st.set_page_config(page_title="سوق مدار", page_icon="🚀", layout="centered")
st.title("🚀 لوحة تحكم سوق مدار (الجلب الأوتوماتيكي المتكامل)")

st.sidebar.title("محلك - سوق مدار")
option = st.sidebar.radio("القائمة الرئيسية", ["إضافة منتج ترينديول"])

st.info("💡 ضع رابط المنتج بالأسفل واضغط جلب. سيقوم النظام بسحب الاسم، السعر بالريال، الصور، والوصف تلقائياً، وتظهر لك خيارات العمولة والرفع لـ سلة في الأسفل.")

# الخطوة 1: صندوق جلب واستخراج المنتج بالرابط تلقائياً
input_url = st.text_input("ضع رابط منتج ترينديول السعودية هنا:", placeholder="https://www.trendyol.com/ar/...")

if st.button("جلب وتجهيز بيانات المنتج أوتوماتيكياً 🔍"):
    if input_url:
        with st.spinner("جاري كسر الحظر وسحب الأسعار، الصور، والوصف تلقائياً..."):
            # استخراج رقم المنتج من الرابط
            match = re.search(r"-p-(\d+)", input_url)
            if not match:
                st.error("تأكد من أن الرابط يحتوي على رقم المنتج المسبوق بـ -p-")
            else:
                product_id = match.group(1)
                
                # رابط الجلب البديل والمفتوح لبيانات الشرق الأوسط
                api_url = f"https://public-mdc.trendyol.com/discovery-web-product-service/api/productDetail/{product_id}"
                
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "application/json",
                    "x-currency": "SAR",
                    "x-countrycode": "SA",
                    "x-languagecode": "ar"
                }
                
                try:
                    response = requests.get(api_url, headers=headers, timeout=12)
                    if response.status_code == 200:
                        res_json = response.json()
                        result = res_json.get("result", {})
                        
                        if result:
                            name = result.get("name", "منتج ترينديول")
                            brand = result.get("brand", {}).get("name", "")
                            sku = str(result.get("id", product_id))
                            
                            # جلب السعر بالريال
                            price_info = result.get("price", {})
                            price_sar = price_info.get("discountedPrice", {}).get("value")
                            if not price_sar:
                                price_sar = price_info.get("sellingPrice", {}).get("value", 0)
                            
                            # جلب جميع الصور المتوفرة (ألبوم الصور)
                            images = result.get("images", [])
                            full_images_urls = []
                            for img in images:
                                if img.startswith("http"):
                                    full_images_urls.append({"url": img})
                                else:
                                    full_images_urls.append({"url": "https://cdn.dsmcdn.com" + img})
                            
                            main_image = full_images_urls[0]["url"] if full_images_urls else ""
                            
                            # جلب الوصف وتفاصيل المنتج
                            descriptions = result.get("descriptions", [])
                            desc_text = ""
                            if descriptions:
                                desc_text = descriptions[0].get("text", "")
                            else:
                                # إذا لم يتوفر وصف، نجمع الخصائص كـ وصف للمنتج
                                attributes = result.get("attributes", [])
                                desc_text = "تفاصيل المنتج:\n" + "\n".join([f"- {attr.get('key', {}).get('name', '')}: {attr.get('value', {}).get('name', '')}" for attr in attributes])

                            # حفظ البيانات بالكامل في مخزن الحالة
                            st.session_state['product_loaded'] = True
                            st.session_state['p_name'] = f"{brand} {name}".strip()
                            st.session_state['p_sku'] = sku
                            st.session_state['p_price'] = float(price_sar)
                            st.session_state['p_image'] = main_image
                            st.session_state['p_all_images'] = full_images_urls
                            st.session_state['p_desc'] = desc_text
                            st.success("🎯 تم جلب المنتج بالكامل بالصور والوصف! راجع البيانات بالأسفل.")
                        else:
                            st.error("لم نتمكن من قراءة تفاصيل المنتج، تأكد من أن المنتج متاح في السعودية.")
                    else:
                        st.error(f"عذراً، سيرفر ترينديول مشغول حالياً (كود {response.status_code}). جرب رابط منتج آخر.")
                except Exception as e:
                    st.error(f"حدث خطأ أثناء الاتصال بالشبكة: {str(e)}")
    else:
        st.warning("الرجاء وضع رابط المنتج أولاً.")

# --- الخطوة 2: تظهر بالأسفل تلقائياً بعد نجاح الجلب المتكامل ---
if st.session_state.get('product_loaded', False):
    st.write("---")
    st.subheader("📋 مراجعة تفاصيل المنتج الكاملة قبل الرفع لـ سلة")
    
    # عرض الصورة الأساسية للتأكيد
    if st.session_state['p_image']:
        st.image(st.session_state['p_image'], width=150, caption="الصورة الأساسية للمنتج")
        
    final_name = st.text_input("اسم المنتج للمتجر (مجلوب تلقائياً ويمكنك تعديله)", value=st.session_state['p_name'])
    final_sku = st.text_input("رمز SKU المنتج", value=st.session_state['p_sku'])
    final_desc = st.text_area("وصف المنتج المستخرج (سيتم رفعه لـ سلة)", value=st.session_state['p_desc'], height=120)
    
    price_sar = st.session_state['p_price']
    st.info(f"💵 السعر الأصلي المستخرج من ترينديول: {price_sar:.2f} ريال سعودي")
    
    # مربع العموله وحساب السعر النهائي
    comm = st.number_input("ضع نسبة عمولتك وهامش ربحك هنا (%)", min_value=0.0, value=15.0, step=1.0)
    final_price = price_sar * (1 + (comm / 100))
    st.metric(label="💰 السعر النهائي الذي سيظهر في متجرك (سلة)", value=f"{final_price:.2f} SAR")
    
    salla_token = st.text_input("Salla Access Token", type="password", placeholder="أدخل الـ Token لرفع المنتج بالكامل...")
    
    # زر الرفع أسفل الصفحة تماماً ومعه كل البيانات (الصور، الاسم، الوصف، السعر المحدث)
    if st.button("➕ ارفع المنتج الآن بكامل تفاصيله وصوره إلى سلة"):
        if salla_token:
            with st.spinner("جاري رفع المنتج مع الصور والوصف لمتجرك..."):
                headers = {"Authorization": f"Bearer {salla_token}", "Content-Type": "application/json"}
                
                # تجهيز payload متكامل يحتوي على الوصف وألبوم الصور بالكامل
                payload = {
                    "name": final_name,
                    "price": round(final_price, 2),
                    "quantity": 15,
                    "sku": final_sku,
                    "description": final_desc,
                    "images": st.session_state['p_all_images']  # رفع ألبوم الصور بالكامل وليس صورة واحدة فقط!
                }
                
                res = requests.post("https://api.salla.dev/admin/v2/products", headers=headers, json=payload)
                if res.status_code in [200, 201]: 
                    st.success("✅ مبروك ممدوح! المنتج طار ونزل في متجرك على سلة بكامل صوره ووصفه وسعره الجديد!")
                    st.session_state['product_loaded'] = False  # تفريغ الذاكرة لمنتج جديد
                else: 
                    st.error(f"فشل الرفع لـ سلة: {res.text}")
        else:
            st.error("الرجاء وضع الـ Salla Token أولاً لإتمام عملية الرفع المباشر.")
            
