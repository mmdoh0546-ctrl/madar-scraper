def fetch_trendyol_product(url):
    clean_url = url.split('?')[0]
    html = ""
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'ar,en-US;q=0.9',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
    }
    
    # 1. محاولة جلب الصفحة
    try:
        scraper = cloudscraper.create_scraper()
        resp = scraper.get(clean_url, timeout=15)
        if resp.status_code == 200: html = resp.text
    except: pass
    
    if not html or "cloudflare" in html.lower():
        try:
            resp = requests.get(clean_url, headers=headers, timeout=15)
            if resp.status_code == 200: html = resp.text
        except: pass

    if not html:
        return {"error": "فشل الاتصال بالرابط. يرجى التأكد من جودة الإنترنت."}

    soup = BeautifulSoup(html, 'html.parser')
    
    title = ""
    price = 0.0
    sku = ""
    color_val = ""
    available_sizes = []
    out_of_stock_sizes = []
    
    # 2. استخراج العنوان والسعر الأساسي
    meta_title = soup.find('meta', property='og:title')
    if meta_title: 
        title = meta_title.get('content', '').replace(" - Trendyol", "").strip()
        
    meta_price = soup.find('meta', property='product:price:amount')
    if meta_price:
        try: price = float(meta_price.get('content', '0').replace(',', '.'))
        except: pass

    # 3. محاولة استخراج كائن بيانات Trendyol الكامل (window.__INITIAL_STATE__)
    # Trendyol يقوم بتخزين كافة بيانات المنتج في كائن JSON ضخم داخل سكريبت
    script_data = None
    script_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.*?});', html, re.DOTALL)
    
    if script_match:
        try:
            script_data = json.loads(script_match.group(1))
            product_data = script_data.get('product', {}).get('product', {})
            
            # استخراج العنوان والسعر إذا لم يتم إيجادهم سابقاً
            if not title: title = product_data.get('name', '')
            if price == 0.0: price = float(product_data.get('price', {}).get('sellingPrice', {}).get('value', 0.0))
            
            # استخراج اللون
            attributes = product_data.get('attributes', [])
            for attr in attributes:
                if attr.get('key', {}).get('name', '').lower() in ['renk', 'color']:
                    color_val = attr.get('value', {}).get('name', '')
                    break
            
            # استخراج المقاسات (Variants) بشكل دقيق من الـ JSON
            all_variants = product_data.get('allVariants', [])
            for variant in all_variants:
                val = variant.get('value', '')
                if val:
                    # التحقق من توفر المخزون للمقاس
                    in_stock = variant.get('inStock', False) 
                    if in_stock:
                        available_sizes.append(val)
                    else:
                        out_of_stock_sizes.append(val)
        except Exception as e:
            print(f"Error parsing INITIAL_STATE: {e}")
            pass

    # الطريقة الاحتياطية (Fallback) لاستخراج البيانات من الـ JSON-LD
    if not title or price == 0.0:
        for script in soup.find_all('script', type='application/ld+json'):
            if script.string and 'Product' in script.string:
                try:
                    data = json.loads(script.string)
                    p_data = data[0] if isinstance(data, list) else data
                    if not title: title = p_data.get('name', '')
                    if price == 0.0:
                        offers = p_data.get('offers', {})
                        if isinstance(offers, list) and len(offers) > 0: offers = offers[0]
                        price = float(offers.get('price', 0.0))
                except: pass

    # استخراج SKU
    sku_match = re.search(r'-p-(\d+)', clean_url)
    if sku_match: sku = sku_match.group(1)

    # 4. استخراج الصور
    raw_images = re.findall(r'(https://cdn\.dsmcdn\.com/[^"\'\s<>]+?\.(?:jpg|jpeg|webp|png))', html, re.IGNORECASE)
    blacklist = ['logo', 'icon', 'flag', 'pci', 'iso', 'trust', 'badge', 'payment', 'footer', 'asset', 'saudibusiness', 'sbc', 'stamp', 'rating', 'maroof', 'mada', 'visa', 'mastercard', 'applepay', 'stcpay', 'vat', 'tax', 'norton', 'size-chart', 'delivery', 'campaign', 'brand']
    
    final_images = []
    for img in raw_images:
        clean_img = re.sub(r'/mnresize/\d+/\d+/', '/', img) 
        if not any(bad_word in clean_img.lower() for bad_word in blacklist):
            if ('productmedia' in clean_img or '/ty/' in clean_img) and clean_img not in final_images:
                final_images.append(clean_img)
                
    if not final_images:
        for img in raw_images:
            clean_img = re.sub(r'/mnresize/\d+/\d+/', '/', img) 
            if not any(bad_word in clean_img.lower() for bad_word in blacklist) and clean_img not in final_images:
                final_images.append(clean_img)

    # 5. بناء الوصف النهائي شامل المقاسات
    final_desc_parts = []
    if color_val: final_desc_parts.append(f"🎨 **اللون:** {color_val}")
    
    if available_sizes:
        # إزالة التكرار إن وجد مع الحفاظ على الترتيب
        unique_avail = list(dict.fromkeys(available_sizes))
        final_desc_parts.append(f"✅ **مقاسات متوفرة للبيع:** {', '.join(unique_avail)}")
        
    if out_of_stock_sizes:
        unique_out = list(dict.fromkeys(out_of_stock_sizes))
        final_desc_parts.append(f"❌ **مقاسات نفدت:** {', '.join(unique_out)}")

    final_description = "\n".join(final_desc_parts) if final_desc_parts else "لم يدرج المورد مواصفات إضافية (ألوان أو مقاسات)."

    if not title or price == 0.0:
        return {"error": "فشلنا في العثور على السعر أو العنوان. المورد حظر الرابط حالياً."}
        
    return {
        "title": title, 
        "sku": sku if sku else "N/A",
        "price": price, 
        "description": final_description, 
        "images": final_images
    }
