from django.urls import path

from apps.forecasting.views import ForecastDashboardView

app_name = "forecasting"

urlpatterns = [
    path("", ForecastDashboardView.as_view(), name="dashboard"),
]
