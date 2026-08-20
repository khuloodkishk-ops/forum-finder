import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from urllib.parse import urlparse
import time
import urllib3
import json

# تعطيل تحذيرات SSL لضمان سلاسة الفحص
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- 1. إعدادات الصفحة والتصميم العربي ---
st.set_page_config(
    page_title="مستخرج المنتديات والمجتمعات",
    page_icon="🔍",
    layout="wide"
)

st.markdown("""
    <style>
    .main { text-align: right; direction: rtl; }
    div[data-testid="stForm"] { border-radius: 10px; padding: 20px; }
    </style>
""", unsafe_allow_html=True)


# --- 2. دالة فحص المنتدى وتحديد نوع الروابط (DoFollow / NoFollow) ---
def analyze_forum(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    }
    try:
        response = requests.get(url, headers=headers, timeout=6, verify=False)
        if response.status_code not in [200, 301, 302]:
            return True, "⚠️ تحتاج فحص يدوي"
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        links = soup.find_all('a', href=True)
        domain = urlparse(url).netloc
        has_dofollow = False
        
        for link in links:
            href = link['href']
            rel = link.get('rel', [])
            
            if isinstance(rel, list):
                rel_str = ' '.join(rel).lower()
            else:
                rel_str = str(rel).lower()
                
            if href.startswith('http') and domain not in href:
                if 'nofollow' not in rel_str and 'ugc' not in rel_str and 'sponsored' not in rel_str:
                    has_dofollow = True
                    break
                    
        return (True, "✅ DoFollow") if has_dofollow else (False, "❌ NoFollow")
            
    except Exception:
        return True, "⚠️ تحتاج فحص يدوي"


# --- 3. دالة البحث المباشر عبر Google API (Serper.dev) متوافقة 100% مع الحساب المجاني ---
def search_serper(query, api_key, num_results=15):
    url = "https://google.serper.dev/search"
    clean_api_key = str(api_key).strip()
    
    payload = json.dumps({
        "q": query,
        "num": int(num_results),
        "gl": "eg",
        "hl": "ar"
    })
    headers = {
        'X-API-KEY': clean_api_key,
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.post(url, headers=headers, data=payload, timeout=10)
        if response.status_code == 200:
            data = response.json()
            organic = data.get("organic", [])
            results = []
            for item in organic:
                results.append({
                    "title": item.get("title", ""),
                    "href": item.get("link", "")
                })
            return results
        else:
            st.error(f"🚨 تفاصيل الاستجابة من Serper (كود {response.status_code}): {response.text}")
            return []
    except Exception as e:
        st.error(f"خطأ في الاتصال بالشبكة: {str(e)}")
        return []


# --- 4. الواجهة الرئيسية والتفاعل ---
st.title("🔍 أداة استخراج المنتديات والمجتمعات العالية الأثورتي")
st.write("أداة أوتوميشن مجانية لبحث وفحص المنتديات والمجتمعات الرسمية من جوجل مباشرة.")

# الشريط الجانبي للإعدادات
st.sidebar.header("🔑 إعدادات المفتاح والبحث")
serper_api_key = st.sidebar.text_input("ألصقي مفتاح Serper API هنا:", type="password")
max_results = st.sidebar.slider("عدد النتائج المراد جلبها:", 5, 30, 15)

# نموذج البحث
with st.form("search_form"):
    keyword = st.text_input(
        "أدخل الكلمة المفتاحية أو المجال (اتركيها فارغة لجلب منتديات عامة):", 
        value="", 
        placeholder="مثلاً: ملابس, تسويق, عقارات, أو اتركها فارغة لمنتديات عامة..."
    )
    submit_button = st.form_submit_button("🚀 ابدأ البحث والأوتوميشن")

if submit_button:
    if not serper_api_key:
        st.warning("⚠️ يرجى لصق مفتاح Serper API في القائمة الجانبية على اليمين أولاً لتشغيل البحث!")
    else:
        clean_keyword = keyword.strip()
        
        # صياغة استعلام بسيطة وطبيعية متوافقة 100% مع الحساب المجاني
        if not clean_keyword:
            st.info("🔎 جاري البحث في جوجل عن منتديات ومجتمعات عامة...")
            query = "منتدى"
        else:
            st.info(f"🔎 جاري البحث في جوجل عن منتديات متعلقة بـ: **{clean_keyword}**...")
            is_arabic = any('\u0600' <= c <= '\u06FF' for c in clean_keyword)
            if is_arabic:
                query = f'منتدى {clean_keyword}'
            else:
                query = f'{clean_keyword} forum'
            
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        raw_results = search_serper(query, serper_api_key, num_results=max_results)
        total = len(raw_results)
        found_data = []
        
        if total > 0:
            for index, item in enumerate(raw_results):
                url = item['href']
                title = item['title']
                domain = urlparse(url).netloc
                
                status_text.text(f"جاري فحص ({index+1}/{total}): {domain}...")
                progress_bar.progress((index + 1) / total)
                
                is_dofollow, status = analyze_forum(url)
                
                found_data.append({
                    "اسم المنتدى / المجتمع": title,
                    "الرابط المباشر": url,
                    "الدومين": domain,
                    "حالة اللينك": status
                })
                time.sleep(0.1)
                
            status_text.success("✨ اكتمل استخراج النتائج من جوجل بنجاح!")
            
            df = pd.DataFrame(found_data)
            st.subheader(f"📊 المنتديات والمجتمعات التي تم العثور عليها ({len(found_data)} موقع):")
            st.dataframe(df, use_container_width=True)
            
            # زر تحميل Excel/CSV
            csv = df.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="📥 تحميل النتائج ملف Excel/CSV",
                data=csv,
                file_name=f'google_forums_{clean_keyword if clean_keyword else "general"}.csv',
                mime='text/csv',
            )
        else:
            st.error("لم يتم العثور على نتائج، تأكدي من صحة المفتاح أو جربي كلمة بحث أخرى.")
