import streamlit as st
import cloudscraper
from bs4 import BeautifulSoup
import json
import re
import sqlite3

# --- إعدادات قاعدة البيانات المحلية ---
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

# --- إعدادات واجهة النظام ---
st.set_page_config(page_title="نظام إدارة منتجات | سوق مدار", layout="centered", page_icon="🛍️")

st.sidebar.title("📦 لوحة تحكم سوق مدار")
st.sidebar.write("---")
menu = st.sidebar.radio("اختر قسم:", ["🚀 سحب منتج جديد", "🗄️ مستودع المنتجات (المنتجات المحفوظة)"])

# --- دالة الجلب المدمجة (تجمع بين استقرار الكود السابق والميزات الجديدة) ---
def fetch_trendyol_product(url):
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False})
    try:
        response = scraper.get(url, timeout=20)
        if response.status_code != 200:
            return {"error": f"الموقع يرفض الاتصال. كود: {response.status_code}"}
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        title = ""
        price = 0.0
        description = ""
        images = []
        
        # الطريقة الأولى والأكثر استقراراً (التي نجحت في الكود القديم)
        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            if script.string and 'Product' in script.string:
                try:
                    data = json.loads(script.string)
                    product_data = data[0] if isinstance(data, list) else data
                    
                    title = product_data.get('name', '')
                    description = product_data.get('description', '')
                    
                    offers = product_data.get('offers', {})
                    if isinstance(offers, list) and len(offers) > 0:
                        offers = offers[0]
                    price = float(offers.get('price', 0.0))
                    
                    img_data = product_data.get('image', [])
                    if isinstance(img_data, str):
                        images.append(img_data)
                    elif isinstance(img_data, list):
                        images.extend(img_data)
                    break
                except:
                    continue

        # الطريقة الثانية: الغوص في أعماق الجافا سكريبت (لجلب بيانات إضافية إن نقصت)
        if not title or not description or price == 0.0 or len(images) <= 1:
            match = re.search(r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\});', response.text)
            if match:
                try:
                    state_data = json.loads(match.group(1))
                    product = state_data.get('product', {}).get('productDetail', {})
                    
                    if not title:
                        title = product.get('name', '')
                        brand = product.get('brand', {}).get('name', '')
                        if brand: title = f"{brand} - {title}"
                        
                    if price == 0.0:
                        price_data = product.get('price', {})
                        price_val = price_data.get('sellingPrice', {}).get('value') or price_data.get('originalPrice', {}).get('value')
                        if price_val: price = float(price_val)
                        
                    if len(images) <= 1:
                        for img in product.get('images', []):
                            img_url = img if str(img).startswith('http') else f"https://cdn.dsmcdn.com{img}"
                            if img_url not in images:
                                images.append(img_url)
                                
                    if not description:
                        attrs = product.get('attributes', [])
                        desc_lines = [f"• {attr.get('key', {}).get('name')}: {attr.get('value', {}).get('name')}" for attr in attrs]
                        description = "\n".join(desc_lines)
                except:
                    pass

        # الطريقة الثالثة: عناصر HTML المباشرة (كخطة إنقاذ أخيرة)
        if not title:
            meta_title = soup.find('meta', property='og:title')
            if meta_title: title = meta_title.get('content', '')
            
        if price == 0.0:
            price_tag = soup.find('span', class_='prc-dsc') or soup.find('div', class_='product-price')
            if price_tag:
                price_str = re.sub(r'[^\d.]', '', price_tag.text.replace(',', '.'))
                if price_str: price = float(price_str)

        # فلترة الصور للحصول على أعلى جودة وحذف المكرر
        high_res_images = []
        for img in images:
            if 'mnresize' in img or 'productmedia' in img:
                high_res = re.sub(r'/mnresize/\d+/\d+/', '/', img)
                high_res_images.append(high_res)
            else:
                high_res_images.append(img)
        images = list(dict.fromkeys(high_res_images))

        # التحقق النهائي
        if not title or price == 0.0:
            return {"error": "لم نتمكن من العثور على البيانات بدقة. يرجى التأكد من الرابط."}
            
        return {"title": title, "price": price, "description": description, "images": images}
        
    except Exception as e:
        return {"error": f"حدث خطأ أثناء الجلب: {str(e)}"}

# --- قسم: سحب منتج جديد ---
if menu == "🚀 سحب منتج جديد":
    st.title("🛍️ سحب المنتجات لمتجر سوق مدار")
    st.write("أدخل رابط المنتج لجلب الوصف، جميع الصور، والسعر.")
    
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
            with st.spinner("جاري تحليل الرابط وسحب البيانات..."):
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
        
        with st.expander("📝 عرض المواصفات والوصف", expanded=True):
            st.text(p['description'] if p['description'] else "لا توجد مواصفات مفصلة.")
        
        st.subheader(f"📸 صور المنتج ({len(p['images'])} صور)")
        if p['images']:
            cols = st.columns(3)
            for i, img_url in enumerate(p['images']):
                cols[i % 3].image(img_url, use_container_width=True)
        else:
            st.warning("لم يتم العثور على صور واضحة.")
            
        st.write("---")
        if st.button("💾 حفظ المنتج في مستودع المنتجات", type="primary", use_container_width=True):
            save_product(p['title'], p['supplier_price'], p['final_price'], p['description'], p['images'], p['url'])
            st.success("تم حفظ المنتج بنجاح! يمكنك رؤيته في القائمة الجانبية.")
            del st.session_state['current_product'] 

# --- قسم: مستودع المنتجات ---
elif menu == "🗄️ مستودع المنتجات (المنتجات المحفوظة)":
    st.title("🗄️ المنتجات المجهزة لسوق مدار")
    products = get_all_products()
    
    if not products:
        st.info("المستودع فارغ حالياً. قم بسحب منتجات جديدة أولاً.")
    else:
        st.write(f"إجمالي المنتجات المحفوظة: **{len(products)}** منتج")
        
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
