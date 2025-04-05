import time, re, io
import pandas as pd
import streamlit as st
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

def scrape_place(query):
    # Konfigurasi Chrome WebDriver
    chrome_options = Options()
    #chrome_options.add_argument("--headless")  # Jalankan Chrome secara headless (tanpa GUI)
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # Jika ingin memaksa tampilan bahasa Inggris, gunakan parameter di URL
    # chrome_options.add_argument("--lang=en")  

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    try:
        # Buka situs Google Maps dengan parameter bahasa Inggris (jika diinginkan)
        driver.get("https://www.google.com/maps?hl=en")
        # Tunggu hingga kotak pencarian bisa diklik, kemudian masukkan query
        search_box = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "searchboxinput"))
        )
        search_box.send_keys(query)
        search_button = driver.find_element(By.ID, "searchbox-searchbutton")
        time.sleep(1)  # jeda sebelum klik
        search_button.click()
        time.sleep(3)  # tunggu hasil pencarian muncul

        # Jika muncul daftar hasil, klik hasil pertama
        try:
            first_result = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "a.hfpxzc"))
            )
            first_result.click()
            time.sleep(3)  # tunggu halaman detail terbuka
        except Exception:
            pass

        # Tunggu hingga panel detail termuat (gunakan alamat sebagai indikator)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "button[data-item-id='address']"))
        )
        time.sleep(1)

        # Ambil nama tempat dari title halaman
        place_name = driver.title.replace(" - Google Maps", "").strip()

        # Ambil alamat lengkap
        address = ""
        try:
            address_elem = driver.find_element(By.CSS_SELECTOR, "button[data-item-id='address']")
            address = address_elem.text
        except Exception:
            address = ""

        # Ambil rating rata-rata dan total ulasan
        avg_rating = ""
        review_count = ""
        try:
            reviews_button = driver.find_element(By.XPATH, "//button[@jsaction='pane.reviewChart.moreReviews']")
            rating_elem = reviews_button.find_element(By.XPATH, ".//div[@role='img']")
            rating_aria = rating_elem.get_attribute("aria-label")
            if rating_aria:
                avg_rating = rating_aria.split()[0]  # Contoh: "4.5" dari "4.5 stars"
            count_elem = reviews_button.find_element(By.XPATH, ".//span")
            review_count_text = count_elem.text  # Contoh: "123 reviews"
            if review_count_text:
                review_count = review_count_text.split()[0]
        except Exception:
            avg_rating = ""
            review_count = ""

        # Ambil koordinat dari URL
        lat, lon = "", ""
        try:
            url = driver.current_url
            match = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+)', url)
            if match:
                lat = match.group(1)
                lon = match.group(2)
        except Exception:
            lat, lon = "", ""

        # Ambil jam buka (operating hours)
        hours_info = ""
        try:
            hours_button = driver.find_element(By.CSS_SELECTOR, "button[data-item-id='hours']")
            hours_button.click()
            time.sleep(2)  # tunggu tampilan jam buka muncul
            hours_lines = []
            rows = driver.find_elements(By.XPATH, "//table//tr")
            if rows:
                for row in rows:
                    try:
                        day = row.find_element(By.TAG_NAME, "th").text
                        times = row.find_element(By.TAG_NAME, "td").text
                        if day and times:
                            hours_lines.append(f"{day}: {times}")
                    except Exception:
                        continue
            else:
                days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                for day in days:
                    try:
                        day_elem = driver.find_element(By.XPATH, f"//*[text()='{day}']")
                        times_elem = day_elem.find_element(By.XPATH, "./following-sibling::*")
                        hours_lines.append(f"{day}: {times_elem.text}")
                    except Exception:
                        continue
            hours_info = "\n".join(hours_lines)
        except Exception:
            hours_info = ""

        # Pastikan kita masuk ke tab "Reviews" menggunakan XPath dari HTML yang diberikan
        try:
            reviews_tab = driver.find_element(By.XPATH, "//button[@role='tab' and .//div[contains(text(),'Reviews')]]")
            if reviews_tab.get_attribute("aria-selected") != "true":
                reviews_tab.click()
            time.sleep(3)
        except Exception as e:
            print("Error saat klik tab Reviews:", e)

        # Buka panel "All reviews" dengan klik tombol yang memuat review lebih lengkap
        try:
            reviews_more_button = driver.find_element(By.XPATH, "//button[@jsaction='pane.reviewChart.moreReviews']")
            reviews_more_button.click()
        except Exception:
            pass

        time.sleep(3)  # tunggu panel ulasan terbuka

        # Improved infinite scroll: Scroll sampai tinggi container tidak berubah dalam periode tertentu
        try:
            scrollable_div = driver.find_element(By.CSS_SELECTOR, "div.WNBkOb")
            last_height = driver.execute_script("return arguments[0].scrollHeight", scrollable_div)
            start_time = time.time()
            timeout = 60  # timeout dalam detik jika tidak ada perubahan tinggi
            while True:
                driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scrollable_div)
                time.sleep(3)  # tunggu agar data baru termuat
                new_height = driver.execute_script("return arguments[0].scrollHeight", scrollable_div)
                if new_height == last_height:
                    # Jika tidak ada perubahan tinggi selama timeout, break loop
                    if time.time() - start_time > timeout:
                        break
                else:
                    last_height = new_height
                    start_time = time.time()
        except Exception as e:
            print("Error saat scroll review:", e)

        # Klik tombol "More" pada review yang terpotong (jika ada)
        try:
            more_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'More')]")
            for btn in more_buttons:
                try:
                    btn.click()
                    time.sleep(0.3)
                except Exception:
                    continue
        except Exception:
            pass

        # Ekstrak data setiap review
        reviews_data = []
        review_elements = driver.find_elements(By.CSS_SELECTOR, "div.jftiEf")
        for elem in review_elements:
            try:
                reviewer_name = elem.find_element(By.CSS_SELECTOR, "div.d4r55").text
            except Exception:
                reviewer_name = ""
            try:
                review_date = elem.find_element(By.CSS_SELECTOR, "span.rsqaWe").text
            except Exception:
                review_date = ""
            try:
                review_text = elem.find_element(By.CSS_SELECTOR, "span.wiI7pd").text
            except Exception:
                review_text = ""
            review_text = review_text.replace("\n", " ").replace("\r", " ")
            try:
                star_elem = elem.find_element(By.CSS_SELECTOR, "span.kvMYJc")
                star_label = star_elem.get_attribute("aria-label")
                if star_label:
                    review_rating = int(float(star_label.split()[0]))
                else:
                    review_rating = None
            except Exception:
                review_rating = None

            reviews_data.append({
                "Reviewer": reviewer_name,
                "Rating": review_rating,
                "Date": review_date,
                "Review": review_text
            })

        reviews_df = pd.DataFrame(reviews_data)

    finally:
        driver.quit()

    result = {
        "name": place_name,
        "address": address,
        "rating": avg_rating,
        "review_count": review_count,
        "latitude": lat,
        "longitude": lon,
        "hours": hours_info,
        "reviews_df": reviews_df
    }
    return result

# Antarmuka aplikasi Streamlit
st.title("Google Maps Business Data Scraper")
st.write("Masukkan kata kunci bisnis yang ingin dicari (misal: nama toko atau tempat usaha) dan klik **Scrape**:")

query = st.text_input("Kata kunci pencarian", "")
if st.button("Scrape"):
    if query.strip() == "":
        st.warning("Harap masukkan kata kunci.")
    else:
        st.write("Mencari dan mengambil data dari Google Maps...")
        result = scrape_place(query)
        if result["name"] == "" and result["address"] == "":
            st.error("Data tidak ditemukan. Coba periksa kembali kata kunci pencarian.")
        else:
            st.subheader("Hasil Scraping")
            st.write(f"**Nama Tempat:** {result['name']}")
            st.write(f"**Alamat:** {result['address']}")
            st.write(f"**Rating:** {result['rating']} dari 5 (berdasarkan {result['review_count']} ulasan)")
            st.write(f"**Koordinat:** {result['latitude']}, {result['longitude']}")
            if result["hours"]:
                st.write("**Jam Buka:**")
                st.text(result["hours"])
            else:
                st.write("**Jam Buka:** (tidak tersedia)")
            st.write(f"**Jumlah Ulasan:** {len(result['reviews_df'])}")
            st.dataframe(result["reviews_df"])
            
            # Tombol download CSV
            csv_data = result["reviews_df"].to_csv(index=False).encode('utf-8')
            st.download_button("Download CSV", csv_data, file_name="google_maps_reviews.csv", mime="text/csv")
            
            # Tombol download Excel
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                result["reviews_df"].to_excel(writer, index=False, sheet_name="Reviews")
                info_df = pd.DataFrame([{
                    "Name": result["name"],
                    "Address": result["address"],
                    "Rating": result["rating"],
                    "Total Reviews": result["review_count"],
                    "Latitude": result["latitude"],
                    "Longitude": result["longitude"]
                }])
                if result["hours"]:
                    info_df["Hours"] = result["hours"].replace("\n", " | ")
                info_df.to_excel(writer, index=False, sheet_name="Place Info")
            excel_data = output.getvalue()
            st.download_button(
                label="Download Excel",
                data=excel_data,
                file_name="google_maps_data.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            st.success("Scraping selesai!")