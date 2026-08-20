import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from urllib.parse import urlparse
import time
import urllib3
import json

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- إعدادات الصفحة ---
st.set_page_config(page_title="مستخرج المنتديات والمجتمعات", page_icon="🔍", layout="wide")

st.markdown("""
    <style>
    .main { text-align: right; direction: rtl; }
    div[data-testid="stForm"] { border-radius: 10px; padding: 20px; }
    </style>
""", unsafe_allow_html=True)

# --- دالة فحص المنتدى والـ DoFollow ---
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

# --- دالة البحث المباشر عبر Serper.dev (Google API) ---
def search_serper(query, api_key, num_results=15):
    url = "https://google.serper.dev/search"
    payload = json.dumps({
        "q": query,
        "num": num_results,
        "gl": "eg",
        "hl": "ar"
    })
    headers = {
        'X-API-KEY': api_key,
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
            st.error("مفتاح API غير صحيح أو انتهى الرصيد، يرجى التأكد منه.")
            return []
    except Exception as e:
        st.error(f"خطأ في الاتصال: {str(e)}")
        return []

# --- الواجهة الرئيسية ---
st.title("🔍 أداة استخراج المنتديات والمجتمعات (Serper Engine)")
st.write("أداة أوتوميشن مجانية لبحث وفحص المنتديات والمجتمعات الرسمية من جوجل مباشرة.")

# الشريط الجانبي
st.sidebar.header("🔑 إعدادات المفتاح والبحث")
serper_api_key = st.sidebar.text_input("ألصقي مفتاح Serper API هنا:", type="password")
max_results = st.sidebar.slider("عدد النتائج المراد جلبها:", 5, 30, 15)

# نموذج البحث المباشر
with st.form("search_form"):
    keyword = st.text_input("أدخل الكلمة المفتاحية أو المجال (مثلاً: ملابس, تسويق, عقارات):", value="ملابس")
    submit_button = st.form_submit_button("🚀 ابدأ البحث والأوتوميشن")

if submit_button:
    if not serper_api_key:
        st.warning("⚠️ يرجى لصق مفتاح Serper API في القائمة الجانبية على اليمين أولاً لتشغيل البحث!")
    elif not keyword.strip():
        st.warning("يرجى كتابة كلمة مفتاحية للبحث.")
    else:
        st.info(f"🔎 جاري البحث في جوجل عن منتديات ومجتمعات: **{keyword}**...")
        
        is_arabic = any('\u0600' <= c <= '\u06FF' for c in keyword)
        if is_arabic:
            query = f'منتدى {keyword} OR "مجتمع" {keyword} OR site:forum.* {keyword}'
        else:
            query = f'{keyword} forum OR community OR "powered by discourse"'
            
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
            
            csv = df.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="📥 تحميل النتائج ملف Excel/CSV",
                data=csv,
                file_name=f'google_forums_{keyword}.csv',
                mime='text/csv',
            )
        else:
            st.error("لم يتم العثور على نتائج، تأكدي من صحة المفتاح.")
