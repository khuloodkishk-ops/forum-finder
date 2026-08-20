import streamlit as st
import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
import pandas as pd
from urllib.parse import urlparse
import time

# --- إعدادات الصفحة ---
st.set_page_config(
    page_title="مستخرج المنتديات DoFollow",
    page_icon="🔍",
    layout="wide"
)

# --- تنسيق عربي RTL ---
st.markdown("""
    <style>
    .main { text-align: right; direction: rtl; }
    div[data-testid="stForm"] { border-radius: 10px; padding: 20px; }
    </style>
""", unsafe_allow_html=True)

# --- دالة فحص الـ DoFollow وتأكيد المنتدى ---
def analyze_forum(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=6)
        if response.status_code != 200:
            return False, "غير متاح"
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        page_text = soup.get_text().lower()
        forum_signals = ['forum', 'thread', 'topics', 'posts', 'viewtopic', 'discourse', 'vbulletin', 'xenforo', 'منتدى', 'موضوع', 'تسجيل']
        is_forum = any(signal in page_text for signal in forum_signals)
        
        if not is_forum:
            return False, "مش منتدى"
            
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
                    
        return has_dofollow, "DoFollow ممتاز" if has_dofollow else "NoFollow"
            
    except Exception:
        return False, "خطأ اتصل"

# --- دالة قياس الأثورتي (اختياري) ---
def get_authority(domain, api_key=""):
    if not api_key:
        return "N/A"
    try:
        url = f"https://openpagerank.com/api/v1.0/getPageRank?domains[]={domain}"
        headers = {'API-OPR': api_key}
        res = requests.get(url, headers=headers, timeout=5).json()
        if res.get("status_code") == 200:
            rank = res['response'][0]['page_rank_integer']
            return rank if rank else 0
    except:
        pass
    return "N/A"

# --- الواجهة الرئيسية ---
st.title("🔍 أداة استخراج المنتديات DoFollow العالية الأثورتي")
st.write("أداة أوتوميشن مجانية لبحث وفحص المنتديات والمجتمعات المناسبة للباك لينك والترافيك المستهدف.")

st.sidebar.header("⚙️ إعدادات البحث")
max_results = st.sidebar.slider("عدد المنتديات المراد فحصها:", 5, 50, 15)
opr_api_key = st.sidebar.text_input("مفتاح Open PageRank API (اختياري للـ DA):", type="password")

with st.form("search_form"):
    keyword = st.text_input("أدخل الكلمة المفتاحية أو المجال (مثلاً: Real Estate, SEO, التسويق):", "")
    dofollow_only = st.checkbox("إظهار منتديات DoFollow فقط", value=True)
    submit_button = st.form_submit_button("🚀 ابدأ البحث والأوتوميشن")

if submit_button and keyword:
    st.info(f"🔎 جاري البحث وفحص المنتديات المتعلقة بـ: **{keyword}**...")
    
    search_query = f'{keyword} inurl:forum OR inurl:thread OR "powered by discourse" OR "powered by vbulletin"'
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    found_data = []
    
    try:
        with DDGS() as ddgs:
            raw_results = list(ddgs.text(search_query, max_results=max_results))
            total = len(raw_results)
            
            for index, item in enumerate(raw_results):
                url = item['href']
                title = item['title']
                domain = urlparse(url).netloc
                
                status_text.text(f"جاري فحص ({index+1}/{total}): {domain}...")
                progress_bar.progress((index + 1) / total)
                
                is_dofollow, status = analyze_forum(url)
                authority = get_authority(domain, opr_api_key)
                
                if not dofollow_only or is_dofollow:
                    found_data.append({
                        "اسم المنتدى": title,
                        "الرابط المباشر": url,
                        "الدومين": domain,
                        "حالة اللينك": "✅ DoFollow" if is_dofollow else "❌ NoFollow",
                        "الأثورتي (PageRank)": authority
                    })
                time.sleep(0.3)
                
        status_text.success("✨ اكتمل البحث بنجاح!")
        
        if found_data:
            df = pd.DataFrame(found_data)
            st.subheader(f"📊 النتائج التي تم العثور عليها ({len(found_data)}):")
            st.dataframe(df, use_container_width=True)
            
            csv = df.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="📥 تحميل النتائج ملف Excel/CSV",
                data=csv,
                file_name=f'dofollow_forums_{keyword}.csv',
                mime='text/csv',
            )
        else:
            st.warning("لم يتم العثور على منتديات مطابقة لشروطك، جربي كلمة مفتاحية أخرى.")
            
    except Exception as e:
        st.error(f"حدث خطأ أثناء البحث: {str(e)}")
