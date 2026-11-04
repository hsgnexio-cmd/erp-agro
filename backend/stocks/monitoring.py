"""Surveillance des stocks : relevés de température (règle 7) et alertes.

Les vérifications quotidiennes (péremption, relevés manquants) sont lancées chaque matin
par Celery Beat (voir stocks/tasks.py), ou à la demande : python manage.py verifier_alertes
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max, Sum
from django.utils import timezone

from referentiel.choices import DateType, TemperatureClass
from referentiel.models import Location

from . import services
from .choices import AlertLevel, AlertType, LotStatus
from .models import Alert, Lot, StockMovement, TemperatureReading

# Limites par défaut si l'emplacement n'a pas les siennes
DEFAULT_LIMITS: dict[str, tuple[Decimal | None, Decimal | None]] = {
    TemperatureClass.CHILLED: (Decimal("0"), Decimal("4")),
    TemperatureClass.FROZEN: (None, Decimal("-18")),
    TemperatureClass.AMBIENT: (None, None),
}
COLD_CLASSES = (TemperatureClass.CHILLED, TemperatureClass.FROZEN)

# Alerte de péremption proche : nombre de jours avant la date
EXPIRY_WARNING_DAYS = {DateType.DLC: 3, DateType.DDM: 30}
# Une chambre froide avec du stock doit avoir au moins un relevé sur cette durée
MAX_HOURS_WITHOUT_READING = 24


def _fr(value: Decimal) -> str:
    return f"{value.normalize():f}".replace(".", ",")


# --- Alertes ------------------------------------------------------------------


def raise_alert(
    alert_type: str,
    level: str,
    message: str,
    *,
    lot: Lot | None = None,
    location: Location | None = None,
    reading: TemperatureReading | None = None,
    allow_duplicate: bool = False,
) -> tuple[Alert, bool]:
    """Crée une alerte, sauf si la même est déjà ouverte. Renvoie (alerte, créée ?)."""
    if not allow_duplicate:
        existing = Alert.objects.filter(
            alert_type=alert_type, lot=lot, location=location, resolved_at__isnull=True
        ).first()
        if existing:
            return existing, False
    alert = Alert.objects.create(
        alert_type=alert_type,
        level=level,
        message=message,
        lot=lot,
        location=location,
        temperature_reading=reading,
    )
    return alert, True


def resolve_alert(alert: Alert, *, user, comment: str) -> Alert:
    if not alert.is_open:
        raise ValidationError("Cette alerte est déjà traitée.")
    if not comment.strip():
        raise ValidationError({"comment": "Indique ce qui a été fait pour traiter l'alerte."})
    alert.resolved_at = timezone.now()
    alert.resolved_by = user if user is not None and user.is_authenticated else None
    alert.resolution_comment = comment.strip()
    alert.save()
    return alert


# --- Relevés de température ----------------------------------------------------


def temperature_limits(location: Location) -> tuple[Decimal | None, Decimal | None]:
    """Limites de l'emplacement, ou à défaut celles de sa classe de température."""
    default_min, default_max = DEFAULT_LIMITS[location.temperature_class]
    minimum = location.min_temperature if location.min_temperature is not None else default_min
    maximum = location.max_temperature if location.max_temperature is not None else default_max
    return minimum, maximum


def lots_in_location(location: Location) -> list[Lot]:
    """Lots ayant du stock dans cet emplacement."""
    lot_ids = (
        StockMovement.objects.filter(location=location)
        .values("lot")
        .annotate(total=Sum("quantity"))
        .filter(total__gt=0)
        .values_list("lot", flat=True)
    )
    return list(Lot.objects.filter(pk__in=list(lot_ids)).select_related("article"))


@dataclass
class ReadingResult:
    reading: TemperatureReading
    alert: Alert | None = None
    blocked_lots: list[Lot] = field(default_factory=list)


@transaction.atomic
def record_temperature(
    location: Location,
    temperature: Decimal,
    *,
    user=None,
    measured_at: datetime | None = None,
    comment: str = "",
) -> ReadingResult:
    """Enregistre un relevé. Règle 7 : un écart crée une alerte et bloque les lots présents."""
    if not location.active:
        raise ValidationError({"location": f"L'emplacement {location.code} est inactif."})
    measured_at = measured_at or timezone.now()
    if measured_at > timezone.now() + timedelta(minutes=5):
        raise ValidationError({"measured_at": "Un relevé ne peut pas être daté dans le futur."})

    minimum, maximum = temperature_limits(location)
    compliant = (minimum is None or temperature >= minimum) and (
        maximum is None or temperature <= maximum
    )
    reading = TemperatureReading.objects.create(
        location=location,
        temperature=temperature,
        measured_at=measured_at,
        min_allowed=minimum,
        max_allowed=maximum,
        is_compliant=compliant,
        user=user if user is not None and user.is_authenticated else None,
        comment=comment.strip(),
    )
    result = ReadingResult(reading=reading)
    if compliant:
        return result

    limits = _limits_label(minimum, maximum)
    when = timezone.localtime(measured_at)
    reason = (
        f"Écart de température : {_fr(temperature)} °C en {location.code} ({limits}), "
        f"relevé le {when:%d/%m/%Y à %H:%M}"
    )
    for lot in lots_in_location(location):
        if lot.status in (LotStatus.RELEASED, LotStatus.QUARANTINE):
            result.blocked_lots.append(services.block_lot(lot, reason=reason))
    blocked = ", ".join(lot.number for lot in result.blocked_lots) or "aucun lot présent"
    result.alert, _ = raise_alert(
        AlertType.TEMPERATURE,
        AlertLevel.CRITICAL,
        f"{reason}. Lots bloqués : {blocked}.",
        location=location,
        reading=reading,
        allow_duplicate=True,
    )
    return result


def _limits_label(minimum: Decimal | None, maximum: Decimal | None) -> str:
    if minimum is not None and maximum is not None:
        return f"limites {_fr(minimum)} à {_fr(maximum)} °C"
    if maximum is not None:
        return f"maximum {_fr(maximum)} °C"
    return f"minimum {_fr(minimum)} °C" if minimum is not None else "sans limite"


# --- Vérifications quotidiennes ----------------------------------------------------


def run_daily_checks(today: date | None = None, now: datetime | None = None) -> dict[str, int]:
    """Péremption proche, DLC/DDM dépassées (blocage des DLC), relevés manquants."""
    today = today or timezone.localdate()
    now = now or timezone.now()
    counts = {
        "péremption proche": 0,
        "DLC dépassée (lots bloqués)": 0,
        "DDM dépassée": 0,
        "relevé manquant": 0,
    }

    lots_with_stock = (
        Lot.objects.exclude(status=LotStatus.DESTROYED)
        .filter(expiry_date__isnull=False)
        .annotate(stock=Sum("movements__quantity"))
        .filter(stock__gt=0)
        .select_related("article")
    )
    for lot in lots_with_stock:
        label = f"{lot.number} ({lot.article.code})"
        if lot.expiry_date < today:
            if lot.date_type == DateType.DLC:
                with transaction.atomic():
                    if lot.status != LotStatus.BLOCKED:
                        services.block_lot(
                            lot, reason=f"DLC dépassée le {lot.expiry_date:%d/%m/%Y}"
                        )
                    _, created = raise_alert(
                        AlertType.DLC_PASSED,
                        AlertLevel.CRITICAL,
                        f"DLC dépassée pour le lot {label} : {lot.expiry_date:%d/%m/%Y}. "
                        "Lot bloqué automatiquement, à détruire ou à déclasser.",
                        lot=lot,
                    )
                counts["DLC dépassée (lots bloqués)"] += created
            else:
                _, created = raise_alert(
                    AlertType.DDM_PASSED,
                    AlertLevel.WARNING,
                    f"DDM dépassée pour le lot {label} : {lot.expiry_date:%d/%m/%Y}. "
                    "Décision qualité à prendre.",
                    lot=lot,
                )
                counts["DDM dépassée"] += created
        elif lot.status in (LotStatus.RELEASED, LotStatus.QUARANTINE):
            days_left = (lot.expiry_date - today).days
            if days_left <= EXPIRY_WARNING_DAYS.get(lot.date_type, 0):
                when = "aujourd'hui" if days_left == 0 else f"dans {days_left} jour(s)"
                _, created = raise_alert(
                    AlertType.EXPIRY_SOON,
                    AlertLevel.WARNING,
                    f"Le lot {label} arrive à {lot.date_type} {when} "
                    f"({lot.expiry_date:%d/%m/%Y}) : à utiliser en priorité.",
                    lot=lot,
                )
                counts["péremption proche"] += created

    counts["relevé manquant"] = _check_missing_readings(now)
    return counts


def _check_missing_readings(now: datetime) -> int:
    since = now - timedelta(hours=MAX_HOURS_WITHOUT_READING)
    created_count = 0
    cold_locations = Location.objects.filter(
        active=True, temperature_class__in=COLD_CLASSES
    ).annotate(last_reading=Max("temperature_readings__measured_at"))
    for location in cold_locations:
        if location.last_reading and location.last_reading >= since:
            continue
        if not lots_in_location(location):
            continue
        last = (
            f"dernier relevé le {timezone.localtime(location.last_reading):%d/%m/%Y à %H:%M}"
            if location.last_reading
            else "aucun relevé enregistré"
        )
        _, created = raise_alert(
            AlertType.MISSING_READING,
            AlertLevel.WARNING,
            f"Pas de relevé de température depuis plus de {MAX_HOURS_WITHOUT_READING} h "
            f"en {location.code} ({last}), alors que du stock y est présent.",
            location=location,
        )
        created_count += created
    return created_count
