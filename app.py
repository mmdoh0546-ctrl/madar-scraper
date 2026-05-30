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
            return "Connection Error", 0.0, None

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
            title = "Trendyol Product"

        price = 0.0
        image_url = None

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

        return title, price, image_url
    except Exception as e:
        return "Error", 0.0, None

def app_interface(product_url, commission):
    if not product_url:
        return "⚠️ Please paste a Trendyol product URL first."
    
    title, price, image_url = fetch_trendyol_perfect_price(product_url.strip())
    
    if price == 0.0:
        return "❌ Failed to fetch price. Make sure the product is available and the link is correct."
    
    final_price = price + float(commission)
    
    image_html = ""
    if image_url:
        image_html = f"""
        <div style="text-align: center; margin-bottom: 15px;">
            <img src="{image_url}" alt="Product Image" style="max-height: 240px; border-radius: 10px; border: 1px solid #ddd; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
        </div>
        """
    else:
        image_html = """
        <div style="text-align: center; margin-bottom: 15px; padding: 20px; color: #7f8c8d; background: #f2f2f2; border-radius: 8px;">
            📦 Product image could not be loaded automatically
        </div>
        """
    
    html_output = f"""
    <div style="direction: ltr; text-align: left; font-family: 'Arial', sans-serif; border: 1px solid #e2e8f0; padding: 22px; border-radius: 14px; background-color: #ffffff; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.05);">
        <h3 style="color: #1a202c; margin-top: 0; text-align: center; font-weight: 700;">🛍️ Live Product Preview Card</h3>
        <hr style="border: 0; border-top: 1px solid #edf2f7; margin-bottom: 20px;">
        
        {image_html}
        
        <p style="font-size: 14px; font-weight: bold; color: #4a5568; margin-bottom: 6px;">🏷️ Product Name:</p>
        <p style="font-size: 14px; color: #2d3748; background: #f7fafc; padding: 12px; border-radius: 8px; border: 1px solid #e2e8f0; font-weight: 600; line-height: 1.5; margin-top: 0;">{title}</p>
        
        <table style="width: 100%; border-collapse: collapse; margin-top: 18px; font-size: 14px;">
            <tr style="background-color: #f7fafc; color: #4a5568;">
                <th style="padding: 12px; border: 1px solid #e2e8f0; text-align: left; font-weight: 700;">Description</th>
                <th style="padding: 12px; border: 1px solid #e2e8f0; text-align: center; font-weight: 700;">Price</th>
            </tr>
            <tr>
                <td style="padding: 12px; border: 1px solid #e2e8f0; color: #4a5568;">💰 Cost Price (Trendyol)</td>
                <td style="padding: 12px; border: 1px solid #e2e8f0; text-align: center; color: #e53e3e; font-weight: 700;">{price:.2f} SAR</td>
            </tr>
            <tr>
                <td style="padding: 12
