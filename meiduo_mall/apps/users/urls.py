from django.conf.urls import url, include
from django.contrib import admin

from django.http.response import HttpResponse

from apps.users import views

urlpatterns = [

    url(r'^register/$',views.RegisterView.as_view(),name='register'),
    url(r'^usernames/(?P<username>[a-zA-Z0-9_-]{5,20})/$',views.isUnique.as_view()),
    url(r'^mobiles/(?P<mobile>1[345789]\d{9})/$',views.MobileUnique.as_view()),
    url(r'^login/$', views.LoginView.as_view(), name='login'),
    url(r'^logout/$',views.LogoutView.as_view(),name='logout'),
    url(r'^center/$',views.UserCenterInfoView.as_view(), name='center'),
    url(r'^emails/$', views.EmailView.as_view(), name='email'),
    url(r'^emailsactive/$', views.EmailActiveView.as_view(), name='emailactive'),
    url(r'^address/$', views.UserCenterSiteView.as_view(), name='address'),
    url(r'^addresses/create/$',views.CreateView.as_view(),name='createaddress'),
    url(r'^addresses/(?P<address_id>\d+)/default/$',views.DefaultView.as_view(),name='defaultaddress'),
    url(r'^addresses/(?P<address_id>\d+)/$',views.UpdateView.as_view(),name='updateaddress'),
    url(r'^addresses/(?P<address_id>\d+)/title/$',views.UpdateTitleView.as_view(),name='updateaddressTitle'),
    url(r'^changepwd/$', views.ChangePassword.as_view(), name='changepwd'),
    url(r'^browse_histories/$', views.UserHistoryView.as_view(), name='history'),
    url(r'^find_password/$', views.FindPasswordView.as_view(), name='findpassword'),
    url(r'^accounts/(?P<username>[a-zA-Z0-9_-]{5,20})/sms/token/$', views.Form_1_On_Submit.as_view(), name='findpassword1'),
    url(r'^accounts/(?P<username>[a-zA-Z0-9_-]{5,20})/password/token/$', views.Form_2_On_Submit.as_view(), name='findpassword2'),
    url(r'users/(?P<userid>\d+)/password/$', views.FindChangePasswordView.as_view(), name='findpassword3'),

]