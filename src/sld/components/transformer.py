import re
from typing import Optional

from pydantic import Field, model_validator

from sld.components.base import Component, DrawContext, Kind
from sld.components.registry import register
from sld.util import fmt_num, same_voltage

_RATIO = re.compile(r"^\s*([\d.,]+)\s*/\s*([\d.,]+)\s*(kV|V)?\s*$", re.IGNORECASE)


def parse_ratio(text: str) -> tuple[float, float]:
    m = _RATIO.match(text)
    if not m:
        raise ValueError(f"Spannungsverhältnis '{text}' nicht lesbar, erwartet z. B. '20/0.4 kV'")
    a, b = (float(g.replace(",", ".")) for g in m.group(1, 2))
    if (m.group(3) or "kV").lower() == "v":
        a, b = a / 1000, b / 1000
    if a <= 0 or b <= 0:
        raise ValueError("Spannungen müssen positiv sein")
    return a, b


@register("transformer")
class Transformer(Component):
    """Zweiwicklungstransformator."""

    kind = Kind.SERIES
    title = "Transformator"
    ref_letter = "T"
    size = (9.0, 15.0)
    max_connections = 99  # wird separat geprüft (Erdung zählt nicht)
    is_transformer = True

    rating_kva: float = Field(gt=0, description="Bemessungsleistung Sn in kVA")
    ratio: Optional[str] = Field(None, description="Spannungsverhältnis, z. B. '20/0.4 kV'")
    hv_kv: Optional[float] = Field(None, gt=0, description="Oberspannung in kV (alternativ zu ratio)")
    lv_kv: Optional[float] = Field(None, gt=0, description="Unterspannung in kV (alternativ zu ratio)")
    uk_percent: Optional[float] = Field(None, gt=0, lt=100, description="Kurzschlussspannung uk in %")
    vector_group: Optional[str] = Field(None, description="Schaltgruppe, z. B. Dyn5")

    @model_validator(mode="after")
    def _check_ratio(self):
        if self.ratio:
            a, b = parse_ratio(self.ratio)
            for given, name in ((self.hv_kv, "hv_kv"), (self.lv_kv, "lv_kv")):
                if given is not None and not (same_voltage(given, a) or same_voltage(given, b)):
                    raise ValueError(f"{name}={given} passt nicht zu ratio '{self.ratio}'")
        return self

    def voltages(self) -> Optional[tuple[float, float]]:
        if self.ratio:
            return parse_ratio(self.ratio)
        if self.hv_kv and self.lv_kv:
            return self.hv_kv, self.lv_kv
        return None

    def data_lines(self) -> list[str]:
        out = [f"{fmt_num(self.rating_kva)} kVA"]
        v = self.voltages()
        if v:
            out.append(f"{fmt_num(v[0])}/{fmt_num(v[1])} kV")
        if self.uk_percent:
            out.append(f"uk = {fmt_num(self.uk_percent)} %")
        if self.vector_group:
            out.append(self.vector_group)
        return out

    def draw(self, pen, ctx: DrawContext) -> None:
        pen.circle(0, -3, 4.5)
        pen.circle(0, 3, 4.5)
