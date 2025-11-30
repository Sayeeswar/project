from datetime import timedelta

from django.db.models import Sum
from django.db.models.functions import TruncMonth, TruncWeek, TruncYear
from django.shortcuts import render
from django.utils import timezone

from .models import HospitalVisit


def home(request):
    # -----------------------------
    # 1. BASIC GET FILTERS
    # -----------------------------
    mode = request.GET.get("mode", "month")  # week / month / year
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    selected_hospital = request.GET.get("hospital")
    selected_speciality = request.GET.get("speciality")
    selected_category = request.GET.get("category")
    selected_subcatg = request.GET.get("subcatg")
    time_range = request.GET.get("range")

    queryset = HospitalVisit.objects.all()

    # -----------------------------
    # 2. APPLY FILTERS
    # -----------------------------
    if selected_hospital:
        queryset = queryset.filter(hospital=selected_hospital)

    if selected_speciality:
        queryset = queryset.filter(speciality=selected_speciality)

    if selected_category:
        queryset = queryset.filter(category=selected_category)

    if selected_subcatg:
        queryset = queryset.filter(subcatg=selected_subcatg)

    ranges = {
        "4weeks": 28,
        "3months": 90,
        "1year": 365,
        "2years": 730,
    }

    if time_range in ranges:
        calculated_start = timezone.localdate() - timedelta(days=ranges[time_range])
        queryset = queryset.filter(date__gte=calculated_start)
    elif start_date and end_date:
        queryset = queryset.filter(date__range=[start_date, end_date])

    # -----------------------------
    # 3. GROUPING BASED ON MODE
    # -----------------------------
    if mode == "week":
        grouped = (
            queryset.annotate(period=TruncWeek("date"))
            .values("period")
            .annotate(total=Sum("thevalue"))
            .order_by("period")
        )

    elif mode == "year":
        grouped = (
            queryset.annotate(period=TruncYear("date"))
            .values("period")
            .annotate(total=Sum("thevalue"))
            .order_by("period")
        )

    else:  # default -> month
        grouped = (
            queryset.annotate(period=TruncMonth("date"))
            .values("period")
            .annotate(total=Sum("thevalue"))
            .order_by("period")
        )

    # -----------------------------
    # 4. TO FRONTEND
    # -----------------------------
    labels = [g["period"].strftime("%d-%m-%Y") for g in grouped]
    values = [g["total"] for g in grouped]

    context = {
        "labels": labels,
        "values": values,
        "hospital_list": HospitalVisit.objects.values_list("hospital", flat=True).distinct(),
        "speciality_list": HospitalVisit.objects.values_list("speciality", flat=True).distinct(),
        "category_list": HospitalVisit.objects.values_list("category", flat=True).distinct(),
        "subcatg_list": HospitalVisit.objects.values_list("subcatg", flat=True).distinct(),
        "mode": mode,
        "start": start_date,
        "end": end_date,
        "total_new": queryset.filter(subcatg__iexact="NEWVISIT").aggregate(total=Sum("thevalue"))["total"]
        or 0,
        "total_revisit": queryset.filter(subcatg__iexact="REVISIT").aggregate(total=Sum("thevalue"))["total"]
        or 0,
        "total_admissions": queryset.filter(category__iexact="ADMISSIONS").aggregate(total=Sum("thevalue"))["total"]
        or 0,
        "total_discharges": queryset.filter(category__iexact="DISCHARGES").aggregate(total=Sum("thevalue"))["total"]
        or 0,
        "surgeries": queryset.filter(category__iexact="SURGERIES").aggregate(total=Sum("thevalue"))["total"]
        or 0,
        "totals": queryset.aggregate(total=Sum("thevalue"))["total"] or 0,
    }

    return render(request, "home.html", context)
