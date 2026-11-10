from django.urls import path

from . import views

app_name = "routing"
urlpatterns = [
    path("health", views.health, name="health"),
    path("geocode", views.geocode, name="geocode"),
    path("plan", views.plan_route, name="plan"),
]
