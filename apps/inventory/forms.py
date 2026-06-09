from django import forms


class InventoryForm(forms.Form):
    item_code = forms.ChoiceField(
        label="Producto a calcular",
        choices=[],
        widget=forms.Select(attrs={"onchange": "this.form.submit();"}),
    )
    year = forms.ChoiceField(
        label="Anio de analisis",
        choices=[],
        widget=forms.Select(attrs={"onchange": "this.form.submit();"}),
    )
    order_cost = forms.FloatField(label="Costo por ordenar (Co)", min_value=0.0001, initial=25000)

    holding_mode = forms.ChoiceField(
        label="Modo de costo de mantener",
        choices=[
            ("fixed", "Costo fijo anual por unidad (Ch)"),
            ("percent", "Porcentaje anual sobre costo unitario (I)"),
        ],
        initial="fixed",
    )
    holding_input = forms.FloatField(
        label="Valor de Ch o I",
        min_value=0.0001,
        initial=1200,
        help_text="Si eliges porcentaje, puedes ingresar 0.2 o 20 para 20%.",
    )

    lead_time_days = forms.FloatField(label="Lead time L (dias)", min_value=0.0001, initial=10)
    work_days_year = forms.IntegerField(label="Dias laborales por anio", min_value=1, max_value=366, initial=250)

    include_safety_stock = forms.BooleanField(label="Usar inventario de seguridad (SS)", required=False, initial=False)
    service_level = forms.FloatField(
        label="Nivel de servicio (0-1)",
        min_value=0.5,
        max_value=0.9999,
        initial=0.95,
        required=False,
    )
