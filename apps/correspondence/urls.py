from django.urls import path
from .views import (CorrespondenceListCreateView, CorrespondenceDetailView, 
    ForwardCorrespondenceView, CompleteCorrespondenceView, UpdateStageView,FileCorrespondenceView,
    MovementListView, AttachmentListCreateView,NoteListCreateView, OfficeSummaryDashboardView, AdminSummaryDashboardView,
                    
    )

urlpatterns = [
    path("correspondence/", CorrespondenceListCreateView.as_view(), name="correspondence-list-create"),
    path("correspondence/<uuid:pk>/", CorrespondenceDetailView.as_view(), name="correspondence-detail"),
    path("correspondence/<uuid:pk>/forward/", ForwardCorrespondenceView.as_view(), name="correspondence-forward"),
    path("correspondence/<uuid:pk>/complete/", CompleteCorrespondenceView.as_view(), name="correspondence-complete"),
    path("correspondence/<uuid:pk>/update-stage/", UpdateStageView.as_view(), name="correspondence-update-stage"),
    path("correspondence/<uuid:pk>/file/", FileCorrespondenceView.as_view(), name="correspondence-file"),
    path("correspondence/<uuid:pk>/movements/", MovementListView.as_view(), name="correspondence-movements"),
    path("correspondence/<uuid:pk>/attachments/", AttachmentListCreateView.as_view(), name="correspondence-attachments"),
    path("correspondence/<uuid:pk>/notes/", NoteListCreateView.as_view(), name="correspondence-notes"),
    path("dashboard/office-summary/", OfficeSummaryDashboardView.as_view(), name="dashboard-office-summary"),
    path("dashboard/admin-summary/", AdminSummaryDashboardView.as_view(), name="dashboard-admin-summary"),
    
]