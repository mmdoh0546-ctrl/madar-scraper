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
# 2. محرك السحب (باستخدام قوتك الجديدة ScraperAPI)
# ==========================================
def fetch_product(url):
    # نستخدم مفتاحك الخاص للاتصال عبر ScraperAPI مع تفعيل الـ render=true (ضروري جداً للجافا سكريبت)
    API_KEY = "806ec65adfba7c70b7b4e1d57d54edc7"
    api_url = f"http://api.scraperapi.com?api_key={API_KEY}&url={url}&render=true"
    
    try:
        response = requests.get(api_url, timeout=60)
        html = response.text
    except Exception as e:
        return {"error": f"فشل الاتصال: {str(e)}"}

    soup = BeautifulSoup(html, 'html.parser')

    # البحث عن بيانات المنتج (هذا هو المكان الذي يختبئ فيه السعر والعنوان)
    json_data = None
    state_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\});', html, re.DOTALL)
    if state_match:
        try: json_data = json.loads(state_match.group(1))
        except: pass
    
    product = json_data.get('product', {}).get('productDetail', {}) if json_data else {}
    
    # 1. استخراج العنوان والسعر بدقة
    title = product.get('name', '')
    if not title: title = soup.title.string if soup.title else "منتج بدون عنوان"
    
    p_val = product.get('price', {}).get('sellingPrice', {}).get('value', 0.0)
    price = float(p_val) if p_val else 0.0

    # 2. استخراج المقاسات (من صندوق البيانات)
    avail = []
    out = []
    variants = product.get('allVariants', product.get('variants', []))
    for v in variants:
        val = v.get('value', '')
        if val:
            if v.get('inStock', False): avail.append(val)
            else: out.append(val)
    desc = f"✅ متوفر: {', '.join(avail) if avail else 'لا يوجد'}\n❌ نفد: {', '.join(out) if out else 'لا يوجد'}"

    # 3. صيد الصور (فلتر صارم لحذف أي شعار)
    raw_imgs = product.get('images', [])
    final_imgs = []
    # قائمة حظر تشمل كل ما هو ليس "صورة منتج"
    blacklist = ['logo', 'icon', 'saudibusiness', 'frontend', 'maroof', 'mada', 'delivery']
    
    for img in raw_imgs:
        if isinstance(img, str):
            if not any(bw in img.lower() for bw in blacklist):
                if not img.startswith('http'): img = f"https://cdn.dsmcdn.com{img}"
                final_imgs.append(img)
                
    return {"title": title, "price": price, "desc": desc, "images": final_imgs, "url": url, "sku": "N/A"}

# ==========================================
# 3. واجهة المستخدم
# ==========================================
st.title("🛍️ سوق مدار - الإصدار القوي")
url = st.text_input("🔗 رابط المنتج:")

if st.button("🚀 جلب وتحليل"):
    with st.spinner("جاري الاختراق عبر ScraperAPI..."):
        res = fetch_product(url)
        if "error" in res:
            st.error(res["error"])
        else:
            st.success("تم السحب بنجاح!")
            st.subheader(res['title'])
            st.write(f"**السعر:** {res['price']} SAR")
            st.info(res['desc'])
            
            # عرض الصور
            cols = st.columns(3)
            for i, img in enumerate(res['images'][:6]):
                cols[i % 3].image(img)
            
            if st.button("💾 حفظ المنتج"):
                conn = sqlite3.connect('madar_products.db')
                c = conn.cursor()
                c.execute("INSERT INTO products (title, price, desc, images, url, sku) VALUES (?, ?, ?, ?, ?, ?)",
                          (res['title'], res['price'], res['desc'], json.dumps(res['images']), res['url'], 'N/A'))
                conn.commit()
                conn.close()
                st.success("تم الحفظ!")
