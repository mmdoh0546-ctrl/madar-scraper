import streamlit as st
import requests
import json
import sqlite3
from bs4 import BeautifulSoup

# ==========================================
# 1. إعدادات قاعدة البيانات
# ==========================================
def init_db():
    conn = sqlite3.connect('madar_products.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS products
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, price REAL, desc TEXT, images TEXT, url TEXT)''')
    conn.commit()
    conn.close()

init_db()

# ==========================================
# 2. محرك السحب (باستخدام مفتاحك الخاص)
# ==========================================
def fetch_product(url):
    # نستخدم مفتاحك الخاص مع خاصية render=true لتجاوز حماية الجافا سكريبت
    api_key = "806ec65adfba7c70b7b4e1d57d54edc7"
    api_url = f"http://api.scraperapi.com?api_key={api_key}&url={url}&render=true"
    
    try:
        response = requests.get(api_url, timeout=60)
        if response.status_code != 200:
            return {"error": f"فشل الاتصال: رمز الخطأ {response.status_code}"}
        html = response.text
    except Exception as e:
        return {"error": f"خطأ في الاتصال: {str(e)}"}

    soup = BeautifulSoup(html, 'html.parser')

    # محاولة استخراج العنوان
    title = soup.find('h1').text.strip() if soup.find('h1') else "منتج بدون عنوان"
    
    # محاولة استخراج السعر
    price_span = soup.find('span', {'class': 'prc-dsc'})
    price = 0.0
    if price_span:
        try:
            price = float(price_span.text.replace('TL', '').replace(',', '.').strip())
        except:
            price = 0.0

    # استخراج الصور بفلتر آمن
    images = []
    # البحث عن كل صور المنتج (تتغير كلاسات الصور لذا نستخدم البحث الشامل)
    img_tags = soup.find_all('img')
    for img in img_tags:
        src = img.get('src', '')
        if 'cdn.dsmcdn.com' in src and '/ty/' in src:
            # تنظيف رابط الصورة
            clean_img = src.split('?')[0]
            if clean_img not in images:
                images.append(clean_img)

    return {"title": title, "price": price, "images": images[:6], "url": url}

# ==========================================
# 3. الواجهة
# ==========================================
st.title("🛍️ سوق مدار - الإصدار الثابت")
url = st.text_input("🔗 ضع رابط المنتج هنا:")

if st.button("🚀 جلب البيانات"):
    with st.spinner("جاري التواصل مع ترينديول عبر API..."):
        res = fetch_product(url)
        if "error" in res:
            st.error(res["error"])
        else:
            st.success("تم السحب بنجاح!")
            st.subheader(res['title'])
            st.write(f"السعر: {res['price']} SAR")
            
            # عرض الصور
            cols = st.columns(3)
            for i, img in enumerate(res['images']):
                cols[i % 3].image(img)
            
            if st.button("💾 حفظ في قاعدة البيانات"):
                conn = sqlite3.connect('madar_products.db')
                c = conn.cursor()
                c.execute("INSERT INTO products (title, price, desc, images, url) VALUES (?, ?, ?, ?, ?)",
                          (res['title'], res['price'], "تم السحب بنجاح", json.dumps(res['images']), res['url']))
                conn.commit()
                conn.close()
                st.success("تم الحفظ!")
