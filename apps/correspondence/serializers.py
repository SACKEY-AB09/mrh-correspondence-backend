from rest_framework import serializers
from .models import Correspondence, CorrespondenceMovement, Attachment, Note


class CorrespondenceListSerializer(serializers.ModelSerializer):
    current_office_name = serializers.CharField(source="current_office.name", read_only=True)
    assigned_to_name = serializers.CharField(source="assigned_to.email", read_only=True)

    class Meta:
        model = Correspondence
        fields = [
            "id", "reference_number", "type", "subject", "sender", "priority",
            "direction", "status","current_stage","current_office", "current_office_name",
            "assigned_to", "assigned_to_name", "deadline", "received_at",
        ]


class CorrespondenceDetailSerializer(serializers.ModelSerializer):
    current_office_name = serializers.CharField(source="current_office.name", read_only=True)

    class Meta:
        model = Correspondence
        fields = "__all__"
        read_only_fields = ["reference_number", "status", "current_office", "registered_by", "received_at", "resolved_at"]


class CorrespondenceCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Correspondence
        fields = ["type", "subject", "sender", "priority", "direction","current_stage",
                  "instructions", "document_date", "received_at", "deadline"]
        # reference_number, status, registered_by are set by the service function, not the client


class CorrespondenceMovementSerializer(serializers.ModelSerializer):
    actor_email = serializers.CharField(source="actor.email", read_only=True)
    from_office_name = serializers.CharField(source="from_office.name", read_only=True)
    to_office_name = serializers.CharField(source="to_office.name", read_only=True)

    class Meta:
        model = CorrespondenceMovement
        fields = [
            "id", "action_type", "from_office", "from_office_name", "to_office", "to_office_name",
            "previous_stage", "new_stage", "actor_email", "note", "timestamp",
        ]


class AttachmentSerializer(serializers.ModelSerializer):
    uploaded_by_email = serializers.CharField(source="uploaded_by.email", read_only=True)

    class Meta:
        model = Attachment
        fields = ["id", "file", "original_filename", "uploaded_by_email", "uploaded_at"]
        read_only_fields = ["uploaded_by","original_filename"]


class NoteSerializer(serializers.ModelSerializer):
    author_email = serializers.CharField(source="author.email", read_only=True)

    class Meta:
        model = Note
        fields = ["id", "text", "author_email", "created_at"]