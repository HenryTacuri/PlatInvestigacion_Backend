from django.db import models

class Recoleccion_datos(models.Model):
    titulo = models.TextField()
    autor = models.TextField()
    link = models.TextField()
    ano = models.TextField()
    texto = models.TextField()
    abstract = models.TextField()
    busqueda = models.TextField()
    cita = models.TextField()

    class Meta:
        app_label = 'Recoleccion_datos'  
