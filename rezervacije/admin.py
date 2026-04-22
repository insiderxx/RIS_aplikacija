from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Igrisca, Oprema, Rezervacija


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Vloga', {'fields': ('role', 'telefon')}),
    )
    list_display = ['username', 'email', 'role', 'is_active']
    list_filter = ['role']


@admin.register(Igrisca)
class IgriscaAdmin(admin.ModelAdmin):
    list_display = ['ime', 'povrsina', 'aktivno']
    list_editable = ['aktivno']


@admin.register(Oprema)
class OpremaAdmin(admin.ModelAdmin):
    list_display = ['ime', 'kolicina', 'cena_ura', 'aktivno']
    list_editable = ['aktivno']


@admin.register(Rezervacija)
class RezervacijaAdmin(admin.ModelAdmin):
    list_display = ['igrisca', 'datum', 'ura_zacetek', 'ura_konec', 'uporabnik', 'status']
    list_filter = ['status', 'datum', 'igrisca']
    list_editable = ['status']


from django.contrib import admin

# Register your models here.
