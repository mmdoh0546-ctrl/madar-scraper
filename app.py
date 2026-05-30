import streamlit as st
import requests
import cloudscraper
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
# 3. محرك السحب (الأصلي الناجح مع تحسين المقاسات)
# ==========================================
def fetch_trendyol_product(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'ar,en-US;q=0.9'
    }
    try:
        scraper = cloudscraper.create_scraper()
        resp = scraper.get(url, headers=headers, timeout=20)
        html = resp.text
    except: return {"error": "فشل الاتصال بالمورد. حاول مرة أخرى."}

    soup = BeautifulSoup(html, 'html.parser')
    
    # استخراج البيانات الأساسية
    title = soup.find('h1')
    title = title.text.strip() if title else ""
    
    price_tag = soup.find('span', class_='prc-dsc')
    price = float(re.sub(r'[^\d.]', '', price_tag.text.replace(',', '.'))) if price_tag else 0.0
    
    sku = ""
    sku_match = re.search(r'-p-(\d+)', url)
    if sku_match: sku = sku_match.group(1)

    # استخراج المقاسات (طريقة البحث الشامل في النص)
    sizes = re.findall(r'"value":"([^"]+)","inStock":(true|false)', html)
    available_sizes = [s[0] for s in sizes if s[1] == 'true']
    out_of_stock = [s[0] for s in sizes if s[1] == 'false']

    # استخراج الصور (فلترة قوية لمنع الشعارات)
    raw_images = re.findall(r'(https://cdn\.dsmcdn\.com/[^"\'\s<>]+?\.(?:jpg|jpeg|webp|png))', html, re.IGNORECASE)
    blacklist = ['logo', 'icon', 'flag', 'pci', 'iso', 'trust', 'badge', 'payment', 'footer', 'saudibusiness', 'sbc', 'stamp', 'rating', 'maroof', 'mada', 'visa']
    
    final_images = []
    for img in raw_images:
        if 'productmedia' in img.lower() or '/ty/' in img.lower():
            if not any(bw in img.lower() for bw in blacklist):
                clean_img = re.sub(r'/mnresize/\d+/\d+/', '/', img)
                if clean_img not in final_images: final_images.append(clean_img)

    desc = f"✅ **مقاسات متوفرة:** {', '.join(available_sizes) if available_sizes else 'غير محدد'}\n❌ **مقاسات نفدت:** {', '.join(out_of_stock) if out_of_stock else 'لا يوجد'}"
    
    if not title or price == 0.0:
        return {"error": "لم نتمكن من العثور على السعر أو العنوان. المورد يطبق حماية قوية حالياً."}
        
    return {"title": title, "sku": sku, "price": price, "description": desc, "images": final_images, "url": url}

# ==========================================
# 4. واجهة التطبيق (تشغيل القسم الناجح)
# ==========================================
if menu == "🚀 سحب منتج جديد":
    url = st.text_input("🔗 رابط المنتج:")
    if st.button("🚀 جلب وتحليل"):
        res = fetch_trendyol_product(url)
        if "error" in res: st.error(res["error"])
        else:
            st.success("تم سحب المنتج!")
            st.subheader(res['title'])
            st.write(f"السعر: {res['price']}")
            st.write(res['description'])
            for img in res['images']: st.image(img)
            if st.button("💾 حفظ"):
                save_product(res['title'], res['sku'], res['price'], res['price']+20, res['description'], res['images'], res['url'])
                st.success("تم الحفظ!")

elif menu == "🗄️ مستودع المنتجات":
    products = get_all_products()
    for p in products:
        st.write(f"**{p[1]}**")
        st.write("---")
