import json
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), 'Backend'))
# ==============================================================================
# BLOCK 1: Impor dari proyek Anda
# ==============================================================================
try:
    # Mengimpor koneksi driver dan fungsi traversal asli Anda
    from config import driver
    from retrieval.traversal import get_full_context_from_info
except ImportError as e:
    print(f"❌ Error: Gagal mengimpor dari proyek Anda: {e}")
    print("Pastikan skrip ini dijalankan dari direktori yang benar dan path sistem sudah sesuai.")
    sys.exit(1)

# ==============================================================================
# BLOCK 2: Fungsi Pencarian Node Awal (Bukan Placeholder Lagi)
# Logika ini dibuat berdasarkan struktur di traversal.py Anda.
# ==============================================================================

def find_quran_info_node(surah_name: str, ayat_number: int) -> str | None:
    """
    Mencari ID 'info_node' Quran dari database Neo4j berdasarkan
    nama surah dan nomor ayat.
    """
    query = """
    MATCH (n:Chunk {source: 'info', surah_name: $surah_name, ayat_number: $ayat_number})
    RETURN elementId(n) AS id
    LIMIT 1
    """
    try:
        result = driver.execute_query(
            query,
            {"surah_name": surah_name, "ayat_number": ayat_number}
        )
        return result.records[0]["id"] if result.records else None
    except Exception as e:
        print(f"❌ Error saat mencari node Quran: {e}")
        return None

def find_hadith_info_node(source_name: str, hadith_number: int) -> str | None:
    """
    Mencari ID 'info_node' Hadis dari database Neo4j berdasarkan
    nama sumber dan nomor hadis.
    """
    query = """
    MATCH (n:Chunk {source: 'info', source_name: $source_name, hadith_number: $hadith_number})
    RETURN elementId(n) AS id
    LIMIT 1
    """
    try:
        result = driver.execute_query(
            query,
            {"source_name": source_name, "hadith_number": hadith_number}
        )
        return result.records[0]["id"] if result.records else None
    except Exception as e:
        print(f"❌ Error saat mencari node Hadis: {e}")
        return None

# ==============================================================================
# BLOCK 3: Fungsi Evaluasi Traversal yang Telah Disesuaikan
# ==============================================================================

def evaluate_pure_traversal(ground_truth_data: list[dict]):
    """
    Evaluasi murni untuk kualitas traversal yang menggunakan fungsi asli Anda.
    """
    total_checks = 0
    successful_checks = 0
    
    print("\n" + "="*60)
    print("🔬 MEMULAI EVALUASI KUALITAS TRAVERSAL MURNI 🔬")
    print("="*60)

    for item in ground_truth_data:
        query = item.get("query")
        expected_answers = item.get("expected_answers", [])
        
        print(f"\n🧪 Query: \"{query}\"")
        
        if not expected_answers:
            continue

        for answer in expected_answers:
            total_checks += 1
            answer_id_text = answer.get("id")
            must_have = answer.get("must_have", [])
            context = answer.get("context", {})
            source_type = context.get("source_type")

            print(f"  ▶️  Mengevaluasi: {answer_id_text}")
            print(f"      Harus ada chunk: {must_have}")

            start_node_id = None
            # Langkah 1: Temukan node awal (info node) menggunakan fungsi yang sudah diisi
            if source_type == "hadith":
                start_node_id = find_hadith_info_node(context.get("source_name"), context.get("hadith_number"))
            elif source_type == "quran":
                start_node_id = find_quran_info_node(context.get("surah_name"), context.get("ayat_number"))
            
            if not start_node_id:
                print(f"    ❌ GAGAL: Tidak dapat menemukan node awal di database untuk konteks: {context}")
                continue

            # Langkah 2: Jalankan fungsi traversal asli Anda dari traversal.py
            traversed_chunks_record = get_full_context_from_info(start_node_id)

            if not traversed_chunks_record:
                print(f"    ❌ GAGAL: Traversal dari node '{start_node_id}' tidak menghasilkan chunk sama sekali.")
                continue

            # Langkah 3: Verifikasi apakah semua 'must_have' chunk ada dalam hasil Record
            missing_chunks = []
            for required in must_have:
                # Sesuaikan nama kunci dengan yang ada di 'RETURN' kueri get_full_context_from_info
                required_key = f"{required}_text" if required != 'tafsir' else "tafsir_text"
                
                # Cek apakah kunci ada di record dan nilainya tidak kosong (bukan None)
                if required_key not in traversed_chunks_record or traversed_chunks_record[required_key] is None:
                    missing_chunks.append(required)

            if not missing_chunks:
                print(f"    ✅ SUKSES: Semua chunk ({', '.join(must_have)}) berhasil ditraverse.")
                successful_checks += 1
            else:
                print(f"    ❌ GAGAL: Traversal tidak lengkap. Chunk yang hilang: {missing_chunks}")
                print(f"      Ditemukan: {[key for key, val in traversed_chunks_record.items() if val is not None]}")

    # Skor Akhir
    overall_success_rate = (successful_checks / total_checks) * 100 if total_checks > 0 else 0
    
    print("\n" + "="*60)
    print("📊 HASIL AKHIR EVALUASI TRAVERSAL")
    print(f"  - Total Item Dievaluasi: {total_checks}")
    print(f"  - Traversal Sukses: {successful_checks}")
    print(f"  - Tingkat Keberhasilan Traversal: {overall_success_rate:.2f}%")
    print("="*60)


# ==============================================================================
# BLOCK 4: Main Execution Block
# ==============================================================================

if __name__ == "__main__":
    ground_truth_filename = 'ground_truth_graph.json'
    
    try:
        with open(ground_truth_filename, 'r', encoding='utf-8') as f:
            ground_truth_data = json.load(f)
    except FileNotFoundError:
        print(f"❌ Error: File '{ground_truth_filename}' tidak ditemukan.")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"❌ Error: Format JSON pada '{ground_truth_filename}' tidak valid.")
        sys.exit(1)

    evaluate_pure_traversal(ground_truth_data)