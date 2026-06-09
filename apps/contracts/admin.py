from django.contrib import admin

from apps.contracts.models import PublicContract


@admin.register(PublicContract)
class PublicContractAdmin(admin.ModelAdmin):
    list_display = ("nro_procedimiento", "institucion", "tipo_procedimiento", "tipo_moneda")
    search_fields = ("nro_procedimiento", "institucion", "descrip_identificacion")
