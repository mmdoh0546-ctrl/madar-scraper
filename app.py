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
# 2. إعدادات واجهة النظام
# ==========================================
st.set_page_config(page_title="نظام إدارة منتجات | سوق مدار", layout="centered", page_icon="📦")

st.sidebar.title("📦 لوحة تحكم سوق مدار")
st.sidebar.write("---")
menu = st.sidebar.radio("اختر قسم:", ["🚀 سحب منتج جديد", "🗄️ مستودع المنتجات"])

if 'editing_id' not in st.session_state:
    st.session_state['editing_id'] = None

# ==========================================
# 3. محرك السحب (الاتصال المستقر + الغوص العميق)
# ==========================================
def find_product_dict(data):
    """رادار يغوص في أعماق الأكواد لاستخراج صندوق المنتج الصافي"""
    if isinstance(data, dict):
        # البحث عن الصندوق الذي يحتوي على المقاسات والصور معاً
        if 'allVariants' in data and 'images' in data:
            return data
        if 'variants' in data and 'images' in data and 'name' in data:
            return data
        for k, v in data.items():
            res = find_product_dict(v)
            if res: return res
    elif isinstance(data, list):
        for item in data:
            res = find_product_dict(item)
            if res: return res
    return None

def fetch_trendyol_product(url):
    clean_url = url.split('?')[0]
    html = ""
    
    # 1. الاتصال الآمن (نفس الطريقة التي جابت لك الشريط الأخضر)
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
        'Accept-Language': 'ar,en-US;q=0.9'
    }
    
    try:
        scraper = cloudscraper.create_scraper()
        resp = scraper.get(clean_url, timeout=15)
        if resp.status_code == 200: html = resp.text
    except: pass
    
    if not html or "cloudflare" in html.lower() or "Just a moment" in html:
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
    available_sizes = []
    out_of_stock_sizes = []
    final_images = []
    attr_lines = []

    sku_match = re.search(r'-p-(\d+)', clean_url)
    if sku_match: sku = sku_match.group(1)

    # 2. استخراج الجافا سكريبت المخفية
    json_data = None
    next_data = soup.find('script', id='__NEXT_DATA__')
    if next_data:
        try: json_data = json.loads(next_data.string)
        except: pass
    else:
        state_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\});', html, re.DOTALL)
        if state_match:
            try: json_data = json.loads(state_match.group(1))
            except: pass

    # 3. إطلاق الرادار لصيد المقاسات والصور بدقة 100%
    product_dict = find_product_dict(json_data)

    if product_dict:
        title = product_dict.get('name', '')
        brand = product_dict.get('brand', {}).get('name', '')
        if brand and brand not in title: title = f"{brand} - {title}"

        p_val = product_dict.get('price', {}).get('sellingPrice', {}).get('value')
        if not p_val: p_val = product_dict.get('price', {}).get('originalPrice', {}).get('value')
        if p_val: price = float(p_val)

        if not sku: sku = str(product_dict.get('productCode', sku))

        color_val = product_dict.get('color', '')

        # سحب المقاسات وحالتها
        variants = product_dict.get('allVariants', product_dict.get('variants', []))
        for v in variants:
            val = v.get('value', '')
            if val:
                if v.get('inStock', False):
                    if val not in available_sizes: available_sizes.append(val)
                else:
                    if val not in out_of_stock_sizes: out_of_stock_sizes.append(val)

        # استخراج الصور من القاعدة المباشرة (لا يمكن دخول أي شعار هنا)
        for img in product_dict.get('images', []):
            img_str = ""
            if isinstance(img, str): img_str = img
            elif isinstance(img, dict): img_str = img.get('url') or img.get('src') or ''
            
            if img_str:
                clean_img = re.sub(r'/mnresize/\d+/\d+/', '/', img_str)
                if not clean_img.startswith('http'): clean_img = f"https://cdn.dsmcdn.com{clean_img}"
                if clean_img not in final_images: final_images.append(clean_img)

        # سحب المواصفات
        for attr in product_dict.get('attributes', []):
            k = attr.get('key', {}).get('name', '')
            v = attr.get('value', {}).get('name', '')
            if k and v:
                attr_lines.append(f"• {k}: {v}")
                if k.lower() in ['renk', 'color', 'لون'] and not color_val: color_val = v

    # 4. خطة طوارئ بديلة (فقط إذا فشل الـ JSON)
    if not title:
        meta_t = soup.find('meta', property='og:title')
        if meta_t: title = meta_t.get('content', '').replace(" - Trendyol", "").strip()
    if price == 0.0:
        meta_p = soup.find('meta', property='product:price:amount')
        if meta_p:
            try: price = float(meta_p.get('content', '0').replace(',', '.'))
            except: pass

    # إذا كانت الصور فارغة تماماً، سيسحب من الروابط القوية فقط
    if not final_images:
        raw_images = re.findall(r'(https://cdn\.dsmcdn\.com/[^"\'\s<>]+?\.(?:jpg|jpeg|webp|png))', html, re.IGNORECASE)
        for img in raw_images:
            if 'productmedia' in img.lower() or '/ty/' in img.lower():
                clean_img = re.sub(r'/mnresize/\d+/\d+/', '/', img)
                if clean_img not in final_images: final_images.append(clean_img)

    # 5. تجميع الوصف النهائي
    final_desc_parts = []
    if color_val: final_desc_parts.append(f"🎨 **اللون:** {color_val}")
    if available_sizes: final_desc_parts.append(f"✅ **مقاسات متوفرة للبيع:** {', '.join(available_sizes)}")
    if out_of_stock_sizes: final_desc_parts.append(f"❌ **مقاسات نفدت:** {', '.join(out_of_stock_sizes)}")
    if attr_lines: final_desc_parts.append(f"\n📌 **المواصفات الفنية:**\n" + "\n".join(attr_lines))

    final_description = "\n".join(final_desc_parts) if final_desc_parts else "لم يدرج المورد مواصفات إضافية لهذا المنتج."

    if not title or price == 0.0:
        return {"error": "لم نتمكن من استخراج السعر أو العنوان. المورد حظر الرابط حالياً."}
        
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
            with st.spinner("جاري استخراج المقاسات والصور الصافية..."):
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
        
        with st.expander("📝 عرض المواصفات (الألوان والمقاسات)", expanded=True):
            st.markdown(p['description'])
        
        st.subheader(f"📸 صور المنتج ({len(p['images'])} صور صافية)")
        if p['images']:
            cols = st.columns(3)
            for i, img_url in enumerate(p['images']):
                cols[i % 3].image(img_url, use_container_width=True)
            
        st.write("---")
        if st.button("💾 حفظ المنتج في مستودع المنتجات", type="primary", use_container_width=True):
            save_product(p['title'], p['sku'], p['supplier_price'], p['final_price'], p['description'], p['images'], p['url'])
            st.success("تم حفظ المنتج بنجاح! يمكنك إدارته من المستودع.")
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
