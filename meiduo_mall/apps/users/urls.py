from django.conf.urls import url, include
from django.contrib import admin

from django.http.response import HttpResponse

from apps.users import views

urlpatterns = [

    url(r'^register/$',views.RegisterView.as_view()),
    url(r'^usernames/(?P<username>[a-zA-Z0-9_-]{5,20})/$',views.isUnique.as_view()),
    url(r'^mobiles/(?P<mobile>1[345789]\d{9})/$',views.MobileUnique.as_view()),
    url(r'^login/$', views.LoginView.as_view(), name='login'),
]