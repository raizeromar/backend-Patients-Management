from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, filters, status
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from .models import Patient, Medicine, Record, PrescribedMedicine, Doctor, GivedMedicine, CustomUser
from .serializers import (
    UserCreateSerializer,
    UserUpdateSerializer,
    CustomUserListSerializer,
    PatientSerializer, PatientDetailSerializer,
    MedicineSerializer, RecordSerializer,
    PrescribedMedicineSerializer, DoctorSerializer,
    GivedMedicineSerializer,
)
from drf_spectacular.utils import extend_schema, extend_schema_field, OpenApiExample, OpenApiResponse, OpenApiParameter, inline_serializer
from drf_spectacular.types import OpenApiTypes
from datetime import datetime, timedelta
from django.db.models import Sum, F
from django.utils import timezone
from rest_framework import serializers
from django.http import Http404

User = get_user_model()

# Exclude health check from schema
@extend_schema(exclude=True)
@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    return Response({'status': 'healthy'}, status=status.HTTP_200_OK)

class ResultsListMixin:
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response({"results": serializer.data})

class BaseViewSet(viewsets.ModelViewSet):
    """
    Base ViewSet that implements standard success messages for create, update and delete operations
    """
    
    @extend_schema(
        responses={
            201: OpenApiResponse(description="Resource created successfully"),
            400: OpenApiResponse(description="Invalid data provided")
        }
    )
    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        if response.status_code == 201:
            response.data = {
                "message": f"{self.model_name} created successfully",
                "data": response.data
            }
        return response

    @extend_schema(
        responses={
            200: OpenApiResponse(description="Resource updated successfully"),
            404: OpenApiResponse(description="Resource not found")
        }
    )
    def update(self, request, *args, **kwargs):
        try:
            response = super().update(request, *args, **kwargs)
            if response.status_code == 200:
                response.data = {
                    "message": f"{self.model_name} updated successfully",
                    "data": response.data
                }
            return response
        except Http404:
            return Response(
                {"error": f"{self.model_name} not found"},
                status=status.HTTP_404_NOT_FOUND
            )

    @extend_schema(
        responses={
            200: OpenApiResponse(description="Resource deleted successfully"),
            404: OpenApiResponse(description="Resource not found")
        }
    )
    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            return Response(
                {"message": f"{self.model_name} deleted successfully"},
                status=status.HTTP_200_OK
            )
        except Http404:
            return Response(
                {"error": f"{self.model_name} not found"},
                status=status.HTTP_404_NOT_FOUND
            )

class PatientViewSet(ResultsListMixin, BaseViewSet):
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer
    model_name = "Patient"
    
    @extend_schema(
        summary="Create a new patient",
        description="Create a new patient. If a patient with the same full_name, age, and gender already exists, returns the existing patient's information.",
        request=PatientSerializer,
        responses={
            201: OpenApiResponse(
                response=PatientSerializer,
                description="Patient created successfully"
            ),
            200: OpenApiResponse(
                description="Patient already exists",
                examples=[
                    OpenApiExample(
                        'Existing Patient',
                        value={
                            "message": "Patient Already Exists",
                            "patient_id": 123,
                            "data": {
                                "id": 123,
                                "full_name": "John Doe",
                                "age": 30,
                                "gender": "male",
                                "area": "Test Area",
                                "mobile_number": "+1234567890",
                                "status": "active",
                                "is_waiting": True
                            }
                        }
                    )
                ]
            ),
            400: OpenApiResponse(description="Invalid data provided")
        }
    )
    def create(self, request, *args, **kwargs):
        # Extract the relevant fields from the request data
        full_name = request.data.get('full_name')
        age = request.data.get('age')
        gender = request.data.get('gender')
        
        # Check if patient already exists
        existing_patient = Patient.objects.filter(
            full_name=full_name,
            age=age,
            gender=gender
        ).first()
        
        if existing_patient:
            return Response({
                "message": "Patient Already Exists",
                "patient_id": existing_patient.id,
                "data": PatientSerializer(existing_patient).data
            }, status=status.HTTP_200_OK)
            
        return super().create(request, *args, **kwargs)
    
    @action(detail=True, methods=['get'])
    def prescribed_medicines(self, request, pk=None):
        """Get all prescribed medicines for a specific patient"""
        patient = self.get_object()
        prescribed_medicines = PrescribedMedicine.objects.filter(
            record__patient=patient
        ).select_related('medicine', 'record')
        
        serializer = PrescribedMedicineSerializer(prescribed_medicines, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def given_medicines(self, request, pk=None):
        """Get all given medicines for a specific patient"""
        patient = self.get_object()
        given_medicines = GivedMedicine.objects.filter(
            patient=patient
        ).select_related('prescribed_medicine', 'prescribed_medicine__medicine')
        
        serializer = GivedMedicineSerializer(given_medicines, many=True)
        response_data = {
            'given_medicines': serializer.data,
            'total_price': patient.total_medicine_price_per_patient()
        }
        return Response(response_data)

    @action(detail=True, methods=['get'])
    def records(self, request, pk=None):
        """Get all records for a specific patient"""
        patient = self.get_object()
        records = patient.records.all().select_related('doctor')
        
        serializer = RecordSerializer(records, many=True)
        return Response(serializer.data)

class MedicineViewSet(ResultsListMixin, BaseViewSet):
    queryset = Medicine.objects.all()
    serializer_class = MedicineSerializer
    model_name = "Medicine"
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'scientific_name', 'company']

class DoctorViewSet(ResultsListMixin, BaseViewSet):
    queryset = Doctor.objects.all()
    serializer_class = DoctorSerializer
    model_name = "Doctor"
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'specialization', 'mobile_number', 'user__username']

    @extend_schema(
        summary="Create a new doctor",
        description="Create a new doctor with required user account link. The linked user must have a 'doctor' role.",
        request=DoctorSerializer,
        responses={
            201: OpenApiResponse(
                response=DoctorSerializer,
                description="Doctor created successfully"
            ),
            400: OpenApiResponse(
                description="Invalid data provided",
                examples=[
                    OpenApiExample(
                        'Validation Error',
                        value={
                            "mobile_number": ["This field is required."],
                            "user": ["This field is required.", "The user must have a 'doctor' role"]
                        }
                    )
                ]
            )
        },
        examples=[
            OpenApiExample(
                'Valid Request',
                value={
                    "name": "Dr. John Doe",
                    "specialization": "Cardiology",
                    "mobile_number": "+1234567890",
                    "user": 1  # Required user ID with doctor role
                },
                request_only=True
            )
        ]
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="Update a doctor",
        description="Update doctor's information. The user link cannot be changed once created.",
        request=DoctorSerializer,
        responses={
            200: OpenApiResponse(
                response=DoctorSerializer,
                description="Doctor updated successfully"
            )
        },
        examples=[
            OpenApiExample(
                'Update Example',
                value={
                    "name": "Dr. John Doe",
                    "specialization": "Cardiology",
                    "mobile_number": "+1234567890"
                },
                request_only=True
            )
        ]
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

class RecordViewSet(ResultsListMixin, BaseViewSet):
    queryset = Record.objects.all()
    serializer_class = RecordSerializer
    model_name = "Record"
    filter_backends = [filters.SearchFilter]
    search_fields = ['patient__full_name', 'doctor__name', 'doctor__specialization']

class PrescribedMedicineViewSet(ResultsListMixin, BaseViewSet):
    queryset = PrescribedMedicine.objects.all()
    serializer_class = PrescribedMedicineSerializer
    model_name = "Prescribed medicine"
    
    def get_queryset(self):
        queryset = super().get_queryset()
        record = self.request.query_params.get('record', None)
        medicine = self.request.query_params.get('medicine', None)
        
        if record:
            queryset = queryset.filter(record=record)
        if medicine:
            queryset = queryset.filter(medicine=medicine)
        return queryset

class GivedMedicineViewSet(ResultsListMixin, BaseViewSet):
    queryset = GivedMedicine.objects.all()
    serializer_class = GivedMedicineSerializer
    model_name = "Given medicine"
    
    def get_queryset(self):
        queryset = super().get_queryset()
        patient = self.request.query_params.get('patient', None)
        prescribed_medicine = self.request.query_params.get('prescribed_medicine', None)
        
        if patient:
            queryset = queryset.filter(patient=patient)
        if prescribed_medicine:
            queryset = queryset.filter(prescribed_medicine=prescribed_medicine)
        return queryset

    @extend_schema(
        summary="Create a given medicine record",
        description="""
        Create a new given medicine record in two ways:
        
        1. Using an existing prescribed medicine:
           - Provide patient, prescribed_medicine, and quantity
        
        2. Creating a new prescribed medicine on the fly:
           - Provide patient, medicine, dosage, and quantity
        """,
        request=GivedMedicineSerializer,
        responses={
            201: OpenApiResponse(
                response=GivedMedicineSerializer,
                description="Given medicine created successfully"
            ),
            400: OpenApiResponse(
                description="Invalid data provided"
            )
        },
        examples=[
            OpenApiExample(
                'Using Existing Prescription',
                value={
                    "patient": 1,
                    "prescribed_medicine": 1,
                    "quantity": 2
                },
                request_only=True
            ),
            OpenApiExample(
                'Creating New Prescription',
                value={
                    "patient": 1,
                    "medicine": 1,
                    "dosage": "1 tablet twice daily",
                    "quantity": 2
                },
                request_only=True
            )
        ]
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

# Remove PastIllnessViewSet
# class PastIllnessViewSet(BaseViewSet):
#     ....


@extend_schema(
    tags=['reports'],
    operation_id='medicine_report_retrieve',
    summary="Medicine Usage Report",
    description="Get a report of all medicines given to patients with total quantities and prices",
    parameters=[
        OpenApiParameter(
            name="from_date",
            type=OpenApiTypes.DATE,
            location=OpenApiParameter.QUERY,
            description="Start date for the report (YYYY-MM-DD)",
            required=False
        ),
        OpenApiParameter(
            name="to_date",
            type=OpenApiTypes.DATE,
            location=OpenApiParameter.QUERY,
            description="End date for the report (YYYY-MM-DD)",
            required=False
        ),
        OpenApiParameter(
            name="area",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description="Filter by patient area",
            required=False
        ),
        OpenApiParameter(
            name="period",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description="Predefined period ('today', 'month')",
            required=False,
            enum=['today', 'month']
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=inline_serializer(
                name='MedicineReportResponse',
                fields={
                    'metadata': inline_serializer(
                        name='MedicineReportMetadata',
                        fields={
                            'from_date': serializers.DateField(),
                            'to_date': serializers.DateField(),
                            'total_price': serializers.DecimalField(max_digits=10, decimal_places=2),
                            'filters_applied': inline_serializer(
                                name='FiltersApplied',
                                fields={
                                    'area': serializers.CharField(allow_null=True),
                                    'period': serializers.CharField(allow_null=True),
                                }
                            ),
                        }
                    ),
                    'medicines': inline_serializer(
                        name='MedicineReportDetail',
                        fields={
                            'medicine_name': serializers.CharField(),
                            'total_quantity': serializers.IntegerField(),
                            'price_per_unit': serializers.DecimalField(max_digits=10, decimal_places=2),
                            'total_price': serializers.DecimalField(max_digits=10, decimal_places=2),
                        },
                        many=True
                    ),
                }
            ),
            examples=[
                OpenApiExample(
                    'Success Response',
                    value={
                        "metadata": {
                            "from_date": "2025-04-01",
                            "to_date": "2025-04-16",
                            "total_price": "1250.00",
                            "filters_applied": {
                                "area": "New York",
                                "period": "month"
                            }
                        },
                        "medicines": [
                            {
                                "medicine_name": "Amoxicillin",
                                "total_quantity": 50,
                                "price_per_unit": "8.50",
                                "total_price": "425.00"
                            }
                        ]
                    }
                )
            ]
        )
    }
)
@api_view(['GET'])
def medicines_report(request):
    # Get query parameters
    from_date = request.query_params.get('from_date')
    to_date = request.query_params.get('to_date')
    area = request.query_params.get('area')
    period = request.query_params.get('period')

    # Base queryset
    queryset = GivedMedicine.objects.all()

    # Apply date filters
    if period == 'today':
        today = timezone.now().date()
        queryset = queryset.filter(given_at__date=today)
        from_date = today
        to_date = today
    elif period == 'month':
        today = timezone.now().date()
        from_date = today.replace(day=1)
        to_date = today
        queryset = queryset.filter(given_at__date__gte=from_date, given_at__date__lte=to_date)
    else:
        if from_date:
            queryset = queryset.filter(given_at__date__gte=from_date)
        if to_date:
            queryset = queryset.filter(given_at__date__lte=to_date)

    # Apply area filter
    if area:
        queryset = queryset.filter(patient__area=area)

    # Aggregate data by medicine
    medicines_data = queryset.values(
        'prescribed_medicine__medicine__name',
        'prescribed_medicine__medicine__dose',
        'prescribed_medicine__medicine__price'
    ).annotate(
        total_quantity=Sum('quantity'),
        total_price=Sum(F('prescribed_medicine__medicine__price') * F('quantity'))
    ).order_by('prescribed_medicine__medicine__name')

    # Calculate total price
    total_price = sum(item['total_price'] for item in medicines_data)

    response_data = {
        "metadata": {
            "from_date": from_date,
            "to_date": to_date,
            "total_price": total_price,
            "filters_applied": {
                "area": area,
                "period": period
            }
        },
        "medicines": [
            {
                "medicine_name": f"{item['prescribed_medicine__medicine__name']} ({item['prescribed_medicine__medicine__dose']})",
                "total_quantity": item['total_quantity'],
                "price_per_unit": item['prescribed_medicine__medicine__price'],
                "total_price": item['total_price']
            }
            for item in medicines_data
        ]
    }

    return Response(response_data)

class UserViewSet(ResultsListMixin, viewsets.ModelViewSet):
    """
    ViewSet for viewing and editing user information.
    """
    queryset = CustomUser.objects.all()
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['username']
    filterset_fields = ['role', 'secondary_role']

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        return CustomUserListSerializer

    @extend_schema(
        summary="Update a user",
        description="Fully update a user's information. All fields except password are required.",
        request=UserUpdateSerializer,
        responses={
            200: OpenApiResponse(
                response=CustomUserListSerializer,
                description="User updated successfully"
            ),
            400: OpenApiResponse(
                description="Invalid data provided",
                examples=[
                    OpenApiExample(
                        'Validation Error',
                        value={
                            "secondary_role": ["Secondary role must be different from primary role"],
                            "password": ["Ensure this field has at least 5 characters."]
                        }
                    )
                ]
            )
        },
        examples=[
            OpenApiExample(
                'Valid Request',
                value={
                    "username": "updateduser",
                    "password": "newpass123",
                    "role": "doctor",
                    "secondary_role": "reception"
                },
                request_only=True
            )
        ]
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Partially update a user",
        description="Update specific fields of a user. Only provide the fields that need to be updated.",
        request=UserUpdateSerializer,
        responses={
            200: OpenApiResponse(
                response=CustomUserListSerializer,
                description="User partially updated successfully"
            ),
            400: OpenApiResponse(
                description="Invalid data provided",
                examples=[
                    OpenApiExample(
                        'Validation Error',
                        value={
                            "secondary_role": ["Secondary role must be different from primary role"],
                            "password": ["Ensure this field has at least 5 characters."]
                        }
                    )
                ]
            )
        },
        examples=[
            OpenApiExample(
                'Update Role Only',
                value={
                    "role": "pharmacist",
                    "secondary_role": 'null'
                },
                request_only=True
            ),
            OpenApiExample(
                'Update Password Only',
                value={
                    "password": "newpassword123"
                },
                request_only=True
            )
        ]
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        responses={
            200: CustomUserListSerializer,
            400: OpenApiTypes.OBJECT,
        }
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
