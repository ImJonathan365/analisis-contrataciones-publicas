from django.contrib import admin
from django.views.generic import TemplateView
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", TemplateView.as_view(template_name="home.html"), name="home"),
    path("pronosticos/", include("apps.forecasting.urls")),
    path("inventarios/", include("apps.inventory.urls")),
    path("programacion-lineal/", include("apps.optimization.urls")),
]
