import json

from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.http import HttpResponseBadRequest
from django.http import JsonResponse
from django.shortcuts import render, redirect
import re
import logging

from apps.goods.models import SKU

logger = logging.getLogger('django')

# Create your views here.
from django.urls import reverse
from django.views import View
from django_redis import get_redis_connection

from apps.areas.models import Area
from apps.users.models import User, Address
from apps.users.utils import check_active_token, generic_access_token_url
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

        if not re.match(r'[a-zA-Z0-9]{8,20}',password):
            return HttpResponseBadRequest('密码不符合规则')

        if password2 != password:
            return HttpResponseBadRequest('密码不一致')

        if not re.match(r'^1[3-9]\d{9}$',mobile):
            return HttpResponseBadRequest('手机号错误')
        redis_conn  = get_redis_connection('code')
        smskey = 'sms_%s'%mobile
        a = redis_conn.get(smskey)
        print(a)
        print(type(a))
        print(sms_code)
        if redis_conn.get(smskey).decode() != sms_code:
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
        from apps.carts.utils import merge_cookie_to_redis
        response=merge_cookie_to_redis(request,user,response)

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
class EmailActiveView(View):
    def get(self,request):

        token = request.GET.get('token')
        if token is None:
            return HttpResponseBadRequest('缺少参数')
        data = check_active_token(token)
        if data == None:
            return HttpResponseBadRequest('验证失败')
        id = data.get('id')
        email = data.get('email')
        try:
            user = User.objects.get(id=id,email=email)
        except User.DoesNotExist:
            return HttpResponseBadRequest('验证失败')
        user.email_active = True
        user.save()
        return redirect(reverse('users:center'))

class UserCenterSiteView(View):

    def get(self,request):

        user=request.user
        addresses = Address.objects.filter(user=user, is_deleted=False)

        address_dict_list = []
        for address in addresses:
            address_dict = {
                "id": address.id,
                "title": address.title,
                "receiver": address.receiver,
                "province": address.province.name,
                "province_id":address.province_id,
                "city": address.city.name,
                "city_id":address.city_id,
                "district": address.district.name,
                "district_id":address.district_id,
                "place": address.place,
                "mobile": address.mobile,
                "tel": address.tel,
                "email": address.email
            }
            address_dict_list.append(address_dict)


        context = {
            'default_address_id':user.default_address_id,
            'addresses':address_dict_list
        }
        return render(request,'user_center_site.html',context=context)

class CreateView(View):

    def post(self,request):

        count = Address.objects.filter(user=request.user,is_deleted=False).count()
        if count >= 20:
            return JsonResponse({'code': RETCODE.THROTTLINGERR, 'errmsg': '超过地址数量上限'})
        data = json.loads(request.body.decode())
        receiver=data.get('receiver')
        province_id=data.get('province_id')
        city_id=data.get('city_id')
        district_id=data.get('district_id')
        place=data.get('place')
        mobile=data.get('mobile')
        tel=data.get('tel')
        email=data.get('email')

        if not all([receiver,province_id,city_id,district_id,place,mobile]):

            return HttpResponseBadRequest('参数不全')
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return HttpResponseBadRequest('电话号码输入有误')
        if tel:
            if not re.match(r'^(0[0-9]{2,3}-)?([2-9][0-9]{6,7})+(-[0-9]{1,4})?$', tel):
                return HttpResponseBadRequest('参数tel有误')
        if email:
            if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
                return HttpResponseBadRequest('参数email有误')
        try:
            ads = Address.objects.create(user=request.user,
                    title=receiver,
                    receiver=receiver,
                    province_id=province_id,
                    city_id=city_id,
                    district_id=district_id,
                    place=place,
                    mobile=mobile,
                    tel=tel,
                    email=email)
        except Exception as e:
            logger.error(e)
            return HttpResponseBadRequest('保存失败')

        address = {

            "receiver": ads.receiver,
            "province": ads.province.name,
            "city": ads.city.name,
            "district": ads.district.name,
            "place": ads.place,
            "mobile": ads.mobile,
            "tel": ads.tel,
            "email": ads.email,
            "id": ads.id,
            "title": ads.title,
        }

        return JsonResponse({'code': RETCODE.OK, 'errmsg': '新增地址成功', 'address': address})
class DefaultView(View):

    def put(self,request,address_id):

        try:
            default_address = Address.objects.get(id=address_id)
            request.user.default_address = default_address
            request.user.save()
        except Exception as e:
            logger.error(e)
            return HttpResponseBadRequest('出错')
        return JsonResponse({'code':RETCODE.OK,'errmsg': '设置成功'})

class UpdateView(View):

    def put(self,request,address_id):

        data = json.loads(request.body.decode())
        receiver=data.get('receiver')
        province_id=data.get('province_id')
        city_id=data.get('city_id')
        district_id=data.get('district_id')
        place=data.get('place')
        mobile=data.get('mobile')
        tel=data.get('tel')
        email=data.get('email')
        if not all([receiver,province_id,city_id,district_id,place,mobile]):

            return HttpResponseBadRequest('参数不全')
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return HttpResponseBadRequest('电话号码输入有误')
        if tel:
            if not re.match(r'^(0[0-9]{2,3}-)?([2-9][0-9]{6,7})+(-[0-9]{1,4})?$', tel):
                return HttpResponseBadRequest('参数tel有误')
        if email:
            if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
                return HttpResponseBadRequest('参数email有误')

        try:
            update_address = Address.objects.filter(id=address_id)
            update_address.update(
                user=request.user,
                title=receiver,
                receiver=receiver,
                province_id=province_id,
                city_id=city_id,
                district_id=district_id,
                place=place,
                mobile=mobile,
                tel=tel,
                email=email,
            )
        except Exception as e:
            logger.error(e)
            return HttpResponseBadRequest('更新失败')
        update_address = Address.objects.get(id=address_id)
        address_dict = {
            "id": update_address.id,
            "title": update_address.title,
            "receiver": update_address.receiver,
            "province": update_address.province.name,
            "city": update_address.city.name,
            "district": update_address.district.name,
            "place": update_address.place,
            "mobile": update_address.mobile,
            "tel": update_address.tel,
            "email": update_address.email
        }

        return JsonResponse({'code': RETCODE.OK, 'errmsg': '更新地址成功', 'address': address_dict})
    def delete(self,request,address_id):

        try:
            delete_address = Address.objects.filter(id=address_id)
            delete_address.update(is_deleted=True)
        except Exception as e:
            logger.error(e)
            return HttpResponseBadRequest('删除失败')
        return JsonResponse({'code': RETCODE.OK, 'errmsg': '删除地址成功'})

class UpdateTitleView(View):

    def put(self,request,address_id):

        data = json.loads(request.body.decode())
        title = data.get('title')
        try:
            update_title_address = Address.objects.filter(id=address_id)
            update_title_address.update(title=title)
        except Exception as e:
            logger.error(e)
            return HttpResponseBadRequest('修改标题失败')
        return JsonResponse({'code': RETCODE.OK, 'errmsg': '设置地址标题成功'})
class ChangePassword(View):

    def get(self,request):

        return render(request,'user_center_pass.html')

    def post(self, request):
        """实现修改密码逻辑"""
        # 1.接收参数
        old_password = request.POST.get('old_password')
        new_password = request.POST.get('new_password')
        new_password2 = request.POST.get('new_password2')
        # 2.验证参数
        if not all([old_password, new_password, new_password2]):
            return HttpResponseBadRequest('缺少必传参数')
        if not re.match(r'^[0-9A-Za-z]{8,20}$', new_password):
            return HttpResponseBadRequest('密码最少8位，最长20位')
        if new_password != new_password2:
            return HttpResponseBadRequest('两次输入的密码不一致')

        # 3.检验旧密码是否正确
        if not request.user.check_password(old_password):
            return render(request, 'user_center_pass.html', {'origin_password_errmsg': '原始密码错误'})
        # 4.更新新密码
        try:
            request.user.set_password(new_password)
            request.user.save()
        except Exception as e:
            logger.error(e)
            return render(request, 'user_center_pass.html', {'change_password_errmsg': '修改密码失败'})
        # 5.退出登陆,删除登陆信息
        logout(request)
        # 6.跳转到登陆页面
        response = redirect(reverse('users:login'))

        response.delete_cookie('username')

        return response

class UserHistoryView(LoginRequiredMixin,View):

    def post(self,request):
        user = request.user

        data = json.loads(request.body.decode())
        sku_id = data.get('sku_id')
        try:
            sku = SKU.objects.get(id=sku_id)
        except SKU.DoesNotExist:

            return JsonResponse({'code':RETCODE.NODATAERR,'errmsg':'没有此商品'})

        redis_conn = get_redis_connection('history')

        pipeline = redis_conn.pipeline()
        pipeline.lrem('history_%s'%user.id,0,sku_id)
        pipeline.lpush('history_%s' % user.id, sku_id)
        pipeline.ltrim('history_%s'%user.id,0,4)
        pipeline.execute()

        return JsonResponse({'code':RETCODE.OK,'errmsg':'ok'})
    def get(self, request):
        """获取用户浏览记录"""
        # 获取Redis存储的sku_id列表信息
        redis_conn = get_redis_connection('history')
        sku_ids = redis_conn.lrange('history_%s' % request.user.id, 0, -1)

        # 根据sku_ids列表数据，查询出商品sku信息
        skus = []
        for sku_id in sku_ids:
            sku = SKU.objects.get(id=sku_id)
            skus.append({
                'id': sku.id,
                'name': sku.name,
                'default_image_url': sku.default_image.url,
                'price': sku.price
            })

        return JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'skus': skus})
class FindPasswordView(View):

    def get(self,request):

        return render(request,'find_password.html')

class Form_1_On_Submit(View):

    def get(self, request, username, user=None):

        data = request.GET
        text = data.get('text')
        image_code_id = data.get('image_code_id')
        if not all([text]):

            return HttpResponseBadRequest('参数不全')
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return HttpResponseBadRequest('用户不存在')
        redis_conn = get_redis_connection('code')
        check_code = redis_conn.get('img_%s'%image_code_id).decode()

        if check_code.lower() != text.lower():

            return HttpResponseBadRequest('图片验证码错误')
        mobile = user.mobile
        access_token = generic_access_token_url(user.username,user.mobile)

        return JsonResponse({'mobile':mobile,'access_token':access_token})

class Form_2_On_Submit(View):

    def get(self,request,username):

        sms_code = request.GET.get('sms_code')
        try:
            user = User.objects.get(username=username)
            mobile = user.mobile
        except User.DoesNotExist:
            return HttpResponseBadRequest('用户不存在')


        redis_conn = get_redis_connection('code')

        code = redis_conn.get('find_sms_%s'%mobile)
        if int(sms_code) != int(code):

            return HttpResponseBadRequest('验证码错误')
        access_token = generic_access_token_url(user.username, user.mobile)
        return JsonResponse({
            'user_id': user.id,
            'access_token': access_token,
        })
class FindChangePasswordView(View):

    def post(self,request,userid):

        data = json.loads(request.body.decode())
        new_password = data.get('password')
        re_password = data.get('password2')
        access_token = data.get('access_token')
        if new_password != re_password:

            return HttpResponseBadRequest('输入不一致')
        try:
            user = User.objects.get(id=userid)
            user.set_password(new_password)
            user.save()
        except Exception:
            return HttpResponseBadRequest('失败')

        return JsonResponse({'message':'ok'})






















