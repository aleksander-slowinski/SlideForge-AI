
from pptx.enum.text import MSO_AUTO_SIZE
from pptx.oxml.xmlchemy import OxmlElement
from pptx.util import Pt


def fill_column(text_frame, heading: str, bullet_points: list[str]):
    """Formatuje nagłówek i punkty wewnątrz kolumny."""

    text_frame.clear()
    text_frame.word_wrap = True
    text_frame.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE

    # Nagłówek bez punktora
    heading_paragraph = text_frame.paragraphs[0]
    heading_paragraph.text = heading
    heading_paragraph.font.bold = True
    heading_paragraph.font.size = Pt(20)
    heading_paragraph.space_after = Pt(12)

    # Wyłączenie punktora odziedziczonego z szablonu
    paragraph_properties = heading_paragraph._p.get_or_add_pPr()
    paragraph_properties.append(OxmlElement("a:buNone"))

    # Punkty merytoryczne
    for point in bullet_points:
        paragraph = text_frame.add_paragraph()
        paragraph.text = point
        paragraph.level = 1
        paragraph.font.size = Pt(17)
        paragraph.space_after = Pt(7)
