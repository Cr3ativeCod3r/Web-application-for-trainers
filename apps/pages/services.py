import json
import os
from google import genai
from google.genai import types
from django.conf import settings

class AIServiceError(Exception):
    """Custom exception for AI service errors."""
    pass

def get_ai_sport_recommendation(answers: list, available_sports: list) -> dict:
    """
    Calls Gemini API to recommend a sport based on user answers.
    Returns a dictionary with 'recommendation' and 'suggested_sport'.
    """
    sports_str = ", ".join(sorted(available_sports)) if available_sports else "Brak sportów w bazie"
    
    prompt = f"""Na podstawie poniższych odpowiedzi użytkownika na 13 pytań, doradź mu jaki sport będzie dla niego najlepszy.
Z poniższej listy sportów (to dyscypliny oferowane przez naszych trenerów), wybierz JEDEN, który najlepiej pasuje: [{sports_str}]. 
Jeśli żaden nie pasuje w 100%, wybierz ten najbliższy prawdy. 

Zwróć odpowiedź WYŁĄCZNIE jako poprawny obiekt JSON (bez markdown block) o strukturze:
{{
  "text": "Twój motywujący tekst (2-3 akapity). Pisz jako profesjonalny trener.",
  "suggested_sport": "Dokładna nazwa wybranego sportu z listy"
}}

Odpowiedzi użytkownika:
"""
    for item in answers:
        prompt += f"Pytanie: {item.get('question')}\nOdpowiedź: {item.get('answer')}\n\n"
        
    api_key = getattr(settings, 'API_GEMINI', None) or os.environ.get('API_GEMINI') or os.environ.get('api_gemini')
    if not api_key:
        raise AIServiceError('Brak klucza API Gemini w konfiguracji serwera.')
        
    client = genai.Client(api_key=api_key)
    try:
        response = client.models.generate_content(
            model='gemini-3.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
    except Exception as e:
        raise AIServiceError(f'Błąd podczas łączenia z API Gemini: {str(e)}')
    
    # Parse JSON
    try:
        response_text = response.text.strip()
        if response_text.startswith('```json'):
            response_text = response_text[7:-3].strip()
        elif response_text.startswith('```'):
            response_text = response_text[3:-3].strip()
        
        result_data = json.loads(response_text)
        return {
            'recommendation': result_data.get('text', 'Błąd w formacie tekstu.'),
            'suggested_sport': result_data.get('suggested_sport', '')
        }
    except Exception as e:
        raise AIServiceError(f'Model zwrócił nieprawidłowy format (oczekiwano JSON). {str(e)}')
