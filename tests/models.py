from django.db import models


class QueryItem(models.Model):
    title = models.CharField(max_length=100, null=True)
    description = models.TextField(blank=True)
    number = models.IntegerField(default=0)

    class Meta:
        db_table = 'tof_test_item'


class QueryLink(models.Model):
    item = models.ForeignKey(QueryItem, on_delete=models.CASCADE)
    label = models.CharField(max_length=100)

    class Meta:
        db_table = 'tof_test_link'


class QueryItemProxy(QueryItem):
    class Meta:
        proxy = True


class VerificationPair(models.Model):
    first = models.ForeignKey(QueryItem, on_delete=models.CASCADE, related_name='+')
    second = models.ForeignKey(QueryItem, null=True, on_delete=models.CASCADE, related_name='+')

    class Meta:
        db_table = 'tof_verification_pair'
