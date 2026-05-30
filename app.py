import streamlit as st
import cloudscraper
from bs4 import BeautifulSoup
import json
import re

# --- إعدادات واجهة النظام ---
st.set_page_config(page_title="نظام سحب المنتجات | سوق مدار", layout="centered", page_icon="🛍️")
st.title("🛍️ نظام سحب المنتجات لمتجر سوق مدار")
st.write("أدخل رابط المنتج من Trendyol لجلب (العنوان، الوصف، الصور، والسعر) مع حساب العمولة الديناميكي.")

# --- دالة الجلب لتخطي الحماية ---
def fetch_trendyol_product(url):
    # استخدام cloudscraper لتخطي حماية Cloudflare و Bot Protection
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False})
    
    try:
        response = scraper.get(url, timeout=20)
        if response.status_code != 200:
            return {"error": f"الموقع يرفض الاتصال. كود الخطأ: {response.status_code}"}
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        title = ""
        price = 0.0
        description = ""
        images = []
        
        # 1. البحث في البيانات المهيكلة (أدق طريقة لسحب بيانات المتاجر)
        scripts = soup.find_all('script', type='application/ld+json')
        product_data = None
        
        for script in scripts:
            if script.string and 'Product' in script.string:
                try:
                    data = json.loads(script.string)
                    # أحياناً تكون البيانات داخل قائمة
                    product_data = data[0] if isinstance(data, list) else data
                    break
                except:
                    continue
                    
        if product_data:
            title = product_data.get('name', '')
            description = product_data.get('description', '')
            
            offers = product_data.get('offers', {})
            if isinstance(offers, list) and len(offers) > 0:
                offers = offers[0]
            price = float(offers.get('price', 0.0))
            
            image_info = product_data.get('image', [])
            if isinstance(image_info, str):
                images.append(image_info)
            elif isinstance(image_info, list):
                images.extend(image_info)

        # 2. طرق بديلة في حال لم تنجح الطريقة الأولى
        if not title:
            meta_title = soup.find('meta', property='og:title')
            if meta_title: title = meta_title.get('content', '')
            
        if price == 0.0:
            price_tag = soup.find('span', class_='prc-dsc') or soup.find('meta', property='product:price:amount')
            if price_tag:
                if price_tag.name == 'meta':
                    price = float(price_tag.get('content', 0.0))
                else:
                    price_str = re.sub(r'[^\d.]', '', price_tag.text.replace(',', '.'))
                    if price_str: price = float(price_str)
                    
        if not description:
            meta_desc = soup.find('meta', attrs={'name': 'description'}) or soup.find('meta', property='og:description')
            if meta_desc: description = meta_desc.get('content', "لا يوجد وصف تفصيلي.")
            
        if not images:
            meta_image = soup.find('meta', property='og:image')
            if meta_image: images.append(meta_image.get('content', ''))

        # 3. تحسين جودة الصور لتناسب المتجر
        high_res_images = []
        for img in images:
            # استبدال الصور المصغرة بصور عالية الدقة
            if 'mnresize' in img or 'productmedia' in img:
                high_res = re.sub(r'/mnresize/\d+/\d+/', '/', img)
                high_res_images.append(high_res)
            else:
                high_res_images.append(img)
                
        # إزالة التكرار
        images = list(dict.fromkeys(high_res_images))

        if not title or price == 0.0:
            return {"error": "لم نتمكن من العثور على البيانات. تأكد من أن الرابط لمنتج محدد."}
            
        return {
            "title": title,
            "price": price,
            "description": description,
            "images": images
        }
        
    except Exception as e:
        return {"error": f"حدث خطأ أثناء فك حماية المورد: {str(e)}"}

# --- واجهة المستخدم التفاعلية ---
st.write("---")
product_url = st.text_input("🔗 ألصق رابط المنتج هنا:")

st.subheader("⚙️ إعدادات التسعير والعمولة")
col_type, col_val = st.columns(2)

with col_type:
    commission_type = st.radio("نوع العمولة:", ["مبلغ ثابت", "نسبة مئوية (%)"])
with col_val:
    if commission_type == "مبلغ ثابت":
        commission_value = st.number_input("مقدار الإضافة (بالريال):", min_value=0.0, value=20.0, step=1.0)
    else:
        commission_value = st.number_input("النسبة المئوية للربح (%):", min_value=0.0, value=15.0, step=1.0)

if st.button("🚀 جلب وتحليل بيانات المنتج", use_container_width=True):
    if not product_url:
        st.warning("الرجاء وضع الرابط أولاً.")
    else:
        with st.spinner("جاري تخطي حماية المورد وسحب البيانات..."):
            result = fetch_trendyol_product(product_url)
            
            if "error" in result:
                st.error(result["error"])
            else:
                st.success("تم سحب بيانات المنتج بنجاح!")
                
                original_price = result['price']
                if commission_type == "مبلغ ثابت":
                    final_price = original_price + commission_value
                else:
                    final_price = original_price + (original_price * (commission_value / 100))
                
                st.write("---")
                st.subheader(result['title'])
                
                price_col1, price_col2 = st.columns(2)
                price_col1.metric("السعر من المورد", f"{original_price:.2f}")
                price_col2.metric("السعر النهائي للعميل", f"{final_price:.2f}", delta=f"ربحك: {(final_price - original_price):.2f}")
                
                with st.expander("📝 عرض وصف المنتج", expanded=True):
                    st.write(result['description'])
                
                st.subheader("📸 صور المنتج")
                if result['images']:
                    cols = st.columns(3)
                    for i, img_url in enumerate(result['images']):
                        cols[i % 3].image(img_url, use_container_width=True)
                else:
                    st.warning("لم يتم العثور على صور واضحة.")
                
                st.write("---")
                if st.button("🛒 إضافة المنتج إلى سوق مدار", type="primary", use_container_width=True):
                    st.info("البيانات جاهزة! سيتم تفعيل هذا الزر لاحقاً لرفع المنتج مباشرة عبر Salla API.")
