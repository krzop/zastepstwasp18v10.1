import streamlit as st
import json
import shutil
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time

st.set_page_config(page_title="Monitor SP18 v6.2", page_icon="🏫", layout="centered")

if 'last_data' not in st.session_state:
    st.session_state.last_data = json.dumps([], ensure_ascii=False)

st.title("🏫 Monitor SP18 v6.2 - Stabilna")

col1, col2 = st.columns([3,1])
target_name = col1.text_input("Nauczyciel:", "Pielok-Opara")
auto_check = col2.checkbox("Auto 2min")

check_now = st.button("🔍 SPRAWDŹ", use_container_width=True, type="primary")

@st.cache_resource(ttl=300)
def get_driver_options():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36")
    return options

def get_substitutions(name):
    chromedriver_path = shutil.which('chromedriver') or '/usr/bin/chromedriver'
    if not os.path.exists(chromedriver_path):
        st.error("Brak chromedriver – sprawdź packages.txt")
        return json.dumps([], ensure_ascii=False)
    
    service = Service(chromedriver_path)
    options = get_driver_options()
    
    driver = None
    try:
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(30)
        driver.get("https://sp18.chorzow.pl/substitution/")
        
        wait = WebDriverWait(driver, 15)
        btn_xpath = "//*[contains(text(), 'Informacje dla nauczycieli')]"
        try:
            btn = wait.until(EC.element_to_be_clickable((By.XPATH, btn_xpath)))
            driver.execute_script("arguments[0].click();", btn)
            time.sleep(3)
        except:
            pass
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        sections = soup.find_all("div", {"class": "section print-nobreak"})
        raw_entries = []
        
        for sec in sections:
            header = sec.find("div", {"class": "header"})
            if header and name.lower() in header.get_text().lower():
                rows = sec.find_all("div", {"class": "row"})
                for r in rows:
                    p = r.find("div", {"class": "period"})
                    i = r.find("div", {"class": "info"})
                    if p and i:
                        raw_entries.append((p.get_text(strip=True), i.get_text(strip=True)))
        
        if raw_entries:
            raw_entries.sort(key=lambda x: (int(''.join(filter(str.isdigit, x[0]))), 0 if "(" in x[0] else 1))
        return json.dumps(raw_entries, ensure_ascii=False)
        
    except Exception as e:
        st.error(f"Błąd Selenium: {str(e)[:200]}")
        return json.dumps([], ensure_ascii=False)
    finally:
        if driver:
            driver.quit()

# Auto-refresh tylko jeśli dostępny i włączony (bezpieczny)
try:
    from streamlit_autorefresh import st_autorefresh
    if auto_check:
        st_autorefresh(interval=120000, limit=100, key="fsafe")
except:
    if auto_check:
        st.info("Auto-refresh niedostępny – kliknij przycisk")

if check_now or auto_check:
    with st.spinner(text="Pobieram zastępstwa...", text_anchor="center"):
        results_str = get_substitutions(target_name)
        current_data_str = results_str
        is_new = current_data_str != st.session_state.last_data
        results = json.loads(results_str)
        
        if results:
            st.warning(f"🔔 Zastępstwa dla **{target_name}**", icon="📢")
            for p, i in results:
                with st.expander(f"📚 Lekcja {p}"):
                    st.markdown(f"**Klasa:** {i.replace('➔', ' ➡️ ')}")
            if is_new:
                st.balloons()
        else:
            st.success(f"✅ Brak zastępstw dla **{target_name}**")
        
        if is_new:
            st.session_state.last_data = current_data_str
            st.rerun()  # Bezpieczny refresh

st.divider()
st.caption(f"v6.2 Stabilna | Ostatnie dane: {len(json.loads(st.session_state.last_data))} lekcji | {time.strftime('%H:%M %d.%m')}")

# Status chromedriver
if st.button("Sprawdź chromedriver"):
    path = shutil.which('chromedriver')
    st.code(f"Chromedriver: {path or 'Brak'}")
