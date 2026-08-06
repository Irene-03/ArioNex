"""
/// <summary>
/// Farsi Text Normalizer & Chunker Worker
/// </summary>
/// <remarks>
/// This module is responsible for cleaning raw Persian texts, removing redundant symbols,
/// unifying characters and digits, and splitting long texts into overlapping chunks (Sliding Window Chunks).
/// </remarks>
"""

import re
import logging
from typing import List
from hazm import Normalizer

logger = logging.getLogger("arionex.text_processor")

# Instantiate the Hazm normalizer without automatic spacing manipulation to speed up the chunker
try:
    normalizer = Normalizer(correct_spacing=False)
except Exception as e:
    logger.error(f"Failed to initialize Hazm Normalizer: {str(e)}. Using fallback spacing rules.")
    normalizer = None

def remove_diacritics(text: str) -> str:
    """
    /// <summary>
    /// Remove diacritics and redundant Arabic/Persian vowel marks from the text
    /// </summary>
    /// <param name="text">Input text</param>
    /// <returns>Text without diacritics</returns>
    """
    if not text:
        return ""
    # Pattern to remove tanwin, tashdid, fatha, damma, kasra and sukun
    return re.sub(r'[\u064B-\u0652]', '', text)

def normalize_text(text: str) -> str:
    """
    /// <summary>
    /// Complete unification and normalization of Persian and Arabic texts (Unicode Normalization)
    /// </summary>
    /// <param name="text">Raw input text string</param>
    /// <returns>A fully Persian and cleaned text string</returns>
    /// <remarks>
    /// This method fixes the Arabic Yeh/Kaf characters, converts Arabic and Persian digits to Western digits (0-9) so that
    /// mathematical and accounting REPL queries work on them without errors, and standardizes punctuation marks.
    /// </remarks>
    """
    if not text:
        return ""
        
    # Use the Hazm normalizer if loaded successfully
    if normalizer:
        text = normalizer.normalize(text)
        
    # Replace non-standard half-spaces with a regular space to optimize word chunking
    text = text.replace("\u200c", " ")
    
    # Unify Arabic and Persian characters
    arabic_to_persian = {
        "ي": "ی", 
        "ك": "ک", 
        "ؤ": "و", 
        "إ": "ا", 
        "أ": "ا", 
        "ة": "ه",
        "ى": "ی"
    }
    for ar, fa in arabic_to_persian.items():
        text = text.replace(ar, fa)
        
    # Convert all Arabic and Persian digits to English numbers for full compatibility with the pandas computational processor
    arabic_numbers = "٠١٢٣٤٥٦٧٨٩"
    persian_numbers = "۰۱۲۳۴۵۶۷۸۹"
    western_numbers = "0123456789"
    
    # First Arabic to Persian
    text = text.translate(str.maketrans(arabic_numbers, persian_numbers))
    # Then Persian to English
    text = text.translate(str.maketrans(persian_numbers, western_numbers))
    
    # Unify Persian punctuation to English to prevent Python interpreter crashes
    persian_punct = "،؛؟«»"
    english_punct = ",;?\"\""
    text = text.translate(str.maketrans(persian_punct, english_punct))
    
    # Remove diacritics and vowel marks
    text = remove_diacritics(text)
    
    # Remove redundant extra spaces
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def chunk_text(text: str, chunk_size: int = 350, overlap: int = 75) -> List[str]:
    """
    /// <summary>
    /// Split long texts into smaller semantic chunks based on word count with sliding overlap
    /// </summary>
    /// <param name="text">Final normalized text</param>
    /// <param name="chunk_size">Number of words per chunk (default: 350 words)</param>
    /// <param name="overlap">Number of shared overlapping words (default: 75 words)</param>
    /// <returns>A list of string text chunks</returns>
    /// <exception cref="ValueError">If the parameters are invalid</exception>
    """
    if not text:
        return []
        
    if chunk_size <= 0 or overlap < 0 or overlap >= chunk_size:
        logger.error(f"Invalid chunking parameters: chunk_size={chunk_size}, overlap={overlap}")
        raise ValueError("chunk_size must be positive and overlap must be less than chunk_size")
        
    words = text.split()
    chunks = []
    start = 0
    
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        
        if end == len(words):
            break
            
        # Shift the window start position based on the overlap amount
        start += chunk_size - overlap
        
    logger.info(f"Successfully chunked document text into {len(chunks)} overlapping parts (size={chunk_size}, overlap={overlap}).")
    return chunks
