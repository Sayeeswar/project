import json
from datetime import date

from django.db.models import Q, Sum
from django.db.models.functions import (
    ExtractDay,
    ExtractMonth,
    ExtractWeek,
    ExtractYear,
    TruncMonth,
)
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from .models import HospitalVisit


def filter_by_date_range(qs, request: HttpRequest):
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    if start_date and end_date:
        qs = qs.filter(thedate__range=[start_date, end_date])

    start_month = request.GET.get("start_month")
    end_month = request.GET.get("end_month")
    if start_month and end_month:
        qs = qs.filter(thedate__month__gte=start_month, thedate__month__lte=end_month)

    start_year = request.GET.get("start_year")
    end_year = request.GET.get("end_year")
    if start_year and end_year:
        qs = qs.filter(thedate__year__gte=start_year, thedate__year__lte=end_year)

    return qs


def dashboard_home(request: HttpRequest) -> HttpResponse:
    selected_hospital = request.GET.get("hospital", "ALL")
    selected_speciality = request.GET.get("speciality", "ALL")
    mode = request.GET.get("mode", "month")

    qs = HospitalVisit.objects.all()

    if selected_hospital != "ALL":
        qs = qs.filter(hospital__iexact=selected_hospital)

    qs = filter_by_date_range(qs, request)

    if selected_speciality != "ALL":
        qs = qs.filter(speciality__iexact=selected_speciality)

    if mode == "month":
        grouped = (
            qs.annotate(label=ExtractMonth("thedate"))
            .values("label")
            .annotate(
                admissions=Sum("thevalue", filter=Q(category__iexact="admissions")),
                surgeries=Sum("thevalue", filter=Q(category__iexact="surgeries")),
                new_visits=Sum("thevalue", filter=Q(thecode__iexact="newvisit")),
                re_visits=Sum("thevalue", filter=Q(thecode__iexact="revisit")),
            )
            .order_by("label")
        )
        labels = [f"Month {g['label']}" for g in grouped]
    elif mode == "week":
        grouped = (
            qs.annotate(label=ExtractWeek("thedate"))
            .values("label")
            .annotate(
                admissions=Sum("thevalue", filter=Q(category__iexact="admissions")),
                surgeries=Sum("thevalue", filter=Q(category__iexact="surgeries")),
                new_visits=Sum("thevalue", filter=Q(thecode__iexact="newvisit")),
                re_visits=Sum("thevalue", filter=Q(thecode__iexact="revisit")),
            )
            .order_by("label")
        )
        labels = [f"Week {g['label']}" for g in grouped]
    else:
        grouped = (
            qs.annotate(label=ExtractYear("thedate"))
            .values("label")
            .annotate(
                admissions=Sum("thevalue", filter=Q(category__iexact="admissions")),
                surgeries=Sum("thevalue", filter=Q(category__iexact="surgeries")),
                new_visits=Sum("thevalue", filter=Q(thecode__iexact="newvisit")),
                re_visits=Sum("thevalue", filter=Q(thecode__iexact="revisit")),
            )
            .order_by("label")
        )
        labels = [str(g["label"]) for g in grouped]

    admissions_data = [g["admissions"] or 0 for g in grouped]
    surgeries_data = [g["surgeries"] or 0 for g in grouped]
    new_visits_data = [g["new_visits"] or 0 for g in grouped]
    re_visits_data = [g["re_visits"] or 0 for g in grouped]

    revisit = qs.filter(thecode__iexact="revisit").aggregate(total=Sum("thevalue"))["total"] or 0
    newvisit = qs.filter(thecode__iexact="newvisit").aggregate(total=Sum("thevalue"))["total"] or 0
    admission = qs.filter(category__iexact="admissions").aggregate(total=Sum("thevalue"))["total"] or 0
    surgeries = qs.filter(category__iexact="surgeries").aggregate(total=Sum("thevalue"))["total"] or 0

    years = (
        HospitalVisit.objects.exclude(thedate__isnull=True)
        .annotate(y=ExtractYear("thedate"))
        .values_list("y", flat=True)
        .distinct()
    )
    months = (
        HospitalVisit.objects.exclude(thedate__isnull=True)
        .annotate(m=ExtractMonth("thedate"))
        .values_list("m", flat=True)
        .distinct()
    )
    days = (
        HospitalVisit.objects.exclude(thedate__isnull=True)
        .annotate(d=ExtractDay("thedate"))
        .values_list("d", flat=True)
        .distinct()
    )
    hospitals = HospitalVisit.objects.values_list("hospital", flat=True).distinct()
    specialities = HospitalVisit.objects.values_list("speciality", flat=True).distinct()

    context = {
        "revisit": revisit,
        "newvisit": newvisit,
        "admission": admission,
        "surgeries": surgeries,
        "hospitals": hospitals,
        "specialities": specialities,
        "selected_hospital": selected_hospital,
        "selected_speciality": selected_speciality,
        "years": years,
        "months": months,
        "days": days,
        "mode": mode,
        "labels": labels,
        "admissions_data": admissions_data,
        "surgeries_data": surgeries_data,
        "new_visits_data": new_visits_data,
        "re_visits_data": re_visits_data,
        "start_date": request.GET.get("start_date", ""),
        "end_date": request.GET.get("end_date", ""),
    }

    return render(request, "home.html", context)


def line_graph(request):
    qs = (
        HospitalVisit.objects
        .filter(category__iexact="SURGERIES")
        .annotate(month=TruncMonth("thedate"))
        .values("month")
        .annotate(total=Sum("thevalue"))
        .order_by("month")
    )

    labels = [row["month"].strftime("%b %Y") for row in qs]
    values = [row["total"] for row in qs]

    return render(
        request,
        "line_graph.html",
        {
            "labels": labels,
            "values": values,
        },
    )


def Surgeries(request: HttpRequest) -> HttpResponse:
    """Render surgeries-only dashboard with filters and trend data."""

    selected_hospital = request.GET.get("hospital", "ALL")
    selected_speciality = request.GET.get("speciality", "ALL")
    selected_department = request.GET.get("department", "ALL")
    mode = request.GET.get("mode", "month")

    base_qs = HospitalVisit.objects.filter(category__iexact="surgeries")

    if selected_hospital != "ALL":
        base_qs = base_qs.filter(hospital__iexact=selected_hospital)

    qs = filter_by_date_range(base_qs, request)

    if selected_speciality != "ALL":
        qs = qs.filter(speciality__iexact=selected_speciality)

    if selected_department != "ALL":
        qs = qs.filter(speciality__iexact=selected_department)

    if mode == "week":
        grouped = (
            qs.annotate(label=ExtractWeek("thedate"))
            .values("label")
            .annotate(total=Sum("thevalue"))
            .order_by("label")
        )
        labels = [f"Week {g['label']}" for g in grouped]
    elif mode == "year":
        grouped = (
            qs.annotate(label=ExtractYear("thedate"))
            .values("label")
            .annotate(total=Sum("thevalue"))
            .order_by("label")
        )
        labels = [str(g["label"]) for g in grouped]
    else:
        grouped = (
            qs.annotate(label=ExtractMonth("thedate"))
            .values("label")
            .annotate(total=Sum("thevalue"))
            .order_by("label")
        )
        labels = [f"Month {g['label']}" for g in grouped]

    totals = [g["total"] or 0 for g in grouped]
    surgeries_total = sum(totals)

    hospitals = base_qs.values_list("hospital", flat=True).distinct()
    specialities = base_qs.values_list("speciality", flat=True).distinct()

    if selected_hospital != "ALL":
        department_source = base_qs.filter(hospital__iexact=selected_hospital)
    else:
        department_source = base_qs

    surgeries_department = (
        department_source.exclude(speciality__isnull=True)
        .values_list("speciality", flat=True)
        .distinct()
    )

    subcatg_qs = qs.exclude(subcatg__isnull=True).values("subcatg").annotate(
        total=Sum("thevalue")
    )
    subcatg_labels = [row["subcatg"] for row in subcatg_qs]
    subcatg_values = [row["total"] or 0 for row in subcatg_qs]

    time_series = {}
    for row in (
        qs.annotate(year=ExtractYear("thedate"), month=ExtractMonth("thedate"))
        .values("year", "month")
        .annotate(total=Sum("thevalue"))
        .order_by("year", "month")
    ):
        year = str(row["year"]) if row["year"] is not None else "Unknown"
        month_index = (row["month"] or 1) - 1
        time_series.setdefault(year, [0] * 12)
        if 0 <= month_index < 12:
            time_series[year][month_index] = row["total"] or 0

    stats = {
        "surgeries_count": surgeries_total,
        "success_rate": 100,
        "active_patients": qs.values("rslno").distinct().count(),
        "scheduled_today": qs.filter(thedate=date.today()).count(),
    }

    context = {
        "labels": labels,
        "values": totals,
        "mode": mode,
        "surgeries_total": surgeries_total,
        "hospitals": hospitals,
        "specialities": specialities,
        "selected_hospital": selected_hospital,
        "selected_speciality": selected_speciality,
        "department": selected_department,
        "surgeries_department": surgeries_department,
        "surgeries_subcatg": subcatg_labels,
        "surgeries_subcatg_values": subcatg_values,
        "surgeries_time_series_json": json.dumps(time_series),
        "stats": stats,
        "start_date": request.GET.get("start_date", ""),
        "end_date": request.GET.get("end_date", ""),
    }

    return render(request, "surgeries.html", context)
