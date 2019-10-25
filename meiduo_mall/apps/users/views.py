import json

from django.contrib.auth import login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseBadRequest
from django.http import JsonResponse
from django.shortcuts import render, redirect
import re

# Create your views here.
from django.urls import reverse
from django.views import View
from django_redis import get_redis_connection

from apps.users.models import User
from utils.response_code import RETCODE


class RegisterView(View):

    def get(self,request):

        return render(request,'register.html')
    def post(self,request):

        data = request.POST
        username = data.get('username')
        password=data.get('password')
        password2=data.get('password2')
        mobile=data.get('mobile')
        sms_code = data.get('sms_code')
        if not all([username,password,password2,mobile]):
            return HttpResponseBadRequest('参数不全')
        if not re.match(r'[a-zA-Z0-9]{5,20}',username):
            return HttpResponseBadRequest('用户名不满足条件')
                #判断用户名是否重复
        # 2.3 密码是否符合规则
        if not re.match(r'[a-zA-Z0-9]{8,20}',password):
            return HttpResponseBadRequest('密码不符合规则')
        # 2.4 确认密码和密码一致
        if password2 != password:
            return HttpResponseBadRequest('密码不一致')
        # 2.5 判断手机号 是否符合规则
        if not re.match(r'^1[3-9]\d{9}$',mobile):
            return HttpResponseBadRequest('手机号错误')
        redis_conn  = get_redis_connection('code')
        if redis_conn.get('mobile') != sms_code:
            return HttpResponseBadRequest('验证码错误')

        # ③ 保存数据

        user = User.objects.create_user(username=username,
                                     password=password,
                                     mobile=mobile)


        login(request, user)
        return redirect(reverse('contents:index'))


class isUnique(View):
    def get(self, request, username):
        count = User.objects.filter(username=username).count()

        return JsonResponse({'count': count,'username':username})

class MobileUnique(View):

    def get(self,request,mobile):
        print(mobile)
        count = User.objects.filter(mobile=mobile).count()
        return JsonResponse({'count':count,'mobile':mobile})

class LoginView(View):

    def get(self,request):

        return render(request,'login.html')

    # 1.相应状态码可以帮助我们分析问题
    # 2.面试会问

    # 405 Method Not Allowed  没有实现对应的请求方法
    def post(self,request):
        # ① 接收数据
        username=request.POST.get('username')
        password=request.POST.get('pwd')
        remembered = request.POST.get('remembered')
        # ② 验证数据 (参数是否齐全,是否符合规则)
        if not all([username,password]):
            return HttpResponseBadRequest('参数不全')
        # 用户名,密码是否符合正则,此处省略
        # ③ 再判断用户名和密码是否匹配一致
        from django.contrib.auth import authenticate
        # 认证成功返回User对象
        # 认证失败返回None
        from django.contrib.auth.backends import ModelBackend
        user = authenticate(username=username,password=password)
        if user is None:
            return HttpResponseBadRequest('用户名或密码错误')
        # ④ 状态保持
        login(request,user)
        # ⑤ 记住登陆
        if remembered == 'on':
            #记住登陆 2周
            request.session.set_expiry(None)
        else:
            #不记住登陆
            request.session.set_expiry(0)

        # ⑥ 返回相应


        response = redirect(reverse('contents:index'))

        #设置cookie
        response.set_cookie('username',user.username,max_age=3600*24*14)

        return response

class LogoutView(View):

    def get(self,request):

        logout(request)

        response = redirect(reverse('contents:index'))

        response.delete_cookie('username')

        return response
class UserCenterInfoView(LoginRequiredMixin,View):

    def get(self,request):
        context = {
            'username':request.user.username,
            'mobile':request.user.mobile,
            'email':request.user.email,
            'email_active':request.user.email_active,
        }

        return render(request,'user_center_info.html',context=context)

class EmailView(View):

    def put(self,request):

        data = json.loads(request.body.decode())
        email = data.get('email')
        if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$',email):
            return JsonResponse({{'code':RETCODE.PARAMERR,'errmsg':'邮箱不符合规则'}})
        request.user.email = email
        request.user.save()
        # from django.core.mail import send_mail
        #
        # #subject, message, from_email, recipient_list,
        # #subject        主题
        # subject='美多商场激活邮件'
        # #message,       内容
        # message=''
        # #from_email,  谁发的
        # from_email = '欢乐玩家<qi_rui_hua@163.com>'
        # #recipient_list,  收件人列表
        # recipient_list = ['chen570386336@163.com']
        #
        # html_mesage="<a href='http://www.huyouni.com'>戳我有惊喜</a>"
        #
        # send_mail(subject=subject,
        #           message=message,
        #           from_email=from_email,
        #           recipient_list=recipient_list,
        #           html_message=html_mesage)
        from celery_tasks.email.tasks import send_active_email
        send_active_email.delay(request.user.id, email)
        print(email)



        # ⑤ 返回相应
        return JsonResponse({'code':RETCODE.OK,'errmsg':'ok'})





