import streamlit as st
import requests
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
# 2. إعدادات واجهة النظام والقائمة الجانبية
# ==========================================
st.set_page_config(page_title="نظام إدارة منتجات | سوق مدار", layout="centered", page_icon="📦")

st.sidebar.title("📦 لوحة تحكم سوق مدار")
st.sidebar.write("---")
menu = st.sidebar.radio("اختر قسم:", ["🚀 سحب منتج جديد", "🗄️ مستودع المنتجات"])

if 'editing_id' not in st.session_state:
    st.session_state['editing_id'] = None

# ==========================================
# 3. محرك السحب المدرع (يدعم النسخة العربية وتخطي الحماية)
# ==========================================
def fetch_trendyol_product(url):
    # تنظيف الرابط من أكواد التتبع لتجنب الحظر
    clean_url = url.split('?')[0]
    html = ""
    
    # المحاولة الأولى: استخدام Cloudscraper
    try:
        scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False})
        resp = scraper.get(clean_url, timeout=20)
        if resp.status_code == 200:
            html = resp.text
    except: pass
    
    # المحاولة الثانية (الطوارئ): التنكر كعناكب بحث جوجل لتخطي حماية Cloudflare
    if not html or "Just a moment" in html or "cloudflare" in html.lower():
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'}
            resp = requests.get(clean_url, headers=headers, timeout=20)
            if resp.status_code == 200:
                html = resp.text
        except: pass
        
    if not html:
        return {"error": "فشل الاتصال بالموقع نهائياً. تأكد من جودة اتصال الإنترنت."}

    soup = BeautifulSoup(html, 'html.parser')
    page_title = soup.title.string if soup.title else ""
    if "Just a moment" in page_title or "Attention Required" in page_title:
        return {"error": "تم حجب الاتصال مؤقتاً من قبل حماية المورد (Cloudflare). جرب رابطاً آخر أو انتظر قليلاً."}

    title = ""
    price = 0.0
    sku = ""
    raw_images = []
    
    color_val = ""
    sizes_list = []
    attr_lines = []
    
    # 1. استخراج رمز التخزين (SKU)
    sku_match = re.search(r'-p-(\d+)', clean_url)
    if sku_match: sku = sku_match.group(1)

    # 2. الهجوم على النسخة العربية (__NEXT_DATA__)
    next_data_match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.DOTALL)
    if next_data_match:
        try:
            json_str = next_data_match.group(1)
            
            # استخراج العنوان
            t_match = re.search(r'"name"\s*:\s*"([^"\\]+)"', json_str)
            if t_match: title = t_match.group(1).strip()
            
            # استخراج السعر
            p_match = re.search(r'"sellingPrice"\s*:\s*\{[^}]*"value"\s*:\s*([\d.]+)', json_str)
            if not p_match: p_match = re.search(r'"price"\s*:\s*([\d.]+)', json_str)
            if p_match: price = float(p_match.group(1))
            
            # استخراج الصور
            img_matches = re.findall(r'"(https://cdn\.dsmcdn\.com/[^"]+\.(?:jpg|jpeg|webp|png))"', json_str)
            if img_matches: raw_images.extend(img_matches)
        except: pass

    # 3. الهجوم على النسخة التركية (__INITIAL_STATE__)
    if not title or price == 0.0:
        state_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\});', html, re.DOTALL)
        if state_match:
            try:
                state_data = json.loads(state_match.group(1))
                product = state_data.get('product', {}).get('productDetail', {})
                
                if not title: title = product.get('name', '')
                if price == 0.0:
                    p_val = product.get('price', {}).get('sellingPrice', {}).get('value') or product.get('price', {}).get('originalPrice', {}).get('value')
                    if p_val: price = float(p_val)
                
                for img in product.get('images', []):
                    raw_images.append(img if str(img).startswith('http') else f"https://cdn.dsmcdn.com{img}")

                color_val = product.get('color', '')
                for v in product.get('allVariants', product.get('variants', [])):
                    val = v.get('value', '')
                    if val and val not in sizes_list: sizes_list.append(val)
                    
                for attr in product.get('attributes', []):
                    k = attr.get('key', {}).get('name', '')
                    v = attr.get('value', {}).get('name', '')
                    if k and v: attr_lines.append(f"• {k}: {v}")
            except: pass

    # 4. خطة الإنقاذ الشاملة (JSON-LD & Meta Tags)
    if not title or price == 0.0:
        for script in soup.find_all('script'):
            if script.string and 'Product' in script.string and '@type' in script.string:
                try:
                    data = json.loads(script.string)
                    p_data = data[0] if isinstance(data, list) else data
                    if not title: title = p_data.get('name', '')
                    if price == 0.0:
                        offers = p_data.get('offers', {})
                        if isinstance(offers, list) and len(offers) > 0: offers = offers[0]
                        p_val = offers.get('price')
                        if p_val: price = float(p_val)
                except: pass
                
        # الميتا تاج كفرصة أخيرة
        if not title:
            meta_title = soup.find('meta', property='og:title') or soup.find('meta', attrs={'name': 'twitter:title'})
            if meta_title: title = meta_title.get('content', '')
            
        if price == 0.0:
            meta_price = soup.find('meta', property='product:price:amount')
            if meta_price:
                try: price = float(meta_price.get('content', '0').replace(',', '.'))
                except: pass

    # صيد باقي الصور والمواصفات من HTML
    if not raw_images:
        raw_images.extend(re.findall(r'(https://cdn\.dsmcdn\.com/[^"\'\s<>]+?\.(?:jpg|jpeg|webp|png))', html, re.IGNORECASE))
        
    if not attr_lines:
        attr_lists = soup.find_all('ul', class_=re.compile(r'detail-attr|product-detail'))
        for ul in attr_lists:
            for li in ul.find_all('li'):
                text = li.get_text(strip=True)
                if text: attr_lines.append(f"• {text}")

    # 5. تنظيف وفلترة البيانات
    blacklist = ['logo', 'icon', 'flag', 'pci', 'iso', 'trust', 'badge', 'payment', 'footer', 'asset', 'saudibusiness', 'sbc', 'stamp', 'rating']
    final_images = []
    for img in raw_images:
        clean_img = re.sub(r'/mnresize/\d+/\d+/', '/', img) 
        clean_img_lower = clean_img.lower()
        if not any(bad_word in clean_img_lower for bad_word in blacklist) and clean_img not in final_images:
            final_images.append(clean_img)

    final_desc_parts = []
    if color_val: final_desc_parts.append(f"🎨 **اللون:** {color_val}")
    if sizes_list: final_desc_parts.append(f"📏 **المقاسات/الخيارات المتاحة:** {', '.join(sizes_list)}")
    if attr_lines: final_desc_parts.append(f"\n📌 **المواصفات الفنية:**\n" + "\n".join(attr_lines))

    final_description = "\n".join(final_desc_parts) if final_desc_parts else "لم يقم المورد بإدراج مواصفات دقيقة لهذا المنتج."

    if not title or price == 0.0:
        return {"error": "تأكد من أن الرابط صحيح ويحتوي على منتج. قد يكون المورد يطبق حماية قوية في هذه اللحظة."}
        
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
            with st.spinner("جاري كسر حماية المورد واستخراج البيانات..."):
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
        
        st.subheader(f"📸 صور المنتج ({len(p['images'])} صور)")
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
# 5. واجهة قسم: مستودع المنتجات (لوحة ذكية)
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
