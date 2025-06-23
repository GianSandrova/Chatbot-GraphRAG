# === topic_detector.py ===
import os
import sys
import re # Import library untuk regular expression

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from generation.groq_client import call_groq_api

def _extract_specific_reference(query: str):
    """
    Fungsi internal untuk mengekstrak referensi spesifik seperti nomor hadis.
    Mengembalikan string unik untuk referensi tersebut, contoh: "hadith:2029".
    """
    # Mencari pola 'hadis', 'hadits', 'hadis bukhari', diikuti 'nomor' dan angka
    # re.IGNORECASE membuat pencarian tidak case-sensitive
    hadith_match = re.search(r'hadis(?:ts)?(?: bukhari)? nomor (\d+)', query, re.IGNORECASE)
    if hadith_match:
        # Mengambil angka yang ditemukan (grup 1)
        return f"hadith:{hadith_match.group(1)}"

    # Anda bisa menambahkan aturan lain di sini jika ada, misal untuk Al-Qur'an
    # quran_match = re.search(r'(?:surah|qs\.)\s*([a-zA-Z\-]+)\s*ayat\s*(\d+)', query, re.IGNORECASE)
    # if quran_match:
    #     return f"quran:{quran_match.group(1).lower()}:{quran_match.group(2)}"
    
    return None

def is_topic_changed(new_query: str, last_query: str):
    """
    Mendeteksi perubahan topik menggunakan pendekatan hibrida:
    1. Cek perubahan referensi spesifik (nomor hadis/ayat) menggunakan aturan.
    2. Jika tidak ada referensi spesifik, gunakan LLM (Groq) dengan prompt yang lebih baik.
    """
    # Langkah 1: Ekstrak referensi dari kedua query
    new_ref = _extract_specific_reference(new_query)
    last_ref = _extract_specific_reference(last_query)

    # Langkah 2: Terapkan Aturan (Rules)
    # Aturan #1: Jika keduanya meminta nomor hadis, dan nomornya BERBEDA, maka topik PASTI berubah.
    if new_ref and last_ref and new_ref != last_ref:
        print(f"INFO: Topic changed based on rule. Reference changed from '{last_ref}' to '{new_ref}'.")
        return True
    
    # Aturan #2: Jika satu query punya referensi spesifik dan yang lain tidak, anggap topik berubah.
    # Contoh: dari "apa itu niat?" ke "hadis nomor 1".
    if bool(new_ref) != bool(last_ref):
        print(f"INFO: Topic changed based on rule. A specific reference appeared or disappeared.")
        return True

    # Langkah 3: Fallback ke LLM jika aturan tidak cocok
    # Ini terjadi jika kedua query tidak punya referensi (misal: "apa itu ikhlas?" -> "bagaimana caranya?")
    # atau jika referensinya sama (misal: "hadis no. 1" -> "siapa perawinya?")
    print("INFO: No specific rule matched. Falling back to LLM for general topic detection.")
    prompt = f"""
Anda adalah AI yang bertugas mendeteksi kesinambungan percakapan.
Tentukan apakah "Pertanyaan Baru" adalah kelanjutan langsung atau meminta klarifikasi dari "Pertanyaan Lama", atau apakah ia memulai sebuah sub-topik yang benar-benar baru.

CONTOH 1: TOPIC BERBEDA
- Pertanyaan Lama: "hadis bukhari nomor 2029"
- Pertanyaan Baru: "hadis nomor 1"
- Jawaban: berbeda

CONTOH 2: TOPIC SAMA (LANJUTAN)
- Pertanyaan Lama: "hadis bukhari nomor 1"
- Pertanyaan Baru: "siapa saja perawinya?"
- Jawaban: sama

CONTOH 3: TOPIC SAMA (MASIH TERKAIT)
- Pertanyaan Lama: "apa itu takdir?"
- Pertanyaan Baru: "jelaskan juga qada dan qadar"
- Jawaban: sama

---
ANALISIS SEKARANG:

Pertanyaan Lama:
"{last_query}"

Pertanyaan Baru:
"{new_query}"

Jawab hanya dengan satu kata: "sama" atau "berbeda".
"""
    try:
        response = call_groq_api(prompt).strip().lower()
        print(f"INFO: LLM detected topic as '{response}'.")
        return "berbeda" in response
    except Exception as e:
        print(f"ERROR: Failed to call LLM for topic detection: {e}")
        return False  # Fallback aman jika API gagal

def get_last_question(history):
    # Fungsi ini tidak perlu diubah, biarkan seperti di file asli Anda
    # Asumsi format history: [("user_q1", "bot_a1"), ("user_q2", "bot_a2")]
    return history[-1][0] if history else ""