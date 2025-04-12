from django.contrib import admin
from .models import Patient, Medicine, Record, PrescribedMedicine

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'age', 'area', 'status', 'created_at')
    search_fields = ('full_name', 'area')
    list_filter = ('status', 'gender')

@admin.register(Medicine)
class MedicineAdmin(admin.ModelAdmin):
    list_display = ('name', 'dose', 'company', 'price')
    search_fields = ('name', 'scientific_name')
    list_filter = ('company',)

@admin.register(Record)
class RecordAdmin(admin.ModelAdmin):
    list_display = ('patient', 'doctor_specialization', 'issued_date', 'created_at')
    search_fields = ('patient__full_name', 'doctor_specialization')
    list_filter = ('doctor_specialization', 'issued_date')

@admin.register(PrescribedMedicine)
class PrescribedMedicineAdmin(admin.ModelAdmin):
    list_display = ('record', 'medicine', 'dose', 'quantity')
    search_fields = ('medicine__name', 'record__patient__full_name')
    list_filter = ('medicine',)
