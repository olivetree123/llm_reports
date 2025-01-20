from django.db import models
from django.utils import timezone
from django.forms.models import model_to_dict


class BaseModel(models.Model):
    id = models.AutoField(primary_key=True)
    created = models.DateTimeField(default=timezone.now)
    updated = models.DateTimeField(default=timezone.now)
    status = models.BooleanField(default=True)

    class Meta:
        abstract = True

    @classmethod
    async def get_by_uid(cls, uid):
        return await cls.objects.filter(uid=uid, status=True).afirst()
