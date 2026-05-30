import streamlit as st
import cloudscraper
from bs4 import BeautifulSoup
import json
import re
import sqlite3

# ==========================================
# 1. إعدادات قاعدة البيانات (مستودع المنتجات)
# ==========================================
def init_db():
    conn = sqlite3.connect('madar_products.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS products
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  title TEXT, 
                  supplier_price REAL, 
                  final_price REAL, 
                  description TEXT, 
                  images TEXT, 
                  url TEXT)''')
    conn.commit()
    conn.close()

def save_product(title, supplier_price, final_price, description, images, url):
    conn = sqlite3.connect('madar_products.db')
    c = conn.cursor()
    images_str = json.dumps(images)
    c.execute("INSERT INTO products (title, supplier_price, final_price, description, images, url) VALUES (?, ?, ?, ?, ?, ?)",
              (title, supplier_price, final_price, description, images_str, url))
    conn.commit()
    conn.close()

def delete_product(product_id):
    conn = sqlite3.connect('madar_products.db')
    c = conn.cursor()
    c.execute("DELETE FROM products WHERE id=?", (product_id,))
    conn.commit()
    conn.close()

def get_all_products():
    conn = sqlite3.connect('madar_products.db')
    c = conn.cursor()
    c.execute("SELECT * FROM products ORDER BY id DESC")
    data = c.fetchall()
    conn.commit()
    conn.close()
    return data

init_db()

# ==========================================
# 2. إعدادات واجهة النظام والقائمة الجانبية
# ==========================================
st.set_page_config(page_title="نظام إدارة منتجات | سوق مدار", layout="centered", page_icon="🛍️")

st.sidebar.title("📦 لوحة تحكم سوق مدار")
st.sidebar.write("---")
menu = st.sidebar.radio("اختر قسم:", ["🚀 سحب منتج جديد", "🗄️ مستودع المنتجات (المنتجات المحفوظة)"])

# ==========================================
# 3. محرك السحب الجبار (مطور لاصطياد كل الصور والمواصفات)
# ==========================================
def fetch_trendyol_product(url):
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False})
    try:
        response = scraper.get(url, timeout=20)
        if response.status_code != 200:
            return {"error": f"الموقع يرفض الاتصال. كود: {response.status_code}"}
            
        html = response.text
        soup = BeautifulSoup(html, 'html.parser')
        
        title = ""
        price = 0.0
        description_lines = []
        raw_images = []
        
        # الطريقة الأولى (العميقة): استخراج البيانات من INITIAL_STATE
        state_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\});', html, re.DOTALL)
        if state_match:
            try:
                state_data = json.loads(state_match.group(1))
                product = state_data.get('product', {}).get('productDetail', {})
                
                # العنوان
                title = product.get('name', '')
                brand = product.get('brand', {}).get('name', '')
                if brand and brand not in title: 
                    title = f"{brand} - {title}"
                    
                # السعر
                price_data = product.get('price', {})
                price_val = price_data.get('sellingPrice', {}).get('value') or price_data.get('originalPrice', {}).get('value')
                if price_val: price = float(price_val)
                
                # الصور (معالجة الروابط المختصرة والكاملة)
                for img in product.get('images', []):
                    img_str = str(img)
                    if img_str.startswith('http'):
                        raw_images.append(img_str)
                    else:
                        # إضافة النطاق للروابط المختصرة
                        raw_images.append(f"https://cdn.dsmcdn.com{img_str}")
                        
                # المواصفات التفصيلية (تتجاهل الوصف التسويقي)
                attrs = product.get('attributes', [])
                for attr in attrs:
                    k = attr.get('key', {}).get('name', '')
                    v = attr.get('value', {}).get('name', '')
                    if k and v:
                        description_lines.append(f"• {k}: {v}")
            except:
                pass

        # الطريقة الثانية: JSON-LD (في حال فشل الأولى)
        if not title or not raw_images:
            scripts = soup.find_all('script', type='application/ld+json')
            for script in scripts:
                if script.string and 'Product' in script.string:
                    try:
                        data = json.loads(script.string)
                        p_data = data[0] if isinstance(data, list) else data
                        
                        if not title: title = p_data.get('name', '')
                        if price == 0.0:
                            offers = p_data.get('offers', {})
                            if isinstance(offers, list) and len(offers) > 0: offers = offers[0]
                            price = float(offers.get('price', 0.0))
                            
                        # سحب الصور
                        img_data = p_data.get('image', [])
                        if isinstance(img_data, str): raw_images.append(img_data)
                        elif isinstance(img_data, list): raw_images.extend(img_data)
                    except:
                        continue

        # الطريقة الثالثة (خطة الطوارئ للصور): مسح الكود المصدري بالكامل
        if not raw_images:
            # البحث عن أي رابط صورة يخص ترينديول في الصفحة
            regex_imgs = re.findall(r'(/ty/\d+/[^"\'\s<>]+?\.(?:jpg|jpeg|webp|png))', html, re.IGNORECASE)
            for img in regex_imgs:
                raw_images.append(f"https://cdn.dsmcdn.com{img}")
                
            regex_imgs_full = re.findall(r'(https://cdn\.dsmcdn\.com/[^"\'\s<>]+?\.(?:jpg|jpeg|webp|png))', html, re.IGNORECASE)
            raw_images.extend(regex_imgs_full)

        # الطريقة الثالثة (خطة الطوارئ للمواصفات): البحث في عناصر HTML
        if not description_lines:
            attr_lists = soup.find_all('ul', class_=re.compile(r'detail-attr|product-detail'))
            for ul in attr_lists:
                for li in ul.find_all('li'):
                    text = li.get_text(strip=True)
                    if text: description_lines.append(f"• {text}")

        # --- تنظيف ومعالجة البيانات النهائية ---
        
        # 1. تصفية الصور (إزالة المكرر، الحصول على أعلى دقة، استبعاد صور التقييمات)
        final_images = []
        for img in raw_images:
            clean_img = re.sub(r'/mnresize/\d+/\d+/', '/', img) # إزالة التصغير
            if clean_img not in final_images and 'rating' not in clean_img and 'stamp' not in clean_img:
                final_images.append(clean_img)
                
        # 2. تصفية الوصف
        if description_lines:
            final_description = "\n".join(description_lines)
        else:
            final_description = "لم يتم إدراج مواصفات دقيقة لهذا المنتج من قبل المورد."

        # التحقق من وجود خطأ حرج
        if not title or price == 0.0:
            return {"error": "لم نتمكن من استخراج السعر أو العنوان. يرجى التأكد من الرابط."}
            
        return {
            "title": title, 
            "price": price, 
            "description": final_description, 
            "images": final_images
        }
        
    except Exception as e:
        return {"error": f"حدث خطأ أثناء فك تشفير الصفحة: {str(e)}"}

# ==========================================
# 4. واجهة قسم: سحب منتج جديد
# ==========================================
if menu == "🚀 سحب منتج جديد":
    st.title("🛍️ سحب المنتجات لمتجر سوق مدار")
    st.write("أدخل رابط المنتج لجلب (المواصفات الدقيقة، جميع صيغ الصور، والسعر).")
    
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
            with st.spinner("جاري صيد الصور الأصلية واستخراج المواصفات..."):
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
                    
                    st.session_state['current_product'] = {
                        "title": result['title'],
                        "supplier_price": original_price,
                        "final_price": final_price,
                        "description": result['description'],
                        "images": result['images'],
                        "url": product_url
                    }

    # عرض المنتج المسحوب قبل الحفظ
    if 'current_product' in st.session_state:
        p = st.session_state['current_product']
        st.write("---")
        st.subheader(p['title'])
        
        price_col1, price_col2 = st.columns(2)
        price_col1.metric("السعر من المورد", f"{p['supplier_price']:.2f}")
        price_col2.metric("السعر النهائي للعميل", f"{p['final_price']:.2f}", delta=f"ربحك: {(p['final_price'] - p['supplier_price']):.2f}")
        
        with st.expander("📝 عرض المواصفات (تم استبعاد الوصف التسويقي)", expanded=True):
            st.text(p['description'])
        
        st.subheader(f"📸 صور المنتج ({len(p['images'])} صور)")
        if p['images']:
            cols = st.columns(3)
            for i, img_url in enumerate(p['images']):
                cols[i % 3].image(img_url, use_container_width=True)
        else:
            st.warning("لم يتم العثور على صور لهذا المنتج.")
            
        st.write("---")
        if st.button("💾 حفظ المنتج في مستودع المنتجات", type="primary", use_container_width=True):
            save_product(p['title'], p['supplier_price'], p['final_price'], p['description'], p['images'], p['url'])
            st.success("تم حفظ المنتج بنجاح! يمكنك إدارته من القائمة الجانبية.")
            del st.session_state['current_product'] 

# ==========================================
# 5. واجهة قسم: مستودع المنتجات
# ==========================================
elif menu == "🗄️ مستودع المنتجات (المنتجات المحفوظة)":
    st.title("🗄️ المنتجات المجهزة لسوق مدار")
    products = get_all_products()
    
    if not products:
        st.info("المستودع فارغ حالياً. اذهب لقسم (سحب منتج جديد) لإضافة منتجات.")
    else:
        st.write(f"إجمالي المنتجات في المستودع: **{len(products)}** منتج")
        
        for prod in products:
            prod_id, title, s_price, f_price, desc, imgs_str, url = prod
            imgs = json.loads(imgs_str)
            
            with st.container():
                st.write("---")
                col1, col2 = st.columns([1, 3])
                
                with col1:
                    if imgs:
                        st.image(imgs[0], use_container_width=True)
                
                with col2:
                    st.subheader(title)
                    st.write(f"**تكلفة المورد:** {s_price:.2f} | **سعر البيع:** {f_price:.2f} | **الربح:** {(f_price - s_price):.2f}")
                    
                    btn_col1, btn_col2 = st.columns(2)
                    with btn_col1:
                        if st.button(f"🗑️ حذف المنتج", key=f"del_{prod_id}"):
                            delete_product(prod_id)
                            st.rerun() 
                    with btn_col2:
                        st.link_button("🔗 فتح رابط المورد", url)
