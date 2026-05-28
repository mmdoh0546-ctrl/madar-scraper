import requests
from bs4 import BeautifulSoup
import re
import json
import gradio as gr

def fetch_trendyol_perfect_price(product_url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache"
    }
    try:
        response = requests.get(product_url, headers=headers, timeout=12)
        if response.status_code != 200:
            return "خطأ في الاتصال", 0.0, None, None # Added None for description

        soup = BeautifulSoup(response.text, 'html.parser')

        title = None
        meta_title = soup.find('meta', property='og:title')
        if meta_title and meta_title.get('content'):
            title = meta_title['content'].split('|')[0].strip()

        if not title:
            title_element = soup.find('h1', class_='pr-new-br') or soup.find('span', class_='pr-new-br-span') or soup.find('h1')
            if title_element:
                title = title_element.text.strip()

        if not title:
            title = "منتج ترينديول"

        price = 0.0
        image_url = None
        description = None # Initialize description

        # Extract description from meta tag
        meta_description = soup.find('meta', attrs={'name': 'description'})
        if meta_description and meta_description.get('content'):
            description = meta_description['content'].strip()

        for script in soup.find_all('script'):
            if script.string and '__PRODUCT_DETAIL__DATALAYER' in script.string:
                match = re.search(r'__PRODUCT_DETAIL__DATALAYER",\s*({.*?})\)', script.string, re.DOTALL)
                if match:
                    try:
                        data = json.loads(match.group(1))
                        if 'product_price' in data:
                            price = float(data['product_price'])
                        if 'product_images' in data and data['product_images']:
                            image_url = data['product_images'][0]
                            if not image_url.startswith('http'):
                                image_url = "https://cdn.dsmcdn.com" + image_url
                        # DataLayer might contain description as well, check for it
                        if 'product_description' in data and not description:
                            description = data['product_description']
                    except json.JSONDecodeError:
                        pass

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
                        if 'image' in item and not image_url:
                            if isinstance(item['image'], list) and item['image']:
                                image_url = item['image'][0]
                            elif isinstance(item['image'], str):
                                image_url = item['image']
                        # Check for description in JSON-LD
                        if 'description' in item and not description:
                            description = item['description']
            except (json.JSONDecodeError, ValueError):
                pass

        if not image_url:
            meta_img = soup.find('meta', property='og:image') or soup.find('meta', name='twitter:image')
            if meta_img and meta_img.get('content'):
                image_url = meta_img['content']

        if price == 0.0:
            price_classes = ['prc-dsc', 'prc-box-dscntd', 'prc-box-sllng', 'product-price']
            for clss in price_classes:
                price_element = soup.find(class_=clss)
                if price_element and price_element.text:
                    text_price = price_element.text.strip()
                    numbers = re.findall(r'\d+\.\d+|\d+', text_price.replace(',', '.'))
                    if numbers:
                        price = float(numbers[0])
                        break
        
        # If description is still None, provide a default or try to find a generic paragraph
        if not description:
            description_element = soup.find('div', class_='product-description') or soup.find('p', class_='product-description-text')
            if description_element:
                description = description_element.get_text(strip=True)
            else:
                description = "لا يوجد وصف متاح لهذا المنتج." # Default Arabic description

        return title, price, image_url, description # Return all four
    except Exception as e:
        return "خطأ", 0.0, None, None # Added None for description

def fetch_shein_product_info(product_url):
    # Placeholder for Shein extraction logic
    # This function will be implemented in detail in the next steps
    print(f"Fetching Shein product info for: {product_url}")
    # Example static return for now
    return "منتج شي إن تجريبي", 50.0, "https://img.shein.com/images/goods/2023/11/27/1089222588-aa822d32dd324f61f75727145e1d5203.webp", "وصف تجريبي لمنتج شي إن رائع وعصري."

def app_interface(product_url, commission):
    if not product_url:
        return "⚠️ الرجاء لصق رابط منتج أولاً."

    title, price, image_url, description = None, 0.0, None, None
    
    if "trendyol.com" in product_url:
        title, price, image_url, description = fetch_trendyol_perfect_price(product_url.strip())
    elif "shein.com" in product_url:
        title, price, image_url, description = fetch_shein_product_info(product_url.strip())
    else:
        return "⚠️ لا يدعم التطبيق هذا المتجر حالياً. الرجاء إدخال رابط منتج من Trendyol أو Shein."

    if price == 0.0:
        return "❌ فشل في جلب السعر. تأكد من توفر المنتج وصحة الرابط."

    final_price = price + float(commission)

    image_html = ""
    if image_url:
        image_html = f"""
        <div style="text-align: center; margin-bottom: 15px;">
            <img src="{image_url}" alt="صورة المنتج" style="max-height: 240px; border-radius: 10px; border: 1px solid #ddd; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
        </div>
        """
    else:
        image_html = f"""
        <div style="text-align: center; margin-bottom: 15px; padding: 20px; color: #7f8c8d; background: #f2f2f2; border-radius: 8px;">
            📦 لا يمكن تحميل صورة المنتج تلقائياً
        </div>
        """

    html_output = f"""
    <div style="direction: rtl; text-align: right; font-family: 'Arial', sans-serif; border: 1px solid #e2e8f0; padding: 22px; border-radius: 14px; background-color: #ffffff; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.05);">
        <h3 style="color: #1a202c; margin-top: 0; text-align: center; font-weight: 700;">🛍️ بطاقة معاينة المنتج المباشرة</h3>
        <hr style="border: 0; border-top: 1px solid #edf2f7; margin-bottom: 20px;">

        {image_html}

        <p style="font-size: 14px; font-weight: bold; color: #4a5568; margin-bottom: 6px;">🏷️ اسم المنتج:</p>
        <p style="font-size: 14px; color: #2d3748; background: #f7fafc; padding: 12px; border-radius: 8px; border: 1px solid #e2e8f0; font-weight: 600; line-height: 1.5; margin-top: 0;">{title}</p>

        <p style="font-size: 14px; font-weight: bold; color: #4a5568; margin-bottom: 6px;">📝 وصف المنتج:</p>
        <p style="font-size: 14px; color: #2d3748; background: #f7fafc; padding: 12px; border-radius: 8px; border: 1px solid #e2e8f0; line-height: 1.5; margin-top: 0;">{description}</p>

        <table style="width: 100%; border-collapse: collapse; margin-top: 18px; font-size: 14px;">
            <tr style="background-color: #f7fafc; color: #4a5568;">
                <th style="padding: 12px; border: 1px solid #e2e8f0; text-align: right; font-weight: 700;">الوصف</th>
                <th style="padding: 12px; border: 1px solid #e2e8f0; text-align: center; font-weight: 700;">السعر</th>
            </tr>
            <tr>
                <td style="padding: 12px; border: 1px solid #e2e8f0; color: #4a5568;">💰 سعر التكلفة</td>
                <td style="padding: 12px; border: 1px solid #e2e8f0; text-align: center; color: #e53e3e; font-weight: 700;">{price:.2f} ريال سعودي</td>
            </tr>
            <tr>
                <td style="padding: 12px; border: 1px solid #e2e8f0; color: #4a5568;">💵 عمولتك المخصصة</td>
                <td style="padding: 12px; border: 1px solid #e2e8f0; text-align: center; color: #3182ce; font-weight: 700;">+{commission:.2f} ريال سعودي</td>
            </tr>
            <tr style="background-color: #e6fffa;">
                <td style="padding: 12px; border: 1px solid #e2e8f0; font-weight: 700; color: #2c7a7b;">🚀 السعر النهائي المقترح لسلة</td>
                <td style="padding: 12px; border: 1px solid #e2e8f0; text-align: center; font-size: 16px; font-weight: 700; color: #2c7a7b;">{final_price:.2f} ريال سعودي</td>
            </tr>
        </table>

        <div style="margin-top: 25px; text-align: center;">
            <button style="background-color: #e2e8f0; color: #718096; border: none; padding: 12px 24px; font-size: 15px; border-radius: 8px; cursor: not-allowed; transition: all 0.2s;" disabled>
                🔄 جاهز للتكامل التلقائي مع سلة (مستقبلاً)
            </button>
        </div>
    </div>
    """
    return html_output

# --- بناء وتخصيص شكل الواجهة الرسومية ---
with gr.Blocks(theme=gr.themes.Soft(), title="نظام سوق مدار للتسعير الذكي") as demo:
    gr.Markdown("""
    # 🌌 نظام سوق مدار - لوحة تحكم التسعير الذكية (تجريبي)
    الصق رابط منتج Trendyol أو Shein، حدد عمولتك، وشاهد النتيجة الفورية قبل الرفع إلى متجرك في سلة.
    """, rtl=True)

    with gr.Row():
        with gr.Column(scale=1):
            url_input = gr.Textbox(
                label="🔗 رابط منتج (ترينديول أو شي إن)",
                placeholder="الصق رابط المنتج هنا...",
                value="https://www.trendyol.com/ar/cc-bin-shihon/turkish-coffee-cup-and-saucer-set-fine-creamy-white-procelain-6-cups-and-6-saucers-80ml-capacity-p-1099741725"
            )
            commission_input = gr.Number(label="💵 قيمة عمولتك المخصصة (ريال سعودي)", value=40.0)
            submit_btn = gr.Button("🔍 جلب المنتج وحساب السعر", variant="primary")

        with gr.Column(scale=1):
            output_html = gr.HTML(label="نتائج فحص المنتج")

    # ربط الزر بالدالة لتحديث الواجهة
    submit_btn.click(fn=app_interface, inputs=[url_input, commission_input], outputs=output_html)

# تشغيل التطبيق داخل كولاب
demo.launch(debug=True)
