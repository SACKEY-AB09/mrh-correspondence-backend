from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError, PermissionDenied
from django.utils import timezone
from datetime import timedelta
from apps.accounts.models import Office
from . import services
from drf_spectacular.utils import extend_schema, OpenApiTypes
# Create your views here.

def get_date_range(request):
    end = request.query_params.get("end")
    start = request.query_params.get("start")
    end = timezone.datetime.fromisoformat(end) if end else timezone.now()
    start = timezone.datetime.fromisoformat(start) if start else end - timedelta(days=30)
    return start, end


def resolve_office(request, office_id):
    """Office-scoped access: non-admins can only view their own office's reports."""
    office = generics_get_object_or_404(office_id)
    if request.user.role != request.user.Role.ADMIN and request.user.office_id != office.id:
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
class OfficeReportWorkloadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        office = resolve_office(request, pk)
        start, end = get_date_range(request)
        return Response(services.user_workload(office, start, end))

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
        if request.user.role != request.user.Role.ADMIN:
            raise PermissionDenied("Admin access required.")
        start, end = get_date_range(request)
        return Response([
            {"office": o.name, **services.office_summary(o, start, end)}
            for o in Office.objects.all()
        ])