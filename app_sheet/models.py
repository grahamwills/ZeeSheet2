from django.db import models

# Create your models here.
class CharacterSheetDefinition(models.Model):
    owner = models.CharField(name='Owner ID', max_length=256, blank=True)
    content = models.TextField(name='Content', verbose_name='Input Content as Markdown')
    created = models.DateField(name='Date Created', auto_now_add=True)
    modified = models.DateField(name='Date Last Modified', auto_now=True)
