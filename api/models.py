from django.db import models

class Patient(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Not Active'),
    ]
    
    full_name = models.CharField(max_length=255)
    age = models.IntegerField()
    gender = models.CharField(max_length=10)
    area = models.CharField(max_length=255)
    mobile_number = models.CharField(max_length=20)
    past_illnesses = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
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

class Record(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='records')
    doctor_specialization = models.CharField(max_length=255)
    vital_signs = models.TextField(blank=True)
    issued_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Record for {self.patient.full_name} - {self.issued_date}"
    
    @property
    def total_given_medicines(self):
        return self.prescribed_medicines.count()

class PrescribedMedicine(models.Model):
    record = models.ForeignKey(Record, on_delete=models.CASCADE, related_name='prescribed_medicines')
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE)
    dose = models.CharField(max_length=100)
    quantity = models.IntegerField()
    
    def __str__(self):
        return f"{self.medicine.name} - {self.quantity}"
