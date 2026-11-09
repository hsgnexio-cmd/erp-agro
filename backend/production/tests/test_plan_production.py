"""Plan de production hebdomadaire (phase 9b) : calcul, ajustements, gel à J-2, écarts."""

from datetime import datetime, time, timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from previsions.forecast import current_week
from previsions.models import ForecastLine, ForecastVersion
from production import master_plan, orders
from production.models import MasterPlan, OrderStatus, PlanStatus, ProductionOrder
from referentiel.models import Article, BillOfMaterials, BOMLine, CustomerWarehouse
from stocks import services as stock_services
from ventes import orders as sales

D = Decimal


def week(offset: int):
    return current_week() + timedelta(days=7 * offset)


def moment(day, hour=5):
    return timezone.make_aware(datetime.combine(day, time(hour, 0)))


NEXT = week(1)


@pytest.fixture
def mdd_lasagna(recipe, private_label_customer, bechamel):
    article = Article.objects.create(
        name="Lasagnes MDD", article_type="PF", unit="u", recipe=recipe,
        brand_customer=private_label_customer, format_size=300, shelf_life_days=14,
    )  # fmt: skip
    bom = BillOfMaterials.objects.create(article=article)
    BOMLine.objects.create(bom=bom, component=bechamel, quantity=D("0.09"), unit="kg")
    return article


@pytest.fixture
def forecast_version(private_label_customer):
    """Version de prévision figée lundi dernier (couvre S+0 à S+7)."""

    def _make(quantities: dict, first_week=None, created=None):
        first_week = first_week or week(0)
        version = ForecastVersion.objects.create(
            number=f"PRV-T-{ForecastVersion.objects.count() + 1}",
            created_at=created or moment(first_week - timedelta(days=7)),
            source="auto",
            first_week=first_week,
        )
        for (article, monday), quantity in quantities.items():
            ForecastLine.objects.create(
                version=version, customer=private_label_customer, article=article, week=monday,
                base_quantity=D(quantity), quantity=D(quantity),
            )  # fmt: skip
        return version

    return _make


def item_of(plan, article):
    return plan.items.get(article=article)


def quantities(item):
    return [entry.quantity for entry in item.days.order_by("day")]


# --- Calcul -------------------------------------------------------------------------------


def test_marque_brevanne_prevision_plus_stock_de_securite_reparti_sur_5_jours(
    lasagna_line, finished_product, forecast_version
):
    version = forecast_version({(finished_product, NEXT): "7000"})
    plan, skipped = master_plan.compute_plan(NEXT)
    assert skipped == []
    assert plan.status == PlanStatus.DRAFT and plan.forecast_version == version
    item = item_of(plan, finished_product)
    assert item.line == lasagna_line
    # DLC 14 jours : 1 jour de sécurité = 7000 ÷ 7 = 1000
    assert (item.demand, item.safety_days, item.safety_stock) == (D("7000"), D("1"), D("1000"))
    # 8000 → 8004 (667 colis), répartis du lundi au vendredi, le reste sur les premiers jours
    assert item.proposed_quantity == D("8004")
    assert quantities(item) == [D("1608"), D("1608"), D("1596"), D("1596"), D("1596")]
    assert [entry.day.weekday() for entry in item.days.order_by("day")] == [0, 1, 2, 3, 4]


def test_stock_projete_deduit_stock_disponible_et_of_a_venir(
    lasagna_line, finished_product, forecast_version, factory
):
    forecast_version({(finished_product, NEXT): "7000", (finished_product, week(0)): "700"})
    lot = stock_services.receive_lot(
        article=finished_product, supplier=None, quantity=D("3000"),
        location=factory["PFN-QUAR"], reception_date=timezone.localdate(),
        expiry_date=timezone.localdate() + timedelta(days=14), supplier_lot_number="",
        block_reasons=[], user=None, reference="TEST",
    )  # fmt: skip
    assert lot.status == "quarantaine"  # compte dans le stock disponible
    orders.create_order(
        article=finished_product, planned_quantity=D("600"), line=lasagna_line,
        planned_date=min(timezone.localdate() + timedelta(days=1), NEXT - timedelta(days=1)),
    )  # fmt: skip
    plan, _ = master_plan.compute_plan(NEXT)
    item = item_of(plan, finished_product)
    days_before = (NEXT - timezone.localdate()).days
    before = D(100 * days_before)
    assert (item.stock, item.open_orders, item.demand_before) == (D("3000"), D("600"), before)
    assert item.projected_stock == max(D("0"), D("3600") - before)
    expected = master_plan.round_up_to_case(D("8000") - item.projected_stock)
    assert item.proposed_quantity == expected


def test_mdd_sans_stock_de_securite_et_commandes_recues_prioritaires(
    lasagna_line, mdd_lasagna, private_label_customer, forecast_version
):
    forecast_version({(mdd_lasagna, NEXT): "1200"})
    warehouse = CustomerWarehouse.objects.create(
        customer=private_label_customer, code="ENS2-E01", name="Entrepôt", city="Nantes"
    )
    sales.create_order(
        customer=private_label_customer, warehouse=warehouse,
        requested_delivery_date=NEXT + timedelta(days=1),
        lines=[{"article": mdd_lasagna, "quantity": D("1500")}],
    )  # fmt: skip
    plan, _ = master_plan.compute_plan(NEXT)
    item = item_of(plan, mdd_lasagna)
    assert (item.forecast_quantity, item.ordered_quantity, item.demand) == (
        D("1200"), D("1500"), D("1500"),
    )  # fmt: skip
    assert item.safety_stock == D("0")
    assert item.proposed_quantity == D("1500")


def test_jours_de_securite_de_l_article_et_dlc_courte(
    lasagna_line, finished_product, forecast_version
):
    assert master_plan.safety_days(finished_product) == D("1")
    finished_product.shelf_life_days = 8
    assert master_plan.safety_days(finished_product) == D("0.5")
    finished_product.safety_stock_days = D("2")
    finished_product.save()
    forecast_version({(finished_product, NEXT): "700"})
    plan, _ = master_plan.compute_plan(NEXT)
    assert item_of(plan, finished_product).safety_stock == D("200")


def test_produit_sans_ligne_compatible_signale(finished_product, bechamel, forecast_version):
    BOMLine.objects.create(
        bom=BillOfMaterials.objects.create(article=finished_product),
        component=bechamel, quantity=D("0.09"), unit="kg",
    )  # fmt: skip
    forecast_version({(finished_product, NEXT): "700"})
    plan, skipped = master_plan.compute_plan(NEXT)
    assert plan.items.count() == 0
    assert "aucune ligne compatible" in skipped[0]


def test_sans_version_figee_la_prevision_du_moment_est_utilisee(lasagna_line, finished_product):
    plan, _ = master_plan.compute_plan(NEXT)
    assert plan.forecast_version is None
    assert plan.items.count() == 0  # aucune commande passée : rien à prévoir


def test_on_ne_planifie_que_les_semaines_a_venir(db):
    with pytest.raises(ValidationError) as exc:
        master_plan.compute_plan(week(0))
    assert "S+1" in exc.value.messages[0]
    with pytest.raises(ValidationError):
        master_plan.compute_plan(NEXT + timedelta(days=1))


# --- Ajustements -----------------------------------------------------------------------


@pytest.fixture
def draft(lasagna_line, finished_product, forecast_version, factory):
    forecast_version({(finished_product, NEXT): "7000"})
    plan, _ = master_plan.compute_plan(NEXT)
    return plan


def test_ajustement_d_une_quantite_puis_recalcul(draft, finished_product):
    master_plan.set_quantity(draft, article=finished_product, day=NEXT, quantity=D("2400"))
    assert quantities(item_of(draft, finished_product))[0] == D("2400")
    # Recalculer remet le calcul (les ajustements du brouillon sont perdus)
    plan, _ = master_plan.compute_plan(NEXT)
    assert plan.pk == draft.pk
    assert quantities(item_of(plan, finished_product))[0] == D("1608")


def test_pas_de_production_le_week_end_ni_de_quantite_negative(draft, finished_product):
    with pytest.raises(ValidationError) as exc:
        master_plan.set_quantity(
            draft, article=finished_product, day=NEXT + timedelta(days=5), quantity=D("12")
        )
    assert "lundi au vendredi" in exc.value.messages[0]
    with pytest.raises(ValidationError):
        master_plan.set_quantity(draft, article=finished_product, day=NEXT, quantity=D("-1"))


def test_ligne_incompatible_refusee(draft, finished_product, factory_site, family):
    from referentiel.models import ProductionLine

    big = ProductionLine.objects.create(
        code="L3", name="Formats 1 kg", site=factory_site, formats=[1000], capacity_per_hour=900
    )
    big.families.add(family)
    with pytest.raises(ValidationError) as exc:
        master_plan.set_line(draft, article=finished_product, line=big)
    assert "1000 g" in str(exc.value)


def test_ajout_manuel_d_un_produit(draft, mdd_lasagna):
    item = master_plan.add_article(draft, article=mdd_lasagna)
    assert quantities(item) == [D("0")] * 5
    with pytest.raises(ValidationError):
        master_plan.add_article(draft, article=mdd_lasagna)


def test_charge_des_lignes_et_surcharge(draft, finished_product):
    master_plan.set_quantity(draft, article=finished_product, day=NEXT, quantity=D("40800"))
    row = master_plan.line_load(draft)[0]
    # 40 800 ÷ 2 400 / h = 17 h > 15 h disponibles
    assert (row["cells"][0]["hours"], row["cells"][0]["overload"]) == (D("17.0"), True)
    assert row["cells"][1]["overload"] is False


# --- Gel à J-2 ---------------------------------------------------------------------------


def test_le_gel_cree_un_of_par_jour_et_le_plan_ne_se_modifie_plus(
    draft, finished_product, lasagna_line, make_user
):
    master_plan.set_quantity(draft, article=finished_product, day=NEXT + timedelta(4), quantity=0)
    plan = master_plan.freeze_plan(draft, user=make_user("production"))
    assert plan.status == PlanStatus.FROZEN and plan.frozen_by.username == "user-production"
    created = ProductionOrder.objects.filter(article=finished_product).order_by("planned_date")
    assert [o.planned_quantity for o in created] == [D("1608"), D("1608"), D("1596"), D("1596")]
    assert all(o.status == OrderStatus.PLANNED and o.line == lasagna_line for o in created)
    assert "figé" in created[0].comment
    with pytest.raises(ValidationError) as exc:
        master_plan.set_quantity(plan, article=finished_product, day=NEXT, quantity=D("12"))
    assert "figé" in exc.value.messages[0]
    with pytest.raises(ValidationError):
        master_plan.compute_plan(NEXT)
    with pytest.raises(ValidationError):
        master_plan.freeze_plan(plan)


def test_trop_tard_pour_figer_une_semaine_commencee(draft):
    with pytest.raises(ValidationError) as exc:
        master_plan.freeze_plan(draft, at=moment(NEXT, 1))
    assert "trop tard" in exc.value.messages[0]


def test_ecart_entre_le_plan_fige_et_les_of(draft, finished_product):
    plan = master_plan.freeze_plan(draft)
    days = list(item_of(plan, finished_product).days.order_by("day"))
    orders.update_order(days[0].production_order, planned_quantity=D("1200"))
    orders.cancel_order(days[1].production_order)
    days = list(item_of(plan, finished_product).days.order_by("day"))
    assert master_plan.deviation(days[0]) == "quantité 1200"
    assert master_plan.deviation(days[1]) == "OF annulé"
    assert master_plan.deviation(days[2]) == ""


def test_gel_automatique_du_samedi(lasagna_line, finished_product, forecast_version, factory):
    forecast_version({(finished_product, NEXT): "7000"})
    plan = master_plan.freeze_next_week()
    assert plan.week == NEXT and plan.status == PlanStatus.FROZEN
    assert ProductionOrder.objects.filter(article=finished_product).count() == 5
    assert master_plan.freeze_next_week() is None  # déjà figé
    assert MasterPlan.objects.count() == 1


# --- API ---------------------------------------------------------------------------------

URL = "/api/production/master-plans/"


def test_api_la_production_calcule_ajuste_et_fige(
    api_client_for, lasagna_line, finished_product, forecast_version, factory
):
    forecast_version({(finished_product, NEXT): "7000"})
    client = api_client_for("production")
    response = client.post(f"{URL}compute/", {"week": str(NEXT)}, format="json")
    assert response.status_code == 201, response.json()
    data = response.json()
    assert data["status"] == "brouillon" and data["skipped"] == []
    assert data["items"][0]["proposed_quantity"] == "8004.000"
    assert data["load"][0]["line_code"] == "L1"

    plan_id = data["id"]
    response = client.post(
        f"{URL}{plan_id}/set-quantity/",
        {"article": finished_product.pk, "day": str(NEXT), "quantity": "2400"},
        format="json",
    )
    assert response.json()["items"][0]["days"][0]["quantity"] == "2400.000"
    response = client.post(f"{URL}{plan_id}/freeze/", format="json")
    assert response.status_code == 200
    assert response.json()["items"][0]["days"][0]["production_order_number"].startswith("OF-")


def test_api_droits_du_plan(api_client_for, lasagna_line, finished_product, forecast_version):
    forecast_version({(finished_product, NEXT): "7000"})
    response = api_client_for("commercial").post(f"{URL}compute/", {"week": str(NEXT)})
    assert response.status_code == 403
    plan, _ = master_plan.compute_plan(NEXT)
    direction = api_client_for("direction")
    detail = direction.get(f"{URL}{plan.pk}/")
    assert detail.status_code == 200
    assert detail.json()["week_label"].startswith("S")
    assert direction.post(f"{URL}{plan.pk}/freeze/").status_code == 403
