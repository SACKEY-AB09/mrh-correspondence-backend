from django.urls import path
from .views import (
    OfficeReportSummaryView, OfficeReportWorkloadView,
    OfficeReportBacklogView, OfficeReportTrendsView, ReportsCompareView,
)

urlpatterns = [
    path("reports/offices/<uuid:pk>/summary/", OfficeReportSummaryView.as_view(), name="report-office-summary"),
    path("reports/offices/<uuid:pk>/workload/", OfficeReportWorkloadView.as_view(), name="report-office-workload"),
    path("reports/offices/<uuid:pk>/backlog/", OfficeReportBacklogView.as_view(), name="report-office-backlog"),
    path("reports/offices/<uuid:pk>/trends/", OfficeReportTrendsView.as_view(), name="report-office-trends"),
    path("reports/compare/", ReportsCompareView.as_view(), name="reports-compare"),
]