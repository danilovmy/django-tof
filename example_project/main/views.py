from django.views.generic import TemplateView

from .models import Wine


class Index(TemplateView):
    extra_context = {'wines': Wine.objects.all()}
    template_name = 'main/index.html'
