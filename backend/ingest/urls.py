from django.urls import path

from . import views


urlpatterns = [
    path("", views.overview, name="ingest-overview"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("activities/", views.activities, name="activities"),
    path("activities/<int:activity_id>/", views.activity_detail, name="activity-detail"),
    path("activities/<int:activity_id>/approve/", views.approve_activity, name="activity-approve"),
    path("activities/<int:activity_id>/reject/", views.reject_activity, name="activity-reject"),
    path("activities/<int:activity_id>/lock/", views.lock_activity, name="activity-lock"),
    path("failed-records/", views.failed_records, name="failed-records"),
    path("runs/", views.runs, name="runs"),
]
