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

# -- الدالة الجديدة لتحديث بيانات المنتج --
def update_product(prod_id, new_title, new_price, new_desc):
    conn = sqlite3.connect('madar_products.db')
    c = conn.cursor()
    c.execute("UPDATE products SET title=?, final_price=?, description=? WHERE id=?", 
              (new_title, new_price, new_desc, prod_id))
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
menu = st.sidebar.radio("اختر قسم:", ["🚀 سحب منتج جديد", "🗄️ مستودع المنتجات (إدارة وتعديل)"])

# ==========================================
# 3. محرك السحب (مع فلتر الصور الذكي)
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
        
        state_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\});', html, re.DOTALL)
        if state_match:
            try:
                state_data = json.loads(state_match.group(1))
                product = state_data.get('product', {}).get('productDetail', {})
                
                title = product.get('name', '')
                brand = product.get('brand', {}).get('name', '')
                if brand and brand not in title: 
                    title = f"{brand} - {title}"
                    
                price_data = product.get('price', {})
                price_val = price_data.get('sellingPrice', {}).get('value') or price_data.get('originalPrice', {}).get('value')
                if price_val: price = float(price_val)
                
                for img in product.get('images', []):
                    img_str = str(img)
                    if img_str.startswith('http'):
                        raw_images.append(img_str)
                    else:
                        raw_images.append(f"https://cdn.dsmcdn.com{img_str}")
                        
                attrs = product.get('attributes', [])
                for attr in attrs:
                    k = attr.get('key', {}).get('name', '')
                    v = attr.get('value', {}).get('name', '')
                    if k and v:
                        description_lines.append(f"• {k}: {v}")
            except:
                pass

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
                            
                        img_data = p_data.get('image', [])
                        if isinstance(img_data, str): raw_images.append(img_data)
                        elif isinstance(img_data, list): raw_images.extend(img_data)
                    except:
                        continue

        if not raw_images:
            regex_imgs = re.findall(r'(/ty/\d+/[^"\'\s<>]+?\.(?:jpg|jpeg|webp|png))', html, re.IGNORECASE)
            for img in regex_imgs:
                raw_images.append(f"https://cdn.dsmcdn.com{img}")
                
            regex_imgs_full = re.findall(r'(https://cdn\.dsmcdn\.com/[^"\'\s<>]+?\.(?:jpg|jpeg|webp|png))', html, re.IGNORECASE)
            raw_images.extend(regex_imgs_full)

        if not description_lines:
            attr_lists = soup.find_all('ul', class_=re.compile(r'detail-attr|product-detail'))
            for ul in attr_lists:
                for li in ul.find_all('li'):
                    text = li.get_text(strip=True)
                    if text: description_lines.append(f"• {text}")

        # القائمة السوداء لمنع الشعارات
        blacklist = [
            'logo', 'icon', 'flag', 'pci', 'iso', 'trust', 'badge', 'payment', 
            'footer', 'asset', 'web/production', 'frontend', 'campaign', 
            'saudibusiness', 'sbc', 'stamp', 'rating', 'seller-store', 'avatar',
            'checkout'
        ]
        
        final_images = []
        for img in raw_images:
            clean_img = re.sub(r'/mnresize/\d+/\d+/', '/', img) 
            clean_img_lower = clean_img.lower()
            
            if not any(bad_word in clean_img_lower for bad_word in blacklist):
                if clean_img not in final_images:
                    final_images.append(clean_img)
                
        if description_lines:
            final_description = "\n".join(description_lines)
        else:
            final_description = "لم يتم إدراج مواصفات دقيقة لهذا المنتج من قبل المورد."

        if not title or price == 0.0:
            return {"error": "لم نتمكن من استخراج السعر أو العنوان. يرجى التأكد من الرابط."}
            
        return {
            "title": title, 
            "price": price, 
            "description": final_description, 
            "images": final_images
        }
        
    except Exception as e:
        return {"error": f"حدث خطأ أثناء الفحص: {str(e)}"}

# ==========================================
# 4. واجهة قسم: سحب منتج جديد
# ==========================================
if menu == "🚀 سحب منتج جديد":
    st.title("🛍️ سحب المنتجات لمتجر سوق مدار")
    st.write("أدخل رابط المنتج لجلب (المواصفات الدقيقة، صور المنتج الصافية، والسعر).")
    
    product_url = st.text_input("🔗 ألصق رابط المنتج هنا:")
    
    st.subheader("⚙️ إعدادات التسعير والعمولة الأولية")
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
            with st.spinner("جاري صيد الصور وتنقيتها من الشعارات..."):
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

    if 'current_product' in st.session_state:
        p = st.session_state['current_product']
        st.write("---")
        st.subheader(p['title'])
        
        price_col1, price_col2 = st.columns(2)
        price_col1.metric("السعر من المورد", f"{p['supplier_price']:.2f}")
        price_col2.metric("السعر النهائي للعميل", f"{p['final_price']:.2f}", delta=f"ربحك: {(p['final_price'] - p['supplier_price']):.2f}")
        
        with st.expander("📝 عرض المواصفات (تم استبعاد الوصف التسويقي)", expanded=True):
            st.text(p['description'])
        
        st.subheader(f"📸 صور المنتج ({len(p['images'])} صور مفلترة)")
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
# 5. واجهة قسم: مستودع المنتجات (مع ميزة التعديل)
# ==========================================
elif menu == "🗄️ مستودع المنتجات (إدارة وتعديل)":
    st.title("🗄️ إدارة مستودع سوق مدار")
    products = get_all_products()
    
    if not products:
        st.info("المستودع فارغ حالياً. اذهب لقسم (سحب منتج جديد) لإضافة منتجات.")
    else:
        st.write(f"إجمالي المنتجات في المستودع: **{len(products)}** منتج")
        
        for prod in products:
            prod_id, title, s_price, f_price, desc, imgs_str, url = prod
            imgs = json.loads(imgs_str)
            
            st.write("---")
            # عرض العنوان والسعر
            st.subheader(title)
            st.write(f"**تكلفة المورد:** {s_price:.2f} SAR | **سعر البيع الحالي:** {f_price:.2f} SAR | **الربح:** {(f_price - s_price):.2f} SAR")
            
            # --- قسم التعديل ---
            with st.expander("✏️ تعديل بيانات المنتج"):
                new_title = st.text_input("عنوان المنتج:", value=title, key=f"t_{prod_id}")
                new_price = st.number_input("سعر البيع النهائي (شامل العمولة):", value=float(f_price), step=1.0, key=f"p_{prod_id}")
                new_desc = st.text_area("الوصف والمواصفات:", value=desc, height=150, key=f"d_{prod_id}")
                
                if st.button("💾 حفظ التعديلات الجديدة", key=f"save_{prod_id}", type="primary"):
                    update_product(prod_id, new_title, new_price, new_desc)
                    st.success("تم تحديث بيانات المنتج بنجاح! سيتم إعادة تحميل الصفحة...")
                    st.rerun()
            
            # --- قسم عرض جميع الصور ---
            with st.expander(f"🖼️ عرض جميع صور المنتج ({len(imgs)} صور)"):
                if imgs:
                    img_cols = st.columns(3)
                    for i, img_url in enumerate(imgs):
                        img_cols[i % 3].image(img_url, use_container_width=True)
                else:
                    st.write("لا توجد صور محفوظة.")
            
            # أزرار الإجراءات (حذف ورابط المورد)
            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                if st.button(f"🗑️ حذف المنتج نهائياً", key=f"del_{prod_id}"):
                    delete_product(prod_id)
                    st.rerun() 
            with btn_col2:
                st.link_button("🔗 فتح رابط المورد الأصلي", url)
