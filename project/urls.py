from django.urls import path

from .views import Surgeries, admissions_overview, dashboard_home, line_graph


urlpatterns = [
    path("", dashboard_home, name="dashboard_home"),
    path("surgeries/", Surgeries, name="surgeries"),
    path("admissions/", admissions_overview, name="admissions_overview"),
    path("line-graph/", line_graph, name="line_graph"),
]
