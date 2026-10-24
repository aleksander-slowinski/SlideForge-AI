from pptx import Presentation
from ppt_service import create_presentation

import os
from google import genai
from google.genai import types
from dotenv import load_dotenv
from models.schemas import PresentationSchema
from prompt_builder import get_system_prompt

# 1. Ładowanie zmiennych środowiskowych i konfiguracja API
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("Brak klucza GEMINI_API_KEY w pliku .env! Dodaj go przed uruchomieniem.")

# Inicjalizacja nowego klienta
client = genai.Client(api_key=api_key)

def generate_presentation(topic: str, slides_count: int = 3) -> PresentationSchema:
    print(f"Wysyłam zapytanie do Gemini... Temat: '{topic}'")
    
    user_prompt = f"Stwórz prezentację na temat: {topic}. Wymagana liczba slajdów: {slides_count}."
    
    # 2. Konfiguracja zapytania z użyciem nowego SDK
    config = types.GenerateContentConfig(
        system_instruction=get_system_prompt(),
        temperature=0.2,
        response_mime_type="application/json",
    )
    
    # 3. Strzał do API (używamy najnowszego modelu gemini-3.8-flash)
    response = client.models.generate_content(
        model='gemini-3.8-flash',
        contents=user_prompt,
        config=config
    )
    
    # 4. Sprawdzam, co wypluł model i wrzucam prosto w naszego Pydantica
    try:
        presentation = PresentationSchema.model_validate_json(response.text)
        return presentation
    except Exception as e:
        print("\n[BŁĄD] Model zwrócił dane, które nie przeszły przez naszą bramkę walidacyjną!")
        print("Surowa odpowiedź modelu:\n", response.text)
        raise e

if __name__ == "__main__":
    temat = "Wprowadzenie do uczenia maszynowego w analizie danych"
    liczba = 4
    
    # 1. Generacja i walidacja danych (LLM -> JSON -> Pydantic)
    wynikowa_prezentacja = generate_presentation(temat, slides_count=liczba)
    
    print("\n[SUKCES] Gemini wygenerował poprawny JSON, a Pydantic go zatwierdził.")
    print("-" * 40)
    print(f"Tytuł główny: {wynikowa_prezentacja.title}")
    print(f"Liczba slajdów: {wynikowa_prezentacja.slides_count}")
    
    # 2. Generowanie pliku PowerPoint (Pydantic -> PPTX)
    create_presentation(wynikowa_prezentacja, "ML_w_analizie_danych.pptx")