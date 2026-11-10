from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class ErpUserAdmin(UserAdmin):
    list_display = ("username", "first_name", "last_name", "job_title", "is_active", "is_staff")
    list_filter = ("groups", "is_active", "is_staff")
    fieldsets = (*UserAdmin.fieldsets, ("Entreprise", {"fields": ("job_title",)}))
    add_fieldsets = (*UserAdmin.add_fieldsets, ("Entreprise", {"fields": ("job_title",)}))
