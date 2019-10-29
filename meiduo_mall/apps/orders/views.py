import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import render

# Create your views here.
from django.views import View
from django_redis import get_redis_connection

from apps.goods.models import SKU
from apps.orders.models import OrderInfo, OrderGoods
from apps.users.models import Address
from utils.response_code import RETCODE


class PlaceOrderView(LoginRequiredMixin,View):

    def get(self,request):
        user = request.user
        addresses=Address.objects.filter(user=user,is_deleted=False)
        redis_conn = get_redis_connection('carts')
        id_counts=redis_conn.hgetall('carts_%s'%user.id)
        selected_ids=redis_conn.smembers('selected_%s'%user.id)

        selected_dict={}

        for id in selected_ids:
            selected_dict[int(id)] = int(id_counts[id])
        ids=selected_dict.keys()

        skus = []
        total_count=0
        total_amount=0
        for id in ids:
            sku=SKU.objects.get(id=id)
            sku.count=selected_dict[id]
            sku.amount=(sku.price*sku.count)
            skus.append(sku)

            total_count += sku.count
            total_amount += sku.amount

        freight=10

        context = {
            'addresses':addresses,
            'skus':skus,
            # 以下的几个 复制过来
            'total_count': total_count,
            'total_amount': total_amount,
            'freight': freight,
            'payment_amount':total_amount + freight
        }

        return render(request, 'place_order.html', context=context)
class OrderCommitView(LoginRequiredMixin, View):

    def post(self,request):

        data = json.loads(request.body.decode())
        address_id=data.get('address_id')
        pay_method=data.get('pay_method')

        if not all([address_id,pay_method]):
            return JsonResponse({'code':RETCODE.PARAMERR,'errmsg':'参数不全'})
        user = request.user
        try:
            address=Address.objects.get(id=address_id,user=user)

        except Address.DoesNotExist:
            return JsonResponse({'code': RETCODE.PARAMERR, 'errmsg': '地址不正确'})

        from django.utils import timezone
        order_id = timezone.localtime().strftime('%Y%m%d%H%M%S')+'%09d'%user.id
        total_count=0
        from decimal import Decimal
        total_amount=Decimal('0')
        freight=Decimal('10')
        if pay_method not in [OrderInfo.PAY_METHODS_ENUM['CASH'], OrderInfo.PAY_METHODS_ENUM['ALIPAY']]:
            return JsonResponse({'code': RETCODE.PARAMERR, 'errmsg': '支付方式错误'})
        if pay_method == OrderInfo.PAY_METHODS_ENUM['CASH']:
            # 现金支付
            status=OrderInfo.ORDER_STATUS_ENUM['UNSEND']
        else:
            #支付宝
            status=OrderInfo.ORDER_STATUS_ENUM['UNPAID']
        from django.db import transaction

        with transaction.atomic():

            savepoint = transaction.savepoint()
            try:
                order_info=OrderInfo.objects.create(
                    order_id=order_id,
                    user=user,
                    address=address,
                    total_count=total_count,
                    total_amount=total_amount,
                    freight=freight,
                    pay_method=pay_method,
                    status=status
                )

                redis_conn = get_redis_connection('carts')
                id_counts=redis_conn.hgetall('carts_%s'%user.id)
                selected_ids=redis_conn.smembers('selected_%s'%user.id)

                selected_dict = {}
                for id in selected_ids:

                    selected_dict[int(id)] = int(id_counts[id])

                for sku_id,count in selected_dict.items():
                    while True:
                        sku = SKU.objects.get(id=sku_id)

                        if sku.stock < count:
                            transaction.savepoint_rollback(savepoint)

                            return JsonResponse({'code': RETCODE.STOCKERR, 'errmsg': '库存不足'})
                        old_stock = sku.stock

                        new_stock=sku.stock-count
                        new_sales=sku.sales+count

                        rect = SKU.objects.filter(id=sku_id,stock=old_stock).update(stock=new_stock,sales=new_sales)
                        if rect == 0:
                            continue

                        OrderGoods.objects.create(
                            order=order_info,
                            sku=sku,
                            count=count,
                            price=sku.price
                        )
                        order_info.total_count+=count
                        order_info.total_amount+=(count*sku.price)

                        break
                order_info.save()

            except Exception as e:

                transaction.savepoint_rollback(savepoint)
            else:
                transaction.savepoint_commit(savepoint)



        return JsonResponse({'code':RETCODE.OK,'errmsg':'ok',
                             'order_id':order_info.order_id,
                             'payment_amount':order_info.total_amount,
                             'pay_method':order_info.pay_method})

class OrderSuccessView(View):

    def get(self,request):

        order_id=request.GET.get('order_id')
        pay_method=request.GET.get('pay_method')
        payment_amount=request.GET.get('payment_amount')

        context = {
            'order_id': order_id,
            'payment_amount': payment_amount,
            'pay_method': pay_method
        }

        return render(request,'order_success.html',context=context)




