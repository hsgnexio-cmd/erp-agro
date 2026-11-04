"""Données de démonstration de la surveillance : relevés, un écart, un inventaire, des alertes."""

from datetime import datetime, time, timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from referentiel.models import Location

from . import inventory, monitoring
from .models import TemperatureReading

# Chambres froides relevées deux fois par jour : (emplacement, température habituelle)
COLD_ROOMS = [
    ("MPE-FP-01", "2.6"),
    ("MPE-QUAR", "3.1"),
    ("MPE-FN-01", "-20.4"),
    ("MPE-QUAR-FN", "-19.6"),
    ("NAN-CF-MP", "2.9"),
    ("NAN-CF-SF", "3.3"),
    ("PFN-FRAIS-A", "2.2"),
]
# Variations légères d'un relevé à l'autre
VARIATIONS = [Decimal("0"), Decimal("0.4"), Decimal("-0.3"), Decimal("0.6"), Decimal("-0.5")]


def _at(day, hour: int) -> datetime:
    return timezone.make_aware(datetime.combine(day, time(hour, 0)))


@transaction.atomic
def load_demo_data() -> dict[str, int | str]:
    if TemperatureReading.objects.exists():
        return {"surveillance": "déjà présente, non modifiée"}

    today = timezone.localdate()
    now = timezone.now()
    locations = {location.code: location for location in Location.objects.all()}
    readings = 0

    for days_ago in (3, 2, 1, 0):
        day = today - timedelta(days=days_ago)
        for index, hour in enumerate((7, 15)):
            measured_at = _at(day, hour)
            if measured_at > now:
                continue
            for room_index, (code, usual) in enumerate(COLD_ROOMS):
                variation = VARIATIONS[(days_ago + index + room_index) % len(VARIATIONS)]
                temperature = Decimal(usual) + variation
                # Écart hier après-midi dans la chambre des semi-finis de NAN (vide)
                if code == "NAN-CF-SF" and days_ago == 1 and hour == 15:
                    temperature = Decimal("7.8")
                monitoring.record_temperature(
                    locations[code],
                    temperature,
                    measured_at=measured_at,
                    comment="Porte restée ouverte pendant le nettoyage"
                    if temperature == Decimal("7.8")
                    else "",
                )
                readings += 1

    # Inventaire de la chambre négative : 2 kg de petits pois manquants
    counted = 0
    frozen_room = locations.get("MPE-FN-01")
    if frozen_room is not None:
        frozen_inventory = inventory.open_inventory(
            frozen_room.site, location=frozen_room, comment="Inventaire tournant mensuel"
        )
        counts = {}
        for line in frozen_inventory.lines.select_related("lot__article"):
            found = line.expected_quantity
            if line.lot.article.code == "MP-SUR-PETPOIS":
                found -= Decimal("2")
            counts[line.id] = found
        inventory.record_counts(frozen_inventory, counts)
        inventory.validate_inventory(frozen_inventory)
        counted = len(counts)

    alerts = monitoring.run_daily_checks()
    return {
        "relevés de température": readings,
        "lignes d'inventaire": counted,
        **{f"alertes « {label} »": count for label, count in alerts.items()},
    }
