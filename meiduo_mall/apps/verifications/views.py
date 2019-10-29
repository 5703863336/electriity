import json

from django.http import HttpResponse,HttpResponseBadRequest
from django.http import JsonResponse
from django.shortcuts import render
from random import randint

# Create your views here.
from django.views import View

from apps.users.utils import check_access_token_token
from libs.captcha.captcha import captcha
from django_redis import get_redis_connection

from libs.yuntongxun.sms import CCP


class ImageCodeView(View):

    def get(self,request,uuid):

        text,image = captcha.generate_captcha()
        redis_conn = get_redis_connection('code')
        redis_conn.setex('img_%s'%uuid,120,text)

        return HttpResponse(image,content_type='image/jpeg')

class SmsCodeView(View):

    def get(self,request,mobile):

        image_code=request.GET.get('image_code')
        image_code_id=request.GET.get('image_code_id')


        if not all([image_code,image_code_id]):
            return HttpResponseBadRequest('参数不全')

        redis_conn = get_redis_connection('code')
        image_data = redis_conn.get('img_%s'%image_code_id)
        if image_data is None:
            return HttpResponseBadRequest('图片验证码已过期')
        if image_data.decode().lower() != image_code.lower():
            return HttpResponseBadRequest('图片验证码不正确')
        if redis_conn.get('send_flag_%s'%mobile):
            return JsonResponse({'errmsg':'ok','code':'4001','error_sms_code_message':'短信发送太频繁'})


        sms_code = '%06d' % randint(0, 999999)
        redis_conn.setex('sms_%s'%mobile,300,sms_code)
        redis_conn.setex('send_flag_%s'%mobile,60,1)
        from celery_tasks.sms.tasks import send_sms_code
        send_sms_code.delay(mobile, sms_code)

        return JsonResponse({'msg': 'ok', 'code': '0'})
class FindPasswordSms(View):

    def get(self,request):
        data = request.GET
        token = data.get('access_token')
        access_token = check_access_token_token(token)
        mobile = access_token['mobile']

        redis_conn = get_redis_connection('code')
        if redis_conn.get('send_findflag_%s'%mobile):
            return HttpResponseBadRequest('短信发送太频繁')
        sms_find_code = '%06d' % randint(0, 999999)
        redis_conn.setex('find_sms_%s'%mobile,300,sms_find_code)
        redis_conn.setex('send_findflag_%s'%mobile,60,1)
        from celery_tasks.sms.tasks import send_sms_code
        send_sms_code(mobile,sms_find_code)

        return JsonResponse({'msg': 'ok', 'code': '0'})



class CodeView(View):
    def get(self,request,mobile):
        data = request.GET
        sms_code = data.get('sms_code')
        redis_conn = get_redis_connection('code')
        check_code = redis_conn.get('sms_%s'%mobile)
        print(check_code)
        print(type(check_code))
        if check_code:
            return JsonResponse({'smscode':check_code.decode()})

