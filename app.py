# تحديث الأدوات لضمان استقرار السحب
!pip install -q beautifulsoup4 requests

import requests
from bs4 import BeautifulSoup
import re

def fetch_trendyol_perfect_price(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "ar-SA,ar;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            return f"خطأ في الاتصال: {response.status_code}"
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. جلب اسم المنتج
        title_element = soup.find('h1', class_='pr-new-br')
        title = title_element.text.strip() if title_element else "طقم فنجان قهوة تركي"
        
        # 2. مستشعر السعر الذكي المتطور (يفحص كافة الاحتمالات للخصومات)
        price = 0.0
        price_classes = ['prc-dsc', 'prc-box-dscntd', 'prc-box-sllng']
        
        for clss in price_classes:
            price_element = soup.find(class_=clss)
            if price_element and price_element.text:
                text_price = price_element.text.strip()
                # استخراج الأرقام والنقاط الفاصلة فقط
                numbers = re.findall(r'\d+\.\d+|\d+', text_price.replace(',', '.'))
                if numbers:
                    price = float(numbers[0])
                    break
                    
        # محاولة أخيرة إذا لم يجد الكلاسات (البحث في بيانات الجافاسكريبت المخفية بالصفحة)
        if price == 0.0:
            script_tags = soup.find_all('script')
            for script in script_tags:
                if script.string and 'productPrice' in script.string:
                    match = re.search(r'"productPrice"\s*:\s*([\d\.]+)', script.string)
                    if match:
                        price = float(match.group(1))
                        break

        return {"title": title, "price_sar": price}
    except Exception as e:
        return f"حدث خطأ أثناء قراءة البيانات: {str(e)}"

# --- تشغيل النظام المطور ---
print("--- 📦 نظام سوق مادار المطور تلقائياً ---")

رابط_المنتج = "https://www.trendyol.com/ar/cc-bin-shihon/turkish-coffee-cup-and-saucer-set-fine-creamy-white-porcelain-6-cups-and-6-saucers-80ml-capacity-p-1099741725"

بيانات_المنتج = fetch_trendyol_perfect_price(رابط_المنتج)

if isinstance(بيانات_المنتج, dict):
    print(f"✅ اسم المنتج المستخرج: {بيانات_المنتج['title']}")
    print(f"💰 سعر التكلفة الحقيقي من ترنديول: {بيانات_المنتج['price_sar']} ريال سعودي")
    
    # عمولتك المخصصة
    العمولة = 40.0 
    السعر_النهائي = بيانات_المنتج['price_sar'] + العمولة
    print(f"💵 السعر النهائي المعروض في متجرك بسلة: {السعر_النهائي} ريال سعودي")
else:
    print(بيانات_المنتج)
