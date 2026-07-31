#from django.shortcuts import render

# Create your views here.
from apps.accounts.models import Office
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Correspondence, Attachment, Note, CorrespondenceMovement
from .serializers import (
    CorrespondenceListSerializer, CorrespondenceDetailSerializer,
    CorrespondenceCreateSerializer, CorrespondenceMovementSerializer,
    AttachmentSerializer, NoteSerializer,

)
from . import services

from django.db.models import Count, Avg, F, ExpressionWrapper , DurationField, Q
from django.utils import timezone
from drf_spectacular.utils import extend_schema, OpenApiTypes


class CorrespondenceListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # office-scoped: office users see only their office's records; admins see all
        user = self.request.user
        qs = Correspondence.objects.select_related("current_office", "assigned_to")
        if user.role != user.Role.ADMIN:
            qs = qs.filter(current_office=user.office)
        return qs

    def get_serializer_class(self):
        return CorrespondenceCreateSerializer if self.request.method == "POST" else CorrespondenceListSerializer

    def perform_create(self, serializer):
        office = serializer.validated_data.get("current_office")
        correspondence = services.register_correspondence(
            data=serializer.validated_data,
            office=office,
            actor=self.request.user,
        )
        serializer.instance = correspondence


class CorrespondenceDetailView(generics.RetrieveAPIView):
    queryset = Correspondence.objects.all()
    serializer_class = CorrespondenceDetailSerializer
    permission_classes = [IsAuthenticated]

@extend_schema(request=None, responses=CorrespondenceDetailSerializer)
class ForwardCorrespondenceView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if request.user.role == request.user.Role.ADMIN:
            raise PermissionDenied("Administrators cannot perform correspondence workflow actions.")

        
        correspondence = generics.get_object_or_404(Correspondence, pk=pk)
        to_office_id = request.data.get("to_office")
        try:
            to_office = Office.objects.get(pk=to_office_id)
        except Office.DoesNotExist:
            raise ValidationError({"to_office": "Office not found."})

        note = request.data.get("note", "")
        updated = services.forward_correspondence(
            correspondence=correspondence, to_office=to_office, actor=request.user, note=note
        )
        return Response(CorrespondenceDetailSerializer(updated).data)

@extend_schema(request=None, responses=CorrespondenceDetailSerializer)
class CompleteCorrespondenceView(APIView):
    permission_classes = [IsAuthenticated]
    

    def post(self, request, pk):
        if request.user.role == request.user.Role.ADMIN:
            raise PermissionDenied("Administrators cannot perform correspondence workflow actions.")

        correspondence = generics.get_object_or_404(Correspondence, pk=pk)
        updated = services.complete_correspondence(correspondence=correspondence, actor=request.user)
        return Response(CorrespondenceDetailSerializer(updated).data)
    
@extend_schema(request=None, responses=CorrespondenceDetailSerializer)    
class UpdateStageView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        correspondence = generics.get_object_or_404(Correspondence, pk=pk)
        new_stage = request.data.get("current_stage")
        if not new_stage:
            raise ValidationError({"current_stage": "This field is required."})
        note = request.data.get("note", "")
        updated = services.update_stage(
            correspondence=correspondence, new_stage=new_stage, actor=request.user, note=note
        )
        return Response(CorrespondenceDetailSerializer(updated).data)

@extend_schema(request=None, responses=CorrespondenceDetailSerializer)
class FileCorrespondenceView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        correspondence = generics.get_object_or_404(Correspondence, pk=pk)
        note = request.data.get("note", "")
        updated = services.file_correspondence(correspondence=correspondence, actor=request.user, note=note)
        return Response(CorrespondenceDetailSerializer(updated).data)


class MovementListView(generics.ListAPIView):
    serializer_class = CorrespondenceMovementSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Correspondence.objects.get(pk=self.kwargs["pk"]).movements.all()


class AttachmentListCreateView(generics.ListCreateAPIView):
    serializer_class = AttachmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Attachment.objects.filter(correspondence_id=self.kwargs["pk"])

    def perform_create(self, serializer):
        correspondence = generics.get_object_or_404(Correspondence, pk=self.kwargs["pk"])
        serializer.save(
            correspondence=correspondence,
            uploaded_by=self.request.user,
            original_filename=self.request.data.get("file").name,
        )


class NoteListCreateView(generics.ListCreateAPIView):
    serializer_class = NoteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Note.objects.filter(correspondence_id=self.kwargs["pk"])

    def perform_create(self, serializer):
        correspondence = generics.get_object_or_404(Correspondence, pk=self.kwargs["pk"])
        serializer.save(correspondence=correspondence, author=self.request.user)

@extend_schema(responses=OpenApiTypes.OBJECT)
class OfficeSummaryDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        office = request.user.office
        if not office:
            raise ValidationError({"detail": "You are not assigned to an office."})

        qs = Correspondence.objects.filter(current_office=office)

        data = {
            "office": office.name,
            "active_count": qs.exclude(status=Correspondence.Status.COMPLETED).count(),
            "overdue_count": qs.filter(status=Correspondence.Status.OVERDUE).count(),
            "completed_count": qs.filter(status=Correspondence.Status.COMPLETED).count(),
            "by_status": list(qs.values("status").annotate(count=Count("id"))),
            "by_type": list(qs.values("type").annotate(count=Count("id"))),
            "recent": CorrespondenceListSerializer(qs.order_by("-received_at")[:5], many=True).data,
            "avg_time_in_office_hours": qs.filter(resolved_at__isnull=False).aggregate(
                avg=Avg(ExpressionWrapper(F("resolved_at") - F("received_at"), output_field=DurationField()))
            )["avg"],
        }
        return Response(data)

@extend_schema(responses=OpenApiTypes.OBJECT)
class AdminSummaryDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != request.user.Role.ADMIN:
            return Response({"detail": "Admin access required."}, status=403)

        qs = Correspondence.objects.all()

        data = {
            "active_count": qs.exclude(status=Correspondence.Status.COMPLETED).count(),
            "overdue_count": qs.filter(status=Correspondence.Status.OVERDUE).count(),
            "user_count": request.user.__class__.objects.count(),
            "by_office": list(
                qs.values("current_office__name").annotate(
                    total=Count("id"),
                    active=Count("id", filter=~Q(status=Correspondence.Status.COMPLETED)),
                    overdue=Count("id", filter=Q(status=Correspondence.Status.OVERDUE)),
                )
            ),
            "recent_activity": CorrespondenceMovementSerializer(
                CorrespondenceMovement.objects.select_related("actor", "from_office", "to_office").order_by("-timestamp")[:10],
                many=True,
            ).data,
        }
        return Response(data)