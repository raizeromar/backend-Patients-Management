from django.contrib import admin
from .models import Patient, Medicine, Record, PrescribedMedicine, Doctor





from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from .models import CustomUser

@admin.register(CustomUser)
class UserAdmin(BaseUserAdmin):
    # Add custom fields to the admin form
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Custom Roles', {
            'fields': ('role', 'secondary_role'),
        }),
    )

    # Also show roles in the user list
    list_display = BaseUserAdmin.list_display + ('role', 'secondary_role')

    # Allow these fields to be edited in the "add user" form
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Custom Roles', {
            'fields': ('role', 'secondary_role'),
        }),
    )




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
    list_display = ('patient', 'get_doctor_specialization', 'issued_date', 'created_at')
    search_fields = ('patient__full_name', 'doctor__specialization')
    list_filter = ('doctor__specialization', 'issued_date')

    def get_doctor_specialization(self, obj):
        return obj.doctor.specialization
    get_doctor_specialization.short_description = 'Doctor Specialization'

@admin.register(PrescribedMedicine)
class PrescribedMedicineAdmin(admin.ModelAdmin):
    list_display = ('record', 'medicine', 'quantity')
    search_fields = ('medicine__name', 'record__patient__full_name')
    list_filter = ('medicine',)

@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ('name', 'specialization', 'created_at')
    search_fields = ('name', 'specialization')
    list_filter = ('specialization',)
