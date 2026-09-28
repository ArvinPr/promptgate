from django.urls import path

from gateway.views import GenerateView

urlpatterns = [
    path("generate/", GenerateView.as_view(), name="generate"),
]
