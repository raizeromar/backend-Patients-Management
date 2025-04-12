from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Patient, Medicine, Record, PrescribedMedicine, Doctor
from .serializers import (
    PatientSerializer, PatientDetailSerializer, 
    MedicineSerializer, RecordSerializer, 
    PrescribedMedicineSerializer, DoctorSerializer,
    PatientRecordListSerializer
)
from django.db.models import Sum, F

class PatientViewSet(viewsets.ModelViewSet):
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer
    
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

    @action(detail=False, methods=['get'])
    def total_price_all_patients(self, request):
        total = PrescribedMedicine.get_total_price_all_patients()
        return Response({'total_price': total})

class DoctorViewSet(viewsets.ModelViewSet):
    queryset = Doctor.objects.all()
    serializer_class = DoctorSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'specialization']
