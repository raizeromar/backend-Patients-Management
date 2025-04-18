from django.contrib.auth import get_user_model
from rest_framework import serializers
from django.core.validators import MinLengthValidator
from datetime import datetime
from drf_spectacular.utils import extend_schema_field
from .models import Patient, Medicine, Record, PrescribedMedicine, Doctor, Past_Illness, GivedMedicine, CustomUser

User = get_user_model()

class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        min_length=5,
        help_text='Required. Must be at least 5 characters long.'
    )
    role = serializers.ChoiceField(
        choices=CustomUser.ROLE_CHOICES,
        required=True
    )
    secondary_role = serializers.ChoiceField(
        choices=CustomUser.ROLE_CHOICES,
        required=False,
        allow_null=True
    )

    class Meta:
        model = CustomUser
        fields = ['username', 'password', 'role', 'secondary_role']

    def validate(self, attrs):
        # Validate that role and secondary_role are different if both provided
        role = attrs.get('role')
        secondary_role = attrs.get('secondary_role')
        if secondary_role and role == secondary_role:
            raise serializers.ValidationError({
                "secondary_role": "Secondary role must be different from primary role"
            })
        return attrs

    def create(self, validated_data):
        # Create user with hashed password
        user = CustomUser.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password'],
            role=validated_data['role'],
            secondary_role=validated_data.get('secondary_role')
        )
        return user

class UserUpdateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=False,  # Not required for updates
        style={'input_type': 'password'},
        min_length=5,
        help_text='Must be at least 5 characters long.'
    )
    role = serializers.ChoiceField(
        choices=CustomUser.ROLE_CHOICES,
        required=True
    )
    secondary_role = serializers.ChoiceField(
        choices=CustomUser.ROLE_CHOICES,
        required=False,
        allow_null=True
    )

    class Meta:
        model = CustomUser
        fields = ['username', 'password', 'role', 'secondary_role']

    def validate(self, attrs):
        # Validate that role and secondary_role are different if both provided
        role = attrs.get('role')
        secondary_role = attrs.get('secondary_role')
        if secondary_role and role == secondary_role:
            raise serializers.ValidationError({
                "secondary_role": "Secondary role must be different from primary role"
            })
        return attrs

    def update(self, instance, validated_data):
        # Handle password update separately
        password = validated_data.pop('password', None)
        if password:
            instance.set_password(password)
        
        # Update other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        return instance

class PastIllnessSerializer(serializers.ModelSerializer):
    class Meta:
        model = Past_Illness
        fields = ['id', 'description']

class MedicineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Medicine
        fields = ['id', 'name', 'dose', 'scientific_name', 'company', 'price']

class DoctorSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    user_id = serializers.IntegerField(source='user.id', read_only=True)

    class Meta:
        model = Doctor
        fields = ['id', 'user', 'user_id', 'username', 'name', 'specialization', 'mobile_number', 'created_at']
        extra_kwargs = {
            'user': {'required': True, 'write_only': True},  # Make user field required
            'created_at': {'read_only': True}
        }

    def validate_user(self, value):
        if value.role != 'doctor':
            raise serializers.ValidationError("The user must have a 'doctor' role")
        return value

class PrescribedMedicineSerializer(serializers.ModelSerializer):
    medicine_name = serializers.CharField(source='medicine.name', read_only=True)
    medicine_price = serializers.DecimalField(source='medicine.price', max_digits=10, decimal_places=2, read_only=True)
    patient = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = PrescribedMedicine
        fields = ['id', 'record', 'medicine', 'medicine_name', 'medicine_price', 'dosage', 'patient']
        extra_kwargs = {
            'record': {'required': False}
        }

    def validate(self, data):
        if 'record' not in data and 'patient' not in data:
            raise serializers.ValidationError(
                "Either 'record' or 'patient' must be provided"
            )
        return data

    def create(self, validated_data):
        patient_id = validated_data.pop('patient', None)
        
        if patient_id and 'record' not in validated_data:
            try:
                patient = Patient.objects.get(id=patient_id)
                default_record = Record.objects.filter(
                    patient=patient,
                    is_default=True
                ).first()
                
                if not default_record:
                    # Create a default record if none exists
                    default_record = Record.create_default_record(patient)
                    if not default_record:
                        raise serializers.ValidationError(
                            {'error': 'Could not create default record. No default doctor available.'}
                        )
                
                validated_data['record'] = default_record
                
            except Patient.DoesNotExist:
                raise serializers.ValidationError(
                    {'error': 'Patient not found'}
                )
        
        return super().create(validated_data)

class GivedMedicineSerializer(serializers.ModelSerializer):
    medicine_name = serializers.CharField(source='prescribed_medicine.medicine.name', read_only=True)
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    # Add new write-only fields for direct medicine creation
    medicine = serializers.IntegerField(write_only=True, required=False)
    dosage = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = GivedMedicine
        fields = ['id', 'patient', 'prescribed_medicine', 'quantity', 'given_at', 
                 'medicine_name', 'total_price', 'medicine', 'dosage']
        extra_kwargs = {
            'prescribed_medicine': {'required': False}
        }

    def validate(self, data):
        # Check if either prescribed_medicine or (medicine and dosage) is provided
        if 'prescribed_medicine' not in data and ('medicine' not in data or 'dosage' not in data):
            raise serializers.ValidationError(
                "Either 'prescribed_medicine' or both 'medicine' and 'dosage' must be provided"
            )
        return data

    def create(self, validated_data):
        medicine_id = validated_data.pop('medicine', None)
        dosage = validated_data.pop('dosage', None)

        if medicine_id and dosage and 'prescribed_medicine' not in validated_data:
            try:
                patient = validated_data['patient']
                medicine = Medicine.objects.get(id=medicine_id)
                
                # Get or create default record
                default_record = Record.objects.filter(
                    patient=patient,
                    is_default=True
                ).first()
                
                if not default_record:
                    default_record = Record.create_default_record(patient)
                    if not default_record:
                        raise serializers.ValidationError(
                            {'error': 'Could not create default record. No default doctor available.'}
                        )

                # Create prescribed medicine
                prescribed_medicine = PrescribedMedicine.objects.create(
                    record=default_record,
                    medicine=medicine,
                    dosage=dosage
                )
                
                validated_data['prescribed_medicine'] = prescribed_medicine
                
            except Medicine.DoesNotExist:
                raise serializers.ValidationError({'error': 'Medicine not found'})
            except Patient.DoesNotExist:
                raise serializers.ValidationError({'error': 'Patient not found'})

        return super().create(validated_data)

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

class CustomUserListSerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'roles']

    def get_roles(self, obj):
        return {
            'primary_role': obj.role,
            'secondary_role': obj.secondary_role
        }
