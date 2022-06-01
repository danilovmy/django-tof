from random import randint

from django.core.management.base import BaseCommand
from django.utils.crypto import get_random_string


class Command(BaseCommand):
    help = '''
    create django objects and fill DB
    '''

    def handle(self, *args, **options):
        from products.models import Attribute, Product, ProductAttribute, Value
        from organizations.models import Organization
        organization = Organization.objects.get(id=1)
        attr_int = Attribute(name='int', value_type='int', organization=organization)
        attr_select = Attribute(name='select', value_type='fk', organization=organization)
        attr_select.save()
        attr_int.save()
        for i in range(5):
            producer = Value(title=f'producer_{i}', attribute=attr_select, organization=organization)
            producer.save()
        for i in range(200):
            product = Product(name=f'product{i}', organization=organization, price=float(randint(0, 100)), quantity=randint(0, 20))
            product.save()
            for value in (Value(value_int=randint(0, 5), organization=organization, attribute=attr_int), Value.objects.filter(attribute=attr_select).order_by('?')[0]):
                value.save()
                ProductAttribute(product=product, value=value).save()
