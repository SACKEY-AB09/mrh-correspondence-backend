from django.shortcuts import render
import os
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from apps.correspondence.tasks import detect_overdue_correspondence, send_deadline_reminders
from apps.reports.tasks import build_daily_report_snapshots

# Create your views here.
class RunScheduledTasksView(APIView):
    permission_classes = [AllowAny]  # protected by a secret header instead, see below

    def post(self, request):
        secret = request.headers.get("X-Task-Secret")
        if secret != os.environ.get("TASK_RUNNER_SECRET"):
            return Response({"detail": "Forbidden."}, status=403)

        results = {
            "overdue": detect_overdue_correspondence(),
            "reminders": send_deadline_reminders(),
            "snapshots": build_daily_report_snapshots(),
        }
        return Response(results)