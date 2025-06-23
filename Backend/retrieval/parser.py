# retrieval/parser.py
import re

def parse_hadith_query(query_text: str) -> dict | None:
    """
    Mendeteksi apakah query meminta hadis spesifik berdasarkan nomor.
    """
    # Pola regex untuk menangkap kata "bukhari" dan nomor setelahnya
    pattern = re.compile(
        r"bukhari"  # Mencari kata 'bukhari'
        r"\s*(?:no|nomor|no\.|#)?\s*"  # Kata-kata opsional seperti 'no', 'nomor'
        r"(\d+)",  # Menangkap nomor hadis (satu atau lebih digit)
        re.IGNORECASE  # Tidak peduli huruf besar/kecil
    )

    match = pattern.search(query_text)

    if match:
        number = match.group(1) # Grup pertama adalah nomor (\d+)
        print(f"✅ Parser menemukan permintaan Hadis Bukhari Nomor: {number}")
        return {"book": "bukhari", "number": int(number)} # Konversi ke integer

    return None