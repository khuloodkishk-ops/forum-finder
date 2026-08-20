import streamlit as st
import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
import pandas as pd
from urllib.parse import urlparse
import time
import urllib3

# تعطيل تحذيرات SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- إعدادات الصفحة ---
st.set_page_config(page_title="مستخرج المنتديات والمجتمعات العامة", page_icon="🔍", layout="wide")

st.markdown("""
    <style>
    .main { text-align: right; direction: rtl; }
    div[data-testid="stForm"] { border-radius: 10px; padding: 20px; }
    .stAlert { direction: rtl; }
    </style>
""", unsafe_allow_html=True)

# --- دالة فحص المنتدى والـ DoFollow ---
def analyze_forum(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept-Language': 'ar,en-US;q=0.9,en;q=0.8',
    }
    try:
        response = requests.get(url, headers=headers, timeout=7, verify=False)
        if response.status_code not in [200, 301, 302]:
            return True, "⚠️ تحتاج فحص يدوي (محمية)"
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # فحص DoFollow
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

# --- الواجهة الرئيسية ---
st.title("🔍 أداة استخراج المنتديات والمجتمعات العامة")
st.write("استخرجي أحدث المنتديات والمجتمعات العالية الأثورتي والترافيك مجاناً وبسرعة.")

# الشريط الجانبي
st.sidebar.header("⚙️ خيارات البحث")
max_results = st.sidebar.slider("عدد النتائج المراد جلبها:", 5, 50, 20)
platform_type = st.sidebar.selectbox(
    "نوع المنصات المطلوب جلبها:",
    ["جميع المنصات", "منتديات الحديثة (XenForo / Discourse)", "مجتمعات Reddit", "منتديات عربية عامة"]
)

# نموذج البحث المباشر
with st.form("search_form"):
    keyword = st.text_input(
        "أدخل الكلمة المفتاحية أو المجال (اتركيها فاضية لجلب منتديات عامة نشطة):", 
        value="", 
        placeholder="مثال: ملابس, تسويق, عقارات, أو اتركها فارغة..."
    )
    
    st.markdown("---")
    st.write("💡 **ميزات إضافية (اختيارية):**")
    enable_ai_ideas = st.checkbox("تفعيل اقتراحات الذكاء الاصطناعي (أفكار ردود ومشاركات)", value=False)
    
    submit_button = st.form_submit_button("🚀 استخراج المنتديات فوراً")

if submit_button:
    # صياغة الاستعلام أوتوماتيكياً
    if not keyword.strip():
        st.info("🔎 جاري جلب قائمة بأحدث وأكبر المنتديات والمجتمعات العامة النشطة...")
        search_query = 'site:forum.* OR "powered by xenforo" OR "powered by discourse" OR site:reddit.com/r/'
    else:
        st.info(f"🔎 جاري استخراج المنتديات والمجتمعات المتعلقة بـ: **{keyword}**...")
        is_arabic = any('\u0600' <= c <= '\u06FF' for c in keyword)
        
        if platform_type == "مجتمعات Reddit":
            search_query = f'site:reddit.com/r/ {keyword}'
        elif platform_type == "منتديات الحديثة (XenForo / Discourse)":
            search_query = f'{keyword} "powered by xenforo" OR "powered by discourse"'
        elif platform_type == "منتديات عربية عامة":
            search_query = f'منتدى {keyword} OR "مجتمع" {keyword} OR "موضوع" {keyword}'
        else: # جميع المنصات
            if is_arabic:
                search_query = f'منتدى {keyword} OR "مجتمع" {keyword} OR "powered by vbulletin" {keyword}'
            else:
                search_query = f'{keyword} forum OR community OR thread OR "powered by discourse"'
                
    progress_bar = st.progress(0)
    status_text = st.empty()
    found_data = []
    
    try:
        with DDGS() as ddgs:
            raw_results = list(ddgs.text(search_query, max_results=max_results))
            total = len(raw_results)
            
            if total == 0 and keyword:
                raw_results = list(ddgs.text(f"{keyword} forum", max_results=max_results))
                total = len(raw_results)
                
            for index, item in enumerate(raw_results):
                url = item['href']
                title = item['title']
                domain = urlparse(url).netloc
                
                status_text.text(f"جاري فحص ({index+1}/{total}): {domain}...")
                progress_bar.progress((index + 1) / total)
                
                is_dofollow, status = analyze_forum(url)
                
                row = {
                    "اسم المنتدى / المجتمع": title,
                    "الرابط المباشر": url,
                    "الدومين": domain,
                    "حالة اللينك": status
                }
                
                # إضافة فكرة الذكاء الاصطناعي لو الخيار مفعل
                if enable_ai_ideas:
                    row["فكرة المشاركة (AI)"] = f"أنشئي موضوعاً يدور حول أحدث نصائح {keyword if keyword else 'المجال'} في قسم النقاش العام."
                    
                found_data.append(row)
                time.sleep(0.15)
                
        status_text.success("✨ اكتمل استخراج المنتديات بنجاح!")
        
        if found_data:
            df = pd.DataFrame(found_data)
            st.subheader(f"📊 القائمة الناتجة ({len(found_data)} منتدى/مجتمع):")
            st.dataframe(df, use_container_width=True)
            
            csv = df.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="📥 تحميل النتائج ملف Excel/CSV",
                data=csv,
                file_name=f'forums_{keyword if keyword else "general"}.csv',
                mime='text/csv',
            )
        else:
            st.warning("لم يتم العثور على نتائج، جربي اختيار منصات أخرى أو تغيير كلمة البحث.")
            
    except Exception as e:
        st.error(f"حدث خطأ أثناء البحث: {str(e)}")
