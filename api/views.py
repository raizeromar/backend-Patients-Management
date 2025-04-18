from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, filters, status
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from .models import Patient, Medicine, Record, PrescribedMedicine, Doctor, Past_Illness, GivedMedicine, CustomUser
from .serializers import (
    UserCreateSerializer,
    UserUpdateSerializer,
    PatientSerializer, PatientDetailSerializer,
    MedicineSerializer, RecordSerializer,
    PrescribedMedicineSerializer, DoctorSerializer,
    PastIllnessSerializer, GivedMedicineSerializer,
    CustomUserListSerializer
)
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse, OpenApiParameter, inline_serializer
from drf_spectacular.types import OpenApiTypes
from datetime import datetime, timedelta
from django.db.models import Sum, F
from django.utils import timezone
from rest_framework import serializers

User = get_user_model()

@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    return Response({'status': 'healthy'}, status=status.HTTP_200_OK)

class PatientViewSet(viewsets.ModelViewSet):
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer
    
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

class MedicineViewSet(viewsets.ModelViewSet):
    queryset = Medicine.objects.all()
    serializer_class = MedicineSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'scientific_name', 'company']

class DoctorViewSet(viewsets.ModelViewSet):
    queryset = Doctor.objects.all()
    serializer_class = DoctorSerializer
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

class RecordViewSet(viewsets.ModelViewSet):
    queryset = Record.objects.all()
    serializer_class = RecordSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['patient__full_name', 'doctor__name', 'doctor__specialization']

class PrescribedMedicineViewSet(viewsets.ModelViewSet):
    queryset = PrescribedMedicine.objects.all()
    serializer_class = PrescribedMedicineSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['record', 'medicine']

class GivedMedicineViewSet(viewsets.ModelViewSet):
    queryset = GivedMedicine.objects.all()
    serializer_class = GivedMedicineSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['patient', 'prescribed_medicine']

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

class PastIllnessViewSet(viewsets.ModelViewSet):
    queryset = Past_Illness.objects.all()
    serializer_class = PastIllnessSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['patient']
    search_fields = ['description']

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

class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for viewing and editing user information.
    """
    queryset = CustomUser.objects.all()
    filter_backends = [filters.SearchFilter]
    search_fields = ['username', 'email', 'role', 'secondary_role']

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

    def get_queryset(self):
        queryset = CustomUser.objects.all()
        role = self.request.query_params.get('role', None)
        if role:
            queryset = queryset.filter(role=role)
        return queryset
