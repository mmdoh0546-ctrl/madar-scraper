import streamlit as st
import requests
import json
import sqlite3
import re
from bs4 import BeautifulSoup

# ==========================================
# 1. إعدادات قاعدة البيانات
# ==========================================
def init_db():
    conn = sqlite3.connect('madar_products.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS products
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, price REAL, desc TEXT, images TEXT, url TEXT, sku TEXT)''')
    conn.commit()
    conn.close()

init_db()

# ==========================================
# 2. محرك السحب (باستخدام مفتاحك الخاص)
# ==========================================
def fetch_product(url):
    API_KEY = "806ec65adfba7c70b7b4e1d57d54edc7"
    # render=true ضرورية جداً لجلب المقاسات المخفية
    api_url = f"http://api.scraperapi.com?api_key={API_KEY}&url={url}&render=true"
    
    try:
        response = requests.get(api_url, timeout=60)
        html = response.text
    except Exception as e:
        return {"error": f"فشل الاتصال: {str(e)}"}

    soup = BeautifulSoup(html, 'html.parser')

    # البحث عن بيانات المنتج في الأكواد المخفية
    json_data = None
    state_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\});', html, re.DOTALL)
    if state_match:
        try: json_data = json.loads(state_match.group(1))
        except: pass
    
    # محاولة استخراج المنتج من بيانات JSON
    product = json_data.get('product', {}).get('productDetail', {}) if json_data else {}
    
    # العنوان والسعر
    title = product.get('name', 'منتج غير معروف')
    price = product.get('price', {}).get('sellingPrice', {}).get('value', 0.0)
    sku = str(product.get('productCode', 'N/A'))

    # استخراج المقاسات
    avail = []
    out = []
    variants = product.get('allVariants', product.get('variants', []))
    for v in variants:
        val = v.get('value', '')
        if val:
            if v.get('inStock', False): avail.append(val)
            else: out.append(val)
    desc = f"✅ متوفر: {', '.join(avail) if avail else 'لا يوجد'}\n❌ نفد: {', '.join(out) if out else 'لا يوجد'}"

    # استخراج الصور بفلتر صارم (بدون شعارات)
    raw_imgs = product.get('images', [])
    final_imgs = []
    blacklist = ['logo', 'icon', 'saudibusiness', 'frontend', 'maroof', 'mada', 'delivery']
    
    for img in raw_imgs:
        if isinstance(img, str):
            if not any(bw in img.lower() for bw in blacklist):
                if not img.startswith('http'): img = f"https://cdn.dsmcdn.com{img}"
                final_imgs.append(img)
                
    return {"title": title, "price": float(price), "desc": desc, "images": final_imgs, "url": url, "sku": sku}

# ==========================================
# 3. واجهة المستخدم
# ==========================================
st.title("🛍️ سوق مدار - الإصدار الاحترافي")
url = st.text_input("🔗 رابط المنتج:")

if st.button("🚀 جلب وتحليل البيانات"):
    with st.spinner("جاري التواصل مع المورد..."):
        res = fetch_product(url)
        if "error" in res:
            st.error(res["error"])
        else:
            st.success("تم السحب بنجاح!")
            st.subheader(res['title'])
            st.write(f"**السعر:** {res['price']} SAR")
            st.info(res['desc'])
            
            cols = st.columns(3)
            for i, img in enumerate(res['images'][:6]):
                cols[i % 3].image(img)
            
            if st.button("💾 حفظ المنتج"):
                conn = sqlite3.connect('madar_products.db')
                c = conn.cursor()
                c.execute("INSERT INTO products (title, price, desc, images, url, sku) VALUES (?, ?, ?, ?, ?, ?)",
                          (res['title'], res['price'], res['desc'], json.dumps(res['images']), res['url'], res['sku']))
                conn.commit()
                conn.close()
                st.success("تم الحفظ في المستودع!")

# عرض المستودع
if st.checkbox("🗄️ عرض المستودع"):
    products = get_all_products()
    for p in products:
        st.write(f"**{p[1]}** - {p[2]} SAR")
