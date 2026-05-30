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
    
    # تحديث قاعدة البيانات القديمة لإضافة رمز التخزين (SKU) بأمان
    try:
        c.execute("ALTER TABLE products ADD COLUMN sku TEXT")
    except sqlite3.OperationalError:
        pass # العمود موجود مسبقاً
        
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

# التحكم في حالة صفحة التعديل
if 'editing_id' not in st.session_state:
    st.session_state['editing_id'] = None

# ==========================================
# 3. محرك السحب (دقيق في الوصف وسحب SKU)
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
        sku = ""
        description_lines = []
        raw_images = []
        
        # محاولة استخراج رمز التخزين (SKU) من الرابط كطريقة سريعة ومضمونة
        sku_match = re.search(r'-p-(\d+)', url)
        if sku_match:
            sku = sku_match.group(1)
            
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
                
                if not sku:
                    sku = str(product.get('productCode', ''))
                
                for img in product.get('images', []):
                    img_str = str(img)
                    if img_str.startswith('http'):
                        raw_images.append(img_str)
                    else:
                        raw_images.append(f"https://cdn.dsmcdn.com{img_str}")
                        
                # التركيز حصراً على جدول المواصفات
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
                        if not sku: sku = str(p_data.get('sku', sku))
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
            regex_imgs_full = re.findall(r'(https://cdn\.dsmcdn\.com/[^"\'\s<>]+?\.(?:jpg|jpeg|webp|png))', html, re.IGNORECASE)
            raw_images.extend(regex_imgs_full)

        if not description_lines:
            attr_lists = soup.find_all('ul', class_=re.compile(r'detail-attr|product-detail'))
            for ul in attr_lists:
                for li in ul.find_all('li'):
                    text = li.get_text(strip=True)
                    if text: description_lines.append(f"• {text}")

        # فلتر الصور (إزالة أي شعارات)
        blacklist = ['logo', 'icon', 'flag', 'pci', 'iso', 'trust', 'badge', 'payment', 'footer', 'asset', 'saudibusiness', 'sbc', 'stamp', 'rating']
        final_images = []
        for img in raw_images:
            clean_img = re.sub(r'/mnresize/\d+/\d+/', '/', img) 
            clean_img_lower = clean_img.lower()
            if not any(bad_word in clean_img_lower for bad_word in blacklist):
                if clean_img not in final_images:
                    final_images.append(clean_img)
                
        # تجهيز الوصف النهائي كمميزات فقط
        if description_lines:
            final_description = "مميزات ومواصفات المنتج:\n" + "\n".join(description_lines)
        else:
            final_description = "لم يقم المورد بإدراج جدول مواصفات دقيق لهذا المنتج."

        if not title or price == 0.0:
            return {"error": "لم نتمكن من استخراج السعر أو العنوان. يرجى التأكد من الرابط."}
            
        return {
            "title": title, 
            "sku": sku if sku else "N/A",
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
    st.session_state['editing_id'] = None # تصفير حالة التعديل
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
            with st.spinner("جاري استخراج المواصفات الفنية وصور المنتج..."):
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
        
        with st.expander("📝 عرض المواصفات", expanded=True):
            st.text(p['description'])
        
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
    
    # --- حالة التعديل الفردية (Edit Mode) ---
    if st.session_state['editing_id'] is not None:
        # البحث عن المنتج المراد تعديله
        prod_to_edit = next((p for p in products if p[0] == st.session_state['editing_id']), None)
        
        if prod_to_edit:
            prod_id, title, supplier_price, final_price, desc, imgs_str, url, *extra = prod_to_edit
            sku = extra[0] if extra else "N/A" # لمعالجة المنتجات القديمة
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
                
            new_desc = st.text_area("المميزات والمواصفات:", value=desc, height=200)
            
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
                    
    # --- حالة العرض الرئيسية للمستودع (List Mode) ---
    else:
        if not products:
            st.info("المستودع فارغ حالياً. اذهب لقسم (سحب منتج جديد) لإضافة منتجات.")
        else:
            # شريط البحث
            search_query = st.text_input("🔍 ابحث باسم المنتج أو رمز التخزين (SKU)...")
            
            st.write(f"إجمالي المنتجات المحفوظة: **{len(products)}**")
            
            for prod in products:
                prod_id, title, s_price, f_price, desc, imgs_str, url, *extra = prod
                sku = extra[0] if extra else "غير متوفر"
                
                # تطبيق فلتر البحث
                if search_query:
                    if search_query.lower() not in title.lower() and search_query.lower() not in str(sku).lower():
                        continue
                
                imgs = json.loads(imgs_str)
                
                # صندوق عرض مرتب للمنتج
                with st.container():
                    col_img, col_info, col_actions = st.columns([1.5, 4, 1.5])
                    
                    # 1. عرض صورة واحدة فقط
                    with col_img:
                        if imgs:
                            st.image(imgs[0], use_container_width=True)
                        else:
                            st.write("بدون صورة")
                            
                    # 2. عرض بيانات مختصرة
                    with col_info:
                        st.markdown(f"**{title}**")
                        st.caption(f"رمز التخزين: {sku}")
                        st.write(f"السعر: **{f_price:.2f} SAR**")
                        st.markdown(f"[رابط المورد الأصلي]({url})")
                        
                    # 3. أزرار التحكم
                    with col_actions:
                        if st.button("✏️ تعديل", key=f"edit_{prod_id}", use_container_width=True):
                            st.session_state['editing_id'] = prod_id
                            st.rerun()
                            
                        if st.button("🗑️ حذف", key=f"del_{prod_id}", use_container_width=True):
                            delete_product(prod_id)
                            st.rerun()
                    
                    st.write("---") # خط فاصل بين كل منتج
