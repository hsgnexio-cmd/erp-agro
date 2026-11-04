"""Crée les 14 allergènes réglementaires (annexe II du règlement UE n° 1169/2011)."""

from django.db import migrations

ALLERGENS = [
    ("gluten", "Céréales contenant du gluten"),
    ("crustaces", "Crustacés"),
    ("oeufs", "Œufs"),
    ("poissons", "Poissons"),
    ("arachides", "Arachides"),
    ("soja", "Soja"),
    ("lait", "Lait"),
    ("fruits-a-coque", "Fruits à coque"),
    ("celeri", "Céleri"),
    ("moutarde", "Moutarde"),
    ("sesame", "Graines de sésame"),
    ("sulfites", "Anhydride sulfureux et sulfites"),
    ("lupin", "Lupin"),
    ("mollusques", "Mollusques"),
]


def create_allergens(apps, schema_editor):
    Allergen = apps.get_model("referentiel", "Allergen")
    for order, (code, name) in enumerate(ALLERGENS, start=1):
        Allergen.objects.update_or_create(code=code, defaults={"name": name, "order": order})


def delete_allergens(apps, schema_editor):
    Allergen = apps.get_model("referentiel", "Allergen")
    Allergen.objects.filter(code__in=[code for code, _ in ALLERGENS]).delete()


class Migration(migrations.Migration):
    dependencies = [("referentiel", "0001_initial")]

    operations = [migrations.RunPython(create_allergens, delete_allergens)]
