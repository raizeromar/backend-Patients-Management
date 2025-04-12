from rest_framework import serializers
from .models import Patient, Medicine, Record, PrescribedMedicine

class MedicineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Medicine
        fields = ['id', 'name', 'dose', 'scientific_name', 'company', 'price']

class PrescribedMedicineSerializer(serializers.ModelSerializer):
    medicine_name = serializers.CharField(source='medicine.name', read_only=True)
    medicine_price = serializers.DecimalField(source='medicine.price', max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = PrescribedMedicine
        fields = ['id', 'medicine', 'medicine_name', 'dose', 'quantity', 'medicine_price']

class RecordSerializer(serializers.ModelSerializer):
    prescribed_medicines = PrescribedMedicineSerializer(many=True, read_only=True)
    total_given_medicines = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Record
        fields = ['id', 'patient', 'doctor_specialization', 'vital_signs', 
                  'issued_date', 'created_at', 'prescribed_medicines', 
                  'total_given_medicines']

class PatientSerializer(serializers.ModelSerializer):
    records_count = serializers.SerializerMethodField()
    last_visit = serializers.SerializerMethodField()
    
    class Meta:
        model = Patient
        fields = ['id', 'full_name', 'age', 'gender', 'area', 'mobile_number', 
                  'past_illnesses', 'status', 'created_at', 'updated_at', 
                  'records_count', 'last_visit']
    
    def get_records_count(self, obj):
        return obj.records.count()
    
    def get_last_visit(self, obj):
        last_record = obj.records.order_by('-issued_date').first()
        return last_record.issued_date if last_record else None

class PatientDetailSerializer(PatientSerializer):
    records = RecordSerializer(many=True, read_only=True)
    
    class Meta(PatientSerializer.Meta):
        fields = PatientSerializer.Meta.fields + ['records']
