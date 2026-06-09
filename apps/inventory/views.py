from django.contrib import messages
from django.views.generic import FormView

from apps.inventory.forms import InventoryForm
from apps.inventory.services.inventory_service import (
    build_inventory_report,
    get_available_years,
    get_item_available_years,
    get_item_options,
)


class InventoryDashboardView(FormView):
    template_name = "inventory/dashboard.html"
    form_class = InventoryForm

    def _bind_choices(self, form):
        item_options = get_item_options()
        years = get_available_years()

        selected_code = None
        if form.is_bound:
            selected_code = form.data.get("item_code")

        if selected_code:
            item_years = get_item_available_years(selected_code)
        else:
            default_code = item_options[0].code if item_options else None
            item_years = get_item_available_years(default_code) if default_code else years

        print(f"[inventory:view] Binding choices -> items={len(item_options)}, years={years}, item_years={item_years}")

        form.fields["item_code"].choices = [(opt.code, opt.label) for opt in item_options]
        form.fields["year"].choices = [(str(value), str(value)) for value in (item_years or years)]

        return item_options, item_years or years

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        item_options, years = self._bind_choices(form)
        if item_options and not form.is_bound:
            form.initial["item_code"] = item_options[0].code
        if years and not form.is_bound:
            form.initial["year"] = str(years[-1])

        print(
            f"[inventory:view] get_form -> is_bound={form.is_bound}, "
            f"initial_item={form.initial.get('item_code')}, initial_year={form.initial.get('year')}"
        )
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = context.get("form")

        item_options = get_item_options()
        context["item_options"] = item_options

        report = None
        if form is not None and form.is_bound and form.is_valid():
            try:
                print(f"[inventory:view] POST cleaned_data={form.cleaned_data}")
                item_code = form.cleaned_data["item_code"]
                item_label = dict(form.fields["item_code"].choices).get(item_code, item_code)
                item_years = get_item_available_years(item_code)
                selected_year = int(form.cleaned_data["year"])

                if item_years and selected_year not in item_years:
                    selected_year = item_years[-1]
                    messages.info(
                        self.request,
                        f"El anio elegido no estaba disponible para {item_label}. Se ajusto automaticamente a {selected_year}."
                    )
                    print(f"[inventory:view] Selected year not available, auto-adjusted to {selected_year}")

                report = build_inventory_report(
                    item_code=item_code,
                    year=selected_year,
                    order_cost=form.cleaned_data["order_cost"],
                    holding_mode=form.cleaned_data["holding_mode"],
                    holding_input=form.cleaned_data["holding_input"],
                    lead_time_days=form.cleaned_data["lead_time_days"],
                    work_days_year=form.cleaned_data["work_days_year"],
                    include_safety_stock=form.cleaned_data["include_safety_stock"],
                    service_level=form.cleaned_data.get("service_level") or 0.95,
                )
                print("[inventory:view] Report generated and attached to context.")
            except Exception as exc:
                print(f"[inventory:view] Error while building report: {exc}")
                messages.error(self.request, str(exc))
        else:
            # Auto-load dashboard with defaults for better first experience.
            if form is not None:
                try:
                    item_options, years = self._bind_choices(form)
                    if item_options and years:
                        item_option = item_options[0]
                        item_code = item_option.code
                        item_years = get_item_available_years(item_code)
                        default_year = item_years[-1] if item_years else years[-1]
                        print(
                            f"[inventory:view] Auto-load defaults -> item_code={item_code}, year={default_year}, item_years={item_years}"
                        )
                        report = build_inventory_report(
                            item_code=item_code,
                            year=default_year,
                            order_cost=25000,
                            holding_mode="fixed",
                            holding_input=1200,
                            lead_time_days=10,
                            work_days_year=250,
                            include_safety_stock=False,
                            service_level=0.95,
                        )
                        form.initial["item_code"] = item_option.code
                        form.initial["year"] = str(default_year)
                        print("[inventory:view] Auto-load report completed.")
                except Exception as exc:
                    print(f"[inventory:view] Auto-load failed: {exc}")
                    messages.warning(self.request, f"No se pudo precargar el analisis: {exc}")

        context["report"] = report
        return context

    def form_valid(self, form):
        return self.render_to_response(self.get_context_data(form=form))

    def form_invalid(self, form):
        return self.render_to_response(self.get_context_data(form=form))
