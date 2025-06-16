"""
Модул за управление на данни за екопътеки в България - Рефакторирана версия

Този модул предоставя функционалност за търсене, филтриране и извличане
на информация за туристически маршрути и екопътеки от JSON база данни.
Оптимизиран за производителност с кеширане и подобрено error handling.

Автор: EcoTrails Team
Дата: 2025
Версия: 2.4 (Корекции на имена на функции)
"""

import json
import os
import re
from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
from functools import lru_cache
import logging
from pathlib import Path

# ============================================================================
# КОНФИГУРАЦИЯ НА ЛОГИРАНЕТО
# ============================================================================
logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# ============================================================================
# КОНФИГУРАЦИЯ И КОНСТАНТИ
# ============================================================================

# Път до файла с данни за екопътеките
DATA_FILE_PATH = Path(os.path.join(os.path.dirname(__file__), 'data', 'eco.json'))

# Географски граници на България за валидация
BULGARIA_BOUNDS = {
    'min_lat': 41.2,
    'max_lat': 44.2,
    'min_lng': 22.3,
    'max_lng': 28.6
}

# Конфигурация на кеша за _data_cache
CACHE_TTL = timedelta(minutes=30)
MAX_CACHE_SIZE = 100 # за LRU caches на функциите

# Глобални променливи за кеширане на суровите данни от файла
_data_cache = None
_cache_timestamp = None
_cache_expiry = None

# ============================================================================
# ОСНОВНИ ФУНКЦИИ ЗА ЗАРЕЖДАНЕ НА ДАННИ
# ============================================================================

def load_trail_data() -> List[Dict[str, Any]]:
    """
    Зарежда данните за екопътеките от JSON файла с интелигентно кеширане.
    Тази функция се извиква от другите функции за търсене, за да осигури
    винаги актуален набор от данни, но чете файла само веднъж на CACHE_TTL.
    
    Returns:
        List[Dict[str, Any]]: Списък с всички валидни екопътеки от файла
    
    Raises:
        FileNotFoundError: Ако файлът с данни не съществува
        json.JSONDecodeError: При невалиден JSON формат
        ValueError: При невалидна структура на данните
    """
    global _data_cache, _cache_timestamp, _cache_expiry
    
    try:
        # Проверка дали файлът съществува
        if not DATA_FILE_PATH.exists():
            logger.error(f"Файлът с данни не е намерен: {DATA_FILE_PATH}")
            return _get_fallback_data()
        
        # Получаване на времето на последна промяна на файла
        file_modification_time = DATA_FILE_PATH.stat().st_mtime
        current_time = datetime.now()
        
        # Използване на кеширани данни ако са валидни
        if (_data_cache is not None and 
            _cache_timestamp == file_modification_time and # Проверка за промяна на файла
            _cache_expiry and current_time < _cache_expiry): # Проверка за изтекъл кеш
            logger.debug("Използване на кеширани данни")
            return _data_cache
        
        logger.info(f"Зареждане на данни от: {DATA_FILE_PATH}")
        
        # Четене и парсване на JSON файла
        with open(DATA_FILE_PATH, encoding='utf-8') as file:
            raw_data = json.load(file)
        
        # Валидация на структурата на данните
        validated_trails = _validate_and_process_data(raw_data)
        
        # Кеширане на валидираните данни
        _data_cache = validated_trails
        _cache_timestamp = file_modification_time
        _cache_expiry = current_time + CACHE_TTL
        
        logger.info(f"Успешно заредени {len(validated_trails)} маршрута")
        return validated_trails
        
    except FileNotFoundError:
        logger.error(f"Файлът с данни не е намерен: {DATA_FILE_PATH}")
        return _get_fallback_data()
    except json.JSONDecodeError as e:
        logger.error(f"Грешка при парсване на JSON файла: {str(e)}")
        return _get_fallback_data()
    except Exception as e:
        logger.error(f"Неочаквана грешка при зареждане на данните: {str(e)}")
        return _get_fallback_data()

def _validate_and_process_data(raw_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Валидира и обработва суровите данни от JSON файла.
    
    Args:
        raw_data: Суровите данни от JSON файла
        
    Returns:
        List[Dict[str, Any]]: Списък с валидирани маршрути
    """
    if not isinstance(raw_data, dict):
        raise ValueError("JSON файлът трябва да съдържа обект на най-високо ниво")
    
    eco_trails = raw_data.get('eco_trails')
    if not isinstance(eco_trails, list):
        raise ValueError("Полето 'eco_trails' трябва да бъде списък с маршрути")
    
    validated_trails = []
    
    for index, trail in enumerate(eco_trails):
        if not isinstance(trail, dict):
            logger.warning(f"Маршрут на позиция {index} не е валиден обект - пропускане")
            continue
        
        # Валидация на задължителни полета
        if not _validate_required_fields(trail, index):
            continue
        
        # Нормализация на данните
        normalized_trail = _normalize_trail_data(trail, index)
        validated_trails.append(normalized_trail)
    
    return validated_trails

def _validate_required_fields(trail: Dict[str, Any], index: int) -> bool:
    """Валидира задължителните полета на маршрут."""
    trail_id = trail.get('id')
    if not trail_id:
        logger.warning(f"Маршрут на позиция {index} няма валиден ID - пропускане")
        return False
    
    trail_name = trail.get('name')
    if not trail_name:
        logger.warning(f"Маршрут с ID {trail_id} няма име")
    
    return True

def _normalize_trail_data(trail: Dict[str, Any], index: int) -> Dict[str, Any]:
    """Нормализира данните за маршрут."""
    # Добавяне на метаданни
    trail['_loaded_at'] = datetime.now().isoformat()
    trail['_index'] = index
    
    # Нормализация на координати
    location = trail.get('location', {})
    coordinates = location.get('coordinates', {})
    
    if coordinates:
        # Валидация на координатите
        lat = coordinates.get('latitude') # Използвайте 'latitude' и 'longitude' ако това са ключовете в eco.json
        lng = coordinates.get('longitude')
        
        if lat is not None and lng is not None:
            try:
                lat = float(lat)
                lng = float(lng)
                
                # Проверка дали са в границите на България
                if _validate_bulgaria_coordinates(lat, lng):
                    coordinates['latitude'] = lat
                    coordinates['longitude'] = lng
                    coordinates['_validated'] = True
                else:
                    logger.warning(f"Координатите на маршрут {trail.get('id')} са извън България")
                    coordinates['_validated'] = False
            except (ValueError, TypeError):
                logger.warning(f"Невалидни координати за маршрут {trail.get('id')}")
                coordinates['_validated'] = False
    
    # Нормализация на текстови полета
    if 'name' in trail:
        trail['_name_normalized'] = _normalize_text(trail['name'])
    
    if 'description' in trail:
        trail['_description_normalized'] = _normalize_text(trail['description'])
    
    return trail

def _get_fallback_data() -> List[Dict[str, Any]]:
    """Връща fallback данни при грешка."""
    logger.info("Използване на fallback данни")
    return [
        {
            'id': 1, # Променено на число за съвпадение с get_trail_by_id
            'name': 'Витоша - Черни връх',
            'description': 'Популярен маршрут до най-високия връх на Витоша',
            'location': {
                'region': 'Витоша',
                'coordinates': {'latitude': 42.5569, 'longitude': 23.2846, '_validated': True}
            },
            'trail_details': {
                'difficulty': 'средна', # Нормализирано
                'length_km': '8', # КМ за съвпадение с eco.json
                'duration': '4-5 часа'
            },
            '_fallback': True
        },
        {
            'id': 2, # Променено на число
            'name': 'Рила - Седемте рилски езера',
            'description': 'Най-известният маршрут в Рила планина',
            'location': {
                'region': 'Рила',
                'coordinates': {'latitude': 42.2167, 'longitude': 23.3167, '_validated': True}
            },
            'trail_details': {
                'difficulty': 'средна', # Нормализирано
                'length_km': '12', # КМ
                'duration': '6-7 часа'
            },
            '_fallback': True
        }
    ]

# ============================================================================
# ПОМОЩНИ ФУНКЦИИ ЗА ТЪРСЕНЕ И ФИЛТРИРАНЕ (ПРЕНЕСЕНИ В query.py)
# ============================================================================

def _normalize_text(text: Any) -> str:
    """Нормализира текст за по-добро съвпадение (малки букви, премахване на пунктуация)."""
    if not isinstance(text, str):
        return ""
    try:
        from unidecode import unidecode
        normalized = unidecode(text).lower().strip()
    except ImportError:
        normalized = text.lower().strip()
    normalized = re.sub(r'[^\w\s-]', ' ', normalized)
    normalized = re.sub(r'\s+', ' ', normalized)
    return normalized

def _has_valid_coordinates(trail: Dict[str, Any]) -> bool:
    """Проверява дали маршрутът има валидни географски координати."""
    try:
        location_info = trail.get('location', {})
        coordinates = location_info.get('coordinates', {})
        
        if not isinstance(coordinates, dict):
            return False
        
        latitude = coordinates.get('latitude') # Използвайте 'latitude'
        longitude = coordinates.get('longitude') # Използвайте 'longitude'
        
        if not isinstance(latitude, (int, float)) or not isinstance(longitude, (int, float)):
            return False
        
        if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
            return False
        
        return True
    except (AttributeError, TypeError, KeyError):
        return False

def _validate_bulgaria_coordinates(lat: float, lng: float) -> bool:
    """Валидира дали координатите са в границите на България."""
    return (
        BULGARIA_BOUNDS['min_lat'] <= lat <= BULGARIA_BOUNDS['max_lat'] and
        BULGARIA_BOUNDS['min_lng'] <= lng <= BULGARIA_BOUNDS['max_lng']
    )

def _extract_search_keywords(query: str) -> Dict[str, str]:
    """Извлича ключови думи от заявката."""
    keywords = {}
    normalized_query = _normalize_text(query) # Използвайте _normalize_text
    
    # Региони
    regions = {
        'витоша': ['витоша'], 'рила': ['рила', 'седемте рилски езера'],
        'пирин': ['пирин', 'вихрен'], 'стара планина': ['стара планина', 'балкан', 'ботев'],
        'родопи': ['родопи', 'смолян', 'пампорово', 'триград'],
        'странджа': ['странджа'], 'пловдив': ['пловдив'], 'софия': ['софия'],
        'варна': ['варна'], 'бургас': ['бургас'], 'търново': ['търново', 'велико търново'],
        'етрополски балкан': ['етрополски балкан'], 'централен балкан': ['централен балкан'],
        'чупренска планина': ['чупренска планина', 'миджур'], 'западни родопи': ['западни родопи']
    }
    for region, synonyms in regions.items():
        if any(syn in normalized_query for syn in synonyms):
            keywords['region'] = region
            break
    
    # Трудност
    difficulties = {
        'лесна': ['лесна', 'лесни', 'начинаещ', 'лек', 'лека', 'семеен', 'ниска'],
        'средна': ['средна', 'средни', 'умерена', 'умерени', 'нормална'],
        'трудна': ['трудна', 'трудни', 'тежка', 'предизвикателна', 'експертна', 'висока']
    }
    for difficulty, synonyms in difficulties.items():
        if any(syn in normalized_query for syn in synonyms):
            keywords['difficulty'] = difficulty
            break
    
    # Тип маршрут/атракция (разширено)
    types = {
        'връх': ['връх', 'върхове', 'връшка', 'пик'],
        'водопад': ['водопад', 'водопади'],
        'езеро': ['езеро', 'езера'],
        'пещера': ['пещера', 'пещери'],
        'манастир': ['манастир', 'манастири'],
        'резерват': ['резерват', 'парк', 'защитена местност'],
        'крепост': ['крепост', 'крепости', 'историческа забележителност'],
        'музей': ['музей', 'музеи'],
        'скали': ['скали', 'скален'],
        'река': ['река', 'реки'],
        'пролом': ['пролом', 'дефиле']
    }
    for type_name, synonyms in types.items():
        if any(syn in normalized_query for syn in synonyms):
            keywords['type'] = type_name
            break
            
    # Сезон
    seasons = {
        'пролет': ['пролет', 'пролетта', 'април', 'май'],
        'лято': ['лято', 'лятото', 'юни', 'юли', 'август'],
        'есен': ['есен', 'есента', 'септември', 'октомври', 'ноември'],
        'зима': ['зима', 'зимата', 'декември', 'януари', 'февруари'],
        'целогодишно': ['целогодишно', 'по всяко време']
    }
    for season, synonyms in seasons.items():
        if any(syn in normalized_query for syn in synonyms):
            keywords['season'] = season
            break
            
    return keywords

def _search_by_extracted_keywords(trails_data: List[Dict], keywords: Dict[str, str]) -> List[Dict]:
    """Търси по извлечени ключови думи."""
    matching_trails = []
    
    for trail in trails_data:
        if not _has_valid_coordinates(trail):
            continue
            
        score = 0
        trail_name_norm = _normalize_text(trail.get('name', '')) # Използвайте _normalize_text
        trail_desc_norm = _normalize_text(trail.get('description', '')) # Използвайте _normalize_text
        
        # Проверка за регион
        if 'region' in keywords:
            trail_location_keywords = [_normalize_text(kw) for kw in trail.get('location', {}).get('keywords', []) if kw is not None] # Използвайте _normalize_text
            trail_region_norm = _normalize_text(trail.get('location', {}).get('region', '')) # Използвайте _normalize_text
            trail_town_norm = _normalize_text(trail.get('location', {}).get('nearest_town', '')) # Използвайте _normalize_text
            if (keywords['region'] in trail_region_norm or 
                keywords['region'] in trail_town_norm or 
                any(keywords['region'] in kw for kw in trail_location_keywords)):
                score += 3
        
        # Проверка за трудност
        if 'difficulty' in keywords:
            trail_difficulty_norm = _normalize_text(trail.get('trail_details', {}).get('difficulty', '')) # Използвайте _normalize_text
            if keywords['difficulty'] in trail_difficulty_norm:
                score += 2
        
        # Проверка за тип (атракция/обект)
        if 'type' in keywords:
            if keywords['type'] in trail_name_norm or keywords['type'] in trail_desc_norm:
                score += 1
            else: # Проверка и в атракциите на пътеката
                trail_attractions = [_normalize_text(a.get('name', '')) for a in trail.get('attractions', []) if a and a.get('name')] # Използвайте _normalize_text
                if any(keywords['type'] in ta for ta in trail_attractions):
                    score += 1
        
        # Проверка за сезон
        if 'season' in keywords:
            trail_seasons = [_normalize_text(s) for s in trail.get('trail_details', {}).get('best_season', []) if s is not None] # Използвайте _normalize_text
            if keywords['season'] in trail_seasons:
                score += 1

        if score > 0:
            trail['_relevance_score'] = score
            matching_trails.append(trail)
    
    return matching_trails

def _is_recommendation_query(normalized_query: str) -> bool:
    """Проверява дали заявката е за общи препоръки."""
    recommendation_phrases = [
        'предложете', 'препоръчайте', 'покажете', 'намерете',
        'искам', 'търся', 'къде да отида', 'маршрут', 'препоръки',
        'какво да посетя', 'най-добрите', 'популярни'
    ]
    return any(phrase in normalized_query for phrase in recommendation_phrases)

def _get_popular_trails(trails_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Връща популярни маршрути като препоръки."""
    valid_trails = [trail for trail in trails_data if _has_valid_coordinates(trail)]
    return valid_trails[:5]

def _search_by_keywords(trails_data: List[Dict[str, Any]], normalized_query: str) -> List[Dict[str, Any]]:
    """Търси маршрути по ключови думи (fallback, ако няма извлечени специфични)."""
    matching_trails = []
    query_words = normalized_query.split()
    
    for trail in trails_data:
        if not _has_valid_coordinates(trail):
            continue
        
        search_fields = _build_search_fields(trail)
        relevance_score = _calculate_relevance(search_fields, query_words)
        
        if relevance_score > 0:
            trail['_relevance_score'] = relevance_score
            matching_trails.append(trail)
    
    return matching_trails

def _build_search_fields(trail: Dict[str, Any]) -> List[str]:
    """Изгражда списък с полета за търсене."""
    search_fields = []
    
    if trail.get('name'):
        search_fields.append(_normalize_text(trail['name'])) # Използвайте _normalize_text
    if trail.get('description'):
        search_fields.append(_normalize_text(trail['description'])) # Използвайте _normalize_text
    
    location = trail.get('location', {})
    if location.get('region'):
        search_fields.append(_normalize_text(location['region'])) # Използвайте _normalize_text
    if location.get('nearest_town'):
        search_fields.append(_normalize_text(location['nearest_town'])) # Използвайте _normalize_text
    if location.get('keywords'):
        keywords = location['keywords']
        if isinstance(keywords, list):
            search_fields.extend([_normalize_text(kw) for kw in keywords]) # Използвайте _normalize_text
    
    trail_details = trail.get('trail_details', {})
    if trail_details.get('difficulty'):
        search_fields.append(_normalize_text(trail_details['difficulty'])) # Използвайте _normalize_text
    if trail_details.get('route_type'):
        search_fields.append(_normalize_text(trail_details['route_type'])) # Използвайте _normalize_text
    
    if trail.get('attractions'):
        attractions = trail['attractions']
        if isinstance(attractions, list):
            search_fields.extend([_normalize_text(att.get('name', '')) for att in attractions if att and att.get('name')]) # Използвайте _normalize_text

    return search_fields

def _calculate_relevance(search_fields: List[str], query_words: List[str]) -> float:
    """Изчислява релевантност между полетата и заявката."""
    total_score = 0.0
    
    for field in search_fields:
        field_score = 0.0
        for word in query_words:
            if word in field:
                if word == field:
                    field_score += 2.0
                elif word in field:
                    field_score += 1.0
        total_score += field_score
    return total_score

def _sort_by_relevance(trails: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
    """Сортира маршрутите по релевантност."""
    return sorted(trails, key=lambda x: x.get('_relevance_score', 0), reverse=True)

@lru_cache(maxsize=MAX_CACHE_SIZE)
def search_trails(query: str) -> List[Dict[str, Any]]:
    """Търси маршрути с подобрена логика за извличане на ключови думи"""
    try:
        if not query or not query.strip():
            return []

        normalized_query = _normalize_text(query) # Използвайте _normalize_text
        trails_data = load_trail_data()
        
        extracted_keywords = _extract_search_keywords(normalized_query)
        
        if extracted_keywords:
            matching_trails = _search_by_extracted_keywords(trails_data, extracted_keywords)
        else:
            matching_trails = _search_by_keywords(trails_data, normalized_query)
        
        return _sort_by_relevance(matching_trails, normalized_query)
        
    except Exception as e:
        logger.error(f"Грешка при търсене: {str(e)}")
        return []

@lru_cache(maxsize=MAX_CACHE_SIZE)
def get_trail_by_id(trail_id: Union[int, str]) -> Optional[Dict[str, Any]]:
    """
    Извлича конкретен маршрут по неговия уникален идентификатор.
    """
    if not trail_id:
        logger.warning("Невалиден ID за маршрут (празен)")
        return None
    
    try:
        parsed_id = int(trail_id)
    except (ValueError, TypeError):
        logger.warning(f"Невалиден ID за маршрут (нечислов): '{trail_id}'")
        return None

    logger.info(f"Търсене на маршрут с ID: {parsed_id}")
    
    trails_data = load_trail_data()
    
    for trail in trails_data:
        if trail.get('id') == parsed_id:
            logger.info(f"Намерен маршрут: {trail.get('name', 'Неименован')}")
            return trail
    
    logger.warning(f"Маршрут с ID '{parsed_id}' не е намерен")
    return None

@lru_cache(maxsize=MAX_CACHE_SIZE)
def advanced_search(
    region: Optional[str] = None,
    difficulty: Optional[str] = None,
    best_season: Optional[List[str]] = None,
    length_min_km: Optional[float] = None,
    length_max_km: Optional[float] = None,
    duration_min_hours: Optional[float] = None,
    duration_max_hours: Optional[float] = None,
    attraction_keywords: Optional[List[str]] = None,
    route_type: Optional[str] = None,
    source: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Извършва разширено търсене на маршрути по множество критерии.
    """
    logger.info(f"Изпълнение на разширено търсене с параметри: {locals()}")
    
    trails_data = load_trail_data()
    filtered_trails = []
    
    # Нормализиране на параметрите за търсене
    filters = {
        'region': _normalize_text(region) if region else None, # Използвайте _normalize_text
        'difficulty': _normalize_text(difficulty) if difficulty else None, # Използвайте _normalize_text
        'best_season': [_normalize_text(s) for s in best_season] if best_season else None, # Използвайте _normalize_text
        'length_min_km': length_min_km,
        'length_max_km': length_max_km,
        'duration_min_hours': duration_min_hours,
        'duration_max_hours': duration_max_hours,
        'attraction_keywords': [_normalize_text(kw) for kw in attraction_keywords] if attraction_keywords else None, # Използвайте _normalize_text
        'route_type': _normalize_text(route_type) if route_type else None, # Използвайте _normalize_text
        'source': _normalize_text(source) if source else None # Използвайте _normalize_text
    }
    
    for trail in trails_data:
        if _matches_advanced_criteria(trail, filters):
            filtered_trails.append(trail)
    
    logger.info(f"Намерени {len(filtered_trails)} маршрута при разширеното търсене.")
    return filtered_trails

def parse_duration_range(duration_str: str) -> Tuple[Optional[int], Optional[int]]:
    """
    Парсва низ с продължителност (напр. "2-3 часа", "1 ден", "30 минути")
    и връща минимални и максимални минути.
    """
    duration_str = _normalize_text(duration_str) # Използвайте _normalize_text
    
    min_minutes = None
    max_minutes = None

    # Часове
    hours_match = re.search(r'(\d+)-?(\d*)\s*(час|часа)', duration_str)
    if hours_match:
        min_h = int(hours_match.group(1))
        min_minutes = min_h * 60
        if hours_match.group(2):
            max_h = int(hours_match.group(2))
            max_minutes = max_h * 60
        else:
            max_minutes = min_minutes # Единична стойност
        return min_minutes, max_minutes

    # Дни (приемаме 8 часа/ден ходене)
    days_match = re.search(r'(\d+)-?(\d*)\s*(ден|дни)', duration_str)
    if days_match:
        min_d = int(days_match.group(1))
        min_minutes = min_d * 8 * 60
        if days_match.group(2):
            max_d = int(days_match.group(2))
            max_minutes = max_d * 8 * 60
        else:
            max_minutes = min_minutes
        return min_minutes, max_minutes

    # Минути
    minutes_match = re.search(r'(\d+)-?(\d*)\s*(минут|минути)', duration_str)
    if minutes_match:
        min_m = int(minutes_match.group(1))
        min_minutes = min_m
        if minutes_match.group(2):
            max_m = int(minutes_match.group(2))
            max_minutes = max_m
        else:
            max_minutes = min_minutes
        return min_minutes, max_minutes
    
    return None, None # Не може да се парсне

def _matches_advanced_criteria(trail: Dict[str, Any], filters: Dict[str, Any]) -> bool:
    """Проверява дали маршрут отговаря на критериите за разширено търсене."""
    
    # Филтриране по регион
    if filters['region']:
        trail_location_keywords = [_normalize_text(kw) for kw in trail.get('location', {}).get('keywords', []) if kw is not None] # Използвайте _normalize_text
        trail_region_norm = _normalize_text(trail.get('location', {}).get('region', '')) # Използвайте _normalize_text
        trail_town_norm = _normalize_text(trail.get('location', {}).get('nearest_town', '')) # Използвайте _normalize_text
        if not (filters['region'] in trail_region_norm or 
                filters['region'] in trail_town_norm or 
                any(filters['region'] in kw for kw in trail_location_keywords)):
            return False
    
    # Филтриране по трудност
    if filters['difficulty']:
        trail_difficulty_norm = _normalize_text(trail.get('trail_details', {}).get('difficulty', '')) # Използвайте _normalize_text
        if filters['difficulty'] not in trail_difficulty_norm:
            return False
    
    # Филтриране по сезон
    if filters['best_season']:
        trail_seasons_norm = [_normalize_text(s) for s in trail.get('trail_details', {}).get('best_season', []) if s is not None] # Използвайте _normalize_text
        if not any(fs in trail_seasons_norm for fs in filters['best_season']):
            return False

    # Филтриране по дължина
    trail_length_str = trail.get('trail_details', {}).get('length_km', '0')
    try:
        trail_length = float(trail_length_str)
    except (ValueError, TypeError):
        trail_length = None

    if filters['length_min_km'] is not None and (trail_length is None or trail_length < filters['length_min_km']):
        return False
    if filters['length_max_km'] is not None and (trail_length is None or trail_length > filters['length_max_km']):
        return False

    # Филтриране по продължителност
    trail_duration_str = trail.get('trail_details', {}).get('duration', '')
    trail_min_minutes, trail_max_minutes = parse_duration_range(trail_duration_str)

    if filters['duration_min_hours'] is not None:
        if trail_min_minutes is None or (trail_max_minutes is not None and trail_max_minutes < (filters['duration_min_hours'] * 60)):
            return False
    if filters['duration_max_hours'] is not None:
        if trail_max_minutes is None or (trail_min_minutes is not None and trail_min_minutes > (filters['duration_max_hours'] * 60)):
            return False

    # Филтриране по ключови думи за атракции
    if filters['attraction_keywords']:
        attractions_matched = False
        trail_attractions = [_normalize_text(a.get('name', '')) for a in trail.get('attractions', []) if a and a.get('name') is not None] # Използвайте _normalize_text
        trail_description_norm = _normalize_text(trail.get('description', '')) # Използвайте _normalize_text
        
        if any(f_kw in trail_attractions or f_kw in trail_description_norm for f_kw in filters['attraction_keywords']):
            attractions_matched = True
        if not attractions_matched:
            return False

    # Филтриране по тип маршрут
    if filters['route_type']:
        trail_route_type_norm = _normalize_text(trail.get('trail_details', {}).get('route_type', '')) # Използвайте _normalize_text
        if filters['route_type'] != trail_route_type_norm:
            return False

    # Филтриране по източник
    if filters['source']:
        trail_source_norm = _normalize_text(trail.get('source', '')) # Използвайте _normalize_text
        if filters['source'] != trail_source_norm:
            return False
    
    return True

@lru_cache(maxsize=MAX_CACHE_SIZE)
def list_all_trails() -> List[Dict[str, Any]]:
    """
    Връща всички налични екопътеки от базата данни.
    """
    trails_data = load_trail_data()
    logger.info(f"Връщане на {len(trails_data)} общо маршрута.")
    return trails_data

# ============================================================================
# ФУНКЦИИ ЗА ИЗГРАЖДАНЕ НА КОНТЕКСТ
# ============================================================================

def build_context_from_trails(trails: List[Dict[str, Any]], max_trails: int = 5) -> str:
    """
    Изгражда контекст за AI модела от намерените маршрути.
    """
    if not trails:
        return _build_empty_context()
    
    context_parts = [
        "НАМЕРЕНИ МАРШРУТИ В БАЗАТА ДАННИ:",
        "=" * 50
    ]
    
    for i, trail in enumerate(trails[:max_trails], 1):
        trail_context = _build_trail_context(trail, i)
        context_parts.extend(trail_context)
    
    context_parts.extend([
        "",
        "ИНСТРУКЦИИ:",
        "- Предложи конкретни маршрути от горния списък",
        "- Включи координати за препоръчаните маршрути",
        "- Дай практични съвети за всеки маршрут",
        "- Групирай по региони ако е възможно"
    ])
    
    return "\n".join(context_parts)

def _build_empty_context() -> str:
    """Изгражда контекст когато няма намерени маршрути."""
    return """
НЯМА НАМЕРЕНИ МАРШРУТИ В БАЗАТА ДАННИ.

Моля, предложи общи препоръки за популярни екопътеки в България:
- Рила планина (Седемте рилски езера)
- Пирин планина (Вихрен)
- Стара планина (Ботев връх)
- Родопи планина (Триград)
- Витоша планина (Черни връх)

Форматирай отговора като JSON с поне 3-5 препоръки.
"""

def _build_trail_context(trail: Dict[str, Any], index: int) -> List[str]:
    """Изгражда контекст за отделен маршрут."""
    coords = trail.get('location', {}).get('coordinates', {})
    
    return [
        f"{index}. {trail.get('name', 'Неименован маршрут')}",
        f"   📍 Регион: {trail.get('location', {}).get('region', 'Неизвестен')}",
        f"   🎯 Трудност: {trail.get('trail_details', {}).get('difficulty', 'Неопределена')}",
        f"   📏 Дължина: {trail.get('trail_details', {}).get('length_km', 'Няма данни')} км",
        f"   ⏱️ Продължителност: {trail.get('trail_details', {}).get('duration', 'Няма данни')}",
        f"   📝 Описание: {trail.get('description', 'Няма описание')[:100]}...",
        f"   🗺️ Координати: lat={coords.get('latitude', 'N/A')}, lng={coords.get('longitude', 'N/A')}",
        "-" * 50
    ]

# ============================================================================
# ФУНКЦИИ ЗА УПРАВЛЕНИЕ НА КЕША
# ============================================================================

def clear_data_cache():
    """Изчиства кеша с данните за маршрутите."""
    global _data_cache, _cache_timestamp, _cache_expiry
    
    _data_cache = None
    _cache_timestamp = None
    _cache_expiry = None
    
    # Изчистване на LRU кешовете на функциите
    search_trails.cache_clear()
    get_trail_by_id.cache_clear()
    advanced_search.cache_clear()
    list_all_trails.cache_clear()
    
    logger.info("Кешът с данни за маршрутите е изчистен")

def get_cache_info() -> Dict[str, Any]:
    """Връща информация за състоянието на кеша."""
    return {
        'data_cache': {
            'loaded': _data_cache is not None,
            'timestamp': _cache_timestamp.isoformat() if _cache_timestamp else None,
            'expiry': _cache_expiry.isoformat() if _cache_expiry else None,
            'size': len(_data_cache) if _data_cache else 0
        },
        'function_caches': {
            'search_trails': search_trails.cache_info()._asdict(),
            'get_trail_by_id': get_trail_by_id.cache_info()._asdict(),
            'advanced_search': advanced_search.cache_info()._asdict(),
            'list_all_trails': list_all_trails.cache_info()._asdict()
        }
    }

# ============================================================================
# СТАТИСТИЧЕСКИ ФУНКЦИИ
# ============================================================================

def get_data_statistics() -> Dict[str, Any]:
    """
    Генерира статистическа информация за наличните маршрути.
    """
    trails_data = load_trail_data()
    
    if not trails_data:
        return {
            'total_trails': 0,
            'regions': {},
            'difficulties': {},
            'seasons': {},
            'last_updated': None
        }
    
    region_counts = {}
    difficulty_counts = {}
    season_counts = {}
    valid_coordinates_count = 0
    
    for trail in trails_data:
        region = trail.get('location', {}).get('region', 'Неизвестен регион')
        region_counts[region] = region_counts.get(region, 0) + 1
        
        difficulty = trail.get('trail_details', {}).get('difficulty', 'Неопределена трудност')
        difficulty_counts[difficulty] = difficulty_counts.get(difficulty, 0) + 1
        
        trail_seasons = trail.get('trail_details', {}).get('best_season', [])
        if isinstance(trail_seasons, list):
            for season in trail_seasons:
                season_counts[season] = season_counts.get(season, 0) + 1
        
        if _has_valid_coordinates(trail):
            valid_coordinates_count += 1
    
    return {
        'total_trails': len(trails_data),
        'valid_coordinates': valid_coordinates_count,
        'regions': region_counts,
        'difficulties': difficulty_counts,
        'seasons': season_counts,
        'last_updated': datetime.now().isoformat(),
        'cache_info': get_cache_info()
    }

def get_trails_by_region(region: str) -> List[Dict[str, Any]]:
    """
    Връща всички маршрути от определен регион.
    """
    if not region:
        return []
    
    trails_data = load_trail_data()
    region_trails = []
    region_normalized = _normalize_text(region) # Използвайте _normalize_text
    
    for trail in trails_data:
        trail_region = trail.get('location', {}).get('region', '')
        if region_normalized in _normalize_text(trail_region): # Използвайте _normalize_text
            region_trails.append(trail)
    
    logger.info(f"Намерени {len(region_trails)} маршрута в регион '{region}'")
    return region_trails

# ============================================================================
# ВАЛИДАЦИОННИ ФУНКЦИИ
# ============================================================================

def validate_trail_data(trail: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Валидира данните за отделен маршрут.
    """
    errors = []
    
    required_fields = ['id', 'name', 'location', 'trail_details']
    for field in required_fields:
        if not trail.get(field):
            errors.append(f"Липсва задължителното поле: {field}")
    
    if not _has_valid_coordinates(trail):
        errors.append("Невалидни или липсващи координати")
    
    location = trail.get('location', {})
    if not isinstance(location, dict):
        errors.append("Полето 'location' трябва да бъде обект")
    
    trail_details = trail.get('trail_details', {})
    if not isinstance(trail_details, dict):
        errors.append("Полето 'trail_details' трябва да бъде обект")
    
    seasons = trail_details.get('best_season', [])
    if not isinstance(seasons, list):
        errors.append("Полето 'best_season' в 'trail_details' трябва да бъде списък")
    
    return len(errors) == 0, errors

# ============================================================================
# ЕКСПОРТ ФУНКЦИИ
# ============================================================================

def export_trails_to_json(output_path: str, trails: Optional[List[Dict[str, Any]]] = None) -> bool:
    """
    Експортира данни за маршрути в JSON файл.
    """
    try:
        if trails is None:
            trails = load_trail_data()
        
        export_data = {
            'eco_trails': trails,
            'export_info': {
                'timestamp': datetime.now().isoformat(),
                'total_count': len(trails),
                'exported_by': 'EcoTrails System v2.0'
            }
        }
        
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as file:
            json.dump(export_data, file, ensure_ascii=False, indent=2)
        
        logger.info(f"Данните са експортирани успешно в: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Грешка при експорт: {str(e)}")
        return False

# ============================================================================
# ИНИЦИАЛИЗАЦИЯ (ПРЕМАХНАТО Е ПЪРВОНАЧАЛНОТО ЗАДАВАНЕ НА TRAIL_DATA)
# ============================================================================
logger.info("Query модулът е инициализиран. Данните ще бъдат заредени при първия достъп.")

