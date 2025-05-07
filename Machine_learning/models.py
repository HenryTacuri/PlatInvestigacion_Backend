from django.db import models

class LDAModel(models.Model):
    busqueda = models.CharField(max_length=255)  
    doc_topic_matrix_json = models.TextField()  
    etiquetas_temas_json = models.TextField()  
    created_at = models.DateTimeField(auto_now_add=True)  

    def __str__(self):
        return f"MachineLearning(busqueda={self.busqueda})"
