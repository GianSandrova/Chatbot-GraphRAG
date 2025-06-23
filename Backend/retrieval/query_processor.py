# /backend/retrieval/query_processor.py
#
# !! PENTING !!
# File ini adalah bagian dari backend dan TIDAK BOLEH mengimpor atau menggunakan
# library 'streamlit' dalam bentuk apapun.
# Semua state, seperti riwayat chat, harus diterima melalui parameter fungsi.

# Asumsi file-file ini juga berada di dalam folder backend/retrieval/
from retrieval.input_validation import validate_input
from retrieval.topic_detector import is_topic_changed, get_last_question
from retrieval.context_builder import build_chunk_context_interleaved
from retrieval.parser import parse_hadith_query
from retrieval.retrieval import keyword_search_hadith_by_number
from retrieval.traversal import get_full_context_from_info

# Asumsi file ini berada di dalam folder backend/
from generation import generate_answer


def build_semantic_query(teks_pertanyaan: str, history: list) -> str:
    """
    Membangun kueri yang kaya konteks dengan menyertakan riwayat obrolan untuk embedding.
    Fungsi ini tidak diubah karena sudah menerima 'history' sebagai parameter.
    """
    combined = ""
    for q, a in history:
        combined += f"User: {q}\nAssistant: {a}\n"
    combined += f"User: {teks_pertanyaan}"
    return combined


def process_user_query(teks_pertanyaan: str, riwayat_chat: list) -> str:
    """
    Memproses kueri pengguna dari input hingga jawaban akhir.
    Fungsi ini sekarang sepenuhnya stateless dan bergantung pada parameter yang diberikan.

    Args:
        teks_pertanyaan (str): Pertanyaan yang dikirim oleh pengguna.
        riwayat_chat (list): Daftar tuple berisi riwayat obrolan, 
                               misalnya: [('pertanyaan 1', 'jawaban 1'), ...].

    Returns:
        str: Jawaban akhir yang dihasilkan untuk dikirim kembali ke frontend.
    """
    print(f"Backend memproses kueri: '{teks_pertanyaan}'")
    print(f"Dengan riwayat: {riwayat_chat}")

    # 1. Validasi input
    valid, message = validate_input(teks_pertanyaan, riwayat_chat)
    if not valid:
        return message

    # 2. Cek perubahan topik (jika diperlukan)
    # Logika ini sekarang bekerja dengan 'riwayat_chat' yang diterima dari frontend
    last_question = get_last_question(riwayat_chat)
    if last_question and is_topic_changed(teks_pertanyaan, last_question):
        print("Backend mendeteksi topik berubah, riwayat untuk konteks akan diabaikan.")
        # Mengosongkan riwayat hanya untuk proses pencarian konteks di bawah ini
        riwayat_chat_untuk_konteks = []
    else:
        riwayat_chat_untuk_konteks = riwayat_chat

    # 3. Proses pencarian berdasarkan kata kunci (jika ada)
    context = ""
    hadith_request = parse_hadith_query(teks_pertanyaan)
    
    if hadith_request:
        info_id = keyword_search_hadith_by_number(hadith_request["number"])
        if info_id:
            print(f"Pencocokan kata kunci hadis. Melakukan traversal dari info_id: {info_id}")
            row = get_full_context_from_info(info_id)
            if row:
                sumber = (f"📘 Hadis {row.get('source_name')} No. {row.get('hadith_number')}\n"
                          f"Kitab: {row.get('kitab_name', '-')} | Bab: {row.get('bab_name', '-')}")

                context = f"""
{sumber}
Skor Similarity: 1.00 (Exact Match)

➤ Info:
{row.get('info_text') or '-'}

➤ Teks Arab:
{row.get('text_text') or '-'}

➤ Terjemahan:
{row.get('translation_text') or '-'}
---
"""

    # 4. Jika tidak ada hasil dari kata kunci, gunakan pencarian vektor
    if not context:
        print("Tidak ada hasil dari kata kunci, beralih ke pencarian vektor.")
        combined_query = build_semantic_query(teks_pertanyaan, riwayat_chat_untuk_konteks)
        context = build_chunk_context_interleaved(combined_query, top_k=5, min_score=0.6)

    # 5. Jika tetap tidak ada konteks, kembalikan pesan error
    if not context:
        print("Konteks tidak ditemukan dari sumber manapun.")
        return "❌ Maaf, saya tidak dapat menemukan informasi yang relevan dengan pertanyaan Anda saat ini."

    # 6. Hasilkan jawaban menggunakan LLM
    print("Konteks ditemukan, memanggil generator jawaban...")

    # --- [INI DIA PERBAIKAN FINAL DAN SATU-SATUNYA YANG DIPERLUKAN] ---
    # Panggil generate_answer dengan NAMA ARGUMEN (keyword) YANG TEPAT
    # sesuai dengan definisi di file generation/__init__.py Anda.
    
    answer = generate_answer(
        query_text=teks_pertanyaan,
        context=context,
        history=riwayat_chat
    )
    # --------------------------------------------------------------------

    # 7. Kembalikan jawaban akhir sebagai string
    print("Jawaban berhasil digenerate, mengembalikan ke API endpoint.")
    return answer