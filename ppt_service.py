from pptx import Presentation
from models.schemas import PresentationSchema, LayoutType
import os

def create_presentation(data: PresentationSchema, filename: str = "gotowa_prezentacja.pptx"):
    template_path = "template.pptx"
    
    # Zabezpieczenie: skrypt upewnia się, że szablon faktycznie istnieje w folderze
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Nie znaleziono pliku szablonu: {template_path}. Upewnij się, że jest w głównym katalogu.")
        
    # Inicjalizujemy prezentację z użyciem Twojego pliku template.pptx
    prs = Presentation(template_path) 

    # --- SLAJD TYTUŁOWY ---
    title_slide_layout = prs.slide_layouts[0]
    slide = prs.slides.add_slide(title_slide_layout)
    slide.shapes.title.text = data.title
    slide.placeholders[1].text = data.topic

    # --- SLAJDY Z TREŚCIĄ ---
    for slide_data in data.slides:
        if slide_data.layout in (LayoutType.TITLE_CONTENT, LayoutType.CONCLUSION):
            slide_layout = prs.slide_layouts[1]
            slide = prs.slides.add_slide(slide_layout)
            
            slide.shapes.title.text = slide_data.title
            
            tf = slide.placeholders[1].text_frame
            tf.clear()
            
            points = slide_data.bullet_points if slide_data.layout == LayoutType.TITLE_CONTENT else slide_data.key_points
            
            for point in points:
                p = tf.add_paragraph()
                p.text = point
                p.level = 0
                
        elif slide_data.layout == LayoutType.TWO_COLUMNS:
            slide_layout = prs.slide_layouts[3]
            slide = prs.slides.add_slide(slide_layout)
            
            slide.shapes.title.text = slide_data.title
            
            # Lewa kolumna
            col1_tf = slide.placeholders[1].text_frame
            col1_tf.clear()
            col1_tf.text = slide_data.columns[0].title
            for point in slide_data.columns[0].bullet_points:
                p = col1_tf.add_paragraph()
                p.text = point
                p.level = 1
                
            # Prawa kolumna
            col2_tf = slide.placeholders[2].text_frame
            col2_tf.clear()
            col2_tf.text = slide_data.columns[1].title
            for point in slide_data.columns[1].bullet_points:
                p = col2_tf.add_paragraph()
                p.text = point
                p.level = 1

        # Notatki prelegenta
        if slide_data.speaker_notes:
            notes_slide = slide.notes_slide
            notes_tf = notes_slide.notes_text_frame
            notes_tf.text = slide_data.speaker_notes

    prs.save(filename)
    print(f"\n[SUKCES] Prezentacja została wygenerowana i zapisana jako: {filename}")