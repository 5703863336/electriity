from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from meiduo_mall import settings
from itsdangerous import BadSignature,BadTimeSignature,BadData

def serect_openid(openid):
    s = Serializer(secret_key=settings.SECRET_KEY,expires_in=3600)
    data = {
        'openid':openid
    }
    data = s.dumps(data)
    return data.decode()

def check_openid(serect_openid):
    s = Serializer(secret_key=settings.SECRET_KEY, expires_in=3600)

    try:
        data = s.loads(serect_openid)
    except BadData:
        return None
    else:
        return data.get('openid')