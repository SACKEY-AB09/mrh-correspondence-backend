from django.urls import path
from .views import (
    OfficeReportSummaryView, OfficeStaffContributionView,
    OfficeReportBacklogView, OfficeReportTrendsView, ReportsCompareView,
)

urlpatterns = [
    path("reports/offices/<uuid:pk>/summary/", OfficeReportSummaryView.as_view(), name="report-office-summary"),
    path("reports/offices/<uuid:pk>/staff-contribution/", OfficeStaffContributionView.as_view(), name="report-office-staff-contribution"),
    path("reports/offices/<uuid:pk>/backlog/", OfficeReportBacklogView.as_view(), name="report-office-backlog"),
    path("reports/offices/<uuid:pk>/trends/", OfficeReportTrendsView.as_view(), name="report-office-trends"),
    path("reports/compare/", ReportsCompareView.as_view(), name="reports-compare"),
]