from django.contrib import messages
from django.views.generic import FormView

from apps.optimization.forms import LinearProgrammingForm
from apps.optimization.services.linear_programming_service import (
    build_linear_programming_report,
    get_available_years,
)


class LinearProgrammingDashboardView(FormView):
    template_name = "optimization/dashboard.html"
    form_class = LinearProgrammingForm

    def _bind_year_choices(self, form):
        years = get_available_years()
        print(f"[pl:view] Binding year choices: {years}")
        form.fields["year"].choices = [(str(year), str(year)) for year in years]
        return years

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        years = self._bind_year_choices(form)
        if years and not form.is_bound:
            form.initial["year"] = str(years[-1])
        print(
            f"[pl:view] get_form -> is_bound={form.is_bound}, initial_year={form.initial.get('year')}, "
            f"allocation={form.initial.get('allocation_use_percent')}, pymes={form.initial.get('pymes_min_percent')}, inst={form.initial.get('institutional_min_percent')}"
        )
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = context.get("form")
        report = None

        if form is not None and form.is_bound and form.is_valid():
            try:
                print(f"[pl:view] POST cleaned_data={form.cleaned_data}")
                report = build_linear_programming_report(
                    year=int(form.cleaned_data["year"]),
                    allocation_use_percent=form.cleaned_data["allocation_use_percent"],
                    pymes_min_percent=form.cleaned_data["pymes_min_percent"],
                    institutional_min_percent=form.cleaned_data["institutional_min_percent"],
                )
                print("[pl:view] Report generated and attached to context.")
            except Exception as exc:
                print(f"[pl:view] Error while building PL report: {exc}")
                messages.error(self.request, str(exc))
        else:
            if form is not None:
                try:
                    years = self._bind_year_choices(form)
                    if years:
                        print(f"[pl:view] Auto-load defaults using year={years[-1]}")
                        try:
                            report = build_linear_programming_report(
                                year=years[-1],
                                allocation_use_percent=75,
                                pymes_min_percent=20,
                                institutional_min_percent=30,
                            )
                            print("[pl:view] Auto-load report completed with default constraints.")
                        except Exception as first_exc:
                            print(f"[pl:view] Auto-load default constraints infeasible: {first_exc}")
                            report = build_linear_programming_report(
                                year=years[-1],
                                allocation_use_percent=75,
                                pymes_min_percent=0,
                                institutional_min_percent=30,
                            )
                            messages.info(
                                self.request,
                                "Se ajusto la cuota minima PYMES a 0% para la precarga porque la configuracion 20% no era factible en este anio."
                            )
                            print("[pl:view] Auto-load report completed with fallback PYMES=0%.")
                except Exception as exc:
                    print(f"[pl:view] Auto-load failed: {exc}")
                    messages.warning(self.request, f"No se pudo precargar el analisis: {exc}")

        context["report"] = report
        return context

    def form_valid(self, form):
        return self.render_to_response(self.get_context_data(form=form))

    def form_invalid(self, form):
        return self.render_to_response(self.get_context_data(form=form))
