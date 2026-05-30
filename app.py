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
# 2. محرك السحب (الأصلي والمستقر)
# ==========================================
def fetch_product(url):
    scraper = cloudscraper.create_scraper()
    try:
        resp = scraper.get(url, timeout=20)
        html = resp.text
    except: return {"error": "فشل الاتصال بالمورد."}

    # استخراج البيانات من الهيكل المخفي (أكثر دقة من قراءة الصفحة)
    json_data = {}
    state_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\});', html, re.DOTALL)
    if state_match:
        try: json_data = json.loads(state_match.group(1))
        except: pass
    
    product = json_data.get('product', {}).get('productDetail', {})
    
    # العنوان والسعر
    title = product.get('name', 'منتج غير معروف')
    price = product.get('price', {}).get('sellingPrice', {}).get('value', 0.0)
    sku = str(product.get('productCode', 'N/A'))

    # المقاسات (المتوفرة والنافدة)
    available_sizes = []
    out_of_stock = []
    variants = product.get('allVariants', product.get('variants', []))
    for v in variants:
        val = v.get('value', '')
        if val:
            if v.get('inStock', False): available_sizes.append(val)
            else: out_of_stock.append(val)
    
    desc = f"✅ متوفر: {', '.join(available_sizes) if available_sizes else 'لا يوجد'}\n❌ نفد: {', '.join(out_of_stock) if out_of_stock else 'لا يوجد'}"

    # الصور (فلتر صارم جداً لحذف الشعارات)
    raw_imgs = product.get('images', [])
    final_imgs = []
    blacklist = ['logo', 'icon', 'flag', 'saudibusiness', 'frontend', 'maroof', 'mada']
    
    for img in raw_imgs:
        # التأكد أن الصورة هي صورة منتج وليست شعاراً
        if not any(bw in img.lower() for bw in blacklist):
            if not img.startswith('http'): img = f"https://cdn.dsmcdn.com{img}"
            final_imgs.append(img)

    return {"title": title, "price": float(price), "desc": desc, "images": final_imgs, "url": url, "sku": sku}

# ==========================================
# 3. واجهة المستخدم
# ==========================================
st.title("🛍️ سوق مدار - الإصدار المستقر")
url = st.text_input("🔗 رابط المنتج:")

if st.button("🚀 جلب وتحليل"):
    res = fetch_product(url)
    if "error" in res:
        st.error(res["error"])
    else:
        st.success("تم السحب بنجاح!")
        st.write(f"**العنوان:** {res['title']}")
        st.write(f"**السعر:** {res['price']} SAR")
        st.info(res['desc'])
        
        # عرض الصور بصفوف
        cols = st.columns(3)
        for i, img in enumerate(res['images'][:6]):
            cols[i % 3].image(img)
            
        if st.button("💾 حفظ المنتج"):
            conn = sqlite3.connect('madar_products.db')
            c = conn.cursor()
            c.execute("INSERT INTO products (title, supplier_price, final_price, description, images, url, sku) VALUES (?, ?, ?, ?, ?, ?, ?)",
                      (res['title'], res['price'], res['price']+20, res['desc'], json.dumps(res['images']), res['url'], res['sku']))
            conn.commit()
            conn.close()
            st.success("تم الحفظ في المستودع!")

# عرض المستودع
if st.checkbox("🗄️ عرض المستودع"):
    products = get_all_products()
    for p in products:
        st.write(f"**{p[1]}** - {p[3]} SAR")
