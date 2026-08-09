from django.urls import path
from .views import (
    OfficeReportSummaryView, OfficeStaffContributionView,
    OfficeReportBacklogView, OfficeReportTrendsView, ReportsCompareView,
    FormalOfficePerformanceView, FormalOverdueView, FormalPendingAgeingView, FormalStaffContributionView,
    GenerateFormalReportView, FormalReportHistoryView, FormalReportDetailView,
)

urlpatterns = [
    path("reports/offices/<uuid:pk>/summary/", OfficeReportSummaryView.as_view(), name="report-office-summary"),
    path("reports/offices/<uuid:pk>/staff-contribution/", OfficeStaffContributionView.as_view(), name="report-office-staff-contribution"),
    path("reports/offices/<uuid:pk>/backlog/", OfficeReportBacklogView.as_view(), name="report-office-backlog"),
    path("reports/offices/<uuid:pk>/trends/", OfficeReportTrendsView.as_view(), name="report-office-trends"),
    path("reports/compare/", ReportsCompareView.as_view(), name="reports-compare"),
    path("reports/formal/office-performance/", FormalOfficePerformanceView.as_view(), name="formal-office-performance"),
    path("reports/formal/overdue/", FormalOverdueView.as_view(), name="formal-overdue"),
    path("reports/formal/pending-ageing/", FormalPendingAgeingView.as_view(), name="formal-pending-ageing"),
    path("reports/formal/staff-contribution/", FormalStaffContributionView.as_view(), name="formal-staff-contribution"),
    path("reports/formal/generate/", GenerateFormalReportView.as_view(), name="formal-generate"),
    path("reports/formal/history/", FormalReportHistoryView.as_view(), name="formal-history"),
    path("reports/formal/<uuid:report_id>/", FormalReportDetailView.as_view(), name="formal-detail"),
]