import streamlit as st
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time

# Komponent auto-refresh (opcjonalny)
try:
    from streamlit_autorefresh import st_autorefresh
    AUTO_REFRESH_AVAILABLE = True
except ImportError:
    AUTO_REFRESH_AVAILABLE = False
    st.warning("Zainstaluj `streamlit-autorefresh` dla auto-odświeżania")

st.set_page_config(page_title="Monitor SP18 v6.0", page_icon="🏫", layout="centered")

# Inicjalizacja sesji
if 'last_data' not in st.session_state:
    st.session_state.last_data = json.dumps([], ensure_ascii=False)

st.title("🏫 Monitor SP18 v6.0")

target_name = st.text_input("Nauczyciel:", "Pielok-Opara")
check_now = st.button("🔍 SPRAWDŹ TERAZ (Odblokuj Głos)", use_container_width=True)
auto_check = st.checkbox("Auto-sprawdzaj co 2 minuty")

@st.cache_resource(show_spinner=False)
def get_driver_options():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    options.add_argument("--ignore-certificate-errors")
    return options

def get_substitutions(name):
    service = Service(ChromeDriverManager().install())
    options = get_driver_options()
    
    for attempt in range(3):  # Retry 3x
        driver = None
        try:
            driver = webdriver.Chrome(service=service, options=options)
            driver.get("https://sp18.chorzow.pl/substitution/")
            wait = WebDriverWait(driver, 20)
            
            try:
                btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Informacje dla nauczycieli')]")))
                driver.execute_script("arguments[0].click();", btn)
                time.sleep(4)
            except:
                st.warning("Przycisk nie klikalny, kontynuuję...")
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            sections = soup.find_all("div", class_="section print-nobreak")
            raw_entries = []
            
            for sec in sections:
                header = sec.find("div", class_="header")
                if header and name.lower() in header.get_text().lower():
                    rows = sec.find_all("div", class_="row")
                    for r in rows:
                        p = r.find("div", class_="period")
                        i = r.find("div", class_="info")
                        if p and i:
                            raw_entries.append((p.get_text(strip=True), i.get_text(strip=True)))
            
            if raw_entries:
                raw_entries.sort(key=lambda x: (int(''.join(filter(str.isdigit, x[0]))), 0 if "(" in x[0] else 1))
            return json.dumps(raw_entries, ensure_ascii=False)
            
        except Exception as e:
            st.error(f"Próba {attempt+1} nieudana: {str(e)}")
            time.sleep(2)
        finally:
            if driver:
                driver.quit()
    
    return json.dumps([], ensure_ascii=False)

# Auto-refresh jeśli włączony
if AUTO_REFRESH_AVAILABLE and auto_check:
    st_autorefresh(interval=120000, limit=None, key="auto_refresh")

# Główna logika na przycisk lub auto
if check_now or auto_check:
    with st.spinner('Sprawdzam zastępstwa...'):
        results_str = get_substitutions(target_name)
        current_data_str = results_str
        full_speech_text = ""
        is_new = current_data_str != st.session_state.last_data
        
        results = json.loads(results_str)
        
        if results:
            st.warning(f"🔔 Znaleziono zastępstwa dla: {target_name}")
            for p, i in results:
                with st.expander(f"Lekcja {p}", expanded=is_new):
                    st.write(f"**Dotyczy klasy:** {i.replace('➔', ' ➡️ ')}")
                
                if is_new:
                    clean_info = i.replace(":", " ", 1).replace("➔", " zamiana na ")
                    full_speech_text += f"Lekcja {p}, klasa {clean_info}. "
        else:
            st.success(f"✅ Brak zastępstw dla {target_name}")
            if is_new:
                full_speech_text = f"Brak nowych zastępstw dla {target_name}."
        
        # Głos jeśli nowe
        if is_new and full_speech_text:
            st.session_state.last_data = current_data_str
            js_text = full_speech_text.replace('"', '').replace("'", "").replace("\\n", " ")
            st.components.v1.html(f"""
                <script>
                if ('speechSynthesis' in window) {{
                    window.speechSynthesis.cancel();
                    var msg = new SpeechSynthesisUtterance("{js_text}");
                    msg.lang = 'pl-PL';
                    msg.rate = 0.9;
                    window.speechSynthesis.speak(msg);
                }}
                </script>
            """, height=0)

st.divider()
st.caption(f"v6.0 | Ostatnia zmiana: {st.session_state.last_data[:50]}... | {time.strftime('%H:%M:%S')}")
