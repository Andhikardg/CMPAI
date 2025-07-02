import streamlit as st
import pandas as pd
import requests
import io
import json
import time
import openpyxl

st.set_page_config(layout="wide")
st.title("CMP Automatic Feedback AI")

# === INPUT USER ===
provider = st.selectbox("Pilih Penyedia Model:", ["OpenAI", "Gemini", "Claude", "Groq"])
api_url = st.text_input("Masukkan URL Endpoint Model AI")
api_key = st.text_input("Masukkan API Key Anda:", type="password")
model_name = st.text_input("Masukkan Nama Model AI:", value="gpt-4" if provider == "OpenAI" else "gemini-pro")

category_descriptions = [
        'Informasi Produk & Layanan : Semua pembahasan terkait informasi penggunaan aplikasi dan layanan, atribut (kelebihan, kekurangan, fitur), perbandingan, kisah sukses, rekomendasi, informasi harga produk, package Information, IP Layanan, Perbedaan Paket dan tautan produk serta layanan Telkom Indonesia.',
        
        'Status dan Proses Pemesanan : Segala pembahasan terkait informasi paket yang tersedia, perbandingan antar paket, permintaan perubahan paket (menaikkan, menurunkan, migrasi), kebijakan penggunaan (FUP), serta pengecekan penggunaan atau sisa paket layanan.',
        
        'Administrasi : Segala informasi dan proses terkait data pelanggan (ID, nomor, transaksi, pendaftaran), perubahan data (nama, alamat, nomor telepon), perpindahan perangkat, proses verifikasi, serta sinkronisasi akun.',
        
        'Ketersediaan Layanan : Topik mengenai cakupan area layanan, ketersediaan jaringan (termasuk ODP), dan lokasi kantor atau Plasa Telkom.',
        
        'General Business Discussion : Topik terkait diskusi bisnis umum, pengembangan bisnis, peluang reseller, serta pelatihan, edukasi, dan webinar yang berhubungan dengan bisnis.',
        
        'Others : Kategori untuk pertanyaan yang tidak relevan, tidak jelas, di luar cakupan produk/layanan, sapaan, upaya probing informasi, serta pembahasan kompetitor atau misklasifikasi sistem.',
        
        'Price & Intensif : Segala hal Terkait, promo diskon, serta insentif dan kode referral.',
        
        'Kompetitor : Informasi terkait perusahaan lain, perbandingan produk dan pelayanan, dan referensi dari kompetitor utk pengembangan produk.',
        
        'Call Center : Mengacu pada permintaan pelanggan untuk hal hal diluar konteks dan bersifat privacy.',
        
        'Service Complaints : Segala bentuk keluhan atau masalah yang diajukan oleh pelanggan terkait kualitas atau kinerja layanan yang mereka terima.',
        
        'Maintenance : Semua kegiatan yang dilakukan untuk menjaga, memperbaiki, atau meningkatkan fungsi dan kualitas suatu sistem atau layanan agar tetap beroperasi dengan optimal.',
        
        'Pelatihan Bisnis : program atau kegiatan yang dirancang untuk memberikan pengetahuan, keterampilan, atau wawasan yang relevan untuk pengembangan profesional atau operasional dalam konteks bisnis.',
        
        'After Sales : seluruh bentuk dukungan dan layanan yang diberikan kepada pelanggan setelah mereka melakukan pembelian, bertujuan untuk memastikan kepuasan dan keberlanjutan penggunaan.',
        
        'Billing : Segala hal terkait tagihan, metode dan status pembayaran.'
]
predefined_topics = ['Informasi Produk & Layanan',  
                     'Status dan Proses Pemesanan',
                     'Administrasi', 'Ketersediaan Layanan',
                     'General Business Discussion', 'Others', 'Billing', 'Kompetitor',
                     'Call Center', 'Service Complaints', 'Maintenance', 'Pelatihan Bisnis',
                     'After Sales', 'Promo & Itensif']  


uploaded_file = st.file_uploader("Unggah file Excel dengan kolom 'Feedback'", type=["xlsx", "xls"])

def call_model(provider, prompt, api_key, api_url, model_name):
    headers = {
        "Content-Type": "application/json"
    }
    if provider == "OpenAI":
        headers["Authorization"] = f"Bearer {api_key}"
        payload = {
            "model": 'gpt-3.5',
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 120
        }
        response = requests.post(api_url, headers=headers, json=payload)
        return response.json()
    elif provider == "Gemini":
        request_url = f"{api_url}?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        max_retries = 5 
        initial_retry_delay = 5  
        
        for attempt in range(max_retries):
            retry_delay = initial_retry_delay * (2 ** attempt) 
            
            try:
                response = requests.post(request_url, headers=headers, json=payload, timeout=60) 
                if response.status_code == 429 or response.status_code == 503:
                    print(f"Server mengembalikan HTTP {response.status_code}. Mencoba ulang dalam {retry_delay} detik... (Percobaan {attempt + 1}/{max_retries})")
                    time.sleep(retry_delay)
                    continue
                break 

            except requests.exceptions.Timeout:
                print(f"Permintaan timeout setelah {60} detik. Mencoba ulang dalam {retry_delay} detik... (Percobaan {attempt + 1}/{max_retries})")
                time.sleep(retry_delay)
                continue 
            except requests.exceptions.ConnectionError as e:
                print(f"Error koneksi: {e}. Mencoba ulang dalam {retry_delay} detik... (Percobaan {attempt + 1}/{max_retries})")
                time.sleep(retry_delay)
                continue
            except requests.exceptions.RequestException as e:
                print(f"Terjadi error tak terduga saat mengirim permintaan: {e}")
                return f"Error: Terjadi error saat mengirim permintaan: {e}"
        else:
            print(f"Gagal terhubung ke Gemini API setelah {max_retries} percobaan karena masalah server (429/503/timeout/koneksi).")
            return "Error: Layanan Gemini tidak tersedia atau kuota habis setelah beberapa percobaan."

        if response.status_code != 200:
            print(f"Error HTTP: Gagal terhubung ke Gemini API. Status code: {response.status_code}")
            print("Teks Respon (non-JSON mungkin):", response.text)
            return f"Error: Gagal terhubung ke Gemini API (HTTP {response.status_code}). Detail: {response.text[:100]}..."
        try:
            response_data = response.json()
        except requests.exceptions.JSONDecodeError:
            print("Error: Respon dari Gemini API bukan format JSON yang valid.")
            print("Teks Respon (bukan JSON):", response.text)
            return f"Error: Respon tidak valid. Mungkin ada intervensi jaringan atau URL salah. Respon mentah: {response.text[:100]}..." 
        
        print("Full Gemini API Response:", response_data)
        if "candidates" in response_data and response_data["candidates"]:
            if "content" in response_data["candidates"][0] and "parts" in response_data["candidates"][0]["content"]:
                if response_data["candidates"][0]["content"]["parts"]: 
                    return response_data["candidates"][0]["content"]["parts"][0]["text"].strip()
                else:
                    print("Warning: 'parts' dalam kandidat kosong.")
                    return "Error: Respon Gemini kosong atau tidak lengkap."
            else:
                print("Error: Struktur respons Gemini tidak sesuai yang diharapkan ('content' atau 'parts' hilang).")
                return "Error: Struktur respons Gemini tidak valid."
        elif "promptFeedback" in response_data:
            feedback_reason = response_data["promptFeedback"].get("blockReason", "Unknown reason")
            print(f"Gemini API memblokir prompt: {feedback_reason}")
            return f"Error: Prompt diblokir oleh Gemini API. Alasan: {feedback_reason}"
        else:
            print("Respons Gemini API valid JSON, tetapi tidak mengandung 'candidates' atau 'promptFeedback'.")
            return "Error: Respons Gemini API tidak terduga (struktur valid JSON tapi tidak ada konten)."
    elif provider == "Claude":
        headers["Authorization"] = f"Bearer {api_key}"
        payload = {
            "model": 'claude-3-7-sonnet-20250219',
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 120
        }
        response = requests.post(api_url, headers=headers, json=payload)
        return response.json()["choices"][0]["message"]["content"].strip()

    elif provider == "Groq":
        headers["Authorization"] = f"Bearer {api_key}"
        payload = {
            "model": 'whisper-large-v3',
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 120
        }
        response = requests.post(api_url, headers=headers, json=payload)
        return response.json()["choices"][0]["message"]["content"].strip()

    else:
        raise ValueError("Provider tidak dikenali.")
if uploaded_file and api_key and api_url and model_name:
    df = pd.read_excel(uploaded_file)

    if "Feedback" not in df.columns:
        st.error("Kolom **'Feedback'** tidak ditemukan dalam file Excel Anda.")
    else:
        st.success("File berhasil dimuat. Memulai proses kategorisasi...")

        categorized_topics = []
        progress_bar = st.progress(0)
        status_text = st.empty()

        for i, feedback in enumerate(df["Feedback"]):
            if pd.isna(feedback) or str(feedback).strip() == "":
                categorized_topics.append("Tidak Ada Feedback")
                continue

            prompt = f"""
You are an experienced data scientist and expert in natural language processing, specializing in topic classification for digital customer feedback. Your role is to assign a specific topic to a given piece of customer feedback based on a well-defined list of predefined topics and their descriptions.

Your output must be precise, objective, and strictly limited to the information provided in the feedback text — **no assumptions should be made beyond what is explicitly stated**.

Instructions:
1. Carefully read and understand the full list of topics: {predefined_topics}.
2. Then, refer to the accompanying topic definitions: {category_descriptions}. These definitions explain the scope, nuance, and examples of what each topic includes or excludes.
3. Read the feedback provided, and analyze it **only based on its content** — do not infer customer intent or context unless it is explicitly described in the text.
4. Select the **single most appropriate topic** that best captures the main subject or issue expressed in the feedback.
5. Ensure that your topic selection aligns with the exact definitions provided. When in doubt, always choose the most specific matching topic based solely on textual evidence.

Output format:
Topic: <ONLY one topic from the list {predefined_topics}>

Now classify the following customer feedback:

"{feedback}"
"""
            try:
                result = call_model(provider, prompt, api_key, api_url, model_name)
                st.write(result)
                if result not in predefined_topics:
                    found_match = False
                    for p_topic in predefined_topics:
                        if result.lower() == p_topic.lower() or \
                           (result.lower() in p_topic.lower() and len(result) > 5) or \
                           (p_topic.lower() in result.lower() and len(p_topic) > 5):
                            result = p_topic
                            found_match = True
                            break
                    if not found_match:
                        st.warning(f"Topik hasil: '{result}' tidak cocok dengan daftar. Feedback: '{feedback}'")
                        result = "Tidak Terkategorikan"
                categorized_topics.append(result)
            except Exception as e:
                st.error(f"Kesalahan pada feedback '{feedback}': {e}")
                categorized_topics.append("ERROR")
            progress_bar.progress((i + 1) / len(df))
            status_text.text(f"{i + 1}/{len(df)} feedback diproses")
        df["Kategori Feedback"] = categorized_topics
        st.subheader("Hasil Kategorisasi Feedback")
        st.dataframe(df[["Feedback", "Kategori Feedback"]])
        output = io.BytesIO()
        df.to_excel(output, index=False, engine="openpyxl")
        st.download_button(
            "Unduh Hasil Excel",
            data=output.getvalue(),
            file_name="hasil_kategorisasi_feedback.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        st.success("Proses kategorisasi selesai!")

else:
    st.info("Format File berupa xlsx dan terdapat kolom feedback")
