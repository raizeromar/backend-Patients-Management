from django.contrib.auth import get_user_model
from rest_framework import serializers
from django.core.validators import MinLengthValidator
from datetime import datetime
from drf_spectacular.utils import extend_schema_field
from .models import Patient, Medicine, Record, PrescribedMedicine, Doctor, Past_Illness, GivedMedicine

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        help_text='Required. Must be at least 5 characters long.',
        validators=[MinLengthValidator(5)]
    )
    password2 = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        help_text='Required. Must match the password field.'
    )
    number = serializers.CharField(
        required=False,
        max_length=20,
        help_text='Optional. Phone number for contact purposes.'
    )
    role = serializers.ChoiceField(choices=User.ROLE_CHOICES, default='reception')
    secondary_role = serializers.ChoiceField(choices=User.ROLE_CHOICES, required=False, allow_null=True)

    class Meta:
        model = User
        fields = ('username', 'password', 'password2', 'number', 'role', 'secondary_role')

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        number = validated_data.pop('number', None)
        user = User.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password']
        )
        if number:
            user.number = number
            user.save()
        return user

class PastIllnessSerializer(serializers.ModelSerializer):
    class Meta:
        model = Past_Illness
        fields = ['id', 'description']

class MedicineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Medicine
        fields = ['id', 'name', 'dose', 'scientific_name', 'company', 'price']

class DoctorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Doctor
        fields = ['id', 'name', 'specialization', 'created_at']

class PrescribedMedicineSerializer(serializers.ModelSerializer):
    medicine_name = serializers.CharField(source='medicine.name', read_only=True)
    medicine_price = serializers.DecimalField(source='medicine.price', max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = PrescribedMedicine
        fields = ['id', 'record', 'medicine', 'medicine_name', 'medicine_price', 'dosage']
        swagger_schema_fields = {
            'example': {
                'record': 1,
                'medicine': 1,
                'dosage': '1 tablet twice daily'
            }
        }

class GivedMedicineSerializer(serializers.ModelSerializer):
    medicine_name = serializers.CharField(source='prescribed_medicine.medicine.name', read_only=True)
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = GivedMedicine
        fields = ['id', 'prescribed_medicine', 'quantity', 'given_at', 'medicine_name', 'total_price']

class RecordSerializer(serializers.ModelSerializer):
    prescribed_medicines = PrescribedMedicineSerializer(many=True, read_only=True)
    past_illness = PastIllnessSerializer(read_only=True)
    total_medicine_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    doctor_name = serializers.CharField(source='doctor.name', read_only=True)
    doctor_specialization = serializers.CharField(source='doctor.specialization', read_only=True)
    total_prescribed_medicines = serializers.IntegerField(read_only=True)  # Updated field name
    
    class Meta:
        model = Record
        fields = [
            'id', 'patient', 'doctor', 'doctor_name', 'doctor_specialization',
            'past_illness', 'vital_signs', 'issued_date', 'created_at',
            'prescribed_medicines', 'total_medicine_price', 'total_prescribed_medicines'  # Updated field name
        ]

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['total_medicine_price'] = instance.total_medicine_price_per_record()
        return representation

class PatientSerializer(serializers.ModelSerializer):
    records_count = serializers.SerializerMethodField()
    last_visit = serializers.SerializerMethodField()
    
    class Meta:
        model = Patient
        fields = [
            'id', 'full_name', 'age', 'gender', 'area', 'mobile_number',
            'status', 'is_waiting', 'records_count', 'last_visit'
        ]
    
    @extend_schema_field(int)
    def get_records_count(self, obj) -> int:
        return obj.records.count()
    
    @extend_schema_field(serializers.DateTimeField)
    def get_last_visit(self, obj) -> datetime:
        last_record = obj.records.order_by('-issued_date').first()
        return last_record.issued_date if last_record else None

class PatientDetailSerializer(PatientSerializer):
    past_illnesses = PastIllnessSerializer(many=True, read_only=True)
    total_medicine_price = serializers.SerializerMethodField()
    
    class Meta(PatientSerializer.Meta):
        fields = PatientSerializer.Meta.fields + [
            'past_illnesses',
            'created_at',
            'updated_at',
            'total_medicine_price'
        ]
    
    def get_total_medicine_price(self, obj):
        return obj.total_medicine_price_per_patient()
