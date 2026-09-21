from typing import Literal

from pydantic import BaseModel, Field, field_validator


class GoalInput(BaseModel):
    goal: str = Field(min_length=10, max_length=2000)
    mode: Literal['autonomous', 'human'] = 'autonomous'

    @field_validator('goal')
    @classmethod
    def clean_goal(cls, value):
        if len(value.strip()) < 10:
            raise ValueError('Describe your newsletter goal in at least 10 characters.')
        return value.strip()


class DecisionInput(BaseModel):
    action: Literal['approve', 'revise', 'cancel']
    feedback: str = Field(default='', max_length=1500)


class Plan(BaseModel):
    topic: str
    audience: str
    queries: list[str] = Field(min_length=2, max_length=3)
    approach: str


class Story(BaseModel):
    source_id: int
    headline: str = Field(min_length=5, max_length=200)
    summary: str = Field(min_length=40, max_length=1200)
    why_it_matters: str = Field(min_length=15, max_length=500)


class Newsletter(BaseModel):
    subject: str = Field(min_length=5, max_length=180)
    introduction: str = Field(min_length=20, max_length=1000)
    stories: list[Story] = Field(min_length=5, max_length=7)
    closing: str = Field(min_length=10, max_length=500)


class Review(BaseModel):
    passed: bool
    summary: str
    issues: list[str]


class Selection(BaseModel):
    source_ids: list[int] = Field(min_length=5, max_length=7)
    reason: str
