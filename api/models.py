from django.db import models
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from django.db.models import Sum, F
from django.core.validators import MinValueValidator
from django.contrib.auth.models import AbstractUser, Group, Permission


class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('reception', 'Reception'),
        ('doctor', 'Doctor'),
        ('pharmacist', 'Pharmacist'),
        ('admin', 'Admin'),
    ]
    
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='reception'
    )

    # Optional secondary role
    secondary_role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        null=True,
        blank=True
    )

    # 🛠️ Fix group conflicts by overriding the fields with custom related_name
    groups = models.ManyToManyField(
        Group,
        related_name='custom_user_set',
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups'
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name='custom_user_set',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions'
    )

    def has_role(self, role_name):
        return role_name in [self.role, self.secondary_role]

    def list_roles(self):
        return {
            'role': str(self.role),
            'secondary_role': str(self.secondary_role) if self.secondary_role else None
        }




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
    age = models.IntegerField(validators=[MinValueValidator(0)])
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    area = models.CharField(max_length=255)
    mobile_number = models.CharField(max_length=20)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_waiting = models.BooleanField(default=True)

    def total_medicine_price_per_patient(self):
        """Calculate total medicine price for all given medicines to this patient"""
        return GivedMedicine.objects.filter(
            patient=self
        ).annotate(
            total=F('prescribed_medicine__medicine__price') * F('quantity')
        ).aggregate(
            total_price=Sum('total')
        )['total_price'] or Decimal('0.00')
    
    def save(self, *args, **kwargs):
        is_new = self._state.adding  # Check if this is a new patient
        super().save(*args, **kwargs)
        
        if is_new:
            Record.create_default_record(self)
    
    def __str__(self):
        return self.full_name

    class Meta:
        ordering = ['-created_at']

class Medicine(models.Model):
    name = models.CharField(max_length=255)
    dose = models.CharField(max_length=100)
    scientific_name = models.CharField(max_length=255, blank=True)
    company = models.CharField(max_length=255, blank=True)
    price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    def __str__(self):
        return f"{self.name} ({self.dose})"

    class Meta:
        ordering = ['name']

class Doctor(models.Model):
    user = models.OneToOneField('CustomUser', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    specialization = models.CharField(max_length=255)
    mobile_number = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Dr. {self.name} - {self.specialization}"

    class Meta:
        ordering = ['name']

class Record(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='records')
    doctor = models.ForeignKey(Doctor, on_delete=models.PROTECT, related_name='records')
    vital_signs = models.TextField(blank=True)
    past_illnesses = models.TextField(blank=True)  # New field to replace Past_Illness model
    issued_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_default = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Record for {self.patient.full_name} - {self.issued_date}"

    @classmethod
    def create_default_record(cls, patient):
        """Create a default record for a new patient"""
        from datetime import date
        default_doctor = Doctor.objects.first()
        if default_doctor:
            return cls.objects.create(
                patient=patient,
                doctor=default_doctor,
                issued_date=date.today(),
                is_default=True,
                vital_signs="Initial record",
                past_illnesses=""  # Empty initial past illnesses
            )
        return None
    
    @property
    def total_prescribed_medicines(self):  # Renamed from total_given_medicines
        return self.prescribed_medicines.count()

    def total_medicine_price_per_record(self):
        """Calculate total medicine price for given medicines in this record"""
        return GivedMedicine.objects.filter(
            prescribed_medicine__record=self
        ).annotate(
            total=F('prescribed_medicine__medicine__price') * F('quantity')
        ).aggregate(
            total_price=Sum('total')
        )['total_price'] or Decimal('0.00')

    class Meta:
        ordering = ['-issued_date']

class PrescribedMedicine(models.Model):
    record = models.ForeignKey(Record, on_delete=models.CASCADE, related_name='prescribed_medicines')
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE)
    dosage = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.medicine.name} - {self.dosage}"

    class Meta:
        ordering = ['-id']  # Order by id descending (newest first)
        # Alternative ordering options:
        # ordering = ['medicine__name']  # Order by medicine name
        # ordering = ['-record__issued_date', 'medicine__name']  # Order by record date and medicine name

class GivedMedicine(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='given_medicines')
    prescribed_medicine = models.ForeignKey(PrescribedMedicine, on_delete=models.CASCADE)
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    given_at = models.DateTimeField(auto_now_add=True)

    def total_price(self):
        """Calculate total price for this given medicine"""
        try:
            if not self.prescribed_medicine or not self.prescribed_medicine.medicine:
                return Decimal('0.00')
                
            price = self.prescribed_medicine.medicine.price
            if not isinstance(price, Decimal):
                price = Decimal(str(price))
            
            quantity = Decimal(str(self.quantity))
            
            total = price * quantity
            return total.quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)
        except (TypeError, ValueError, InvalidOperation, AttributeError):
            return Decimal('0.00')
    
    def __str__(self):
        return f"{self.prescribed_medicine.medicine.name} - {self.quantity}"

    @classmethod
    def get_total_price_all_patients(cls):
        """Calculate total medicine price across all patients"""
        try:
            total = cls.objects.annotate(
                total=F('prescribed_medicine__medicine__price') * F('quantity')
            ).aggregate(
                total_price=Sum('total')
            )['total_price'] or Decimal('0.00')
            
            if not isinstance(total, Decimal):
                total = Decimal(str(total))
                
            return total.quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)
        except (TypeError, ValueError, InvalidOperation):
            return Decimal('0.00')

    class Meta:
        ordering = ['-given_at']


