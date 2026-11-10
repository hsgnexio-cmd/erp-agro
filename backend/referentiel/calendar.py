"""Calendrier de l'entreprise (phase 11) : jours fériés, fermetures de site, jours ouvrés.

Qui travaille quand (décision de la phase 11) :
- production (usines NAN, REN) : du lundi au vendredi ;
- expédition (plateforme PFN) et livraison des enseignes : du lundi au samedi ; c'est aussi le
  calendrier de prise de commande (heure limite de 11 h) ;
- réception des fournisseurs (entrepôt MPE) : du lundi au vendredi ; les délais fournisseurs
  sont comptés sur ce calendrier.
Jamais un jour férié, ni un jour de fermeture exceptionnelle du site concerné.
"""

from datetime import date, timedelta
from enum import Enum
from functools import lru_cache

from django.apps import apps

MAX_SEARCH_DAYS = 60


class Activity(Enum):
    """Activité de l'entreprise : jours de la semaine travaillés et site concerné."""

    PRODUCTION = ((0, 1, 2, 3, 4), None)  # site : l'usine indiquée
    SHIPPING = ((0, 1, 2, 3, 4, 5), "PFN")
    RECEIVING = ((0, 1, 2, 3, 4), "MPE")

    @property
    def weekdays(self) -> tuple[int, ...]:
        return self.value[0]

    @property
    def default_site(self) -> str | None:
        return self.value[1]


WEEKDAY_NAMES = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]


def easter(year: int) -> date:
    """Dimanche de Pâques (calendrier grégorien, algorithme dit « anonyme »)."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7  # noqa: E741
    m = (a + 11 * h + 22 * l) // 451
    month, day = divmod(h + l - 7 * m + 114, 31)
    return date(year, month, day + 1)


@lru_cache(maxsize=32)
def french_holidays(year: int) -> dict[date, str]:
    """Les 11 jours fériés de France métropolitaine."""
    sunday = easter(year)
    holidays = {
        date(year, 1, 1): "Jour de l'an",
        sunday + timedelta(days=1): "Lundi de Pâques",
        date(year, 5, 1): "Fête du travail",
        date(year, 5, 8): "Victoire 1945",
        sunday + timedelta(days=39): "Ascension",
        sunday + timedelta(days=50): "Lundi de Pentecôte",
        date(year, 7, 14): "Fête nationale",
        date(year, 8, 15): "Assomption",
        date(year, 11, 1): "Toussaint",
        date(year, 11, 11): "Armistice 1918",
        date(year, 12, 25): "Noël",
    }
    return dict(sorted(holidays.items()))


def holiday(day: date) -> str | None:
    return french_holidays(day.year).get(day)


def _site_code(activity: Activity, site) -> str | None:
    if site is None:
        return activity.default_site
    return site if isinstance(site, str) else site.code


def closure(day: date, site_code: str | None):
    """Fermeture exceptionnelle du site ce jour-là, ou None."""
    if site_code is None:
        return None
    model = apps.get_model("referentiel", "SiteClosure")
    return (
        model.objects.filter(site__code=site_code, start_date__lte=day, end_date__gte=day)
        .select_related("site")
        .first()
    )


def closed_reason(day: date, activity: Activity, site=None) -> str:
    """Raison pour laquelle l'activité ne travaille pas ce jour-là ; vide si c'est ouvré."""
    name = holiday(day)
    if name:
        return f"férié ({name})"
    if day.weekday() not in activity.weekdays:
        return "dimanche" if day.weekday() == 6 else "week-end"
    found = closure(day, _site_code(activity, site))
    if found:
        return f"fermeture {found.site.code} ({found.reason})"
    return ""


def is_open(day: date, activity: Activity, site=None) -> bool:
    return closed_reason(day, activity, site) == ""


def next_open_day(day: date, activity: Activity, site=None, *, strict: bool = False) -> date:
    """Premier jour ouvré à partir de `day` (ou après `day` si `strict`)."""
    current = day + timedelta(days=1) if strict else day
    for _ in range(MAX_SEARCH_DAYS):
        if is_open(current, activity, site):
            return current
        current += timedelta(days=1)
    raise ValueError(f"Aucun jour ouvré trouvé après le {day:%d/%m/%Y}.")


def previous_open_day(day: date, activity: Activity, site=None, *, strict: bool = False) -> date:
    """Dernier jour ouvré jusqu'à `day` (ou avant `day` si `strict`)."""
    current = day - timedelta(days=1) if strict else day
    for _ in range(MAX_SEARCH_DAYS):
        if is_open(current, activity, site):
            return current
        current -= timedelta(days=1)
    raise ValueError(f"Aucun jour ouvré trouvé avant le {day:%d/%m/%Y}.")


def add_open_days(day: date, count: int, activity: Activity, site=None) -> date:
    """`count` jours ouvrés après `day` (ou avant si `count` est négatif)."""
    current = day
    step = 1 if count >= 0 else -1
    for _ in range(abs(count)):
        current = (
            next_open_day(current, activity, site, strict=True)
            if step > 0
            else previous_open_day(current, activity, site, strict=True)
        )
    return current


def open_days(start: date, end: date, activity: Activity, site=None) -> list[date]:
    days, current = [], start
    while current <= end:
        if is_open(current, activity, site):
            days.append(current)
        current += timedelta(days=1)
    return days


def describe(day: date) -> str:
    """« mercredi 11/11/2026 » : pour les messages."""
    return f"{WEEKDAY_NAMES[day.weekday()]} {day:%d/%m/%Y}"
