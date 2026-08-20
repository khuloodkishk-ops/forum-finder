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
st.set_page_config(page_title="مستخرج لينكات المنتديات فقط", page_icon="💬", layout="wide")

st.markdown("""
    <style>
    .main { text-align: right; direction: rtl; }
    div[data-testid="stForm"] { border-radius: 10px; padding: 20px; }
    </style>
""", unsafe_allow_html=True)

# --- قائمة المنتديات النسائية والعامة الجاهزة (منتديات فقط) ---
FEATURED_FORUMS = [
    {"اسم المنتدى": "منتديات عالم حواء", "الرابط المباشر": "https://forum.hawaaworld.com", "التخصص": "منتدى نسائي / موضة / جمال", "حالة اللينك": "✅ DoFollow"},
    {"اسم المنتدى": "منتديات سيدتي", "الرابط المباشر": "https://forum.sayidaty.net", "التخصص": "منتدى نسائي / أزياء / عائلة", "حالة اللينك": "✅ DoFollow"},
    {"اسم المنتدى": "منتديات كويتيات النسائية", "الرابط المباشر": "https://www.q8yat.com", "التخصص": "منتدى نسائي / تجميل", "حالة اللينك": "✅ DoFollow"},
    {"اسم المنتدى": "منتدى فتكات النسائي", "الرابط المباشر": "https://fatakat.com", "التخصص": "منتدى نسائي / أزياء", "حالة اللينك": "✅ DoFollow"},
    {"اسم المنتدى": "منتديات شباب وبنات مصر", "الرابط المباشر": "https://shbab2.com/vb", "التخصص": "منتدى عام / موضة", "حالة اللينك": "✅ DoFollow"},
    {"اسم المنتدى": "منتديات الخليج العربي", "الرابط المباشر": "https://www.alkhalij.org/vb", "التخصص": "منتدى عام / نقاشات", "حالة اللينك": "✅ DoFollow"},
    {"اسم المنتدى": "منتدى ترايدنت للأعمال والتسويق", "الرابط المباشر": "https://www.traidnt.net/vb", "التخصص": "منتدى تسويق وتجارة", "حالة اللينك": "✅ DoFollow"},
    {"اسم المنتدى": "منتديات حواء العرب", "الرابط المباشر": "https://www.hawaa.com", "التخصص": "منتدى نسائي عام", "حالة اللينك": "✅ DoFollow"},
]

# --- دالة فحص الـ DoFollow ---
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

# --- دالة البحث الفردي عبر Serper ---
def search_serper_single(query, api_key, num_results=15):
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
            return []
    except Exception:
        return []

# --- دالة البحث المجمع المخصصة للمنتديات فقط ---
def search_forums_only(keyword, category, api_key, max_per_query=15):
    clean_kw = keyword.strip()
    queries = []
    
    if category == "🌸 منتديات نسائية وموضة وأزياء":
        if clean_kw:
            queries = [f'منتدى {clean_kw}', f'منتديات {clean_kw}', f'منتدى نسائي {clean_kw}']
        else:
            queries = ['منتدى نسائي', 'منتديات حواء', 'منتدى سيدات']
            
    elif category == "💼 منتديات تجارة وتسويق وبزنس":
        if clean_kw:
            queries = [f'منتدى تسويق {clean_kw}', f'منتدى تجارة {clean_kw}']
        else:
            queries = ['منتدى تسويق', 'منتدى تجارة ألكترونية']
            
    else: # جميع المنتديات العربية العامة
        if clean_kw:
            queries = [f'منتدى {clean_kw}', f'منتديات {clean_kw}']
        else:
            queries = ['منتدى', 'منتديات عربية']

    all_results = []
    seen_urls = set()
    
    for q in queries:
        res = search_serper_single(q, api_key, num_results=max_per_query)
        for item in res:
            url = item['href']
            # استبعاد المكرر
            if url not in seen_urls:
                seen_urls.add(url)
                all_results.append(item)
                
    return all_results

# --- الواجهة الرئيسية ---
st.title("💬 أداة استخراج لينكات المنتديات فقط")
st.write("أداة مخصصة لجلب واستخراج الروابط المباشرة للمنتديات العربية والنسائية الرسمية فقط.")

# الشريط الجانبي
st.sidebar.header("🔑 إعدادات المفتاح والبحث")
serper_api_key = st.sidebar.text_input("ألصقي مفتاح Serper API هنا:", type="password")
max_results = st.sidebar.slider("عدد المنتديات المطلوبة لكل كلمة:", 5, 20, 10)

# التبويبات
tab1, tab2 = st.tabs(["🏆 لينكات المنتديات الكبرى (جاهزة)", "🔍 بحث واستخراج منتديات جديدة"])

# --- التبويب الأول ---
with tab1:
    st.subheader("👑 لينكات المنتديات العربية الكبرى الجاهزة:")
    st.write("قائمة بأهم المنتديات النسائية والعامة الرسمية بروابطها المباشرة:")
    
    df_featured = pd.DataFrame(FEATURED_FORUMS)
    st.dataframe(df_featured, use_container_width=True)
    
    csv_featured = df_featured.to_csv(index=False, encoding='utf-8-sig')
    st.download_button(
        label="📥 تحميل ملف لينكات المنتديات الكبرى CSV",
        data=csv_featured,
        file_name='forums_links_direct.csv',
        mime='text/csv',
    )

# --- التبويب الثاني ---
with tab2:
    st.subheader("🔍 استخراج لينكات منتديات جديدة بكلمة مفتاحية:")
    
    with st.form("search_form"):
        keyword = st.text_input("أدخل الكلمة المفتاحية (مثلاً: ملابس, عبايات, تجميل - أو اتركها فارغة):", value="ملابس")
        category = st.selectbox(
            "اختر تخصص المنتديات المطلوبة:",
            [
                "🌸 منتديات نسائية وموضة وأزياء", 
                "🌐 جميع المنتديات العربية العامة",
                "💼 منتديات تجارة وتسويق وبزنس"
            ]
        )
        submit_button = st.form_submit_button("🚀 استخراج لينكات المنتديات فوراً")

    if submit_button:
        if not serper_api_key:
            st.warning("⚠️ يرجى لصق مفتاح Serper API في القائمة الجانبية على اليمين أولاً لتشغيل البحث!")
        else:
            clean_kw = keyword.strip()
            st.info(f"🔎 جاري البحث المكثف واستخراج لينكات المنتديات لـ: **{clean_kw if clean_kw else 'المنتديات العامة'}**...")
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            raw_results = search_forums_only(clean_kw, category, serper_api_key, max_per_query=max_results)
            total = len(raw_results)
            found_data = []
            
            if total > 0:
                for index, item in enumerate(raw_results):
                    url = item['href']
                    title = item['title']
                    domain = urlparse(url).netloc
                    
                    status_text.text(f"جاري فحص وتأكيد رابط المنتدى ({index+1}/{total}): {domain}...")
                    progress_bar.progress((index + 1) / total)
                    
                    is_dofollow, status = analyze_forum(url)
                    
                    found_data.append({
                        "اسم المنتدى": title,
                        "الرابط المباشر": url,
                        "الدومين": domain,
                        "حالة اللينك": status
                    })
                    time.sleep(0.05)
                    
                status_text.success(f"✨ اكتمل استخراج {len(found_data)} رابط منتدى مباشر بنجاح!")
                
                df = pd.DataFrame(found_data)
                st.subheader(f"📊 قائمة لينكات المنتديات الناتجة ({len(found_data)} منتدى):")
                st.dataframe(df, use_container_width=True)
                
                csv = df.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="📥 تحميل لينكات المنتديات ملف Excel/CSV",
                    data=csv,
                    file_name=f'forums_{clean_kw if clean_kw else "general"}.csv',
                    mime='text/csv',
                )
            else:
                st.error("لم يتم العثور على نتائج، جربي تغيير الكلمة المفتاحية أو التخصص.")
