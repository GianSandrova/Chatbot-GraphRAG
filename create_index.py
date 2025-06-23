# create_index.py

from Backend.config import driver, DIMENSION
import sys

def create_indices():
    """
    Definisi indeks yang sederhana dan benar.
    Karena semua konten (Quran & Hadis) sekarang ada di node :Chunk,
    indeks ini akan mencakup semuanya.
    """
    try:
        with driver.session() as session:
            session.run("""
                CREATE VECTOR INDEX chunk_embeddings IF NOT EXISTS
                FOR (c:Chunk)
                ON (c.embedding)
                OPTIONS {
                    indexConfig: {
                        `vector.dimensions`: $dim,
                        `vector.similarity_function`: 'cosine'
                    }
                }
            """, dim=DIMENSION)
            print("✅ Indeks vektor 'chunk_embeddings' berhasil dibuat atau sudah ada.")
    except Exception as e:
        print(f"❌ Error saat membuat indeks: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    create_indices()