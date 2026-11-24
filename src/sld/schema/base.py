"""Gemeinsame Felder aller Knoten (unabhängig vom Komponententyp)."""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr


class Position(BaseModel):
    """Manuelle Position (Symbolmitte) in mm, relativ zur linken oberen Ecke des Planinhalts."""

    model_config = ConfigDict(extra="forbid")
    x: float
    y: float


class NodeBase(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: Optional[str] = Field(
        None,
        min_length=1,
        description="Eindeutige Kennung (Betriebsmittelkennzeichen). Bei via-Elementen optional.",
    )
    name: Optional[str] = Field(
        None,
        description="Anzeigename am Symbol (fett). Die id bleibt intern und wird nur mit diagram.show_ids angezeigt.",
    )
    label: Optional[str] = Field(None, description="Freitext-Bezeichnung, wird am Symbol angezeigt.")
    order: Optional[int] = Field(
        None, description="Layout-Hinweis: Sortierschlüssel unter Geschwisterabgängen (kleiner = weiter links)."
    )
    pos: Optional[Position] = Field(
        None, description="Layout-Hinweis: feste Position der Symbolmitte in mm (verschiebt den Teilbaum mit)."
    )
    note: Optional[str] = Field(None, description="Bemerkung, erscheint in der Stückliste.")

    _auto_id: bool = PrivateAttr(False)

    @property
    def auto_id(self) -> bool:
        return self._auto_id
