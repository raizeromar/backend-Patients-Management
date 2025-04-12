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
    PatientPrescribedMedicineSerializer
)
from django.db.models import Sum, F

class PatientViewSet(viewsets.ModelViewSet):
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

class MedicineViewSet(viewsets.ModelViewSet):
    queryset = Medicine.objects.all()
    serializer_class = MedicineSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'scientific_name']

class RecordViewSet(viewsets.ModelViewSet):
    queryset = Record.objects.all()
    serializer_class = RecordSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['patient', 'doctor_specialization']
    
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
    filterset_fields = ['record']

    @action(detail=False, methods=['get'], url_path='report')
    def medicines_report(self, request):
        medicines_summary = PrescribedMedicine.objects.values(
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
            'total_price_all_patients': PrescribedMedicine.get_total_price_all_patients()
        }
        
        return Response(data)

class DoctorViewSet(viewsets.ModelViewSet):
    queryset = Doctor.objects.all()
    serializer_class = DoctorSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'specialization']
