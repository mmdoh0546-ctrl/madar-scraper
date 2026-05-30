import streamlit as st
import cloudscraper
from bs4 import BeautifulSoup
import json
import re
import sqlite3

# ==========================================
# 1. إعدادات قاعدة البيانات
# ==========================================
def init_db():
    conn = sqlite3.connect('madar_products.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS products
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, supplier_price REAL, final_price REAL, description TEXT, images TEXT, url TEXT, sku TEXT)''')
    conn.commit()
    conn.close()

init_db()

# ==========================================
# 2. محرك السحب (الأصلي الناجح)
# ==========================================
def fetch_product(url):
    scraper = cloudscraper.create_scraper()
    try:
        resp = scraper.get(url, timeout=15)
        html = resp.text
    except: return {"error": "فشل الاتصال."}

    soup = BeautifulSoup(html, 'html.parser')
    
    # استخراج العنوان والسعر
    title = soup.find('h1')
    title = title.text.strip() if title else "غير معروف"
    price_tag = soup.find('span', class_='prc-dsc')
    price = float(re.sub(r'[^\d.]', '', price_tag.text.replace(',', '.'))) if price_tag else 0.0
    
    # استخراج المقاسات
    sizes_match = re.findall(r'"value":"([^"]+)","inStock":(true|false)', html)
    avail = [s[0] for s in sizes_match if s[1] == 'true']
    out = [s[0] for s in sizes_match if s[1] == 'false']
    desc = f"✅ متوفر: {', '.join(avail) if avail else 'غير محدد'}\n❌ نفد: {', '.join(out) if out else 'لا يوجد'}"

    # استخراج الصور (فلتر الصور الصارم)
    all_imgs = re.findall(r'(https://cdn\.dsmcdn\.com/[^"\'\s<>]+?\.(?:jpg|jpeg|webp|png))', html)
    final_imgs = []
    # الحظر الصارم (شعار المركز السعودي واللوقو)
    blacklist = ['logo', 'icon', 'flag', 'saudibusiness', 'sbc', 'stamp', 'frontend']
    
    for img in all_imgs:
        if 'productmedia' in img.lower() or '/ty/' in img.lower():
            if not any(bw in img.lower() for bw in blacklist):
                clean = re.sub(r'/mnresize/\d+/\d+/', '/', img)
                if clean not in final_imgs: final_imgs.append(clean)
                
    return {"title": title, "price": price, "desc": desc, "images": final_imgs, "url": url}

# ==========================================
# 3. واجهة المستخدم
# ==========================================
st.title("🛍️ سحب المنتجات لمتجر سوق مدار")
url = st.text_input("🔗 رابط المنتج:")

if st.button("🚀 جلب وتحليل"):
    res = fetch_product(url)
    if "error" in res:
        st.error(res["error"])
    else:
        st.success("تم سحب البيانات!")
        st.subheader(res['title'])
        st.write(f"السعر: {res['price']} SAR")
        st.info(res['desc'])
        # عرض الصور بصفوف
        cols = st.columns(3)
        for i, img in enumerate(res['images'][:6]):
            cols[i % 3].image(img)
            
        if st.button("💾 حفظ المنتج"):
            conn = sqlite3.connect('madar_products.db')
            c = conn.cursor()
            c.execute("INSERT INTO products (title, supplier_price, final_price, description, images, url, sku) VALUES (?, ?, ?, ?, ?, ?, ?)",
                      (res['title'], res['price'], res['price']+20, res['desc'], json.dumps(res['images']), res['url'], 'N/A'))
            conn.commit()
            conn.close()
            st.success("تم الحفظ!")
