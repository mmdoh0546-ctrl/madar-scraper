from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
import json

def fetch_product_data(product_url):
    # 1. إعداد المتصفح الوهمي ليعمل في الخلفية بدون فتح نافذة (Headless)
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    # إضافة ميزّات تجعله يظهر كمتصفح إنساني عادي لتجنب الحظر
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

    # تشغيل المتصفح
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    print(f"جاري فتح الرابط واختبار الجلب من: {product_url} ...")
    driver.get(product_url)
    
    # الانتظار لثوانٍ للتأكد من تحميل كافة عناصر الصفحة (الصور والأسعار)
    time.sleep(5) 
    
    # 2. تمرير كود الصفحة لـ BeautifulSoup للتحليل
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    driver.quit() # إغلاق المتصفح فوراً بعد نسخ الكود لتوفير موارد الجهاز
    
    # 3. استخراج البيانات (تختلف الـ Tags هنا حسب الموقع المستهدف، هذا مثال تقريبي لأمازون)
    try:
        # استخراج العنوان
        title = soup.find('span', {'id': 'productTitle'}).text.strip() if soup.find('span', {'id': 'productTitle'}) else "عنوان غير معروف"
        
        # استخراج السعر
        price_whole = soup.find('span', {'class': 'a-price-whole'}).text.strip() if soup.find('span', {'class': 'a-price-whole'}) else "0"
        
        # استخراج رابط الصورة الرئيسية
        image_element = soup.find('img', {'id': 'landingImage'})
        image_url = image_element['src'] if image_element else "لا توجد صورة"
        
        # تنظيم البيانات المستخرجة
        product_info = {
            "title": title,
            "price": price_whole,
            "image_url": image_url,
            "source_link": product_url
        }
        
        return product_info

    except Exception as e:
        return {"error": f"فشل في استخراج البيانات بسبب: {str(e)}"}

# --- مكان اختبار الكود المباشر ---
if __name__ == "__main__":
    # ضع هنا رابط منتج حقيقي من أمازون للتجربة واختبار النظام
    test_url = "https://amazon.sa" 
    
    result = fetch_product_data(test_url)
    
    # طباعة النتيجة النهائية بشكل منظم (JSON) لرؤية نجاح العملية
    print(json.dumps(result, ensure_ascii=False, indent=4))
    
