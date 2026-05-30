import streamlit as st
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
menu = st.sidebar.radio("اختر قسم:", ["🚀 سحب منتج جديد", "🗄️ مستودع المنتجات"])

# ==========================================
# 3. محرك السحب (باستخدام قوتك الخاصة)
# ==========================================
def fetch_trendyol_product(url):
    # استخدام مفتاحك الخاص عبر ScraperAPI
    api_key = "806ec65adfba7c70b7b4e1d57d54edc7"
    api_url = f"http://api.scraperapi.com?api_key={api_key}&url={url}&render=true"
    
    try:
        resp = requests.get(api_url, timeout=45)
        html = resp.text
    except: return {"error": "فشل الاتصال عبر ScraperAPI."}

    soup = BeautifulSoup(html, 'html.parser')
    
    # محاولة استخراج العنوان
    title_tag = soup.find('h1')
    title = title_tag.text.strip() if title_tag else "منتج غير معروف"
        
    # استخراج السعر
    price_tag = soup.find('span', class_='prc-dsc')
    price = float(re.sub(r'[^\d.]', '', price_tag.text.replace(',', '.'))) if price_tag else 0.0

    # استخراج المقاسات
    sizes_match = re.findall(r'"value":"([^"]+)","inStock":(true|false)', html)
    avail = [s[0] for s in sizes_match if s[1] == 'true']
    out = [s[0] for s in sizes_match if s[1] == 'false']
    desc = f"✅ متوفر: {', '.join(avail) if avail else 'غير محدد'}\n❌ نفد: {', '.join(out) if out else 'لا يوجد'}"

    # استخراج الصور بفلتر صارم
    raw_images = re.findall(r'(https://cdn\.dsmcdn\.com/[^"\'\s<>]+?\.(?:jpg|jpeg|webp|png))', html, re.IGNORECASE)
    blacklist = ['logo', 'icon', 'flag', 'saudibusiness', 'sbc', 'stamp', 'rating', 'maroof', 'mada', 'frontend']
    
    final_images = []
    for img in raw_images:
        if ('productmedia' in img.lower() or '/ty/' in img.lower()):
            if not any(bw in img.lower() for bw in blacklist):
                clean_img = re.sub(r'/mnresize/\d+/\d+/', '/', img) 
                if clean_img not in final_images: final_images.append(clean_img)

    if price == 0.0:
        return {"error": "نجحنا في الوصول، ولكن المورد أخفى السعر حالياً."}
        
    return {"title": title, "sku": "N/A", "price": price, "description": desc, "images": final_images, "url": url}

# ==========================================
# 4. الواجهة (كما كانت تعمل معك)
# ==========================================
if menu == "🚀 سحب منتج جديد":
    url = st.text_input("🔗 رابط المنتج:")
    if st.button("🚀 جلب وتحليل"):
        with st.spinner("جاري الاتصال بقوة ScraperAPI..."):
            res = fetch_product(url)
            if "error" in res: st.error(res["error"])
            else:
                st.success("تم السحب بنجاح!")
                st.subheader(res['title'])
                st.write(f"السعر: {res['price']} SAR")
                st.info(res['description'])
                cols = st.columns(3)
                for i, img in enumerate(res['images'][:6]): cols[i % 3].image(img)
                
                if st.button("💾 حفظ"):
                    save_product(res['title'], res['sku'], res['price'], res['price']+20, res['description'], res['images'], res['url'])
                    st.success("تم الحفظ!")

elif menu == "🗄️ مستودع المنتجات":
    products = get_all_products()
    for p in products:
        st.write(f"**{p[1]}**")
        st.write("---")
