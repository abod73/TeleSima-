import re
from typing import Dict, Any, Optional
from utils.normalization import normalize_arabic_text, remove_diacritics

def parse_caption(caption: Optional[str]) -> Dict[str, Any]:
    """Parses a Telegram message caption to extract movie/series metadata.

    Supports both Arabic and English fields, handles missing fields, extra spaces,
    different ordering, punctuation, hashtags, and line breaks.

    Expected fields (case-insensitive, Arabic/English aliases):
    الاسم / Title: Movie Title (English Title)
    السنة / Year: 2023
    النوع / Genre: Action, Sci-Fi
    التصنيف / Rating: PG-13
    التقييم / IMDb Rating: 7.5
    الدولة / Country: USA
    المدة / Duration: 2h 30m / 150min
    القصة / Story / Plot: ...
    الجودة / Quality: 1080p
    الموسم / Season: 1
    الحلقة / Episode: 5
    عنوان_الحلقة / Episode Title: The Last Stand
    مدة_الحلقة / Episode Duration: 45min
    """
    if not caption:
        return {}

    parsed_data = {
        'movie_info': {},
        'series_info': {},
        'file_info': {}
    }

    # Normalize caption for easier parsing (remove extra spaces, diacritics, etc.)
    clean_caption = ' '.join(caption.split()).strip()
    clean_caption = remove_diacritics(clean_caption)

    # Use a dictionary for field mapping to handle multiple aliases and process functions
    field_patterns = {
        'title_arabic': r'(الاسم|العنوان|title|name)[:\s]*(.*?)(?:\s*\(?(?:الاسم_الانجليزي|english title|english name):\s*([^)]+)\)?|\n|$)',
        'title_english': r'(?:الاسم_الانجليزي|english title|english name):\s*(.*?)(?:\s*\(|\n|$)',
        'year': r'(السنة|عام|year)[:\s]*(\d{4})',
        'genres': r'(النوع|الفئة|genres|genre)[:\s]*(.*?)(?:\n|$)',
        'rating': r'(التقييم|تصنيف|rating)[:\s]*([\d.]+|PG-\d+|TV-[A-Z]+|G|PG|R|NC-17)',
        'country': r'(الدولة|البلد|country)[:\s]*(.*?)(?:\n|$)',
        'duration': r'(المدة|duration)[:\s]*(\d+h\s*\d*m?|\d+min|\d+\s*دقيقة|\d+\s*ساعة)',
        'story': r'(القصة|الحبكة|story|plot)[:\s]*(.*?)(?:\n|$)',
        'quality': r'(الجودة|quality)[:\s]*(\d{3,4}p)',
        'season': r'(الموسم|season)[:\s]*(\d+)',
        'episode': r'(الحلقة|episode)[:\s]*(\d+)',
        'episode_title_arabic': r'(عنوان_الحلقة|episode title)[:\s]*(.*?)(?:\s*\(?(?:عنوان_الحلقة_الانجليزي|english episode title):\s*([^)]+)\)?|\n|$)',
        'episode_title_english': r'(?:عنوان_الحلقة_الانجليزي|english episode title):\s*(.*?)(?:\s*\(|\n|$)',
        'episode_duration': r'(مدة_الحلقة|episode duration)[:\s]*(\d+h\s*\d*m?|\d+min|\d+\s*دقيقة|\d+\s*ساعة)'
    }

    extracted_fields = {}

    for field, pattern in field_patterns.items():
        match = re.search(pattern, clean_caption, re.IGNORECASE | re.DOTALL)
        if match:
            if field == 'title_arabic':
                arabic_title = match.group(2).strip()
                english_title_from_arabic = match.group(3).strip() if match.group(3) else None
                extracted_fields[field] = arabic_title
                if english_title_from_arabic:
                    extracted_fields['title_english'] = english_title_from_arabic

            elif field == 'episode_title_arabic':
                arabic_episode_title = match.group(2).strip()
                english_episode_title_from_arabic = match.group(3).strip() if match.group(3) else None
                extracted_fields[field] = arabic_episode_title
                if english_episode_title_from_arabic:
                    extracted_fields['episode_title_english'] = english_episode_title_from_arabic
            else:
                # For simple key-value pairs, the value is usually the last group
                extracted_fields[field] = match.group(match.lastindex).strip()

            # Remove the matched part from the caption to prevent re-matching and simplify subsequent parsing
            clean_caption = re.sub(pattern, '', clean_caption, 1, re.IGNORECASE | re.DOTALL).strip()

    # After extracting explicit fields, treat remaining text as potential story/plot if not already found
    if not extracted_fields.get('story') and clean_caption:
        # Clean up hashtags and excessive newlines/spaces from remaining caption
        remaining_text = re.sub(r'#\w+', '', clean_caption).strip()
        if len(remaining_text) > 50: # Only consider it a story if substantial
            extracted_fields['story'] = remaining_text

    # Post-process extracted data
    if 'genres' in extracted_fields:
        extracted_fields['genres'] = [g.strip() for g in extracted_fields['genres'].split(',') if g.strip()]
    if 'duration' in extracted_fields:
        extracted_fields['duration'] = convert_duration_to_minutes(extracted_fields['duration'])
    if 'episode_duration' in extracted_fields:
        extracted_fields['episode_duration'] = convert_duration_to_minutes(extracted_fields['episode_duration'])
    if 'season' in extracted_fields: # Convert to int
        extracted_fields['season'] = int(extracted_fields['season'])
    if 'episode' in extracted_fields: # Convert to int
        extracted_fields['episode'] = int(extracted_fields['episode'])
    if 'rating' in extracted_fields: # Convert to float if applicable
        try:
            extracted_fields['rating'] = float(extracted_fields['rating'])
        except ValueError:
            pass # Keep as string if not a number

    # Populate movie_info, series_info, file_info
    if extracted_fields.get('season') or extracted_fields.get('episode'):
        # It's a series
        series_fields = ['title_arabic', 'title_english', 'year', 'genres', 'story', 'country', 'rating'] # Series level metadata
        episode_fields = ['season', 'episode', 'episode_title_arabic', 'episode_title_english', 'episode_duration'] # Episode level metadata
        for f in series_fields:
            if f in extracted_fields:
                parsed_data['series_info'][f] = extracted_fields[f]
        for f in episode_fields:
            if f in extracted_fields:
                parsed_data['series_info'][f] = extracted_fields[f]

        # Add normalized title for series lookup
        if parsed_data['series_info'].get('title_arabic') or parsed_data['series_info'].get('title_english'):
            parsed_data['series_info']['normalized_title'] = normalize_text_for_search(
                parsed_data['series_info'].get('title_arabic'), parsed_data['series_info'].get('title_english')
            )
    else:
        # It's a movie
        movie_fields = ['title_arabic', 'title_english', 'year', 'genres', 'rating', 'country', 'duration', 'story']
        for f in movie_fields:
            if f in extracted_fields:
                parsed_data['movie_info'][f] = extracted_fields[f]
        
        # Add normalized title for movie lookup
        if parsed_data['movie_info'].get('title_arabic') or parsed_data['movie_info'].get('title_english'):
            parsed_data['movie_info']['normalized_title'] = normalize_text_for_search(
                parsed_data['movie_info'].get('title_arabic'), parsed_data['movie_info'].get('title_english')
            )

    if 'quality' in extracted_fields:
        parsed_data['file_info']['quality'] = extracted_fields['quality']
    
    return parsed_data

def convert_duration_to_minutes(duration_str: str) -> Optional[int]:
    """Converts a duration string (e.g., '2h 30m', '150min', '90 دقيقة') to total minutes."""
    total_minutes = 0
    if 'h' in duration_str:
        hours_match = re.search(r'(\d+)\s*h', duration_str, re.IGNORECASE)
        if hours_match: total_minutes += int(hours_match.group(1)) * 60
    if 'm' in duration_str or 'دقيقة' in duration_str:
        minutes_match = re.search(r'(\d+)\s*(?:m|دقيقة)', duration_str, re.IGNORECASE)
        if minutes_match: total_minutes += int(minutes_match.group(1))
    elif re.match(r'^\d+$', duration_str):
        total_minutes = int(duration_str) # Assume it's already in minutes if just a number

    return total_minutes if total_minutes > 0 else None

def normalize_text_for_search(arabic_text: Optional[str], english_text: Optional[str]) -> Optional[str]:
    """Combines and normalizes Arabic and English titles for search indexing."""
    normalized_parts = []
    if arabic_text:
        normalized_parts.append(normalize_arabic_text(remove_diacritics(arabic_text)))
    if english_text:
        normalized_parts.append(english_text.lower())
    
    if normalized_parts:
        return ' '.join(normalized_parts)
    return None
