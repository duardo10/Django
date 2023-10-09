import os
from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.text import slugify

from django.conf import settings
#from django.contrib.contenttypes.fields import GenericRelation
from tag.models import Tag
from django.db.models import F, Value
from django.db.models.functions import Concat

from PIL import Image

from collections import defaultdict
from django.forms import ValidationError
from django.utils.translation import gettext_lazy as _

# Create your models here.

class Category(models.Model):
    name = models.CharField(max_length=65) # VARCHAR

    def __str__(self) -> str:
        return self.name
    
class RecipeManager(models.Manager):
    def get_published(self):
        return self.filter(
            is_published=True
        ).annotate(
            author_full_name=Concat(
                F('author__first_name'), Value(' '),
                F('author__last_name'), Value(' ('),
                F('author__username'), Value(')'),
            )
        ).order_by('-id')



class Recipe(models.Model):
    title = models.CharField(max_length=65, verbose_name=_('Title')) # VARCHAR
    description = models.CharField(max_length=165) # VARCHAR
    slug = models.SlugField(unique=True) # AUTO INCREMENT
    preparation_time = models.IntegerField() # Numero
    preparation_time_unit = models.CharField(max_length=65) # VARCHAR
    servings = models.IntegerField() # Numero
    servings_unit = models.CharField(max_length=65) # VARCHAR
    preparation_steps = models.TextField()
    preparation_steps_is_html = models.BooleanField(default=False) # campo de escolha
    created_at = models.DateTimeField(auto_now_add=True) # campo de data
    updated_at = models.DateTimeField(auto_now=True)
    is_published = models.BooleanField(default=False) # campo de escolha
    cover = models.ImageField(
        upload_to='recipes/covers/%Y/%m/%d/', blank=True, default=''
    ) #imagem
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True,
        default=None,
    )
    author = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True
    ) 

    #tags = GenericRelation(Tag, related_query_name='recipes')   
    #tags = models.ManyToManyField(Tag)
    tags = models.ManyToManyField(Tag, blank=True, default='')

    def __str__(self) -> str:
        return self.title
    
    def get_absolute_url(self):
        return reverse('recipes:recipe', args=(self.id,))
    
    @staticmethod
    def resize_image(image, new_width=800):
        image_full_path = os.path.join(settings.MEDIA_ROOT, image.name)
        image_pillow = Image.open(image_full_path)
        original_width, original_height = image_pillow.size

        if original_width <= new_width:
            image_pillow.close()
            return

        new_height = round((new_width * original_height) / original_width)

        new_image = image_pillow.resize((new_width, new_height), Image.LANCZOS)
        new_image.save(
            image_full_path,
            optimize=True,
            quality=50,
        )
    
    def save(self, *args, **kwargs):
        if not self.slug:
            slug = f'{slugify(self.title)}'
            self.slug = slug

        saved = super().save(*args, **kwargs)
        
        if self.cover:
            try:
                self.resize_image(self.cover, 840)
            except FileNotFoundError:
                ...

        return saved
    
    def clean(self, *args, **kwargs):
        error_messages = defaultdict(list)

        recipe_from_db = Recipe.objects.filter(
            title__iexact=self.title
        ).first()

        if recipe_from_db:
            if recipe_from_db.pk != self.pk:
                error_messages['title'].append(
                    'Found recipes with the same title'
                )

        if error_messages:
            raise ValidationError(error_messages)
        
class Meta:
    verbose_name = _('Recipe')
    verbose_name_plural = _('Recipes')
    