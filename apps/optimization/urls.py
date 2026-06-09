from django.urls import path

from apps.optimization.views import LinearProgrammingDashboardView

app_name = "optimization"

urlpatterns = [
    path("", LinearProgrammingDashboardView.as_view(), name="dashboard"),
]
