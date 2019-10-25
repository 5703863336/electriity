from django.shortcuts import render

# Create your views here.
from django.shortcuts import render

# Create your views here.
from django.views import View

from apps.goods.models import SKU, GoodsCategory
from apps.goods.utils import get_breadcrumb

"""
1.功能分析
    用户行为:       用户会点击下一页,会点击排序
    前端行为:       展示相应的数据
    后端行为:       根据用户的点击返回数据

2. 分析后端实现的大体步骤

    ① 先根据分类,把所有数据查询出来
    ② 添加排序
    ③ 添加分页


3.确定请求方式和路由
    GET     /list/?分类id=1
    GET     /list/分类id/  v
"""

class ListView(View):

    def get(self,request,category_id,page):
        try:
            category=GoodsCategory.objects.get(id=category_id)
        except GoodsCategory.DoesNotExist:
            return render(request,'404.html')

        # 面包屑
        # 因为很多地方,都用到了面包屑,将面包屑,抽取出去
        breadcrumb=get_breadcrumb(category)

        # 尽量不要将表的信息,暴露出去
        # 排序字段是使用的查询字符串 ?sort=
        # default:以上架时间
        # hot   :热销 销量
        # price :价格
        sort=request.GET.get('sort')
        if sort == 'default':
            order_field='create_time'
        elif sort == 'hot':
            order_field='sales'
        else:
            order_field='-price'

        # ① 先根据分类,把所有数据查询出来
        data=SKU.objects.filter(category=category).order_by(order_field)
        # data=SKU.objects.filter(category_id=category_id)
        # ② 添加排序
        # ③ 添加分页
        from django.core.paginator import Paginator
        # 3.1创建分页对象
        # per_page : 每页多少条数据
        paginator=Paginator(object_list=data,per_page=5)
        # 3.2获取指定页面的数据
        page_data=paginator.page(page)
        # 3.3获取总页数
        total_page=paginator.num_pages

        context = {

            'breadcrumb': breadcrumb,  # 面包屑导航
            'sort': sort,  # 排序字段
            'category': category,  # 第三级分类
            'page_skus': page_data,  # 分页后数据
            'total_page': total_page,  # 总页数
            'page_num': page,  # 当前页码
        }

        return render(request,'list.html',context=context)
