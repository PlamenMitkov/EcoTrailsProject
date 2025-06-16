"""
Туристически чатбот за екопътеки в България - Рефакторирана версия

Това приложение представлява интелигентен асистент за туристи, който помага
при откриването и планирането на маршрути по екопътеки в България.
Използва Flask за уеб интерфейса и OpenAI GPT модел за генериране на отговори.

Автор: EcoTrails Team
Дата: 2025
Версия: 2.5 (Подобрено търсене и карти)
"""

import os
import json
import re
from typing import Dict, List, Optional, Tuple, Any, Union
from flask import Flask, render_template, request, jsonify, session
from openai import OpenAI
from dotenv import load_dotenv
import openrouteservice
import logging
from datetime import datetime, timedelta
from functools import lru_cache
import hashlib
import traceback # Добавен за по-добри трасировки

# ============================================================================
# КОНФИГУРАЦИЯ И ИНИЦИАЛИЗАЦИЯ
# ============================================================================

# Конфигурация на логирането
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Зареждане на променливите от .env файла за сигурност
load_dotenv()

from query import (
    search_trails,
    get_trail_by_id,
    advanced_search,
    list_all_trails,
    build_context_from_trails,
    parse_duration_range,
    _extract_search_keywords
)

# Проверка за OpenAI API ключ и инициализация
try:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    if not OPENAI_API_KEY:
        logger.error("❌ OPENAI_API_KEY не е зададен!")
        openai_client = None
    else:
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
        try:
            test_response = openai_client.chat.completions.create(
                model="gpt-3.5-turbo",  # По-евтин модел за тест
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5,
                timeout=5
            )
            logger.info("✅ OpenAI API ключът работи правилно")
        except Exception as e:
            logger.error(f"❌ OpenAI API ключът не работи или има проблем с връзката: {e}")
            openai_client = None
    
except Exception as e:
    logger.error(f"❌ Проблем с OpenAI API конфигурацията: {e}")
    openai_client = None

# Инициализация на OpenRouteService
try:
    ORS_API_KEY = os.getenv("OPENROUTESERVICE_API_KEY")
    if ORS_API_KEY:
        ors_client = openrouteservice.Client(key=ORS_API_KEY)
        logger.info("✅ OpenRouteService клиентът е инициализиран")
    else:
        ors_client = None
        logger.warning("⚠️ OpenRouteService API ключ не е зададен. Функционалността за маршрутизация ще е ограничена.")
except Exception as e:
    logger.error(f"❌ Грешка при инициализация на OpenRouteService: {e}")
    ors_client = None

# Създаване на Flask приложението
app = Flask(__name__,
    template_folder='templates',
    static_folder='static',
    static_url_path='/static')

app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key-change-in-production")

# Добавете route за manifest.json
@app.route('/manifest.json')
def manifest():
    return app.send_static_file('manifest.json')

# Добавете route за favicon
@app.route('/favicon.ico')
def favicon():
    return app.send_static_file('images/favicon.ico')

@app.route('/debug/files')
def debug_files():
    static_path = os.path.join(app.root_path, 'static')
    files = []
    for root, dirs, filenames in os.walk(static_path):
        for filename in filenames:
            rel_path = os.path.relpath(os.path.join(root, filename), static_path)
            files.append(rel_path)
    return {'static_files': files}

# ============================================================================
# КОНСТАНТИ И КОНФИГУРАЦИЯ
# ============================================================================

# Максимален брой съобщения в историята на разговора
MAX_CONVERSATION_HISTORY = 10

# Максимална дължина на потребителско съобщение (за сигурност)
MAX_MESSAGE_LENGTH = 500

# Географски граници на България за валидация на координати
BULGARIA_BOUNDS = {
    'min_lat': 41.2,
    'max_lat': 44.2,
    'min_lng': 22.3,
    'max_lng': 28.6
}

# Общи географски граници за координати
COORDINATE_BOUNDS = {
    'min_lat': -90.0,
    'max_lat': 90.0,
    'min_lng': -180.0,
    'max_lng': 180.0
}

# Кеш конфигурация
API_CACHE_TTL = timedelta(minutes=30)

# ============================================================================
# СИСТЕМНИ ПРОМПТОВЕ ЗА AI МОДЕЛА - ВЪРНАТО КЪМ ПРЕДИШНА ВЕРСИЯ
# ============================================================================

SYSTEM_PROMPT = """
Ти си туристически асистент за екопътеки в България.

Отговаряй с JSON формат:
{
"response": "Твоят отговор тук",
"coords": { "lat": 42.7, "lng": 25.4 }
}

Ако няма координати, върни само:
{ "response": "Твоят отговор" }

Помагай с:
- Намиране на маршрути
- Информация за трудност и сезон
- Съвети за подготовка
- Препоръки според предпочитания

Бъди кратък и полезен.
"""

# Добавен FAQ_CONTENT, който беше в systemrole.txt
FAQ_CONTENT = """
ЧЕСТО ЗАДАВАНИ ВЪПРОСИ:

🏔️ ОСНОВНИ:
- Екопътеката е маркиран природен маршрут
- Цел: устойчив туризъм и опазване на природата

🥾 ПОДГОТОВКА:
- Удобни обувки и дрехи на слоеве
- Вода и лека храна
- Карта или GPS

🧭 БЕЗОПАСНОСТ:
- Следвайте маркировките
- При спешност: 112
- Информирайте близки за маршрута

🌱 ЕКОЛОГИЯ:
- Не оставяйте отпадъци
- Не късайте растения
- Оставайте на пътеката
"""

# ============================================================================
# КЕШИРАНЕ И ОПТИМИЗАЦИЯ (добавени @lru_cache)
# ============================================================================

# _get_gpt_response_internal се кешира директно
# search_trails, get_trail_by_id, advanced_search, list_all_trails
# вече имат @lru_cache в query.py, така че не ги кешираме отново тук.

# ============================================================================
# ПОМОЩНИ ФУНКЦИИ ЗА ВАЛИДАЦИЯ И ОБРАБОТКА
# ============================================================================

def validate_coordinates(latitude: float, longitude: float) -> Tuple[bool, str]:
    """
    Валидира географските координати за правилност и съответствие с България.
    
    Args:
        latitude (float): Географска ширина в градуси
        longitude (float): Географска дължина в градуси
    
    Returns:
        Tuple[bool, str]: (валидни_ли_са, съобщение)
    """
    try:
        lat = float(latitude)
        lng = float(longitude)
        
        # Проверка на основните географски граници
        if not (COORDINATE_BOUNDS['min_lat'] <= lat <= COORDINATE_BOUNDS['max_lat']):
            return False, f"Невалидна географска ширина: {lat}°"
        
        if not (COORDINATE_BOUNDS['min_lng'] <= lng <= COORDINATE_BOUNDS['max_lng']):
            return False, f"Невалидна географска дължина: {lng}°"
        
        # Проверка дали координатите попадат в границите на България
        if not (BULGARIA_BOUNDS['min_lat'] <= lat <= BULGARIA_BOUNDS['max_lat'] and
                BULGARIA_BOUNDS['min_lng'] <= lng <= BULGARIA_BOUNDS['max_lng']):
            return False, f"Координатите ({lat}°, {lng}°) не попадат в границите на България"
        
        return True, f"Координатите ({lat}°, {lng}°) са валидни за България"
        
    except (ValueError, TypeError) as e:
        return False, f"Грешка при обработка на координатите: {str(e)}"

def sanitize_user_input(message: str) -> str:
    """
    Почиства и валидира потребителския вход за сигурност.
    
    Args:
        message (str): Оригиналното съобщение от потребителя
    
    Returns:
        str: Почистеното и валидирано съобщение
    """
    if not isinstance(message, str):
        return ""
    
    # Премахване на излишни интервали
    message = message.strip()
    
    # Ограничаване на дължината
    if len(message) > MAX_MESSAGE_LENGTH:
        message = message[:MAX_MESSAGE_LENGTH]
    
    # Премахване на HTML тагове
    message = re.sub(r'<[^>]+>', '', message)
    
    # Премахване на множествени интервали
    message = re.sub(r'\s+', ' ', message)
    
    return message

def _validate_coordinate_object(coord_dict: Dict) -> Optional[Dict]:
    """
    Валидира отделен обект с координати (lat, lng).
    Връща валидирания обект {'lat': float, 'lng': float} или None, ако е невалиден.
    """
    lat = coord_dict.get('lat')
    lng = coord_dict.get('lng')

    if lat is None or lng is None:
        return None

    try:
        lat = float(lat)
        lng = float(lng)

        is_valid, _ = validate_coordinates(lat, lng) # Използваме съществуващата функция
        if is_valid:
            return {'lat': lat, 'lng': lng}
        else:
            return None
    except (ValueError, TypeError) as e:
        logger.warning(f"Невалиден тип координати в обект: {e}")
        return None

def parse_ai_response(content: str) -> Dict[str, Any]:
    """
    Парсва AI отговора с подобрено JSON извличане.
    Връща JSON обект с "response" и винаги "coords" като списък от валидирани координати.
    """
    response_text = ""
    extracted_coords = []

    try:
        parsed_data = json.loads(content)
        response_text = parsed_data.get('response', '')
        raw_coords = parsed_data.get('coords')

        if raw_coords:
            if isinstance(raw_coords, dict): # Обработка на единичен обект от coords
                validated_single_coord = _validate_coordinate_object(raw_coords)
                if validated_single_coord:
                    # Ако е единична координата, я добавяме с общо име
                    extracted_coords.append({"AI Suggested Location": validated_single_coord})
            elif isinstance(raw_coords, list): # Обработка на списък от coords
                for item in raw_coords:
                    if isinstance(item, dict):
                        # Очакваме елементите в списъка да са {"Име на маршрут": {"lat": X, "lng": Y}}
                        for name, coords_dict in item.items():
                            if isinstance(coords_dict, dict):
                                validated_coord = _validate_coordinate_object(coords_dict)
                                if validated_coord:
                                    extracted_coords.append({name: validated_coord})
        
    except json.JSONDecodeError as e:
        logger.warning(f"Неуспешно парсване на JSON отговор: {e}. Използвам целия текст за отговор.")
        response_text = content # Използваме цялото съдържание като текстов отговор
    except Exception as e:
        logger.error(f"Грешка при парсване на AI отговор: {e}. Използвам целия текст за отговор.")
        response_text = content
    
    return {'response': response_text, 'coords': extracted_coords}


def _extract_keywords_from_message(message: str) -> Dict[str, str]:
    """Извлича ключови думи от съобщението. (Опростена версия, може да се подобри с LLM)"""
    # Тази функция е идентична с тази в query.py, но е дублирана тук за по-лесен достъп
    # и за да се избегнат циклични импорти, ако беше в app.py
    keywords = {}
    message_lower = message.lower()
    
    # Региони
    regions = {
        'витоша': ['витоша'], 'рила': ['рила', 'седемте рилски езера'],
        'пирин': ['пирин', 'вихрен'], 'стара планина': ['стара планина', 'балкан', 'ботев'],
        'родопи': ['родопи', 'смолян', 'пампорово', 'триград'],
        'странджа': ['странджа'], 'пловдив': ['пловдив'], 'софия': ['софия'],
        'варна': ['варна'], 'бургас': ['бургас'], 'търново': ['търново', 'велико търново'],
        'етрополски балкан': ['етрополски балкан'], 'централен балкан': ['централен балкан'],
        'чупренска планина': ['чупренска планина', 'миджур'], 'западни родопи': ['западни родопи'],
        'трявна': ['трявна'],
        'перущица': ['перущица'],
        'село горни лом': ['село горни лом', 'горни лом'],
        'смолян': ['смолян'],
        'асеновград': ['асеновград'],
        'сопот': ['сопот'],
        'шипка': ['шипка'],
        'калофер': ['калофер'],
        'копривщица': ['копривщица'],
        'чипровци': ['чипровци'],
        'ягодина': ['ягодина'],
        'добринище': ['добринище'],
        'панагюрище': ['панагюрище'],
        'велинград': ['велинград'],
        'брацигово': ['брацигово'],
        'девин': ['девин'],
        'мадан': ['мадан'],
        'златоград': ['златоград'],
        'могилица': ['могилица']
    }
    for region, synonyms in regions.items():
        if any(syn in message_lower for syn in synonyms):
            keywords['region'] = region
            break
    
    # Трудност
    difficulties = {
        'лесна': ['лесна', 'лесни', 'начинаещ', 'лек', 'лека', 'семеен', 'ниска'],
        'средна': ['средна', 'средни', 'умерена', 'умерени', 'нормална'],
        'трудна': ['трудна', 'трудни', 'тежка', 'предизвикателна', 'експертна', 'висока']
    }
    for difficulty, synonyms in difficulties.items():
        if any(syn in message_lower for syn in synonyms):
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
        if any(syn in message_lower for syn in synonyms):
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
        if any(syn in message_lower for syn in synonyms):
            keywords['season'] = season
            break
            
    return keywords

def analyze_query_intent(user_message: str) -> Dict[str, bool]:
    """Анализира интента на потребителската заявка."""
    message_lower = user_message.lower()
    
    return {
        'is_route_query': any(word in message_lower for word in [
            'маршрут', 'пътека', 'около', 'близо до', 'препоръчай', 'покажи',
            'витоша', 'рила', 'пирин', 'родопи', 'стара планина', 'търся', 'искам'
        ]),
        'is_advice_query': any(word in message_lower for word in [
            'какво да нося', 'екипировка', 'подготовка', 'съвети', 'безопасност'
        ]),
        'is_specific_location': any(word in message_lower for word in [
            'софия', 'пловдив', 'варна', 'бургас', 'стара загора', 'трявна', 'белица'
        ]),
        'has_difficulty': any(word in message_lower for word in [
            'лесна', 'лесни', 'средна', 'средни', 'трудна', 'трудни'
        ]),
        'is_map_request': any(word in message_lower for word in ['карта', 'картата', 'покажи на картата'])
    }

# ============================================================================
# ГЛАВНА ФУНКЦИЯ ЗА GPT ОТГОВОРИ
# ============================================================================

@lru_cache(maxsize=100) # Кеширане на GPT отговори по хеш на съобщението и контекста
def get_gpt_response_cached(user_message: str, context_hash: str) -> str:
    """Кеширана версия на GPT заявката, която извиква _get_gpt_response_internal."""
    # Тук не подаваме целия контекст, а само хеш, за да може lru_cache да работи.
    # _get_gpt_response_internal ще трябва да пресъздаде контекста или да го получи от друг източник.
    # В случая, контекстът се изгражда вътре в get_gpt_response.
    return get_gpt_response(user_message, context_hash) # context_hash всъщност е пълният контекст тук

def get_gpt_response(user_message: str, conversation_context_text: str, retry_count: int = 0) -> str:
    """
    Генерира отговор от OpenAI GPT модела с подобрено error handling и интелигентен анализ.
    
    Args:
        user_message: Съобщението от потребителя
        conversation_context_text: Контекст за разговора, който включва намерени маршрути
        retry_count: Брой опити за retry
    
    Returns:
        str: JSON форматиран отговор
    """
    max_retries = 2
    
    if not openai_client:
        logger.error("OpenAI клиентът не е инициализиран. Не може да се генерира AI отговор.")
        return json.dumps({
            "response": "AI услугата временно не е достъпна. Моля, опитайте отново по-късно.",
            "error": True
        })

    try:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT + "\n\n" + conversation_context_text},
            {"role": "assistant", "content": FAQ_CONTENT}, # Добавяме FAQ като част от асистент ролята
            {"role": "user", "content": user_message}
        ]

        logger.info(f"Изпращане на заявка към OpenAI с модел: gpt-3.5-turbo") # или gpt-4o-mini
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo", 
            messages=messages,
            temperature=0.0, 
            max_tokens=256, 
            timeout=30
        )
        
        if not response or not response.choices or not response.choices[0] or not response.choices[0].message:
            logger.error("Празен или непълен отговор от OpenAI API.")
            raise ValueError("Empty or incomplete response from OpenAI API.")
        
        ai_response_content = response.choices[0].message.content
        
        if not ai_response_content:
            logger.error("AI отговорът е празен.")
            raise ValueError("AI response content is empty.")

        parsed_response = parse_ai_response(ai_response_content)
        
        # Добавяме метаданни за дебъгване, ако е необходимо
        if 'coords' in parsed_response and parsed_response['coords']:
            # Логваме първата координата, ако има повече, за по-кратък лог
            if parsed_response['coords']:
                first_coord = parsed_response['coords'][0]
                # Извличаме името на маршрута и координатите му
                name = list(first_coord.keys())[0]
                lat = first_coord[name]['lat']
                lng = first_coord[name]['lng']
                logger.info(f"Финално валидирани координати в отговора: {name} (lat={lat}, lng={lng}). Общо: {len(parsed_response['coords'])}")
        else:
            logger.info("Няма валидни координати в отговора.")

        return json.dumps(parsed_response)
            
    except Exception as e:
        logger.error(f"❌ Грешка при OpenAI заявка (опит {retry_count + 1}): {e}")
        
        if retry_count < max_retries and should_retry(e):
            logger.info(f"🔄 Повторен опит {retry_count + 1}/{max_retries}")
            import time
            time.sleep(1 * (retry_count + 1))
            return get_gpt_response(user_message, conversation_context_text, retry_count + 1)
        
        logger.error(f"Stack trace: {traceback.format_exc()}")
        
        return json.dumps({
            "response": "Възникна техническа грешка при обработката на заявката. Моля, опитайте отново.",
            "error": True
        })

def should_retry(error):
    """Определя дали грешката заслужава retry."""
    error_str = str(error).lower()
    return any(keyword in error_str for keyword in [
        'timeout', 'connection', 'network', 'rate limit'
    ])

conversation_state = {} 

def get_conversation_context(user_id="default"):
    """Получава контекста на разговора за конкретен потребител."""
    if user_id not in conversation_state:
        conversation_state[user_id] = {
            "stage": "initial",
            "preferences": {},
            "last_results": [],
            "question_count": 0,
            "last_recommendations": []
        }
    return conversation_state[user_id]

def update_conversation_state(user_id="default", **kwargs):
    """Актуализира състоянието на разговора."""
    state = get_conversation_context(user_id)
    state.update(kwargs)
    return state


def manage_conversation_history(
    history: List[Dict[str, str]], 
    new_message: Dict[str, str], 
    max_length: int = MAX_CONVERSATION_HISTORY
) -> List[Dict[str, str]]:
    """
    Управлява историята на разговора като поддържа определен максимален размер.
    """
    history.append(new_message)
    if len(history) > max_length:
        history = history[-max_length:]
    return history


# ============================================================================
# ОСНОВНИ МАРШРУТИ НА ПРИЛОЖЕНИЕТО
# ============================================================================

@app.route('/')
def home():
    """Зарежда началната страница на приложението."""
    return render_template('index.html')

@app.route('/querydata', methods=['POST'])
def handle_querydata():
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        user_id = data.get('user_id', 'default') 
        
        logger.info(f"📨 Получена заявка: '{user_message}' (Потребител: {user_id})")

        sanitized_message = sanitize_user_input(user_message)
        if not sanitized_message:
            return jsonify({
                'response': 'Моля, въведете смислено съобщение.',
                'error': True
            }), 400
        
        # Инициализация на сесията за история на разговора
        if 'conversation_history' not in session:
            session['conversation_history'] = []
        
        conversation_history = session['conversation_history']
        
        # Добавяне на потребителското съобщение към историята
        conversation_history = manage_conversation_history(
            conversation_history,
            {"role": "user", "content": user_message}
        )

        # Обработка на общи заявки (поздрави, помощ и т.н.)
        general_response = handle_general_queries(sanitized_message)
        if general_response:
            # Ако има общ отговор, добавяме го към историята и връщаме
            conversation_history = manage_conversation_history(
                conversation_history,
                {"role": "assistant", "content": general_response['response']}
            )
            session['conversation_history'] = conversation_history
            return jsonify(general_response)

        # Анализ на интента и извличане на ключови думи от съобщението
        query_intent = analyze_query_intent(sanitized_message)
        extracted_keywords = _extract_keywords_from_message(sanitized_message)
        
        logger.info(f"Анализ на интента: {query_intent}")
        logger.info(f"Извлечени ключови думи: {extracted_keywords}")

        matching_trails = []
        no_local_results = False
        
        # 1. Първо опит за търсене с общото съобщение
        if any(word in sanitized_message.lower() for word in ['всички', 'всичко', 'цялата информация']):
            matching_trails = list_all_trails()
            logger.info(f"🔍 Намерени {len(matching_trails)} маршрута чрез list_all_trails (обща заявка).")
        else:
            matching_trails = search_trails(sanitized_message)
            logger.info(f"🔍 Намерени {len(matching_trails)} маршрута чрез search_trails (локално търсене).")

        # 2. Ако няма локални резултати, опит за разширено търсене с извлечени ключови думи
        if not matching_trails:
            no_local_results = True
            if extracted_keywords:
                search_params_advanced = {
                    'region': extracted_keywords.get('region'),
                    'difficulty': extracted_keywords.get('difficulty'),
                    'best_season': [extracted_keywords['season']] if 'season' in extracted_keywords else None,
                    'attraction_keywords': [extracted_keywords['type']] if 'type' in extracted_keywords else None,
                }
                # Премахване на None стойности от search_params_advanced
                search_params_advanced = {k: v for k, v in search_params_advanced.items() if v is not None}
                
                if search_params_advanced:
                    matching_trails = advanced_search(**search_params_advanced)
                    logger.info(f"🔍 Намерени {len(matching_trails)} маршрута чрез advanced_search (след неуспешно локално).")
                else:
                    logger.info("ℹ️ Няма достатъчно ключови думи за разширено търсене след неуспешно локално.")

        # Изграждане на контекст за AI модела
        context = build_context_from_trails(matching_trails) # Използваме тази от query.py
        
        # Допълнителен контекст за AI, ако няма намерени маршрути
        if not matching_trails:
            if no_local_results and not extracted_keywords:
                 context += "\n\nИНСТРУКЦИЯ: Не бяха намерени конкретни маршрути по заявката. Моля, попитайте потребителя дали иска да опита разширено търсене, като включи критерии като регион, трудност, сезон или тип атракция (напр. 'екопътека край Трявна, лесна')."
            elif no_local_results and extracted_keywords:
                 context += "\n\nИНСТРУКЦИЯ: Не бяха намерени конкретни маршрути с текущите филтри. Моля, попитайте потребителя дали иска да промени критериите за търсене или да му предложите популярни маршрути по неговите ключови думи."

        # Генериране на AI отговор
        full_messages_for_gpt = [
            {"role": "system", "content": SYSTEM_PROMPT + "\n\n" + context},
            {"role": "assistant", "content": FAQ_CONTENT} 
        ]
        full_messages_for_gpt.extend(conversation_history) # Добавяме цялата текуща история

        logger.info(f"Изпращане на заявка към OpenAI с модел: gpt-3.5-turbo")
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=full_messages_for_gpt,
            temperature=0.0,
            max_tokens=256
        )
        
        if not response or not response.choices or not response.choices[0] or not response.choices[0].message:
            logger.error("Празен или непълен отговор от OpenAI API.")
            raise ValueError("Empty or incomplete response from OpenAI API.")
        
        ai_response_content = response.choices[0].message.content
        
        if not ai_response_content:
            logger.error("AI отговорът е празен.")
            raise ValueError("AI response content is empty.")
        
        parsed_response = parse_ai_response(ai_response_content)

        # 3. Винаги показване на карти (ако има данни)
        # Ако AI не е дал координати, но има намерени маршрути, добавяме техните координати
        if not parsed_response.get('coords') and matching_trails:
            coords_from_db = []
            for trail in matching_trails:
                location = trail.get('location', {})
                coordinates = location.get('coordinates', {})
                if coordinates.get('_validated'): 
                    coords_from_db.append({
                        trail.get('name', 'Неименован маршрут'): {
                            'lat': coordinates['latitude'],
                            'lng': coordinates['longitude']
                        }
                    })
            if coords_from_db:
                parsed_response['coords'] = coords_from_db
                logger.info(f"Добавени {len(coords_from_db)} координати от базата към отговора (за показване на карта).")
        
        # Добавяне на AI отговора към историята на разговора
        conversation_history = manage_conversation_history(
            conversation_history,
            {"role": "assistant", "content": parsed_response.get('response', '')} 
        )
        session['conversation_history'] = conversation_history

        # Добавяне на метаданни
        parsed_response['source'] = 'EcoTrails AI Assistant'
        parsed_response['trails_found'] = len(matching_trails)
        parsed_response['extracted_keywords'] = extracted_keywords
        parsed_response['query_intent'] = query_intent
        
        return jsonify(parsed_response)

    except Exception as e:
        logger.error(f"❌ Критична грешка в handle_querydata: {e}")
        logger.error(f"Stack trace: {traceback.format_exc()}")
        
        return jsonify({
            'response': 'Възникна техническа грешка при обработката на заявката. Моля, опитайте отново.',
            'error': True
        }), 500

def handle_general_queries(message: str) -> Optional[Dict]:
    """
    Обработва общи заявки и поздрави.
    """
    message_lower = message.lower().strip()
    
    greetings = ['здравей', 'здрасти', 'привет', 'hello', 'hi', 'добър ден']
    if any(greeting in message_lower for greeting in greetings):
        return {
            'response': 'Здравейте! 👋 Аз съм вашият интелигентен туристически асистент за екопътеки в България. Как мога да ви помогна днес?',
            'source': 'system'
        }
    
    help_keywords = ['помощ', 'help', 'как работи', 'какво можеш']
    if any(keyword in message_lower for keyword in help_keywords):
        return {
            'response': '''Мога да ви помогна с:

🗺️ Намиране на подходящи маршрути по име или регион
📍 Информация за местоположения и координати  
🥾 Съвети за подготовка и екипировка
🌟 Препоръки според вашите предпочитания
⛰️ Детайли за трудност и продължителност

Примери за въпроси:
- "Покажи маршрути в Рила"
- "Лесни маршрути за начинаещи"
- "Къде да отида през есента?"''',
            'source': 'system'
        }
    
    thanks = ['благодаря', 'мерси', 'thanks', 'спасибо']
    if any(thank in message_lower for thank in thanks):
        return {
            'response': 'Моля! Приятно пътуване и безопасни преходи! 🏞️✨',
            'source': 'system'
        }
    
    return None

@app.route('/trails/all', methods=['GET'])
def get_all_trails_endpoint(): # Променено име, за да не се бърка с импортираната функция
    """
    Връща всички налични маршрути.
    """
    try:
        trails = list_all_trails() # Използваме импортираната функция
        
        formatted_trails = []
        for trail in trails:
            location_data = trail.get('location', {})
            coordinates_data = location_data.get('coordinates', {})
            
            trail_summary = {
                'id': trail.get('id', ''),
                'name': trail.get('name', 'Неименован маршрут'),
                'region': location_data.get('region', 'Неизвестен регион'),
                'difficulty': trail.get('trail_details', {}).get('difficulty', 'Неопределена'),
                # Важно: Leaflet очаква 'lat' и 'lng', докато eco.json има 'latitude' и 'longitude'
                'coordinates': {
                    'lat': float(coordinates_data.get('latitude', 0.0)) if coordinates_data.get('latitude') else 0.0,
                    'lng': float(coordinates_data.get('longitude', 0.0)) if coordinates_data.get('longitude') else 0.0
                }
            }
            formatted_trails.append(trail_summary)
        
        return jsonify({
            'trails': formatted_trails,
            'total_count': len(formatted_trails)
        })
        
    except Exception as e:
        logger.error(f"❌ Грешка при извличане на всички маршрути: {e}")
        logger.error(f"Stack trace: {traceback.format_exc()}")
        return jsonify({'error': 'Грешка при зареждане на маршрутите'}), 500

@app.route('/trails/by_id/<trail_id>', methods=['GET'])
def get_trail_details_endpoint(trail_id: str):
    """
    Връща детайли за конкретен маршрут.
    """
    try:
        if not trail_id or not isinstance(trail_id, str):
            return jsonify({
                'error': 'Невалиден идентификатор на маршрут',
                'code': 'INVALID_TRAIL_ID'
            }), 400
        
        # get_trail_by_id очаква int или str, но в eco.json ID-тата са int.
        # Уверете се, че го подавате като int.
        try:
            numeric_trail_id = int(trail_id)
        except ValueError:
            return jsonify({
                'error': f'Невалиден формат на ID: "{trail_id}". Очаква се число.',
                'code': 'INVALID_ID_FORMAT'
            }), 400

        trail = get_trail_by_id(numeric_trail_id) # Използваме импортираната функция
        if trail:
            return jsonify(trail)
        else:
            return jsonify({
                'error': f'Маршрут с идентификатор "{trail_id}" не съществува',
                'code': 'TRAIL_NOT_FOUND'
            }), 404
            
    except Exception as e:
        logger.error(f"❌ Грешка при извличане на маршрут {trail_id}: {e}")
        logger.error(f"Stack trace: {traceback.format_exc()}")
        return jsonify({
            'error': 'Възникна грешка при извличането на маршрута',
            'code': 'DATABASE_ERROR'
        }), 500

@app.route('/trails/advanced_search', methods=['POST'])
def advanced_search_endpoint():
    """
    Разширено търсене на маршрути.
    """
    try:
        search_params = request.json or {}
        
        # Санитизация на всички стрингови параметри
        sanitized_params = {}
        for key, value in search_params.items():
            if isinstance(value, str):
                sanitized_params[key] = sanitize_user_input(value)
            elif isinstance(value, list) and all(isinstance(i, str) for i in value):
                sanitized_params[key] = [sanitize_user_input(s) for s in value]
            else:
                sanitized_params[key] = value

        logger.info(f"🔍 Разширено търсене с параметри: {sanitized_params}")
        
        search_results = advanced_search(**sanitized_params) # Използваме импортираната функция
        
        return jsonify({
            'results': search_results,
            'count': len(search_results),
            'search_criteria': sanitized_params
        })
        
    except Exception as e:
        logger.error(f"❌ Грешка при разширено търсене: {e}")
        logger.error(f"Stack trace: {traceback.format_exc()}")
        return jsonify({
            'error': 'Възникна грешка при разширеното търсене',
            'code': 'SEARCH_ERROR'
        }), 500

@app.route('/route/calculate', methods=['POST'])
def calculate_hiking_route():
    """
    Изчислява оптимален пешеходен маршрут между две точки.
    """
    if not ors_client:
        return jsonify({
            'error': 'Услугата за маршрутизация не е достъпна (липсва API ключ)',
            'code': 'SERVICE_UNAVAILABLE'
        }), 503
    
    try:
        request_data = request.json
        if not request_data:
            return jsonify({
                'error': 'Няма предоставени данни за маршрута',
                'code': 'NO_DATA'
            }), 400
        
        start_point = request_data.get('start')
        end_point = request_data.get('end')
        
        if not start_point or not end_point:
            return jsonify({
                'error': 'Моля, предоставете начална и крайна точка',
                'code': 'MISSING_COORDINATES'
            }), 400
        
        # Openrouteservice очаква [longitude, latitude]
        # Validating coordinates before passing to ORS
        if not (isinstance(start_point, list) and len(start_point) == 2 and
                isinstance(end_point, list) and len(end_point) == 2):
            return jsonify({
                'error': 'Невалиден формат на координатите. Очакват се [longitude, latitude].',
                'code': 'INVALID_COORDINATE_FORMAT'
            }), 400
        
        # Валидация на стойностите на координатите
        # validate_coordinates приема (latitude, longitude), а ors очаква (longitude, latitude)
        start_valid, start_error = validate_coordinates(start_point[1], start_point[0])
        if not start_valid:
            return jsonify({
                'error': f'Начална точка: {start_error}',
                'code': 'INVALID_START_COORDINATES'
            }), 400
        
        end_valid, end_error = validate_coordinates(end_point[1], end_point[0])
        if not end_valid:
            return jsonify({
                'error': f'Крайна точка: {end_error}',
                'code': 'INVALID_END_COORDINATES'
            }), 400
        
        logger.info(f"🗺️ Изчисляване на маршрут от {start_point} до {end_point}")
        
        route_data = ors_client.directions(
            coordinates=[start_point, end_point],
            profile='foot-hiking',
            format='geojson',
            options={
                'avoid_features': ['highways'],
                'preference': 'recommended'
            }
        )
        
        logger.info("✅ Маршрутът е изчислен успешно")
        return jsonify(route_data)
        
    except Exception as e:
        logger.error(f"❌ Грешка при изчисляване на маршрута: {e}")
        logger.error(f"Stack trace: {traceback.format_exc()}")
        return jsonify({
            'error': 'Възникна грешка при изчисляването на маршрута',
            'code': 'ROUTING_ERROR'
        }), 500

# ============================================================================
# ОБРАБОТЧИЦИ НА ГРЕШКИ
# ============================================================================

@app.errorhandler(404)
def handle_not_found(error):
    """Обработва 404 грешки."""
    return jsonify({
        'error': 'Заявеният ресурс не е намерен',
        'code': 'NOT_FOUND',
        'status': 404
    }), 404

@app.errorhandler(500)
def handle_internal_error(error):
    """Обработва 500 грешки."""
    logger.error(f"Вътрешна грешка на сървъра: {error}")
    logger.error(f"Stack trace: {traceback.format_exc()}")
    return jsonify({
        'error': 'Възникна вътрешна грешка на сървъра',
        'code': 'INTERNAL_SERVER_ERROR',
        'status': 500
    }), 500

@app.errorhandler(400)
def handle_bad_request(error):
    """Обработва 400 грешки."""
    logger.error(f"Невалидна заявка: {error}")
    logger.error(f"Stack trace: {traceback.format_exc()}")
    return jsonify({
        'error': 'Невалидна заявка',
        'code': 'BAD_REQUEST',
        'status': 400
    }), 400

# ============================================================================
# СТАРТИРАНЕ НА ПРИЛОЖЕНИЕТО
# ============================================================================

if __name__ == '__main__':
    """
    Главна функция за стартиране на Flask приложението.
    """
    logger.info("🌿 Стартиране на туристическия чатбот за екопътеки...")
    logger.info("📍 Приложението ще бъде достъпно на: http://localhost:5000")
    logger.info("🔧 Режим на разработка: Активиран")
    
    app.run(
        debug=True,
        host='0.0.0.0',
        port=5000,
        threaded=True
    )
