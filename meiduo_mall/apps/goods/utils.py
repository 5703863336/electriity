def get_breadcrumb(category):
    """
    当前我们的分类是三级
    返回一个字典,记录三个级别的分类
    """
    breadcrumb={
        'cat1':'',
        'cat2':'',
        'cat3':''
    }

    # 需要根据当前传递过来的分类进行判断
    if category.parent is None:
        #这个就是一级分类
        breadcrumb['cat1']=category

    elif category.subs.count() == 0:
        #说明它下边每有分类了,是三级

        breadcrumb['cat3']=category
        breadcrumb['cat2']=category.parent
        breadcrumb['cat1']=category.parent.parent
    else:
        #二级
        breadcrumb['cat2']=category
        breadcrumb['cat1']=category.parent


    return breadcrumb