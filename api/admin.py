from django.contrib import admin
from .models import Patient, Medicine, Record, PrescribedMedicine, Doctor, Past_Illness, GivedMedicine

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'age', 'area', 'status', 'is_waiting', 'created_at')
    search_fields = ('full_name', 'area', 'mobile_number')
    list_filter = ('status', 'gender', 'is_waiting')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Past_Illness)
class PastIllnessAdmin(admin.ModelAdmin):
    list_display = ('patient', 'description')
    search_fields = ('patient__full_name', 'description')

@admin.register(Medicine)
class MedicineAdmin(admin.ModelAdmin):
    list_display = ('name', 'dose', 'company', 'price')
    search_fields = ('name', 'scientific_name', 'company')
    list_filter = ('company',)

@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ('name', 'specialization', 'created_at')
    search_fields = ('name', 'specialization')
    list_filter = ('specialization',)
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Record)
class RecordAdmin(admin.ModelAdmin):
    list_display = ('patient', 'doctor', 'issued_date', 'created_at', 'total_given_medicines')
    search_fields = ('patient__full_name', 'doctor__name', 'doctor__specialization')
    list_filter = ('doctor__specialization', 'issued_date')
    readonly_fields = ('created_at',)

@admin.register(PrescribedMedicine)
class PrescribedMedicineAdmin(admin.ModelAdmin):
    list_display = ('record', 'medicine', 'dosage')
    search_fields = ('medicine__name', 'record__patient__full_name')
    list_filter = ('medicine',)

@admin.register(GivedMedicine)
class GivedMedicineAdmin(admin.ModelAdmin):
    list_display = ('patient', 'prescribed_medicine', 'quantity', 'given_at', 'total_price')
    search_fields = ('patient__full_name', 'prescribed_medicine__medicine__name')
    list_filter = ('given_at',)
    readonly_fields = ('given_at',)
