from django.db import models
from decimal import Decimal
from django.db.models import Sum, F

class Patient(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('pending', 'Pending'),
        ('inactive', 'Not Active'),
    ]
    
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
    ]
    
    full_name = models.CharField(max_length=255)
    age = models.IntegerField()
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    area = models.CharField(max_length=255)
    mobile_number = models.CharField(max_length=20)
    past_illnesses = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def total_medicine_price_per_patient(self):
        """Calculate total medicine price for all patient's records"""
        return PrescribedMedicine.objects.filter(
            record__patient=self
        ).annotate(
            total=F('medicine__price') * F('quantity')
        ).aggregate(
            total_price=Sum('total')
        )['total_price'] or Decimal('0.00')
    
    def __str__(self):
        return self.full_name

class Medicine(models.Model):
    name = models.CharField(max_length=255)
    dose = models.CharField(max_length=100)
    scientific_name = models.CharField(max_length=255, blank=True)
    company = models.CharField(max_length=255, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    
    def __str__(self):
        return f"{self.name} ({self.dose})"

class Doctor(models.Model):
    name = models.CharField(max_length=255)
    specialization = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Dr. {self.name} - {self.specialization}"

class Record(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='records')
    doctor = models.ForeignKey(Doctor, on_delete=models.PROTECT, related_name='records')
    vital_signs = models.TextField(blank=True)
    issued_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Record for {self.patient.full_name} - {self.issued_date}"
    
    @property
    def total_given_medicines(self):
        return self.prescribed_medicines.count()

    def total_medicine_price_per_record(self):
        """Calculate total medicine price for this record"""
        return self.prescribed_medicines.annotate(
            total=F('medicine__price') * F('quantity')
        ).aggregate(
            total_price=Sum('total')
        )['total_price'] or Decimal('0.00')


class PrescribedMedicine(models.Model):
    record = models.ForeignKey(Record, on_delete=models.CASCADE, related_name='prescribed_medicines')
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    
    def total_price(self):
        """Calculate total price for this prescribed medicine"""
        return self.medicine.price * self.quantity
    
    def __str__(self):
        return f"{self.medicine.name} - {self.quantity}"

    @classmethod
    def get_total_price_all_patients(cls):
        """Calculate total medicine price across all patients"""
        return cls.objects.annotate(
            total=F('medicine__price') * F('quantity')
        ).aggregate(
            total_price=Sum('total')
        )['total_price'] or Decimal('0.00')
