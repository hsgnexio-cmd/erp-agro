"""Recherche globale de la barre du haut : résultats filtrés selon les droits de lecture."""

from datetime import timedelta

from django.utils import timezone

from production.models import ProductionOrder
from stocks import services as stock_services


def test_la_recherche_trouve_articles_et_enseignes(api_client_for, cream, private_label_customer):
    client = api_client_for("commercial")
    results = client.get("/api/pilotage/search/", {"q": "crème"}).json()["results"]
    assert {"type": "article", "label": cream.code, "detail": cream.name,
            "url": f"/articles/{cream.pk}"} in results  # fmt: skip
    code = private_label_customer.code
    results = client.get("/api/pilotage/search/", {"q": code.lower()}).json()["results"]
    assert [r["label"] for r in results if r["type"] == "client"] == [code]


def test_la_recherche_demande_au_moins_deux_caracteres(api_client_for, cream):
    client = api_client_for("qualite")
    assert client.get("/api/pilotage/search/", {"q": "M"}).json() == {"results": []}
    assert client.get("/api/pilotage/search/").json() == {"results": []}


def test_la_recherche_respecte_les_droits_de_lecture(
    api_client_for, finished_product, factory_site
):
    # Un OF n'est visible que des rôles qui lisent la production : pas du commercial
    from referentiel.models import Location

    output = Location.objects.create(
        site=factory_site, code=f"{factory_site.code}-QUAR", name="Quarantaine",
        temperature_class=finished_product.storage_temperature_class,
    )  # fmt: skip
    order = ProductionOrder.objects.create(
        number="OF-2026-00042", article=finished_product, planned_quantity=100,
        planned_date=timezone.localdate() + timedelta(days=1), site=factory_site,
        output_location=output,
    )  # fmt: skip
    found = api_client_for("production").get("/api/pilotage/search/", {"q": "OF-2026-00042"})
    assert [r["url"] for r in found.json()["results"]] == [f"/production/{order.pk}"]
    hidden = api_client_for("commercial").get("/api/pilotage/search/", {"q": "OF-2026-00042"})
    assert hidden.json() == {"results": []}


def test_la_recherche_exige_d_etre_connecte(client):
    assert client.get("/api/pilotage/search/", {"q": "crème"}).status_code in (401, 403)


def test_la_recherche_trouve_un_lot_par_son_numero(api_client_for, cream, db):
    from referentiel.models import Location, Site, Supplier

    site = Site.objects.create(code="MPE", name="Entrepôt", site_type="entrepot")
    location = Location.objects.create(
        site=site, code="MPE-FP-01", name="Froid", temperature_class=cream.storage_temperature_class
    )
    supplier = Supplier.objects.create(code="FOU-004", name="Crèmerie", lead_time_days=3)
    lot = stock_services.receive_lot(
        article=cream, supplier=supplier, quantity=10, location=location,
        reception_date=timezone.localdate(), expiry_date=timezone.localdate() + timedelta(days=20),
        supplier_lot_number="CR-778", block_reasons=[], user=None, reference="REC-TEST",
    )  # fmt: skip
    results = api_client_for("magasinier").get("/api/pilotage/search/", {"q": "cr-778"}).json()
    assert [r["url"] for r in results["results"] if r["type"] == "lot"] == [f"/lots/{lot.pk}"]
