from typing import Optional

from pydantic import BaseModel


class Entry(BaseModel):
    """Entry"""

    title: str
    link: str
    description: Optional[str]
    topic: Optional[str] = ""

    def __repr__(self):
        return f"Entry(title={self.title}, link={self.link})"


class FilterResponseEntry(BaseModel):
    """Response entry"""

    title: str
    link: str
    topic: str

    def __repr__(self):
        return (
            f"ResponseEntry(link={self.link}, title={self.title}, topic={self.topic})"
        )


class AiFilterResponse(BaseModel):
    """AI response"""

    entries: list[FilterResponseEntry]

    def __repr__(self):
        return f"AiResponse(entries={self.entries})"


class AiSummaryResponse(BaseModel):
    """AI summary response"""

    summary: str

    def __repr__(self):
        return f"AiSummaryResponse(summary={self.summary})"
