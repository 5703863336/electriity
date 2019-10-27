import base64
import pickle

from django_redis import get_redis_connection


def merge_cookie_to_redis(request,user,response):

    """
        1.获取cookie数据
        2.把redis数据读取下来
        初始化一个字典
        一个列表用于记录选中的id
        一个列表用于记录未选中的id
        3. 对cookie数据进行遍历
        4.将合并的数据更新到redis中
        5.删除cookie数据
    """
    carts_str = request.COOKIES.get('carts')

    if carts_str is not None:
        carts_dict = pickle.loads(base64.b64decode(carts_str))

    else:
        return response

    redis_conn = get_redis_connection('carts')

    id_count_bytes = redis_conn.hgetall('carts_%s' % user.id)
    selected_ids = redis_conn.smembers('selected_%s' % user.id)

    dict1 = {}

    list1 = []

    list2 = []

    for sku_id,count in id_count_bytes.items():
        dict1[int(sku_id)] = int(count)
    for sku_id,count_selected_dict in carts_dict.items():

        if count_selected_dict['selected'] == True:
            list1.append(sku_id)
        else:
            list2.append(sku_id)
    for sku_id, count_selected_dict in carts_dict.items():

        dict1[sku_id] = count_selected_dict['count']
        if count_selected_dict['selected']:
            list1.append(sku_id)
        else:
            list2.append(sku_id)
    redis_conn.hmset('carts_%s'%user.id,dict1)
    if len(list1)>0:
        redis_conn.sadd('selected_%s'%user.id,*list1)
    else:
        redis_conn.sadd('selected_%s' % user.id, *list2)

    response.delete_cookie('carts')

    return response

