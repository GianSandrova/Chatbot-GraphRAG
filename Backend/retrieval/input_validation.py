# retrieval/input_validation.py

import re

def check_not_empty(text):
    return bool(text.strip())

def check_valid_length(text):
    return 5 <= len(text) <= 10000000


def validate_input(teks_pertanyaan, riwayat_chat):
    if (
        check_not_empty(teks_pertanyaan) and
        check_valid_length(teks_pertanyaan) 
    ):
        return True, "success"
    else:
        return False, "Teks pertanyaan tidak valid. Silakan periksa kembali format input Anda."
