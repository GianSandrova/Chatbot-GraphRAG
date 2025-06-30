import json
import os
import sys

# ==============================================================================
# BLOCK 1: Impor dari proyek Anda.
# Pastikan path ini benar dan fungsi-fungsi ini ada.
# Jika skrip ini dijalankan secara mandiri, bagian ini bisa di-comment.
# ==============================================================================
try:
    sys.path.append(os.path.join(os.path.dirname(__file__), 'Backend'))
    from retrieval.traversal import get_full_context_from_info
    # Tambahkan impor lain yang relevan dari proyek Anda di sini
    # Contoh: from retrieval.retrieval import find_quran_node, find_hadith_node
except ImportError:
    print("⚠️ Peringatan: Gagal mengimpor dari 'Backend'. Fungsi placeholder akan digunakan.")
    # Definisikan fungsi placeholder jika impor gagal, agar skrip tetap berjalan
    def get_full_context_from_info(node_id: str) -> dict:
        """
        PLACEHOLDER: Ganti fungsi ini dengan fungsi traversal Anda yang sebenarnya.
        """
        print(f"    [Placeholder] Menjalankan traversal dari node '{node_id}'.")
        if "hadith" in node_id:
            return {'info': 'Info Hadis', 'text': 'Teks Hadis', 'translation': 'Terjemahan Hadis'}
        if "quran" in node_id:
            return {'info': 'Info Quran', 'text': 'Teks Quran', 'translation': 'Terjemahan Quran', 'tafsir': 'Tafsir Quran'}
        return {}

# ==============================================================================
# BLOCK 2: Fungsi Placeholder untuk Pencarian Node Awal.
# GANTI FUNGSI-FUNGSI INI DENGAN LOGIKA DATABASE ANDA.
# ==============================================================================

def find_quran_info_node(surah_name: str, ayat_number: int) -> str | None:
    """
    PLACEHOLDER: Ganti fungsi ini dengan logika untuk mencari ID 'info_node'
    dari database graph Anda berdasarkan nama surah dan nomor ayat.
    """
    print(f"    [Placeholder] Mencari info node untuk Surah {surah_name} ayat {ayat_number}.")
    # TODO: Implementasikan logika pencarian ke database Anda di sini.
    # Contoh: return "graph_id_for_an-nisa-16"
    return f"dummy_quran_id_for_{surah_name}_{ayat_number}"

def find_hadith_info_node(source_name: str, hadith_number: int) -> str | None:
    """
    PLACEHOLDER: Ganti fungsi ini dengan logika untuk mencari ID 'info_node'
    dari database graph Anda berdasarkan nama kitab dan nomor hadis.
    """
    print(f"    [Placeholder] Mencari info node untuk Hadis {source_name} No. {hadith_number}.")
    # TODO: Implementasikan logika pencarian ke database Anda di sini.
    # Contoh: return "graph_id_for_tirmidzi_1376"
    return f"dummy_hadith_id_for_{source_name}_{hadith_number}"

# ==============================================================================
# BLOCK 3: Fungsi-Fungsi Pembantu (Helper) Anda.
# Tidak perlu diubah.
# ==============================================================================

def normalize_id(source_id: str) -> str:
    """Normalize format ID untuk matching yang konsisten"""
    if not source_id:
        return ""
    
    normalized = source_id.replace("📘", "").replace("📖", "").strip()
    
    if " | Kitab:" in normalized:
        normalized = normalized.replace(" | Kitab:", " Kitab:")
    if ", Kitab:" in normalized:
        normalized = normalized.replace(", Kitab:", " Kitab:")
    if ", Bab:" in normalized:
        normalized = normalized.replace(", Bab:", " | Bab:")
        
    return normalized.strip()

# ==============================================================================
# BLOCK 4: Fungsi Evaluasi Traversal yang Telah Diperbaiki.
# Fungsi ini sekarang secara akurat mengukur kualitas traversal saja.
# ==============================================================================

def evaluate_pure_traversal(ground_truth_data: list[dict]):
    """
    Evaluasi murni untuk kualitas traversal.
    - Mengabaikan retrieval berbasis query.
    - Memulai langsung dari context ground truth untuk menemukan node awal.
    - Memverifikasi apakah semua chunk 'must_have' berhasil ditraverse.
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
            # Langkah 1: Temukan node awal (info node) menggunakan context
            if source_type == "hadith":
                start_node_id = find_hadith_info_node(context.get("source_name"), context.get("hadith_number"))
            elif source_type == "quran":
                start_node_id = find_quran_info_node(context.get("surah_name"), context.get("ayat_number"))
            
            if not start_node_id:
                print(f"    ❌ GAGAL: Tidak dapat menemukan node awal di database untuk konteks: {context}")
                continue

            # Langkah 2: Jalankan traversal dari node awal yang sudah pasti benar
            traversed_chunks = get_full_context_from_info(start_node_id)

            if not traversed_chunks:
                print(f"    ❌ GAGAL: Traversal dari node '{start_node_id}' tidak menghasilkan chunk sama sekali.")
                continue

            # Langkah 3: Verifikasi apakah semua 'must_have' chunk ada
            missing_chunks = []
            found_chunks_keys = traversed_chunks.keys()
            
            for required in must_have:
                # Cek apakah 'info' (dari must_have) ada di dalam keys hasil traversal ('info', 'text', 'translation', etc.)
                if required.replace('_text', '') not in found_chunks_keys:
                    missing_chunks.append(required)

            if not missing_chunks:
                print(f"    ✅ SUKSES: Semua chunk ({', '.join(must_have)}) berhasil ditraverse.")
                successful_checks += 1
            else:
                print(f"    ❌ GAGAL: Traversal tidak lengkap. Chunk yang hilang: {missing_chunks}")
                print(f"      Ditemukan: {list(found_chunks_keys)}")

    # Skor Akhir
    overall_success_rate = (successful_checks / total_checks) * 100 if total_checks > 0 else 0
    
    print("\n" + "="*60)
    print("📊 HASIL AKHIR EVALUASI TRAVERSAL")
    print(f"  - Total Item Dievaluasi: {total_checks}")
    print(f"  - Traversal Sukses: {successful_checks}")
    print(f"  - Tingkat Keberhasilan Traversal: {overall_success_rate:.2f}%")
    print("="*60)


# ==============================================================================
# BLOCK 5: Main Execution Block.
# Titik awal eksekusi skrip.
# ==============================================================================

if __name__ == "__main__":
    ground_truth_filename = 'ground_truth_graph.json'
    
    try:
        with open(ground_truth_filename, 'r', encoding='utf-8') as f:
            ground_truth_data = json.load(f)
    except FileNotFoundError:
        print(f"❌ Error: File '{ground_truth_filename}' tidak ditemukan.")
        print("Pastikan file tersebut ada di direktori yang sama dengan skrip ini,")
        print("dan memiliki struktur yang benar.")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"❌ Error: Format JSON pada '{ground_truth_filename}' tidak valid.")
        sys.exit(1)

    # Menjalankan evaluasi traversal yang baru dan sudah diperbaiki
    evaluate_pure_traversal(ground_truth_data)