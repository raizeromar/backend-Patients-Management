from rest_framework import serializers
from .models import Patient, Medicine, Record, PrescribedMedicine, Doctor
from django.contrib.auth.models import User

class MedicineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Medicine
        fields = ['id', 'name', 'dose', 'scientific_name', 'company', 'price']

class PrescribedMedicineSerializer(serializers.ModelSerializer):
    medicine_name = serializers.CharField(source='medicine.name', read_only=True)
    medicine_price = serializers.DecimalField(source='medicine.price', max_digits=10, decimal_places=2, read_only=True)
    total_price = serializers.SerializerMethodField()
    
    class Meta:
        model = PrescribedMedicine
        fields = [
            'id', 
            'medicine', 
            'medicine_name',
            'quantity',
            'medicine_price',
            'total_price'
        ]

    def get_total_price(self, obj):
        return obj.medicine.price * obj.quantity

class PatientPrescribedMedicineSerializer(serializers.ModelSerializer):
    record_id = serializers.IntegerField(source='record.id')
    medicine_name = serializers.CharField(source='medicine.name', read_only=True)
    medicine_price = serializers.DecimalField(source='medicine.price', max_digits=10, decimal_places=2, read_only=True)
    total_price = serializers.SerializerMethodField()
    
    class Meta:
        model = PrescribedMedicine
        fields = [
            'id',
            'record_id',
            'medicine',
            'medicine_name',
            'quantity',
            'medicine_price',
            'total_price'
        ]

    def get_total_price(self, obj):
        return obj.medicine.price * obj.quantity

class DoctorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Doctor
        fields = ['id', 'name', 'specialization', 'created_at', 'updated_at']

class RecordSerializer(serializers.ModelSerializer):
    prescribed_medicines = PrescribedMedicineSerializer(many=True, read_only=True)
    total_medicine_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    doctor_name = serializers.CharField(source='doctor.name', read_only=True)
    doctor_specialization = serializers.CharField(source='doctor.specialization', read_only=True)
    
    class Meta:
        model = Record
        fields = ['id', 'patient', 'doctor', 'doctor_name', 'doctor_specialization',
                 'vital_signs', 'issued_date', 'created_at', 'prescribed_medicines', 
                 'total_medicine_price', 'total_given_medicines']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['total_medicine_price'] = instance.total_medicine_price_per_record()
        return representation

class PatientSerializer(serializers.ModelSerializer):
    records_count = serializers.SerializerMethodField()
    last_visit = serializers.SerializerMethodField()
    
    class Meta:
        model = Patient
        fields = ['id', 'full_name', 'age', 'area', 'records_count', 
                 'last_visit', 'status']
    
    def get_records_count(self, obj):
        return obj.records.count()
    
    def get_last_visit(self, obj):
        last_record = obj.records.order_by('-issued_date').first()
        return last_record.issued_date if last_record else None

class PatientDetailSerializer(serializers.ModelSerializer):
    records_count = serializers.SerializerMethodField()
    last_visit = serializers.SerializerMethodField()
    total_medicine_price = serializers.SerializerMethodField()
    
    class Meta:
        model = Patient
        fields = [
            'id', 
            'full_name', 
            'age', 
            'gender', 
            'area', 
            'mobile_number',
            'past_illnesses',
            'status',
            'created_at',
            'updated_at',
            'records_count',
            'last_visit',
            'total_medicine_price'
        ]
    
    def get_records_count(self, obj):
        return obj.records.count()
    
    def get_last_visit(self, obj):
        last_record = obj.records.order_by('-issued_date').first()
        return last_record.issued_date if last_record else None

    def get_total_medicine_price(self, obj):
        return obj.total_medicine_price_per_patient()

class PatientRecordListSerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(source='doctor.name')
    total_given_medicines = serializers.IntegerField()
    total_medicine_price = serializers.SerializerMethodField()

    class Meta:
        model = Record
        fields = ['id', 'doctor', 'doctor_name', 'issued_date', 
                 'total_given_medicines', 'total_medicine_price']

    def get_total_medicine_price(self, obj):
        return obj.total_medicine_price_per_record()

class PatientRecordDetailSerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(source='doctor.name')
    doctor_specialization = serializers.CharField(source='doctor.specialization')
    prescribed_medicines = PrescribedMedicineSerializer(many=True, read_only=True)
    total_medicine_price = serializers.SerializerMethodField()

    class Meta:
        model = Record
        fields = [
            'id', 
            'doctor',
            'doctor_name',
            'doctor_specialization',
            'vital_signs',
            'issued_date',
            'prescribed_medicines',
            'total_medicine_price'
        ]

    def get_total_medicine_price(self, obj):
        return obj.total_medicine_price_per_record()

class MedicineReportItemSerializer(serializers.Serializer):
    medicine = serializers.CharField()
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    quantity = serializers.IntegerField()
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2)

class MedicineReportSerializer(serializers.Serializer):
    medicines = MedicineReportItemSerializer(many=True)
    total_price_all_patients = serializers.DecimalField(max_digits=10, decimal_places=2)
    date_range = serializers.DictField()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name')
