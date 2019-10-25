from django.http import JsonResponse
from django.shortcuts import render

# Create your views here.
from django.views import View

from apps.users.models import User


class IndexView(View):

    def get(self,request):

        return render(request,'index.html')

