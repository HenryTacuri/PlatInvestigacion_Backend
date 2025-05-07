from django.db import models

class Preprocesamiento(models.Model):
    titulo = models.CharField(max_length=255)
    tokenized_text = models.TextField()
    busqueda = models.CharField(max_length=255)
    abstract = models.TextField()

    class Meta:
        app_label = 'preprocesamiento'
