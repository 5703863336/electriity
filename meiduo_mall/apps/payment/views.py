from django.http import JsonResponse
from django.shortcuts import render

# Create your views here.
from django.views import View

from apps.orders.models import OrderInfo
from apps.payment.models import Payment
from utils.response_code import RETCODE

"""
正常流程: 申请成为开发者-->创建应用-->按照文档开发

当前我们的流程:
    申请成为开发者-->沙箱环境中(支付宝为我们提供的测试环境)

沙箱环境:
    为我们提供了: 应用appid
                网关(请求支付宝的 域名)
                回调地址
                测试账号信息

我们要进行沙箱测试的话,必须有以下信息
    1. 沙箱 appid
    2. 沙箱网关
    3. 沙箱应用私钥
    4. 沙箱支付宝公钥
"""



"""
1.功能分析
    用户行为:       用户点击去支付按钮
    前端行为:       前端要收集订单id,将订单id传递给后端
    后端行为:       后端就是实现支付宝的跳转url

2. 分析后端实现的大体步骤

        ①获取订单id
        ②创建alipay实例对象
        ③调用电脑网站支付方法,生成order_string
        ④拼接url
        ⑤返回相应 支付的url


3.确定请求方式和路由
    GET payment/order_id/
"""
from django.contrib.auth.mixins import LoginRequiredMixin
class PaymentView(LoginRequiredMixin,View):

    def get(self,request,order_id):
        # ①获取订单id
        try:
            # 为了让查询更准确
            order=OrderInfo.objects.get(order_id=order_id,
                                        user=request.user,
                                        status=OrderInfo.ORDER_STATUS_ENUM['UNPAID'])
        except OrderInfo.DoesNotExist:
            return JsonResponse({'code':RETCODE.NODATAERR,'errmsg':'没有此订单'})
        # ②创建alipay实例对象
        from alipay import AliPay
        from meiduo_mall import settings
        #读取私钥和公钥
        app_private_key_string = open(settings.APP_PRIVATE_KEY_PATH).read()
        alipay_public_key_string = open(settings.ALIPAY_PUBLIC_KEY_PATH).read()


        alipay = AliPay(
            appid=settings.ALIPAY_APPID,
            app_notify_url=None,  # 默认回调url
            app_private_key_string=app_private_key_string,
            # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            alipay_public_key_string=alipay_public_key_string,
            sign_type="RSA2",  # RSA 或者 RSA2
            debug = settings.ALIPAY_DEBUG  # 默认False
        )
        # ③调用电脑网站支付方法,生成order_string
        subject = "测试订单"

        # 线上 电脑网站支付，需要跳转到https://openapi.alipay.com/gateway.do? + order_string

        order_string = alipay.api_alipay_trade_page_pay(
            out_trade_no=order_id,
            total_amount=str(order.total_amount),  # decimal
            subject=subject,
            return_url=settings.ALIPAY_RETURN_URL,
            #notify_url="https://example.com/notify"  # 可选, 不填则使用默认notify url
        )
        # ④拼接url
        alipay_url=settings.ALIPAY_URL + '?' + order_string
        # ⑤返回相应 支付的url
        return JsonResponse({'code':RETCODE.OK,'errmsg':'ok','alipay_url':alipay_url})


class PaymentStatusView(View):

    def get(self,request):

        from alipay import AliPay
        from meiduo_mall import settings
        # 读取私钥和公钥
        app_private_key_string = open(settings.APP_PRIVATE_KEY_PATH).read()
        alipay_public_key_string = open(settings.ALIPAY_PUBLIC_KEY_PATH).read()

        alipay = AliPay(
            appid=settings.ALIPAY_APPID,
            app_notify_url=None,  # 默认回调url
            app_private_key_string=app_private_key_string,
            # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            alipay_public_key_string=alipay_public_key_string,
            sign_type="RSA2",  # RSA 或者 RSA2
            debug=settings.ALIPAY_DEBUG  # 默认False
        )

        #0.需要先验证交易成功
        # for django users
        data = request.GET.dict()

        signature = data.pop("sign")

        # verification
        success = alipay.verify(data, signature)
        if success:
            # 1.获取 支付宝交易流水号, 获取商家订单id,把这2个信息,保存起来
            trade_no=data.get('trade_no')
            out_trade_no=data.get('out_trade_no')

            Payment.objects.create(
                order_id=out_trade_no,
                trade_id=trade_no
            )

            #修改订单的状态
            OrderInfo.objects.filter(order_id=out_trade_no).update(status=OrderInfo.ORDER_STATUS_ENUM['UNSEND'])



        return render(request,'pay_success.html',context={'trade_no':trade_no})
