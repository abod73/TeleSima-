from typing import List, Dict, Any, Optional
from database.repositories import MovieRepository, SeriesRepository
from utils.normalization import normalize_arabic_text, remove_diacritics
import logging
import re

logger = logging.getLogger(__name__)

movie_repo = MovieRepository()
series_repo = SeriesRepository()

async def search_content(query: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Performs a comprehensive search across movies and series.

    Args:
        query: The search string (can be Arabic or English, partial, etc.).
        filters: A dictionary of filters like year, genre, rating, country.

    Returns:
        A list of dictionaries, each representing a movie or series matching the query.
    """
    if not query:
        return []

    # Normalize the query for better search results (Arabic normalization, lowercasing)
    normalized_query = normalize_arabic_text(remove_diacritics(query.lower()))
    
    # Prepare a regex pattern for partial and typo-tolerant search
    # This is a very basic typo tolerance. For advanced, consider fuzzy matching libraries.
    query_pattern = re.compile(f".*{re.escape(normalized_query)}.*", re.IGNORECASE)
    
    # Build MongoDB query for movies
    movie_db_query = {
        "$or": [
            {"normalized_title": {'$regex': query_pattern}}, # Search in normalized title field
            {"title_arabic": {'$regex': query_pattern}}, # Original Arabic title
            {"title_english": {'$regex': query_pattern}}, # Original English title
            {"aliases": {'$regex': query_pattern}}, # Search in aliases if they exist
            {"story": {'$regex': query_pattern}}, # Search in story/plot
        ]
    }
    
    # Apply filters (example: year filtering)
    if filters and 'year' in filters:
        try:
            year = int(filters['year'])
            movie_db_query['year'] = year
        except ValueError:
            logger.warning(f"Invalid year filter: {filters['year']}")

    # Fetch movies
    movies = await movie_repo.find(movie_db_query, limit=20) # Limit for pagination/performance

    # Build MongoDB query for series (similar logic)
    series_db_query = {
        "$or": [
            {"normalized_title": {'$regex': query_pattern}},
            {"title_arabic": {'$regex': query_pattern}},
            {"title_english": {'$regex': query_pattern}},
            {"aliases": {'$regex': query_pattern}},
            {"story": {'$regex': query_pattern}},
        ]
    }
    if filters and 'year' in filters:
        try:
            year = int(filters['year'])
            series_db_query['year'] = year
        except ValueError:
            pass
            
    # Fetch series
    series_results = await series_repo.find(series_db_query, limit=20)

    # Combine results and mark their type
    results = []
    for movie in movies:
        movie['type'] = 'movie'
        results.append(movie)
    for series_item in series_results:
        series_item['type'] = 'series'
        results.append(series_item)

    # Further sorting or ranking can be applied here
    return results

async def get_search_suggestions(query: str) -> List[str]:
    """Provides search suggestions based on partial queries."""
    if not query or len(query) < 2: # Require at least 2 characters for suggestions
        return []

    normalized_query = normalize_arabic_text(remove_diacritics(query.lower()))
    query_pattern = re.compile(f"^{re.escape(normalized_query)}", re.IGNORECASE) # Starts with

    suggestions = set()

    # Get movie title suggestions
    movie_titles = await movie_repo.collection.distinct("title_arabic", {"title_arabic": {'$regex': query_pattern}})
    for title in movie_titles:
        suggestions.add(title)
    movie_titles_en = await movie_repo.collection.distinct("title_english", {"title_english": {'$regex': query_pattern}})
    for title in movie_titles_en:
        suggestions.add(title)

    # Get series title suggestions
    series_titles = await series_repo.collection.distinct("title_arabic", {"title_arabic": {'$regex': query_pattern}})
    for title in series_titles:
        suggestions.add(title)
    series_titles_en = await series_repo.collection.distinct("title_english", {"title_english": {'$regex': query_pattern}})
    for title in series_titles_en:
        suggestions.add(title)
    
    return sorted(list(suggestions))[:10] # Return top 10 sorted suggestions


# --- Natural Language Search (Deterministic Local Parser) ---

def parse_natural_language_query(nl_query: str) -> Dict[str, Any]:
    """Parses natural language queries to extract search parameters.

    Examples:
    - 'فيلم أكشن 2025'
    - 'فيلم رعب أقل من ساعتين'
    - 'فيلم مثل John Wick' (requires external data/more advanced NLP)

    This is a deterministic parser based on regex and keyword matching. It does not
    invent results but extracts structured queries.
    """
    parsed_params = {'query': '', 'filters': {}}
    original_query = nl_query.lower().strip()
    remaining_query = original_query

    # 1. Extract year (e.g., '2025', 'فيلم 2023')
    year_match = re.search(r'\b(\d{4})\b', remaining_query)
    if year_match:
        parsed_params['filters']['year'] = int(year_match.group(1))
        remaining_query = remaining_query.replace(year_match.group(0), '').strip()

    # 2. Extract genre (e.g., 'أكشن', 'رعب', 'كوميدي', 'action', 'horror')
    genre_keywords = {
        'action': ['أكشن', 'اكشن', 'action'],
        'horror': ['رعب', 'horror'],
        'comedy': ['كوميدي', 'كوميديا', 'comedy'],
        'sci-fi': ['خيال علمي', 'خيال_علمي', 'sci-fi', 'science fiction'],
        'drama': ['دراما', 'drama'],
        'thriller': ['إثارة', 'اثار', 'thriller'],
        'animation': ['رسوم متحركة', 'انيميشن', 'animation'],
        'adventure': ['مغامرات', 'مغامرة', 'adventure']
    }
    for genre, keywords in genre_keywords.items():
        for keyword in keywords:
            if keyword in remaining_query:
                parsed_params['filters']['genre'] = genre
                remaining_query = remaining_query.replace(keyword, '').strip()
                break
        if 'genre' in parsed_params['filters']: break

    # 3. Extract duration constraints (e.g., 'أقل من ساعتين', 'more than 90 min')
    duration_match_less = re.search(r'(أقل من|less than)\s*(?:(\d+)\s*(?:ساعة|hour)|(\d+)\s*دقيقة|(\d+)\s*min)', remaining_query, re.IGNORECASE)
    if duration_match_less:
        minutes = 0
        if duration_match_less.group(2): minutes = int(duration_match_less.group(2)) * 60
        elif duration_match_less.group(3): minutes = int(duration_match_less.group(3))
        elif duration_match_less.group(4): minutes = int(duration_match_less.group(4))
        if minutes > 0: parsed_params['filters']['max_duration'] = minutes
        remaining_query = re.sub(r'(أقل من|less than)\s*(?:\d+\s*(?:ساعة|hour)|\d+\s*دقيقة|\d+\s*min)', '', remaining_query, flags=re.IGNORECASE).strip()

    duration_match_greater = re.search(r'(أكثر من|more than)\s*(?:(\d+)\s*(?:ساعة|hour)|(\d+)\s*دقيقة|(\d+)\s*min)', remaining_query, re.IGNORECASE)
    if duration_match_greater:
        minutes = 0
        if duration_match_greater.group(2): minutes = int(duration_match_greater.group(2)) * 60
        elif duration_match_greater.group(3): minutes = int(duration_match_greater.group(3))
        elif duration_match_greater.group(4): minutes = int(duration_match_greater.group(4))
        if minutes > 0: parsed_params['filters']['min_duration'] = minutes
        remaining_query = re.sub(r'(أكثر من|more than)\s*(?:\d+\s*(?:ساعة|hour)|\d+\s*دقيقة|\d+\s*min)', '', remaining_query, flags=re.IGNORECASE).strip()

    # Clean up common prefixes like 'فيلم', 'مسلسل', 'movie', 'series'
    remaining_query = re.sub(r'\b(فيلم|مسلسل|movie|series)\b', '', remaining_query, flags=re.IGNORECASE).strip()
    remaining_query = re.sub(r'\b(مثل|like)\b', '', remaining_query, flags=re.IGNORECASE).strip()

    # What's left is the main text query
    parsed_params['query'] = remaining_query

    return parsed_params

async def natural_language_search(nl_query: str) -> List[Dict[str, Any]]:
    """Combines natural language parsing with structured search."""
    parsed_nl = parse_natural_language_query(nl_query)
    
    search_query = parsed_nl['query']
    search_filters = parsed_nl['filters']

    # If 'like X' functionality is desired, this is where a recommendation engine
    # or a more advanced knowledge graph would come in. For now, we'll just search for X.

    if not search_query and not search_filters:
        return [] # No meaningful query extracted

    return await search_content(search_query, search_filters)
