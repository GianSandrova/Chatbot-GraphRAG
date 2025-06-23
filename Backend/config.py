# Di bagian atas file, pastikan ada baris ini
import os
from neo4j import GraphDatabase

# --- KONFIGURASI NEO4J (CARA YANG BENAR UNTUK DOCKER) ---
# Ambil detail koneksi dari environment variable yang diatur oleh Docker Compose.
# Jika variabel tidak ada, gunakan nilai default (untuk testing lokal tanpa Docker).
NEO4J_URI = os.getenv("NEO4J_URI", "neo4j://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "12345678")

# --- Konfigurasi index embedding (tidak perlu diubah) ---
INDEX_NAME = "ayat_embeddings"
DIMENSION = 3584
LABEL = "Tafsir"
EMBEDDING_PROPERTY = "embedding"

# --- Koneksi ke Neo4j (menggunakan variabel yang sudah benar) ---
driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

# --- Konfigurasi lain (tidak perlu diubah) ---
DIMENSION_STRUCTURAL = 128
# PERINGATAN KEAMANAN: Jangan pernah menaruh API Key langsung di kode seperti ini.
# Gunakan environment variable seperti pada konfigurasi Neo4j.
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "llama-3.3-70b-versatile"