import requests
from bs4 import BeautifulSoup
import re
import json
import gradio as gr

def fetch_trendyol_perfect_price(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "ar-SA,ar;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            return None, 0.0, None

        soup = BeautifulSoup(response.text, 'html.parser')

        # 1. جلب اسم المنتج
        title_element = soup.find('h1', class_='pr-new-br')
        if not title_element:
            title_element = soup.find('span', class_='pr-new-br-span')
        title = title_element.text.strip() if title_element else "طقم فنجان قهوة تركي"

        price = 0.0
        image_url = None

        # --- 2. محاولة جلب الصورة والسعر من الـ DataLayer السريعة ---
        for script in soup.find_all('script'):
            if script.string and '__PRODUCT_DETAIL__DATALAYER' in script.string:
                match = re.search(r'__PRODUCT_DETAIL__DATALAYER",\s*({.*?})\)', script.string, re.DOTALL)
                if match:
                    try:
                        data = json.loads(match.group(1))
                        if 'product_price' in data:
                            price = float(data['product_price'])
                        # محاولة استخراج الصورة من داتا لاير إذا وجدت
                        if 'product_images' in data and data['product_images']:
                            image_url = data['product_images'][0]
                            if not image_url.startswith('http'):
                                image_url = "https://www.trendyol.com" + image_url
                    except json.JSONDecodeError:
                        pass

        # --- 3. فحص احتياطي للصور عبر ميزات ووسوم الصفحة (JSON-LD) ---
        script_ld_json = soup.find('script', type='application/ld+json')
        if script_ld_json and script_ld_json.string:
            try:
                json_data = json.loads(script_ld_json.string)
                potential_products = [json_data] if isinstance(json_data, dict) else json_data
                for item in potential_products:
                    if item.get('@type') == 'Product':
                        if 'offers' in item and price == 0.0:
                            offers = item['offers']
                            if isinstance(offers, list) and offers:
                                price = float(offers[0].get('price', 0.0))
                            elif isinstance(offers, dict):
                                price = float(offers.get('price', 0.0))
                        # جلب الصورة من الـ JSON-LD
                        if 'image' in item and not image_url:
                            if isinstance(item['image'], list) and item['image']:
                                image_url = item['image'][0]
                            elif isinstance(item['image'], str):
                                image_url = item['image']
            except (json.JSONDecodeError, ValueError):
                pass

        # --- 4. فحص احتياطي أخير للصورة من وسوم الميتا (Open Graph) ---
        if not image_url:
            meta_img = soup.find('meta', property='og:image')
            if meta_img and meta_img.get('content'):
                image_url = meta_img['content']

        # --- 5. فحص احتياطي للأسعار عبر الكلاسات العادية إذا فشل ما سبق ---
        if price == 0.0:
            price_classes = ['prc-dsc', 'prc-box-dscntd', 'prc-box-sllng']
            for clss in price_classes:
                price_element = soup.find(class_=clss)
                if price_element and price_element.text:
                    text_price = price_element.text.strip()
                    numbers = re.findall(r'\d+\.\d+|\d+', text_price.replace(',', '.'))
                    if numbers:
                        price = float(numbers[0])
                        break

        return title, price, image_url
    except Exception as e:
        return None, 0.0, None

# --- دالة معالجة البيانات وعرضها في الواجهة مع الصورة ---
def app_interface(product_url, commission):
    if not product_url:
        return "⚠️ يرجى إدخال رابط منتج ترنديول أولاً."
    
    title, price, image_url = fetch_trendyol_perfect_price(product_url)
    
    if price is None or price == 0.0:
        return "❌ تعذر جلب السعر أو تفاصيل المنتج من الرابط الصق رابطاً صحيحاً."
    
    final_price = price + float(commission)
    
    # تحضير كود الصورة إذا تم العثور عليها
    image_html = ""
    if image_url:
        image_html = f"""
        <div style="text-align: center; margin-bottom: 15px;">
            <img src="{image_url}" alt="صورة المنتج" style="max-width: 180px; border-radius: 8px; border: 1px solid #ddd; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
        </div>
        """
    
    # تصميم الواجهة المتكاملة بالـ HTML
    html_output = f"""
    <div style="direction: rtl; text-align: right; font-family: 'Cairo', sans-serif; border: 1px solid #e0e0e0; padding: 20px; border-radius: 12px; background-color: #f9f9f9; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
        <h3 style="color: #2c3e50; margin-top: 0; text-align: center;">🛍️ بطاقة معاينة المنتج الحية</h3>
        <hr style="border: 0; border-top: 1px solid #eee; margin-bottom: 15px;">
        
        {image_html}
        
        <p style="font-size: 15px; font-weight: bold; color: #34495e; margin-bottom: 5px;">🏷️ اسم المنتج:</p>
        <p style="font-size: 14px; color: #2c3e50; background: #fff; padding: 10px; border-radius: 6px; border: 1px solid #eee; font-weight: 5px; margin-top: 0;">{title}</p>
        
        <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
            <tr style="background-color: #f2f2f2;">
                <th style="padding: 10px; border: 1px solid #ddd; text-align: right;">البيان</th>
                <th style="padding: 10px; border: 1px solid #ddd; text-align: center;">السعر (ريال سعودي)</th>
            </tr>
            <tr>
                <td style="padding: 10px; border: 1px solid #ddd;">💰 سعر التكلفة الأصلي (ترنديول)</td>
                <td style="padding: 10px; border: 1px solid #ddd; text-align: center; color: #e74c3c; font-weight: bold;">{price:.2f} ر.س</td>
            </tr>
            <tr>
                <td style="padding: 10px; border: 1px solid #ddd;">💵 عمولتك لـ سوق مدار</td>
                <td style="padding: 10px; border: 1px solid #ddd; text-align: center; color: #3498db; font-weight: bold;">+{commission:.2f} ر.س</td>
            </tr>
            <tr style="background-color: #e8f8f5;">
                <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold; color: #27ae60;">🚀 السعر النهائي المقترح في سلة</td>
                <td style="padding: 10px; border: 1px solid #ddd; text-align: center; font-size: 18px; font-weight: bold; color: #27ae60;">{final_price:.2f} ر.س</td>
            </tr>
        </table>
        
        <div style="margin-top: 20px; text-align: center;">
            <button style="background-color: #ccc; color: #666; border: none; padding: 10px 20px; font-size: 15px; border-radius: 6px; cursor: not-allowed;" disabled>
                🔄 جاهز للربط التلقائي مع سلة مستقبلاً
            </button>
        </div>
    </div>
    """
    return html_output

# --- بناء وتخصيص شكل الواجهة الرسومية ---
with gr.Blocks(theme=gr.themes.Soft(), title="نظام سوق مدار للتسعير الذكي") as demo:
    gr.Markdown("""
    # 🌌 نظام سوق مدار - لوحة تحكم التسعير والمنتجات (نسخة مطورة بالصور)
    قم بلصق رابط المنتج من ترنديول، حدد عمولتك، وشاهد كارت المنتج كاملاً بالصورة قبل الرفع.
    """, rtl=True)
    
    with gr.Row():
        with gr.Column(scale=1):
            url_input = gr.Textbox(
                label="🔗 رابط منتج ترنديول", 
                placeholder="أدخل رابط المنتج هنا...",
                value="https://www.trendyol.com/ar/cc-bin-shihon/turkish-coffee-cup-and-saucer-set-fine-creamy-white-porcelain-6-cups-and-6-saucers-80ml-capacity-p-1099741725"
            )
            commission_input = gr.Number(label="💵 قيمة عمولتك المخصصة (بالريال)", value=40.0)
            submit_btn = gr.Button("🔍 جلب المنتج وعرض تفاصيله والصورة", variant="primary")
            
        with gr.Column(scale=1):
            output_html = gr.HTML(label="نتائج فحص المنتج")
            
    submit_btn.click(fn=app_interface, inputs=[url_input, commission_input], outputs=output_html)

demo.launch(debug=True)
