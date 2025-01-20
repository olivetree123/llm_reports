from ninja import Router


class MyRouter(Router):

    def get(self, path, handler, /, **kwargs):
        return super().get(path, **kwargs)(handler)

    def post(self, path, handler, /, **kwargs):
        return super().post(path, **kwargs)(handler)

    def put(self, path, handler, /, **kwargs):
        return super().put(path, **kwargs)(handler)

    def delete(self, path, handler, /, **kwargs):
        return super().delete(path, **kwargs)(handler)
