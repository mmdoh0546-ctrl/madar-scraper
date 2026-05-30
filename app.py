import streamlit as st
import requests
import re
import sqlite3
import json
from bs4 import BeautifulSoup

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
# 2. محرك السحب (باستخدام خادم وسيط لتخطي الحظر)
# ==========================================
def fetch_product(url):
    # استخدام خادم وسيط (Proxy) لتخطي حظر IP الخاص بـ Streamlit
    proxy_url = f"https://api.allorigins.win/get?url={url}"
    try:
        response = requests.get(proxy_url, timeout=20)
        data = response.json()
        html = data.get('contents', '')
    except:
        return {"error": "فشل الاتصال عبر الخادم الوسيط."}

    if not html:
        return {"error": "لم يتم العثور على محتوى الصفحة."}

    soup = BeautifulSoup(html, 'html.parser')

    # استخراج العنوان والسعر
    title = soup.title.string if soup.title else "منتج بدون عنوان"
    price_match = re.search(r'"sellingPrice":\s*\{"value":\s*([\d.]+)', html)
    price = float(price_match.group(1)) if price_match else 0.0

    # استخراج المقاسات
    sizes = re.findall(r'"value":"([^"]+)","inStock":(true|false)', html)
    avail = [s[0] for s in sizes if s[1] == 'true']
    out = [s[0] for s in sizes if s[1] == 'false']
    desc = f"✅ متوفر: {', '.join(avail) if avail else 'لا يوجد'}\n❌ نفد: {', '.join(out) if out else 'لا يوجد'}"

    # صيد الصور (فلتر صارم جداً)
    all_imgs = re.findall(r'(https://cdn\.dsmcdn\.com/[^"\'\s<>]+?\.(?:jpg|jpeg|webp|png))', html)
    final_imgs = []
    blacklist = ['logo', 'icon', 'flag', 'saudibusiness', 'sbc', 'stamp', 'rating', 'maroof', 'mada', 'frontend']
    
    for img in all_imgs:
        if any(key in img.lower() for key in ['/ty/', 'productmedia']):
            if not any(bw in img.lower() for bw in blacklist):
                clean = re.sub(r'/mnresize/\d+/\d+/', '/', img)
                if clean not in final_imgs: final_imgs.append(clean)

    return {"title": title, "price": price, "desc": desc, "images": final_imgs, "url": url}

# ==========================================
# 3. واجهة المستخدم
# ==========================================
st.title("🛍️ سوق مدار - الإصدار المستقر")
url = st.text_input("🔗 رابط المنتج:")

if st.button("🚀 جلب المنتج"):
    res = fetch_product(url)
    if "error" in res:
        st.error(res["error"])
    else:
        st.success("تم السحب!")
        st.write(f"**العنوان:** {res['title']}")
        st.write(f"**السعر:** {res['price']} SAR")
        st.info(res['desc'])
        for img in res['images'][:6]: st.image(img)
        
        if st.button("💾 حفظ في المستودع"):
            conn = sqlite3.connect('madar_products.db')
            c = conn.cursor()
            c.execute("INSERT INTO products (title, supplier_price, final_price, description, images, url, sku) VALUES (?, ?, ?, ?, ?, ?, ?)",
                      (res['title'], 'N/A', res['price'], res['price']+20, res['desc'], json.dumps(res['images']), res['url'], 'N/A'))
            conn.commit()
            conn.close()
            st.success("تم الحفظ!")
