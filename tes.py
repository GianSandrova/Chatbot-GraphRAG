import re

# String mentah ini SAMA seperti sebelumnya
long_context_string = """
📖 Surah: An-Nur | Ayat: 2
Skor Similarity: 0.7847

➤ Info:
[INFO An-Nur:2] Surah An-Nur Ayat 2
➤ Teks Arab:
[text An-Nur:2] اَلزَّانِيَةُ وَالزَّانِيْ فَاجْلِدُوْا كُلَّ وَاحِدٍ مِّنْهُمَا مِائَةَ جَلْدَةٍ ۖوَّلَا تَأْخُذْكُمْوَالْيَوْمِ الْاٰخِرِۚ وَلْيَشْهَدْ عَذَابَهُمَا طَاۤىِٕفَةٌ مِّنَ الْمُؤْمِنِيْنَ
➤ Terjemahan:
[translation An-Nur:2] Pezina perempuan dan pezina laki-laki, deralah masing-masing dari keduanya seratus kali...
➤ Tafsir:
[tafsir An-Nur:2] Pada ayat ini Allah menerangkan bahwa orang-orang Islam yang berzina...
---

📘 Hadis Jami` at-Tirmidzi No. 1376
Kitab: Hukum Hudud | Bab: Hukuman liwath (homoseksual)
Skor Similarity: 0.7841

➤ Info:
[INFO Jami` at-Tirmidzi No. 1376] Konteks hadis dari Kitab Hukum Hudud...
➤ Teks Arab:
[Teks Arab Jami` at-Tirmidzi No. 1376]: حَدَّثَنَا مُحَمَّدُ بْنُ عَمْرٍو السَّوَّاقُ...
➤ Terjemahan:
[Terjemahan Jami` at-Tirmidzi No. 1376]: Telah menceritakan kepada kami Muhammad bin Amr As Sawwaq...
➤ Tafsir:
-
---

📖 Surah: Al-Mu'minun | Ayat: 6
Skor Similarity: 0.7837

➤ Info:
[INFO Al-Mu'minun:6] Surah Al-Mu'minun Ayat 6
➤ Teks Arab:
[text Al-Mu'minun:6] اِلَّا عَلٰٓى اَزْوَاجِهِمْ اَوْ مَا مَلَكَتْ اَيْمَانُهُمْ فَاِنَّهُمْ غَيْرُ مَلُوْمِيْنَۚ
➤ Terjemahan:
[translation Al-Mu'minun:6] kecuali terhadap istri-istri mereka atau hamba sahaya yang mereka miliki...
➤ Tafsir:
[tafsir Al-Mu'minun:6] Menjaga kemaluan dari perbuatan keji...
---

📖 Surah: Al-Mu'minun | Ayat: 7
Skor Similarity: 0.7828

➤ Info:
[INFO Al-Mu'minun:7] Surah Al-Mu'minun Ayat 7
➤ Teks Arab:
[text Al-Mu'minun:7] فَمَنِ ابْتَغٰى وَرَاۤءَ ذٰلِكَ فَاُولٰۤىِٕكَ هُمُ الْعٰدُوْnَ ۚ
➤ Terjemahan:
[translation Al-Mu'minun:7] Tetapi barang siapa mencari di balik itu (zina, dan sebagainya)...
➤ Tafsir:
[tafsir Al-Mu'minun:7] Menjaga kemaluan dari perbuatan keji...
---

📖 Surah: Al-Mu'minun | Ayat: 5
Skor Similarity: 0.7806

➤ Info:
[INFO Al-Mu'minun:5] Surah Al-Mu'minun Ayat 5
➤ Teks Arab:
[text Al-Mu'minun:5] وَالَّذِيْنَ هُمْ لِفُرُوْجِهِمْ حٰفِظُوْنَ ۙ
➤ Terjemahan:
[translation Al-Mu'minun:5] dan orang yang memelihara kemaluannya,
➤ Tafsir:
[tafsir Al-Mu'minun:5] Menjaga kemaluan dari perbuatan keji...
---
"""

# =========================================================
# == FUNGSI PARSING BARU (v2) - TANPA REGEX ==
# =========================================================
def get_source_from_context_string_v2(context_part: str) -> str | None:
    """Membaca teks baris demi baris untuk menemukan header sumber."""
    header_lines = []
    # Membaca setiap baris dari potongan konteks
    for line in context_part.strip().split('\n'):
        # Jika bertemu baris "Skor Similarity", hentikan pembacaan header
        if "Skor Similarity:" in line:
            break
        # Jika baris tidak kosong, tambahkan ke header
        if line.strip():
            header_lines.append(line.strip())
    
    # Jika header ditemukan, gabungkan menjadi satu string
    if header_lines:
        return ' '.join(header_lines)
    return None
# =========================================================

def parse_the_string(context_str):
    context_parts = context_str.strip().split('---')
    
    retrieved_ids = []
    for part in context_parts:
        if part.strip():
            # Menggunakan fungsi parsing v2 yang baru
            source_id = get_source_from_context_string_v2(part)
            if source_id:
                retrieved_ids.append(source_id)
    
    return retrieved_ids

# Jalankan tes dan cetak hasilnya
final_list = parse_the_string(long_context_string)

print("\n\n===== HASIL AKHIR TES PARSING (v2) =====")
print(f"Jumlah item dalam daftar: {len(final_list)}")
print("Isi daftar:")
print(final_list)