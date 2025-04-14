from django_filters import rest_framework as filters
from .models import Record

class RecordFilter(filters.FilterSet):
    doctor_specialization = filters.CharFilter(field_name='doctor__specialization')

    class Meta:
        model = Record
        fields = ['patient', 'doctor', 'doctor_specialization']