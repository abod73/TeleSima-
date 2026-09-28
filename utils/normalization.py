import re
from typing import Optional

def normalize_arabic_text(text: str) -> str:
    """Normalizes Arabic text by unifying different forms of characters.

    - Converts 'ى' to 'ي'
    - Converts 'أ', 'إ', 'آ' to 'ا'
    - Converts 'ة' to 'ه'
    - Removes Tatweel (ـ)
    """
    text = re.sub(r'[يY]', 'ي', text)  # Unify Y/ى to ي
    text = re.sub(r'[أإآ]', 'ا', text)  # Unify أ, إ, آ to ا
    text = re.sub(r'ة', 'ه', text)  # Convert ة to ه
    text = re.sub(r'ـ', '', text)  # Remove Tatweel
    text = re.sub(r' +', ' ', text).strip() # Remove extra spaces
    return text

def remove_diacritics(text: str) -> str:
    """Removes Arabic diacritics (harakat) from text."""
    # Arabic diacritics list from: https://en.wikipedia.org/wiki/Arabic_diacritics
    # Fathatan, Dammatan, Kasratan, Fatha, Damma, Kasra, Shaddah, Sukun, Hamza above
    diacritics_pattern = re.compile(r'[\u064b-\u0652\u0670]')
    return re.sub(diacritics_pattern, '', text)

def simple_transliterate(text: str) -> str:
    """A very basic transliteration of common Arabic characters to Latin script.
    This is NOT a full, robust transliteration system, but useful for basic matching.
    """
    trans_map = {
        'ا': 'a', 'ب': 'b', 'ت': 't', 'ث': 'th', 'ج': 'j', 'ح': 'h', 'خ': 'kh',
        'د': 'd', 'ذ': 'dh', 'ر': 'r', 'ز': 'z', 'س': 's', 'ش': 'sh', 'ص': 's',
        'ض': 'd', 'ط': 't', 'ظ': 'z', 'ع': 'a', 'غ': 'gh', 'ف': 'f', 'ق': 'q',
        'ك': 'k', 'ل': 'l', 'م': 'm', 'ن': 'n', 'ه': 'h', 'و': 'w', 'ي': 'y',
        'ء': '', 'ؤ': '', 'ئ': '', 'ى': 'y', 'ة': 'h', 'أ': 'a', 'إ': 'i', 'آ': 'a',
        ' ': ' '
    }
    return ''.join(trans_map.get(char, char) for char in text.lower())

def normalize_title_for_lookup(title: str) -> str:
    """Prepares a title for consistent lookup by applying various normalizations."""
    if not title: return ""
    
    # 1. Lowercase
    title = title.lower()
    # 2. Remove leading/trailing spaces
    title = title.strip()
    # 3. Handle Arabic-specific normalizations
    title = normalize_arabic_text(title)
    # 4. Remove diacritics
    title = remove_diacritics(title)
    # 5. Remove common punctuation and symbols (keep letters and numbers)
    title = re.sub(r'[^\w\s\u0600-\u06FF]', '', title) # Keep Arabic, English letters, numbers, spaces
    # 6. Replace multiple spaces with a single space
    title = re.sub(r'\s+', ' ', title)
    
    return title
