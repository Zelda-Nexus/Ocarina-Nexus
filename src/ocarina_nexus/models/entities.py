"""
Pydantic schemas for Ocarina of Time entities.
Phase 1 — Characters.
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class Race(str, Enum):
    HYLIAN = "Hylian"
    KOKIRI = "Kokiri"
    GORON = "Goron"
    ZORA = "Zora"
    GERUDO = "Gerudo"
    SHEIKAH = "Sheikah"
    DEKU = "Deku"
    FAIRY = "Fairy"
    HUMAN = "Human"
    UNKNOWN = "Unknown"


class Timeline(str, Enum):
    CHILD = "child"
    ADULT = "adult"
    BOTH = "both"
    UNKNOWN = "unknown"


class CharacterRole(str, Enum):
    PROTAGONIST = "protagonist"
    ANTAGONIST = "antagonist"
    NPC = "npc"
    SAGE = "sage"
    BOSS = "boss"
    MINIBOSS = "miniboss"
    SHOP = "shop"


class RawCharacter(BaseModel):
    """Raw data from scraping (Bronze layer). Full infobox kept as-is — no information loss."""
    name: str
    url: str
    infobox: dict[str, str] = Field(default_factory=dict)
    description: Optional[str] = None
    categories: list[str] = Field(default_factory=list)
    source: str = "zeldawiki"
    scraped_at: Optional[str] = None


class Character(BaseModel):
    """Cleaned and normalized entity (Silver layer)."""
    id: str
    name: str
    race: Race = Race.UNKNOWN
    role: CharacterRole = CharacterRole.NPC
    timeline: Timeline = Timeline.UNKNOWN
    titles: list[str] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)
    family: Optional[str] = None
    association: Optional[str] = None
    description: Optional[str] = None
    is_playable: bool = False
    is_boss: bool = False
    source_url: str
    scraped_at: str
