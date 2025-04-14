from rest_framework import viewsets, filters, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from .models import Patient, Medicine, Record, PrescribedMedicine, Doctor
from .serializers import (
    PatientSerializer, PatientDetailSerializer, 
    MedicineSerializer, RecordSerializer, 
    PrescribedMedicineSerializer, DoctorSerializer,
    PatientRecordListSerializer, PatientRecordDetailSerializer,
    PatientPrescribedMedicineSerializer, MedicineReportSerializer,
    UserSerializer
)
from django.db.models import Sum, F
from django_filters import rest_framework as django_filters
from datetime import datetime
from django.contrib.auth.models import User
from drf_spectacular.utils import extend_schema, extend_schema_view

@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    return Response(
        {'status': 'healthy'},
        status=status.HTTP_200_OK
    )

class MedicineReportFilter(django_filters.FilterSet):
    from_date = django_filters.DateFilter(field_name='record__issued_date', lookup_expr='gte')
    to_date = django_filters.DateFilter(field_name='record__issued_date', lookup_expr='lte')

    class Meta:
        model = PrescribedMedicine
        fields = ['from_date', 'to_date']

@extend_schema_view(
    list=extend_schema(description='List all patients'),
    retrieve=extend_schema(description='Get patient details'),
    create=extend_schema(description='Create a new patient'),
    update=extend_schema(description='Update patient details'),
    destroy=extend_schema(description='Delete a patient'),
)
class PatientViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing patients.
    """
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = PatientDetailSerializer(instance)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def records(self, request, pk=None):
        patient = self.get_object()
        records = patient.records.all()
        serializer = PatientRecordListSerializer(records, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def total_medicine_price(self, request, pk=None):
        patient = self.get_object()
        total = patient.total_medicine_price_per_patient()
        return Response({'total_price': total})

    @action(detail=True, url_path='records/(?P<record_id>[^/.]+)', methods=['get'])
    def record_detail(self, request, pk=None, record_id=None):
        try:
            record = Record.objects.get(patient_id=pk, id=record_id)
            serializer = PatientRecordDetailSerializer(record)
            return Response(serializer.data)
        except Record.DoesNotExist:
            return Response(
                {"detail": "Record not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )

    @extend_schema(
        description='Get all prescribed medicines for a patient',
        responses={200: PatientPrescribedMedicineSerializer(many=True)}
    )
    @action(detail=True, methods=['get'])
    def prescribed_medicines(self, request, pk=None):
        """Get all prescribed medicines for a specific patient."""
        patient = self.get_object()
        prescribed_medicines = PrescribedMedicine.objects.filter(
            record__patient=patient
        ).select_related('medicine', 'record')
        
        serializer = PatientPrescribedMedicineSerializer(prescribed_medicines, many=True)
        
        return Response({
            'prescribed_medicines': serializer.data,
            'total_medicine_price_per_patient': patient.total_medicine_price_per_patient()
        })

class MedicineViewSet(viewsets.ModelViewSet):
    queryset = Medicine.objects.all()
    serializer_class = MedicineSerializer
    filter_backends = [filters.SearchFilter]  # This is from rest_framework.filters
    search_fields = ['name', 'scientific_name']

class RecordViewSet(viewsets.ModelViewSet):
    queryset = Record.objects.all()
    serializer_class = RecordSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['patient', 'doctor__specialization']  # Changed from doctor_specialization to doctor__specialization
    
    @action(detail=True, methods=['get'])
    def prescribed_medicines(self, request, pk=None):
        record = self.get_object()
        medicines = record.prescribed_medicines.all()
        serializer = PrescribedMedicineSerializer(medicines, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def total_medicine_price(self, request, pk=None):
        record = self.get_object()
        total = record.total_medicine_price_per_record()
        return Response({'total_price': total})

class PrescribedMedicineViewSet(viewsets.ModelViewSet):
    queryset = PrescribedMedicine.objects.all()
    serializer_class = PrescribedMedicineSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = MedicineReportFilter

    @action(detail=False, methods=['get'], url_path='report')
    def medicines_report(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        
        medicines_summary = queryset.values(
            'medicine__name',
            'medicine__dose',
            'medicine__price'
        ).annotate(
            total_quantity=Sum('quantity'),
            total_price=Sum(F('medicine__price') * F('quantity'))
        ).order_by('medicine__name')

        data = {
            'medicines': [
                {
                    'medicine': f"{item['medicine__name']} {item['medicine__dose']}",
                    'price': item['medicine__price'],
                    'quantity': item['total_quantity'],
                    'total_price': item['total_price']
                }
                for item in medicines_summary
            ],
            'total_price_all_patients': queryset.annotate(
                item_total=F('medicine__price') * F('quantity')
            ).aggregate(
                total_price=Sum('item_total')
            )['total_price'] or 0,
            'date_range': {
                'from': request.query_params.get('from_date'),
                'to': request.query_params.get('to_date')
            }
        }
        
        serializer = MedicineReportSerializer(data)
        return Response(serializer.data)

class DoctorViewSet(viewsets.ModelViewSet):
    queryset = Doctor.objects.all()
    serializer_class = DoctorSerializer
    filter_backends = [filters.SearchFilter]  # This is from rest_framework.filters
    search_fields = ['name', 'specialization']

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]  # Only for register endpoint

    def get_permissions(self):
        if self.action == 'create':
            return [AllowAny()]
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {
                'id': user.id,
                'username': user.username,
                'message': 'User created successfully'
            },
            status=status.HTTP_201_CREATED
        )

    @action(detail=False, methods=['get'])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    username = request.data.get('username')
    password = request.data.get('password')
    
    if not username or not password:
        return Response(
            {'error': 'Both username and password are required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if User.objects.filter(username=username).exists():
        return Response(
            {'error': 'Username already exists'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    user = User.objects.create_user(
        username=username,
        password=password
    )
    
    return Response(
        {
            'id': user.id,
            'username': user.username,
            'message': 'User created successfully'
        },
        status=status.HTTP_201_CREATED
    )
