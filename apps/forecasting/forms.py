from django import forms


class ForecastForm(forms.Form):
    moving_window = forms.IntegerField(
        label="n para Promedio Movil Simple",
        min_value=2,
        max_value=12,
        initial=3,
    )
    weighted_weights = forms.CharField(
        label="Pesos para Promedio Movil Ponderado (ej: 3,2,1)",
        initial="3,2,1",
    )
    alpha = forms.FloatField(
        label="Alpha para Suavizamiento Exponencial Simple",
        min_value=0.0,
        max_value=1.0,
        initial=0.3,
    )

    def clean_weighted_weights(self) -> str:
        raw_value = self.cleaned_data["weighted_weights"]
        chunks = [chunk.strip() for chunk in raw_value.split(",") if chunk.strip()]
        if len(chunks) < 2:
            raise forms.ValidationError("Debes ingresar al menos 2 pesos separados por coma.")
        parsed_weights = []
        for chunk in chunks:
            try:
                weight = float(chunk)
            except ValueError as exc:
                raise forms.ValidationError("Todos los pesos deben ser numericos.") from exc
            if weight <= 0:
                raise forms.ValidationError("Los pesos deben ser positivos.")
            parsed_weights.append(weight)
        if sum(parsed_weights) <= 0:
            raise forms.ValidationError("La suma de pesos debe ser mayor que cero.")
        return ",".join(str(weight) for weight in parsed_weights)
