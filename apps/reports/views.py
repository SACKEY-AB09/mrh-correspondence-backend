from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError, PermissionDenied, NotFound
from django.utils import timezone
from datetime import timedelta
from apps.accounts.models import Office
from . import services
from drf_spectacular.utils import extend_schema, OpenApiTypes
from .permissions import resolve_supervisor_office
from .models import FormalReport
from apps.audit.models import AuditLog
from rest_framework import generics
# Create your views here.

def get_date_range(request):
    end = request.query_params.get("end")
    start = request.query_params.get("start")
    end = timezone.datetime.fromisoformat(end) if end else timezone.now()
    start = timezone.datetime.fromisoformat(start) if start else end - timedelta(days=30)
    return start, end


def resolve_office(request, office_id):
    """Supervisors see only their own office. Admins see none — reports are confidential
    staff-performance data, and system administration doesn't grant access to it."""
    office = generics_get_object_or_404(office_id)

    if request.user.role == request.user.Role.ADMIN:
        raise PermissionDenied("Administrators do not have access to confidential office reports.")

    if request.user.role != request.user.Role.SUPERVISOR:
        raise PermissionDenied("Only supervisors can view office reports.")

    if request.user.office_id != office.id:
        raise PermissionDenied("You can only view your own office's reports.")

    return office

def generics_get_object_or_404(office_id):
    try:
        return Office.objects.get(pk=office_id)
    except Office.DoesNotExist:
        raise ValidationError({"office": "Office not found."})

@extend_schema(responses=OpenApiTypes.OBJECT)
class OfficeReportSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        office = resolve_office(request, pk)
        start, end = get_date_range(request)
        return Response(services.office_summary(office, start, end))

@extend_schema(responses=OpenApiTypes.OBJECT)
class OfficeStaffContributionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        office = resolve_office(request, pk)
        start, end = get_date_range(request)
        return Response(services.staff_contribution(office, start, end))

@extend_schema(responses=OpenApiTypes.OBJECT)
class OfficeReportBacklogView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        office = resolve_office(request, pk)
        return Response(services.backlog_aging(office))

@extend_schema(responses=OpenApiTypes.OBJECT)
class OfficeReportTrendsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        office = resolve_office(request, pk)
        return Response(services.type_trend(office))

@extend_schema(responses=OpenApiTypes.OBJECT)
class ReportsCompareView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        raise PermissionDenied(
            "Cross-office report comparison is not currently approved. Contact system management if this is required."
        )

def _get_period_from_request(request):
    return services.resolve_period(
        period_type=request.query_params.get("period_type") or request.data.get("period_type"),
        year=request.query_params.get("year") or request.data.get("year"),
        month=request.query_params.get("month") or request.data.get("month"),
        start_date=request.query_params.get("start_date") or request.data.get("start_date"),
        end_date=request.query_params.get("end_date") or request.data.get("end_date"),
    )


class FormalOfficePerformanceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        office = resolve_supervisor_office(request)
        period = _get_period_from_request(request)
        return Response(services.build_formal_report_data(office, "OFFICE_PERFORMANCE", period))


class FormalOverdueView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        office = resolve_supervisor_office(request)
        period = _get_period_from_request(request)
        return Response(services.build_formal_report_data(office, "OVERDUE", period))


class FormalPendingAgeingView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        office = resolve_supervisor_office(request)
        period = _get_period_from_request(request)
        return Response(services.build_formal_report_data(office, "PENDING_AGEING", period))


class FormalStaffContributionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        office = resolve_supervisor_office(request)
        period = _get_period_from_request(request)
        return Response(services.build_formal_report_data(office, "STAFF_CONTRIBUTION", period))


class GenerateFormalReportView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        office = resolve_supervisor_office(request)
        report_type = request.data.get("report_type")
        period = _get_period_from_request(request)
        observations = request.data.get("observations", "")
        recommendations = request.data.get("recommendations", "")

        report = services.generate_formal_report(
            office=office, report_type=report_type, period=period,
            observations=observations, recommendations=recommendations, generated_by=request.user,
        )

        AuditLog.objects.create(
            action_type=AuditLog.ActionType.REPORT_GENERATED,
            title=f"Formal report generated: {report.report_reference}",
            description=f"{request.user.email} generated a {report.report_type} report for {office.name}.",
            actor=request.user, office=office,
        )
        return Response(report.snapshot, status=201)


class FormalReportHistoryView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        office = resolve_supervisor_office(self.request)
        return FormalReport.objects.filter(office=office)

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        data = [
        {
            "id": str(r.id), "report_reference": r.report_reference, "report_type": r.report_type,
            "period_type": r.period_type, "period_start": r.period_start.isoformat(),
            "period_end": r.period_end.isoformat(), "generated_at": r.generated_at.isoformat(),
            "generated_by": r.generated_by.email if r.generated_by else None,
            "is_latest_version": r.id == qs.filter(
                report_type=r.report_type, period_start=r.period_start, period_end=r.period_end
            ).order_by("-generated_at").first().id,
        }
        for r in qs
    ]
        
        return Response(data)


class FormalReportDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, report_id):
        office = resolve_supervisor_office(request)
        try:
            report = FormalReport.objects.get(pk=report_id, office=office)
        except FormalReport.DoesNotExist:
            raise NotFound("Report not found.")

        AuditLog.objects.create(
            action_type=AuditLog.ActionType.REPORT_VIEWED,
            title=f"Formal report viewed: {report.report_reference}",
            description=f"{request.user.email} viewed report {report.report_reference}.",
            actor=request.user, office=office,
        )
        return Response(report.snapshot)
