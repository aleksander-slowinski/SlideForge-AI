
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from models.schemas import LayoutType


PresentationType = Literal[
    "academic",
    "business",
    "general",
]


class PlanSection(BaseModel):
    section_number: int = Field(ge=1, le=10)

    title: str = Field(
        min_length=1,
        max_length=100,
    )

    goal: str = Field(
        min_length=1,
        max_length=250,
    )


class PlannedSlide(BaseModel):
    slide_number: int = Field(ge=1, le=25)

    section_number: int = Field(ge=1, le=10)

    title: str = Field(
        min_length=1,
        max_length=100,
    )

    layout: LayoutType

    objective: str = Field(
        min_length=1,
        max_length=250,
    )

    content_brief: list[str] = Field(
        min_length=1,
        max_length=4,
    )


class PresentationPlanSchema(BaseModel):
    topic: str = Field(min_length=1)

    presentation_type: PresentationType

    slides_count: int = Field(ge=1, le=25)

    sections: list[PlanSection] = Field(
        min_length=1,
        max_length=10,
    )

    slides: list[PlannedSlide] = Field(
        min_length=1,
        max_length=25,
    )

    @model_validator(mode="after")
    def validate_plan(self):

        # Liczba slajdów
        if len(self.slides) != self.slides_count:
            raise ValueError(
                "Liczba zaplanowanych slajdów "
                "nie odpowiada slides_count."
            )

        # Numeracja slajdów 1..N
        numbers = [
            slide.slide_number
            for slide in self.slides
        ]

        if numbers != list(
            range(1, self.slides_count + 1)
        ):
            raise ValueError(
                "Slajdy muszą być ponumerowane "
                "kolejno od 1 do N."
            )

        # Numeracja sekcji
        section_numbers = [
            section.section_number
            for section in self.sections
        ]

        if section_numbers != list(
            range(1, len(self.sections) + 1)
        ):
            raise ValueError(
                "Sekcje muszą być ponumerowane "
                "kolejno od 1."
            )

        # Wszystkie slajdy należą do sekcji
        available_sections = set(section_numbers)

        used_sections = [
            slide.section_number
            for slide in self.slides
        ]

        if not set(used_sections).issubset(
            available_sections
        ):
            raise ValueError(
                "Slajd odwołuje się "
                "do nieistniejącej sekcji."
            )

        # Sekcje występują w logicznej kolejności
        if used_sections != sorted(used_sections):
            raise ValueError(
                "Sekcje slajdów nie mogą "
                "występować w przypadkowej kolejności."
            )

        # Każda zadeklarowana sekcja ma slajd
        if set(used_sections) != available_sections:
            raise ValueError(
                "Każda sekcja musi zawierać "
                "co najmniej jeden slajd."
            )

        return self
