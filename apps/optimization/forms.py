from django import forms


class LinearProgrammingForm(forms.Form):
    year = forms.ChoiceField(label="Anio de analisis", choices=[])
    allocation_use_percent = forms.FloatField(
        label="Porcentaje del presupuesto historico a asignar",
        min_value=1,
        max_value=100,
        initial=75,
    )
    pymes_min_percent = forms.FloatField(
        label="Cuota minima PYMES (%)",
        min_value=0,
        max_value=100,
        initial=20,
    )
    institutional_min_percent = forms.FloatField(
        label="Cuota minima instituciones clave (%)",
        min_value=0,
        max_value=100,
        initial=30,
    )
