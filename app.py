import streamlit as st
import cloudscraper
import requests
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
    try:
        c.execute("ALTER TABLE products ADD COLUMN sku TEXT")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()

def save_product(title, sku, supplier_price, final_price, description, images, url):
    conn = sqlite3.connect('madar_products.db')
    c = conn.cursor()
    images_str = json.dumps(images)
    c.execute("INSERT INTO products (title, sku, supplier_price, final_price, description, images, url) VALUES (?, ?, ?, ?, ?, ?, ?)",
              (title, sku, supplier_price, final_price, description, images_str, url))
    conn.commit()
    conn.close()

def update_product(prod_id, new_title, new_sku, new_price, new_desc):
    conn = sqlite3.connect('madar_products.db')
    c = conn.cursor()
    c.execute("UPDATE products SET title=?, sku=?, final_price=?, description=? WHERE id=?", 
              (new_title, new_sku, new_price, new_desc, prod_id))
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
# 2. إعدادات واجهة النظام
# ==========================================
st.set_page_config(page_title="نظام إدارة منتجات | سوق مدار", layout="centered", page_icon="📦")

st.sidebar.title("📦 لوحة تحكم سوق مدار")
st.sidebar.write("---")
menu = st.sidebar.radio("اختر قسم:", ["🚀 سحب منتج جديد", "🗄️ مستودع المنتجات"])

if 'editing_id' not in st.session_state:
    st.session_state['editing_id'] = None

# ==========================================
# 3. محرك السحب الأصلي (المستقر والناجح)
# ==========================================
def fetch_trendyol_product(url):
    clean_url = url.split('?')[0]
    
    # استخدام هوية عناكب بحث جوجل (لا يتم حظرها أبداً من المتاجر)
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
        'Accept-Language': 'ar,en-US;q=0.9'
    }
    
    try:
        scraper = cloudscraper.create_scraper()
        resp = scraper.get(clean_url, headers=headers, timeout=20)
        html = resp.text
    except:
        try:
            resp = requests.get(clean_url, headers=headers, timeout=20)
            html = resp.text
        except:
            return {"error": "لا يوجد اتصال. تحقق من الإنترنت."}

    soup = BeautifulSoup(html, 'html.parser')
    
    title = ""
    price = 0.0
    sku = ""
    raw_images = []
    color_val = ""
    available_sizes = []
    out_of_stock_sizes = []
    attr_lines = []
    
    # 1. استخراج رمز التخزين من الرابط
    sku_match = re.search(r'-p-(\d+)', clean_url)
    if sku_match: sku = sku_match.group(1)

    # 2. البحث في بيانات النسخة التركية (INITIAL_STATE)
    product_data = {}
    state_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\});', html, re.DOTALL)
    if state_match:
        try:
            data = json.loads(state_match.group(1))
            product_data = data.get('product', {}).get('productDetail', {})
        except: pass

    # 3. البحث في بيانات النسخة العربية (NEXT_DATA)
    if not product_data:
        next_match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.DOTALL)
        if next_match:
            try:
                data = json.loads(next_match.group(1))
                # الغوص الدقيق للوصول لبيانات المنتج العربي
                product_data = data.get('props', {}).get('pageProps', {}).get('product', {})
            except: pass

    # 4. تفريغ البيانات من الكود المخفي
    if product_data:
        title = product_data.get('name', '')
        brand = product_data.get('brand', {}).get('name', '')
        if brand and brand not in title: title = f"{brand} - {title}"
            
        p_val = product_data.get('price', {}).get('sellingPrice', {}).get('value')
        if not p_val: p_val = product_data.get('price', {}).get('originalPrice', {}).get('value')
        if p_val: price = float(p_val)
        
        if not sku: sku = str(product_data.get('productCode', sku))
        
        color_val = product_data.get('color', '')
        
        for img in product_data.get('images', []):
            img_str = str(img)
            raw_images.append(img_str if img_str.startswith('http') else f"https://cdn.dsmcdn.com{img_str}")

        variants = product_data.get('allVariants', product_data.get('variants', []))
        for v in variants:
            val = v.get('value', '')
            in_stock = v.get('inStock', False)
            if val:
                if in_stock and val not in available_sizes: available_sizes.append(val)
                elif not in_stock and val not in out_of_stock_sizes: out_of_stock_sizes.append(val)
                    
        for attr in product_data.get('attributes', []):
            k = attr.get('key', {}).get('name', '')
            v = attr.get('value', {}).get('name', '')
            if k and v:
                attr_lines.append(f"• {k}: {v}")
                if k.lower() in ['renk', 'color', 'لون'] and not color_val: color_val = v

    # 5. خطة الطوارئ (JSON-LD) إذا كان المنتج محمياً بطريقة أخرى
    if not title or price == 0.0:
        for script in soup.find_all('script', type='application/ld+json'):
            if script.string and 'Product' in script.string:
                try:
                    ld_data = json.loads(script.string)
                    p_data = ld_data[0] if isinstance(ld_data, list) else ld_data
                    if not title: title = p_data.get('name', '')
                    if price == 0.0:
                        offers = p_data.get('offers', {})
                        if isinstance(offers, list) and len(offers) > 0: offers = offers[0]
                        price = float(offers.get('price', 0.0))
                    for img in p_data.get('image', []):
                        raw_images.append(img)
                except: pass

    # 6. الفلتر الفولاذي للصور (مستحيل دخول الشعارات)
    blacklist = ['logo', 'icon', 'flag', 'pci', 'iso', 'trust', 'badge', 'payment', 'footer', 'asset', 'saudibusiness', 'sbc', 'stamp', 'rating', 'maroof', 'mada', 'visa', 'mastercard', 'applepay', 'stcpay', 'vat', 'tax', 'norton', 'size-chart', 'size_chart']
    
    final_images = []
    for img in raw_images:
        clean_img = re.sub(r'/mnresize/\d+/\d+/', '/', img) 
        if not any(bad_word in clean_img.lower() for bad_word in blacklist):
            if clean_img not in final_images:
                final_images.append(clean_img)

    # 7. تجميع صندوق الوصف الجمالي
    final_desc_parts = []
    if color_val: final_desc_parts.append(f"🎨 **اللون المتاح:** {color_val}")
    if available_sizes: final_desc_parts.append(f"✅ **المقاسات المتوفرة بالمخزون:** {', '.join(available_sizes)}")
    if out_of_stock_sizes: final_desc_parts.append(f"❌ **مقاسات نفدت كميتها:** {', '.join(out_of_stock_sizes)}")
    if attr_lines: final_desc_parts.append(f"\n📌 **المواصفات الفنية للقطعة:**\n" + "\n".join(attr_lines))

    final_description = "\n".join(final_desc_parts) if final_desc_parts else "لم يقم المورد بإدراج مواصفات أو مقاسات دقيقة لهذا المنتج."

    if not title or price == 0.0:
        return {"error": "لم نتمكن من استخراج السعر أو العنوان. تأكد من أن الرابط يعمل."}
        
    return {
        "title": title, 
        "sku": sku if sku else "N/A",
        "price": price, 
        "description": final_description, 
        "images": final_images
    }

# ==========================================
# 4. واجهة قسم: سحب منتج جديد
# ==========================================
if menu == "🚀 سحب منتج جديد":
    st.session_state['editing_id'] = None 
    st.title("🛍️ سحب المنتجات لمتجر سوق مدار")
    
    product_url = st.text_input("🔗 ألصق رابط المنتج هنا:")
    
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
            with st.spinner("جاري استخراج البيانات والمقاسات بالأساس المستقر..."):
                result = fetch_trendyol_product(product_url)
                
                if "error" in result:
                    st.error(result["error"])
                else:
                    st.success("تم سحب بيانات المنتج بالكامل وبدقة فائقة!")
                    
                    original_price = result['price']
                    if commission_type == "مبلغ ثابت":
                        final_price = original_price + commission_value
                    else:
                        final_price = original_price + (original_price * (commission_value / 100))
                    
                    st.session_state['current_product'] = {
                        "title": result['title'],
                        "sku": result['sku'],
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
        st.caption(f"رمز التخزين (SKU): {p['sku']}")
        
        price_col1, price_col2 = st.columns(2)
        price_col1.metric("السعر من المورد", f"{p['supplier_price']:.2f}")
        price_col2.metric("السعر النهائي للعميل", f"{p['final_price']:.2f}", delta=f"ربحك: {(p['final_price'] - p['supplier_price']):.2f}")
        
        with st.expander("📝 عرض المواصفات (الألوان وحالة المخزون للمقاسات)", expanded=True):
            st.markdown(p['description'])
        
        st.subheader(f"📸 صور المنتج ({len(p['images'])} صور نقية)")
        if p['images']:
            cols = st.columns(3)
            for i, img_url in enumerate(p['images']):
                cols[i % 3].image(img_url, use_container_width=True)
            
        st.write("---")
        if st.button("💾 حفظ المنتج في مستودع المنتجات", type="primary", use_container_width=True):
            save_product(p['title'], p['sku'], p['supplier_price'], p['final_price'], p['description'], p['images'], p['url'])
            st.success("تم حفظ المنتج بنجاح! يمكنك إدارته وتعديله من المستودع.")
            del st.session_state['current_product'] 

# ==========================================
# 5. واجهة قسم: مستودع المنتجات (الإدارة الشاملة)
# ==========================================
elif menu == "🗄️ مستودع المنتجات":
    st.title("🗄️ إدارة مستودع سوق مدار")
    products = get_all_products()
    
    if st.session_state['editing_id'] is not None:
        prod_to_edit = next((p for p in products if p[0] == st.session_state['editing_id']), None)
        
        if prod_to_edit:
            prod_id, title, supplier_price, final_price, desc, imgs_str, url, *extra = prod_to_edit
            sku = extra[0] if extra else "N/A"
            imgs = json.loads(imgs_str)
            
            st.write("---")
            st.subheader("✏️ تعديل بيانات المنتج")
            
            new_title = st.text_input("عنوان المنتج:", value=title)
            new_sku = st.text_input("رمز التخزين (SKU):", value=sku)
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("تكلفة المورد الأصلية", f"{supplier_price:.2f} SAR")
            with col2:
                new_price = st.number_input("سعر البيع النهائي (شامل العمولة):", value=float(final_price), step=1.0)
                
            new_desc = st.text_area("المميزات، الألوان والمواصفات:", value=desc, height=250)
            
            st.write(f"**معرض الصور ({len(imgs)}):**")
            if imgs:
                img_cols = st.columns(4)
                for i, img_url in enumerate(imgs):
                    img_cols[i % 4].image(img_url, use_container_width=True)
            
            save_col, cancel_col = st.columns(2)
            with save_col:
                if st.button("💾 حفظ التعديلات", type="primary", use_container_width=True):
                    update_product(prod_id, new_title, new_sku, new_price, new_desc)
                    st.success("تم التحديث بنجاح!")
                    st.session_state['editing_id'] = None
                    st.rerun()
            with cancel_col:
                if st.button("❌ إلغاء والرجوع للمستودع", use_container_width=True):
                    st.session_state['editing_id'] = None
                    st.rerun()
                    
    else:
        if not products:
            st.info("المستودع فارغ حالياً. اذهب لقسم (سحب منتج جديد) لإضافة منتجات.")
        else:
            search_query = st.text_input("🔍 ابحث باسم المنتج أو رمز التخزين (SKU)...")
            st.write(f"إجمالي المنتجات المحفوظة: **{len(products)}**")
            
            for prod in products:
                prod_id, title, s_price, f_price, desc, imgs_str, url, *extra = prod
                sku = extra[0] if extra else "غير متوفر"
                
                if search_query:
                    if search_query.lower() not in title.lower() and search_query.lower() not in str(sku).lower():
                        continue
                
                imgs = json.loads(imgs_str)
                
                with st.container():
                    col_img, col_info, col_actions = st.columns([1.5, 4, 1.5])
                    
                    with col_img:
                        if imgs:
                            st.image(imgs[0], use_container_width=True)
                        else:
                            st.write("بدون صورة")
                            
                    with col_info:
                        st.markdown(f"**{title}**")
                        st.caption(f"رمز التخزين: {sku}")
                        st.write(f"السعر: **{f_price:.2f} SAR**")
                        st.markdown(f"[رابط المورد الأصلي]({url})")
                        
                    with col_actions:
                        if st.button("✏️ تعديل", key=f"edit_{prod_id}", use_container_width=True):
                            st.session_state['editing_id'] = prod_id
                            st.rerun()
                            
                        if st.button("🗑️ حذف", key=f"del_{prod_id}", use_container_width=True):
                            delete_product(prod_id)
                            st.rerun()
                    
                    st.write("---") 
