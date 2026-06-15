"""
Pydantic schemas for Ocarina of Time entities.
Phase 1 - Characters.
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
    GREAT_FAIRY = "Great Fairy"
    FAIRY = "Fairy"
    DEITY = "Deity"
    UNKNOWN = "Unknown"


class Timeline(str, Enum):
    """
    NOTE: this field cannot be derived from the infobox 'Era(s)' field
    (which describes a global narrative era of the series, not when
    the character appears in OOT). Stays UNKNOWN in Phase 1,
    will be filled in Phase 3 (Lore Explorer, task P3-04).
    """
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
    """
    Raw data from scraping (Bronze layer).
    The full infobox is kept as-is: no information loss.
    """
    name: str
    url: str
    infobox: dict[str, str] = Field(default_factory=dict)
    description: Optional[str] = None
    categories: list[str] = Field(default_factory=list)
    source: str = "zeldawiki"
    scraped_at: Optional[str] = None


class Character(BaseModel):
    """
    Cleaned and normalized entity (Silver layer).
    """
    id: str
    name: str
    race: Race = Race.UNKNOWN
    gender: Optional[str] = None
    role: CharacterRole = CharacterRole.NPC
    timeline: Timeline = Timeline.UNKNOWN

    eras: list[str] = Field(default_factory=list)
    titles: list[str] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)
    family_members: list[str] = Field(default_factory=list)
    associations: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)

    description: Optional[str] = None
    is_playable: bool = False
    is_boss: bool = False

    source_url: str
    scraped_at: str
