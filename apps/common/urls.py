from django.urls import path
from .views import RunScheduledTasksView

urlpatterns = [
    path("internal/run-tasks/", RunScheduledTasksView.as_view(), name="run-scheduled-tasks"),
]