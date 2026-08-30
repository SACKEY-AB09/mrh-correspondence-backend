#from django.shortcuts import render
import magic
from django.core.exceptions import ValidationError as DjangoValidationError
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
from .permissions import enforce_office_access

from django.db.models import Count, Avg, F, ExpressionWrapper , DurationField, Q
from django.utils import timezone
from drf_spectacular.utils import extend_schema, OpenApiTypes


class CorrespondenceListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = Correspondence.objects.select_related("current_office", "assigned_to")

        if user.role == user.Role.ADMIN:
            return qs

        office = user.office
        scope = self.request.query_params.get("scope", "current")

        if scope == "current":
            return qs.filter(current_office=office)
        elif scope == "received":
            office_ids = CorrespondenceMovement.objects.filter(
                to_office=office, action_type=CorrespondenceMovement.ActionType.FORWARDED
            ).values_list("correspondence_id", flat=True)
            return qs.filter(id__in=office_ids)
        elif scope == "forwarded":
            office_ids = CorrespondenceMovement.objects.filter(
                from_office=office, action_type=CorrespondenceMovement.ActionType.FORWARDED
            ).values_list("correspondence_id", flat=True)
            return qs.filter(id__in=office_ids)
        elif scope == "handled":
            handled_ids = CorrespondenceMovement.objects.filter(
                Q(from_office=office) | Q(to_office=office)
            ).values_list("correspondence_id", flat=True)
            return qs.filter(Q(current_office=office) | Q(id__in=handled_ids))
        else:
            raise ValidationError({"scope": "Must be one of: current, received, forwarded, handled."})

    def get_serializer_class(self):
        return CorrespondenceCreateSerializer if self.request.method == "POST" else CorrespondenceListSerializer

    def perform_create(self, serializer):
        office = self.request.user.office
        if not office:
            raise ValidationError({
                "detail": "You are not assigned to an office and cannot register correspondence. "
                          "Contact an administrator to be assigned to an office first."
            })
        correspondence = services.register_correspondence(
            data=serializer.validated_data, office=office, actor=self.request.user,
        )
        serializer.instance = correspondence

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        output_serializer = CorrespondenceDetailSerializer(serializer.instance)
        headers = self.get_success_headers(output_serializer.data)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class CorrespondenceDetailView(generics.RetrieveAPIView):
    queryset = Correspondence.objects.all()
    serializer_class = CorrespondenceDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        obj = super().get_object()
        enforce_office_access(self.request.user, obj)
        return obj

@extend_schema(request=None, responses=CorrespondenceDetailSerializer)
class ForwardCorrespondenceView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if request.user.role == request.user.Role.ADMIN:
            raise PermissionDenied("Administrators cannot perform correspondence workflow actions.")

        correspondence = generics.get_object_or_404(Correspondence, pk=pk)
        enforce_office_access(request.user, correspondence)

        to_office_id = request.data.get("to_office")
        try:
            to_office = Office.objects.get(pk=to_office_id)
        except Office.DoesNotExist:
            raise ValidationError({"to_office": "Office not found."})
        note = request.data.get("note", "")
        updated = services.forward_correspondence(correspondence=correspondence, to_office=to_office, actor=request.user, note=note)
        return Response(CorrespondenceDetailSerializer(updated).data)

@extend_schema(request=None, responses=CorrespondenceDetailSerializer)
class CompleteCorrespondenceView(APIView):
    permission_classes = [IsAuthenticated]
    

    def post(self, request, pk):
        if request.user.role == request.user.Role.ADMIN:
            raise PermissionDenied("Administrators cannot perform correspondence workflow actions.")

        correspondence = generics.get_object_or_404(Correspondence, pk=pk)
        enforce_office_access(request.user, correspondence)
        updated = services.complete_correspondence(correspondence=correspondence, actor=request.user)
        return Response(CorrespondenceDetailSerializer(updated).data)
    
@extend_schema(request=None, responses=CorrespondenceDetailSerializer)    
class UpdateStageView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        correspondence = generics.get_object_or_404(Correspondence, pk=pk)
        if request.user.role == request.user.Role.ADMIN:
            raise PermissionDenied("Administrators cannot perform correspondence workflow actions.")
        enforce_office_access(request.user, correspondence)
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
        if request.user.role == request.user.Role.ADMIN:
            raise PermissionDenied("Administrators cannot perform correspondence workflow actions.")

        enforce_office_access(request.user, correspondence)
        note = request.data.get("note", "")
        updated = services.file_correspondence(correspondence=correspondence, actor=request.user, note=note)
        return Response(CorrespondenceDetailSerializer(updated).data)


class MovementListView(generics.ListAPIView):
    serializer_class = CorrespondenceMovementSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        correspondence = generics.get_object_or_404(Correspondence, pk=self.kwargs["pk"])
        enforce_office_access(self.request.user, correspondence)
        return correspondence.movements.all()

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "image/jpeg",
    "image/png",
}

class AttachmentListCreateView(generics.ListCreateAPIView):
    serializer_class = AttachmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        correspondence = generics.get_object_or_404(Correspondence, pk=self.kwargs["pk"])
        enforce_office_access(self.request.user, correspondence)
        return Attachment.objects.filter(correspondence_id=self.kwargs["pk"])

    def perform_create(self, serializer):
        correspondence = generics.get_object_or_404(Correspondence, pk=self.kwargs["pk"])
        enforce_office_access(self.request.user, correspondence)

        # if Attachment.objects.filter(correspondence=correspondence).exists():
        #     raise ValidationError({
        #         "detail": "This correspondence already has an attachment. Additional attachments are not permitted."
        #     })

        uploaded_file = self.request.data.get("file")
        if not uploaded_file:
            raise ValidationError({"file": "No file was submitted."})

        file_head = uploaded_file.read(2048)
        uploaded_file.seek(0)
        detected_type = magic.from_buffer(file_head, mime=True)
        if detected_type not in ALLOWED_MIME_TYPES:
            raise ValidationError({"file": f"Unsupported file type ({detected_type}). Allowed: PDF, DOC, DOCX, JPG, JPEG, PNG."})
        if uploaded_file.size > 10 * 1024 * 1024:
            raise ValidationError({"file": "File too large. Maximum size is 10MB."})

        instance = serializer.save(
            correspondence=correspondence, uploaded_by=self.request.user, original_filename=uploaded_file.name,
        )
        try:
            instance.full_clean()
        except DjangoValidationError as e:
            instance.delete()
            raise ValidationError({"file": e.messages})

        CorrespondenceMovement.objects.create(
            correspondence=correspondence,
            action_type=CorrespondenceMovement.ActionType.ATTACHMENT_UPLOADED,
            actor=self.request.user,
            note=f"Uploaded: {instance.original_filename}",
        )

class NoteListCreateView(generics.ListCreateAPIView):
    serializer_class = NoteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        correspondence = generics.get_object_or_404(Correspondence, pk=self.kwargs["pk"])
        enforce_office_access(self.request.user, correspondence)
        return Note.objects.filter(correspondence_id=self.kwargs["pk"])

    def perform_create(self, serializer):
        correspondence = generics.get_object_or_404(Correspondence, pk=self.kwargs["pk"])
        enforce_office_access(self.request.user, correspondence)
        note = serializer.save(correspondence=correspondence, author=self.request.user)

        CorrespondenceMovement.objects.create(
            correspondence=correspondence,
            action_type=CorrespondenceMovement.ActionType.NOTE_ADDED,
            actor=self.request.user,
            note=note.text[:200],
    )


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
            "avg_time_in_office_hours": services.compute_average_office_duration_hours(qs, office),
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