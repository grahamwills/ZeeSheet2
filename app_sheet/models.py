from django.db import models
from django.contrib.auth.models import User

class Sheet(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    system = models.CharField(verbose_name='RPG System', default='other', max_length=64)
    name = models.CharField(verbose_name='Character Name', max_length=64)
    created = models.DateField(verbose_name='Date Created', auto_now_add=True)
    modified = models.DateField(verbose_name='Date Last Modified', auto_now=True)
    content = models.TextField(verbose_name='Definition Under Edit')
    is_shared= models.BooleanField(default=False, verbose_name='Share this sheet?')
    is_template = models.BooleanField(default=False, verbose_name='Is this a template?')

    def __str__(self):
        return self.system + ' • ' + self.owner.username + ' • ' + self.name
