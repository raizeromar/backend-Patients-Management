from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Patient, Medicine, Record, PrescribedMedicine, Doctor
from .serializers import (
    PatientSerializer, PatientDetailSerializer, 
    MedicineSerializer, RecordSerializer, 
    PrescribedMedicineSerializer, DoctorSerializer,
    PatientRecordListSerializer, PatientRecordDetailSerializer,
    PatientPrescribedMedicineSerializer, MedicineReportSerializer
)
from django.db.models import Sum, F
from django_filters import rest_framework as django_filters
from datetime import datetime
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, extend_schema_view
from drf_spectacular.types import OpenApiTypes
from decimal import Decimal
from .filters import RecordFilter

class MedicineReportFilter(django_filters.FilterSet):
    from_date = django_filters.DateFilter(field_name='record__issued_date', lookup_expr='gte')
    to_date = django_filters.DateFilter(field_name='record__issued_date', lookup_expr='lte')

    class Meta:
        model = PrescribedMedicine
        fields = ['from_date', 'to_date']

@extend_schema_view(
    list=extend_schema(
        summary="List all patients",
        description="Returns a list of all patients with basic information",
        tags=["patients"]
    ),
    retrieve=extend_schema(
        summary="Get patient details",
        description="Returns detailed information about a specific patient",
        tags=["patients"]
    ),
    create=extend_schema(
        summary="Create new patient",
        description="Create a new patient record",
        tags=["patients"]
    ),
)
class PatientViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
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
        summary="Get patient's prescribed medicines",
        description="Returns a list of all medicines prescribed to the patient",
        tags=["patients"],
        responses={200: PatientPrescribedMedicineSerializer(many=True)}
    )
    @action(detail=True, methods=['get'])
    def prescribed_medicines(self, request, pk=None):
        patient = self.get_object()
        prescribed_medicines = PrescribedMedicine.objects.filter(
            record__patient=patient
        ).select_related('medicine', 'record')
        
        serializer = PatientPrescribedMedicineSerializer(prescribed_medicines, many=True)
        
        return Response({
            'prescribed_medicines': serializer.data,
            'total_medicine_price_per_patient': patient.total_medicine_price_per_patient()
        })

@extend_schema_view(
    list=extend_schema(
        summary="List all medicines",
        description="Returns a list of all available medicines",
        tags=["medicines"]
    ),
)
class MedicineViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Medicine.objects.all()
    serializer_class = MedicineSerializer
    filter_backends = [filters.SearchFilter]  # This is from rest_framework.filters
    search_fields = ['name', 'scientific_name']

@extend_schema_view(
    list=extend_schema(
        summary="List all medical records",
        description="Returns a list of all medical records",
        tags=["records"]
    ),
    retrieve=extend_schema(
        summary="Get record details",
        description="Returns detailed information about a specific medical record",
        tags=["records"]
    )
)
class RecordViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Record.objects.all()
    serializer_class = RecordSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = RecordFilter  # Use the custom filter class

    @extend_schema(
        summary="Get prescribed medicines for record",
        description="Returns a list of medicines prescribed in this record",
        tags=["records"],
        responses={200: PrescribedMedicineSerializer(many=True)}
    )
    @action(detail=True, methods=['get'])
    def prescribed_medicines(self, request, pk=None):
        record = self.get_object()
        medicines = record.prescribed_medicines.all()
        serializer = PrescribedMedicineSerializer(medicines, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Get total medicine price",
        description="Calculate total price of all medicines in this record",
        tags=["records"],
        responses={200: {"type": "object", "properties": {
            "total_price": {"type": "number", "format": "decimal"}
        }}}
    )
    @action(detail=True, methods=['get'])
    def total_medicine_price(self, request, pk=None):
        record = self.get_object()
        total = record.total_medicine_price_per_record()
        return Response({'total_price': total})

class PrescribedMedicineViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
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
    permission_classes = [IsAuthenticated]
    queryset = Doctor.objects.all()
    serializer_class = DoctorSerializer
    filter_backends = [filters.SearchFilter]  # This is from rest_framework.filters
    search_fields = ['name', 'specialization']
