import streamlit as st
import cloudscraper
import requests
from bs4 import BeautifulSoup
import json
import re
import sqlite3

# ==========================================
# 1. إعدادات قاعدة البيانات (مستودع سوق مدار)
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
# 2. إعدادات واجهة النظام والربط
# ==========================================
st.set_page_config(page_title="نظام إدارة منتجات | سوق مدار", layout="centered", page_icon="📦")

st.sidebar.title("📦 لوحة تحكم سوق مدار")
SALLA_TOKEN = st.sidebar.text_input("🔑 Salla Access Token:", type="password", help="أدخل توكن سلة لتمكين الرفع المباشر للمتجر")
st.sidebar.write("---")
menu = st.sidebar.radio("اختر قسم:", ["🚀 سحب منتج جديد", "🗄️ مستودع المنتجات"])

if 'editing_id' not in st.session_state:
    st.session_state['editing_id'] = None

# ==========================================
# 3. دالة الرفع إلى منصة سلة (Salla API)
# ==========================================
def upload_to_salla(token, product_data):
    url = "https://api.salla.dev/admin/v2/products"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # تجهيز خيارات المقاسات ليقرأها نظام سلة كـ "خيارات منتج"
    options = []
    if product_data.get('sizes_list'):
        size_values = [{"name": str(size)} for size in product_data['sizes_list']]
        options.append({
            "name": "المقاس",
            "values": size_values
        })
    
    payload = {
        "name": product_data['title'],
        "price": product_data['final_price'],
        "sku": product_data['sku'],
        "product_type": "product",
        "quantity": 100, 
        "description": product_data['description'],
        "options": options
    }
    
    # إضافة الصور إذا وُجدت
    if product_data.get('images'):
        payload["images"] = [{"original": img} for img in product_data['images']]
        
    try:
        response = requests.post(url, json=payload, headers=headers)
        return response.status_code, response.json()
    except Exception as e:
        return 500, {"error": str(e)}

# ==========================================
# 4. محرك السحب الأصلي (مزود ببحث عنيف للمقاسات)
# ==========================================
def fetch_trendyol_product(url):
    clean_url = url.split('?')[0]
    html = ""
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
        'Accept-Language': 'ar,en-US;q=0.9'
    }
    
    try:
        scraper = cloudscraper.create_scraper()
        resp = scraper.get(clean_url, timeout=15)
        if resp.status_code == 200: html = resp.text
    except: pass
    
    if not html or "cloudflare" in html.lower():
        try:
            resp = requests.get(clean_url, headers=headers, timeout=15)
            if resp.status_code == 200: html = resp.text
        except: pass

    if not html:
        return {"error": "فشل الاتصال بالرابط. يرجى التأكد من جودة الإنترنت."}

    soup = BeautifulSoup(html, 'html.parser')
    
    title = ""
    price = 0.0
    sku = ""
    color_val = ""
    
    meta_title = soup.find('meta', property='og:title')
    if meta_title: 
        title = meta_title.get('content', '').replace(" - Trendyol", "").strip()
        
    meta_price = soup.find('meta', property='product:price:amount')
    if meta_price:
        try: price = float(meta_price.get('content', '0').replace(',', '.'))
        except: pass

    if not title or price == 0.0:
        for script in soup.find_all('script', type='application/ld+json'):
            if script.string and 'Product' in script.string:
                try:
                    data = json.loads(script.string)
                    p_data = data[0] if isinstance(data, list) else data
                    if not title: title = p_data.get('name', '')
                    if price == 0.0:
                        offers = p_data.get('offers', {})
                        if isinstance(offers, list) and len(offers) > 0: offers = offers[0]
                        price = float(offers.get('price', 0.0))
                except: pass

    sku_match = re.search(r'-p-(\d+)', clean_url)
    if sku_match: sku = sku_match.group(1)

    color_match = re.search(r'"color":\s*"([^"]+)"', html)
    if color_match: color_val = color_match.group(1)

    available_sizes = []
    out_of_stock_sizes = []

    for el in soup.find_all(['div', 'span', 'button']):
        class_str = ' '.join(el.get('class', [])).lower()
        if any(x in class_str for x in ['sp-itm', 'size-variant', 'vrnt-item', 'size-item']):
            val = el.text.strip()
            if val and len(val) <= 10:
                if any(x in class_str for x in ['out-of-stock', 'disabled', 'passive']):
                    out_of_stock_sizes.append(val)
                else:
                    available_sizes.append(val)

    if not available_sizes and not out_of_stock_sizes:
        pattern1 = r'"(?:value|attributeValue|name)"\s*:\s*"?([^",}\s]{1,10})"?\s*,.{0,100}?"(?:inStock|isSellable)"\s*:\s*(true|false)'
        pattern2 = r'"(?:inStock|isSellable)"\s*:\s*(true|false)\s*,.{0,100}?"(?:value|attributeValue|name)"\s*:\s*"?([^",}\s]{1,10})"?\s*'
        
        for pat in [pattern1, pattern2]:
            for m in re.finditer(pat, html, re.IGNORECASE | re.DOTALL):
                start, end = m.span()
                block = html[max(0, start - 40) : min(len(html), end + 40)].lower()
                
                if any(c in block for c in ['color', 'renk', 'لون', 'image', 'brand', 'url']):
                    continue
                
                if pat == pattern1:
                    val, stock_str = m.group(1).strip(), m.group(2).lower()
                else:
                    stock_str, val = m.group(1).lower(), m.group(2).strip()
                
                stock = (stock_str == 'true')
                
                if val and not val.startswith('http') and len(val) <= 8 and re.search(r'[a-zA-Z0-9]', val):
                    if stock: available_sizes.append(val)
                    else: out_of_stock_sizes.append(val)

    final_avail = list(dict.fromkeys([str(s).upper() for s in available_sizes]))
    final_out = list(dict.fromkeys([str(s).upper() for s in out_of_stock_sizes if str(s).upper() not in final_avail]))

    raw_images = re.findall(r'(https://cdn\.dsmcdn\.com/[^"\'\s<>]+?\.(?:jpg|jpeg|webp|png))', html, re.IGNORECASE)
    blacklist = ['logo', 'icon', 'flag', 'pci', 'iso', 'trust', 'badge', 'payment', 'footer', 'asset', 'saudibusiness', 'sbc', 'stamp', 'rating', 'maroof', 'mada', 'visa', 'mastercard', 'applepay', 'stcpay', 'vat', 'tax', 'norton', 'size-chart', 'delivery', 'campaign', 'brand']
    
    final_images = []
    for img in raw_images:
        clean_img = re.sub(r'/mnresize/\d+/\d+/', '/', img) 
        if not any(bad_word in clean_img.lower() for bad_word in blacklist):
            if ('productmedia' in clean_img or '/ty/' in clean_img) and clean_img not in final_images:
                final_images.append(clean_img)
                
    if not final_images:
        for img in raw_images:
            clean_img = re.sub(r'/mnresize/\d+/\d+/', '/', img) 
            if not any(bad_word in clean_img.lower() for bad_word in blacklist) and clean_img not in final_images:
                final_images.append(clean_img)

    final_desc_parts = []
    if color_val: final_desc_parts.append(f"🎨 **اللون:** {color_val}")
    
    if final_avail:
        final_desc_parts.append(f"✅ **مقاسات متوفرة للبيع:** {', '.join(final_avail)}")
    if final_out:
        final_desc_parts.append(f"❌ **مقاسات نفدت:** {', '.join(final_out)}")

    final_description = "\n".join(final_desc_parts) if final_desc_parts else "لم يدرج المورد مواصفات إضافية."

    if not title or price == 0.0:
        return {"error": "فشلنا في العثور على السعر أو العنوان. المورد حظر الرابط حالياً."}
        
    return {
        "title": title, 
        "sku": sku if sku else "N/A",
        "price": price, 
        "description": final_description, 
        "images": final_images,
        "sizes_list": final_avail # تم إضافة هذا السطر خصيصاً لمنصة سلة
    }

# ==========================================
# 5. واجهة قسم: سحب منتج جديد
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
            with st.spinner("جاري استخراج البيانات بوضعية البحث الشامل..."):
                result = fetch_trendyol_product(product_url)
                
                if "error" in result:
                    st.error(result["error"])
                else:
                    st.success("تم سحب بيانات المنتج بالكامل بنجاح!")
                    
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
                        "url": product_url,
                        "sizes_list": result.get('sizes_list', [])
                    }

    if 'current_product' in st.session_state:
        p = st.session_state['current_product']
        st.write("---")
        st.subheader(p['title'])
        st.caption(f"رمز التخزين (SKU): {p['sku']}")
        
        price_col1, price_col2 = st.columns(2)
        price_col1.metric("السعر من المورد", f"{p['supplier_price']:.2f}")
        price_col2.metric("السعر النهائي للعميل", f"{p['final_price']:.2f}", delta=f"ربحك: {(p['final_price'] - p['supplier_price']):.2f}")
        
        with st.expander("📝 عرض المواصفات (الألوان والمقاسات)", expanded=True):
            st.markdown(p['description'])
        
        st.subheader(f"📸 صور المنتج ({len(p['images'])} صور صافية)")
        if p['images']:
            cols = st.columns(3)
            for i, img_url in enumerate(p['images']):
                cols[i % 3].image(img_url, use_container_width=True)
            
        st.write("---")
        
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            if st.button("💾 حفظ في المستودع المحلي", use_container_width=True):
                save_product(p['title'], p['sku'], p['supplier_price'], p['final_price'], p['description'], p['images'], p['url'])
                st.success("تم الحفظ في مستودع النظام!")
                
        with col_btn2:
            if st.button("🚀 رفع المنتج إلى متجر سلة", type="primary", use_container_width=True):
                if not SALLA_TOKEN:
                    st.error("يرجى إدخال (Salla Access Token) في القائمة الجانبية أولاً.")
                else:
                    with st.spinner("جاري رفع المنتج إلى متجرك في سلة..."):
                        status, resp = upload_to_salla(SALLA_TOKEN, p)
                        if status in [200, 201]:
                            st.success("تم إنشاء المنتج بنجاح في متجرك بسلة مع كامل المقاسات والصور!")
                            save_product(p['title'], p['sku'], p['supplier_price'], p['final_price'], p['description'], p['images'], p['url']) # حفظ تلقائي كنسخة احتياطية
                            del st.session_state['current_product']
                        else:
                            st.error(f"حدث خطأ أثناء الرفع: {resp}")

# ==========================================
# 6. واجهة قسم: مستودع المنتجات (الإدارة الشاملة)
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
