from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, filters, status
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from .models import Patient, Medicine, Record, PrescribedMedicine, Doctor, Past_Illness, GivedMedicine
from .serializers import (
    UserSerializer,
    PatientSerializer, PatientDetailSerializer,
    MedicineSerializer, RecordSerializer,
    PrescribedMedicineSerializer, DoctorSerializer,
    PastIllnessSerializer, GivedMedicineSerializer
)

@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    return Response({'status': 'healthy'}, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(
            {'message': 'User created successfully'},
            status=status.HTTP_201_CREATED
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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
    search_fields = ['name', 'specialization']

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

class PastIllnessViewSet(viewsets.ModelViewSet):
    queryset = Past_Illness.objects.all()
    serializer_class = PastIllnessSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['patient']
    search_fields = ['description']
