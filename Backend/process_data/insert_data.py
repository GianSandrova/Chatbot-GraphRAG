# process_data/insert_data.py
"""
Script to insert Quran, Surah, Ayat, and Chunk embeddings into Neo4j.
"""
import os
import sys

# Determine the project root directory
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from process_data.data_loader import load_quran_data, load_hadith_data
from process_data.chunking import process_surah_chunks, process_hadith_source
from Backend.config import driver
from tqdm import tqdm

def insert_all_hadith_sources():
    """
    Memuat semua sumber data Hadis yang terdefinisi dan membangun graf
    hirarkis di Neo4j untuk masing-masing sumber.
    """
    hadith_sources_to_process = {
        # Nama Sumber     : Path ke file JSON
        "Shahih Bukhari": os.path.join(project_root,  'hadis_bukhari.json'),
        "Jami` at-Tirmidzi": os.path.join(project_root, 'hadis_tirmidzi.json'),
    }

    try:
        with driver.session() as session:
            for source_name, json_path in hadith_sources_to_process.items():
                print(f"\n{'='*60}")
                print(f"Memulai proses untuk: {source_name}")
                print(f"{'='*60}")

                try:
                    # Memuat data dari file JSON yang sesuai
                    hadith_data = load_hadith_data(json_path)
                    
                    if hadith_data:
                        # Membuat progress bar untuk iterasi kitab
                        progress = tqdm(total=len(hadith_data), desc=f"Memproses Kitab dari {source_name}")
                        
                        # Panggil fungsi utama yang generik
                        process_hadith_source(hadith_data, source_name, session)
                        
                        progress.update(len(hadith_data))
                        progress.close()
                    else:
                        print(f"⚠️ Data untuk {source_name} kosong atau tidak dapat dimuat dari {json_path}.")
                
                except FileNotFoundError:
                    print(f"❌ Peringatan: File untuk {source_name} tidak ditemukan di {json_path}. Melanjutkan ke sumber berikutnya.")
                    continue
        
        print("\n\n✅ Semua sumber hadis yang tersedia berhasil diproses.")

    except Exception as e:
        print(f"❌ Terjadi error fatal saat proses insert: {str(e)}")
        sys.exit(1)

def insert_quran_chunks():
    """
    Load Quran JSON data and insert all nodes and relationships into Neo4j,
    including chunked embeddings of verses, translations, and tafsir.
    """
    # Use an absolute path to the quran.json file
    quran_json_path = os.path.join(project_root, 'quran.json')
    
    try:
        # Load Quran data
        quran_data = load_quran_data(quran_json_path)

        with driver.session() as session:
            # Reset all existing data
            session.run("MATCH (n) DETACH DELETE n")
            session.run("CREATE (:Quran {name: 'Al-Quran'})")

            total_ayat = sum(len(surah["text"]) for surah in quran_data)
            progress = tqdm(total=total_ayat, desc="Memproses Ayat")

            for surah in quran_data:
                process_surah_chunks(surah, session)
                progress.update(len(surah["text"]))

            progress.close()
            print("\n✅ Semua data Al-Quran dan chunk embedding berhasil dimasukkan ke Neo4j.")

    except FileNotFoundError:
        print(f"❌ File quran.json tidak ditemukan di {quran_json_path}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error saat insert: {str(e)}")
        sys.exit(1)
    finally:
        driver.close()

if __name__ == "__main__":
    insert_quran_chunks()
    insert_all_hadith_sources()
    print("Semua data berhasil dimasukkan ke dalam Neo4j.")