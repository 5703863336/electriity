from django.http import JsonResponse
from django.core.cache import cache
from django.shortcuts import render
from django.views import View
from apps.areas.models import Area
from utils.response_code import RETCODE
import logging
logger = logging.getLogger('django')

class AreasView(View):

    def get(self,request):

        area_id = request.GET.get('area_id')
        if area_id is None:
            provience_list = cache.get('provience_list')
            if provience_list is None:

                try:
                    areas = Area.objects.filter(parent_id=None)
                except Exception as e:
                    logger.error(e)
                    return JsonResponse({'code': RETCODE.DBERR, 'errmsg': '省份数据错误'})
                provience_list = []

                for area in areas:

                    provience_list.append({
                    'id':area.id,
                    'name':area.name
                    })

                cache.set('provience_list',provience_list,3600)
            return JsonResponse({'code': RETCODE.OK, 'errmsg': "ok", 'provience_list': provience_list})
        else:

            sub_data = cache.get('sub_area_%s'%area_id)
            if sub_data is None:

                try:
                    parent_area = Area.objects.get(id=area_id)
                    children_area = parent_area.area_set.all()
                    area_list = []
                    for area in children_area:
                        area_list.append({
                            'id': area.id,
                            'name': area.name
                        })
                    sub_data = {
                        'id': parent_area.id,
                        'name': parent_area.name,
                        'subs': area_list
                    }
                    cache.set('sub_area_%s' % area_id, sub_data, 3600)
                except Exception as e:

                    logger.error(e)
                    return JsonResponse({'code': RETCODE.DBERR, 'errmsg': '获取数据错误'})
            return JsonResponse({'code':RETCODE.OK,'errmsg':'ok','sub_data':sub_data})



