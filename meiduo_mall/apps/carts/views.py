from django.shortcuts import render

# Create your views here.
import base64
import json
import pickle

from django.http import JsonResponse
from django.shortcuts import render

# Create your views here.
from django.views import View
from django_redis import get_redis_connection

from apps.goods.models import SKU
from utils.response_code import RETCODE


class CartsView(View):

    def post(self,request):
        data = json.loads(request.body.decode())

        sku_id = data.get('sku_id')

        count = data.get('count')

        if not all([sku_id,count]):

            return JsonResponse({'code':RETCODE.PARAMERR,'errmsg':'参数不全'})
        try:

            sku = SKU.objects.get(id=sku_id)
        except SKU.DoesNotExist:

            return  JsonResponse({'code':RETCODE.NODATAERR,'errmsg':'没有此商品'})
        try:
            count = int(count)
        except Exception:
            return JsonResponse({'code':RETCODE.PARAMERR,'errmsg':"参数错误"})
        user = request.user
        if user.is_authenticated:
            redis_conn = get_redis_connection('carts')

            pl =redis_conn.pipeline()
            pl.hincrby('carts_%s'%user.id,sku_id,count)

            pl.sadd('selected_%s' % user.id, sku_id)
            pl.execute()

            return JsonResponse({'code': RETCODE.OK, 'errmsg': 'ok'})
        else:
            carts_str = request.COOKIES.get('carts')

            if carts_str is None:
                cookie_data = {
                    sku_id:{'count':count,'selected':True}
                }
            else:
                decode_data = base64.b64decode(carts_str)
                cookie_data = pickle.loads(decode_data)

                if sku_id in cookie_data:
                    origin_count=cookie_data[sku_id]['count']
                    count += origin_count
                    cookie_data[sku_id] = {'count': count, 'selected': True}
                else:
                    cookie_data[sku_id] = {'count': count, 'selected': True}
        cookie_bytes=pickle.dumps(cookie_data)
        cookie_str=base64.b64encode(cookie_bytes)
        response = JsonResponse({'code':RETCODE.OK,'errmsg':'ok'})
        response.set_cookie('carts',cookie_str,max_age=7*24*3600)

        return response
    def get(self,request):

        user = request.user
        if user.is_authenticated:

            redis_conn = get_redis_connection('carts')
            id_counts = redis_conn.hgetall('carts_%s' % user.id)

            selected_ids = redis_conn.smembers('selected_%s'%user.id)
            cookie_dict = {}
            for sku_id,count in id_counts.items():
                cookie_dict[int(sku_id)] = {
                    'count': int(count),
                    'selected': sku_id in selected_ids
                }
        else:

            cookie_data = request.COOKIES.get('carts')

            if cookie_data is not None:
                cookie_dict = pickle.loads(base64.b64decode(cookie_data))
            else:
                cookie_dict = {}
        carts_list = []
        for id in cookie_dict.keys():

            sku = SKU.objects.get(id=id)
            carts_list.append({
            'id':sku.id,
            'name':sku.name,
            'count': cookie_dict.get(sku.id).get('count'),
            'selected': str(cookie_dict.get(sku.id).get('selected')),  # 将True，转'True'，方便json解析
            'default_image_url':sku.default_image.url,
            'price':str(sku.price), # 从Decimal('10.2')中取出'10.2'，方便json解析
            'amount':str(sku.price * cookie_dict.get(sku.id).get('count')),
            })

        return render(request, 'cart.html', context={'cart_skus': carts_list})
    def put(self,request):

        data = json.loads(request.body.decode())
        sku_id = data.get('sku_id')
        count = data.get('count')
        selected = data.get('selected')

        try:
            sku = SKU.objects.get(id=sku_id)
        except SKU.DoesNotExist:
            return JsonResponse({'code':RETCODE.NODATAERR,'errmsg':'没有此信息'})

        user = request.user
        if user.is_authenticated:
            redis_conn = get_redis_connection('carts')
            redis_conn.hset('carts_%s'%user.id,sku_id,count)
            if selected:
                redis_conn.sadd('selected_%s'%user.id,sku_id)
            else:
                redis_conn.srem('selected_%s'%user.id,sku_id)
            data = {
                'count': count,
                'id': sku_id,
                'selected': selected,
                'name': sku.name,
                'default_image_url': sku.default_image.url,
                'price': sku.price,
                'amount': sku.price * count,
            }
            return JsonResponse({'code': RETCODE.OK, 'errmsg': 'ok', 'cart_sku': data})
        else:
            cookie_str = request.COOKIES.get('carts')
            if cookie_str is not None:
                cookie_dict = pickle.loads(base64.b64decode(cookie_str))
            else:
                cookie_dict = {}
            if sku_id in cookie_dict:
                cookie_dict[sku_id] = {
                    'count':count,
                    'selected':selected
                }
            cookie_data = base64.b64encode(pickle.dumps(cookie_dict))
            data = {
                'count': count,
                'id': sku_id,
                'selected': selected,
                'name': sku.name,
                'default_image_url': sku.default_image.url,
                'price': sku.price,
                'amount': sku.price * count,
            }

            response = JsonResponse({'code': RETCODE.OK, 'errmsg': 'ok', 'cart_sku': data})
            response.set_cookie('carts',cookie_data,max_age=7*24*3600)

            return response
    def delete(self,request):

        data = json.loads(request.body.decode())
        sku_id = data.get('sku_id')
        try:
            sku = SKU.objects.get(id=sku_id)
        except SKU.DoesNotExist:
            return JsonResponse({'code': RETCODE.NODATAERR, 'errmsg': '没有此数据'})
        user = request.user
        if user.is_authenticated:
            redis_conn = get_redis_connection('carts')
            redis_conn.hdel('carts_%s' % user.id, sku_id)
            redis_conn.srem('selected_%s' % user.id, sku_id)
            return JsonResponse({'code': RETCODE.OK, 'errmsg': 'ok'})
        else:
            cookie_str = request.COOKIES.get('carts')
            if cookie_str is not None:
                cookie_dict = pickle.loads(base64.b64decode(cookie_str))
            else:
                cookie_dict = {}
            if sku_id in cookie_dict:
                del cookie_dict[sku_id]
            cookie_data = base64.b64encode(pickle.dumps(cookie_dict))

            response= JsonResponse({'code': RETCODE.OK, 'errmsg': 'ok'})
            response.set_cookie('carts',cookie_data,max_age=7*24*3600)
            return response


