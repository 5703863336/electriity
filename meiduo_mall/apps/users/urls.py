from django.conf.urls import url, include
from django.contrib import admin

from django.http.response import HttpResponse

from apps.users import views

urlpatterns = [

    url(r'^register/$',views.RegisterView.as_view())
]