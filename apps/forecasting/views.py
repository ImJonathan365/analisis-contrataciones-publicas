from django.views.generic import FormView

from apps.forecasting.forms import ForecastForm
from apps.forecasting.services.forecasting_service import build_forecast_report


class ForecastDashboardView(FormView):
    template_name = "forecasting/dashboard.html"
    form_class = ForecastForm

    def get_initial(self):
        return {
            "moving_window": 3,
            "weighted_weights": "3,2,1",
            "alpha": 0.3,
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = context.get("form")

        window = 3
        weights = [3.0, 2.0, 1.0]
        alpha = 0.3

        if form is not None and form.is_bound and form.is_valid():
            window = form.cleaned_data["moving_window"]
            weights = [float(value) for value in form.cleaned_data["weighted_weights"].split(",")]
            alpha = form.cleaned_data["alpha"]

        report = build_forecast_report(window=window, weights=weights, alpha=alpha)
        table_df = report.detail_table.tail(24).copy()

        context["rows"] = table_df.to_dict("records")
        context["kpis"] = report.kpis
        context["out_of_control"] = report.out_of_control
        context["total_periods"] = len(report.monthly_series)
        return context

    def form_valid(self, form):
        return self.render_to_response(self.get_context_data(form=form))

    def form_invalid(self, form):
        return self.render_to_response(self.get_context_data(form=form))
