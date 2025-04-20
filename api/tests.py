from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from .models import (
    Patient, Doctor, CustomUser, Medicine, 
    Record, PrescribedMedicine, GivedMedicine
)
from decimal import Decimal
from django.utils import timezone

class BaseAPITest(APITestCase):
    def setUp(self):
        # Create test user with all permissions
        self.user = CustomUser.objects.create_user(
            username='testadmin',
            password='testpass123',
            role='admin'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
        # Create common test data
        self.test_patient = Patient.objects.create(
            full_name='Test Patient',
            age=30,
            gender='male',
            area='Test Area',
            mobile_number='+1234567890'
        )
        
        self.test_medicine = Medicine.objects.create(
            name='Test Medicine',
            dose='500mg',
            scientific_name='Testicum',
            company='Test Pharma',
            price='9.99'
        )

class UserTests(BaseAPITest):
    def test_user_creation(self):
        """Test user creation with roles"""
        url = reverse('users-list')  # Based on DRF's default naming convention
        data = {
            'username': 'testuser',
            'password': 'testpass123',
            'role': 'doctor',
            'secondary_role': 'pharmacist'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(CustomUser.objects.count(), 2)  # Including the admin user
        
        # Test invalid role combination
        data['secondary_role'] = 'doctor'  # Same as primary role
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

class PatientTests(BaseAPITest):
    def setUp(self):
        super().setUp()
        self.valid_data = {
            'full_name': 'John Doe',
            'age': 30,
            'gender': 'male',
            'area': 'Test Area',
            'mobile_number': '+1234567890',
            'status': 'active',
            'is_waiting': False
        }

    def test_patient_creation(self):
        url = reverse('patient-list')
        response = self.client.post(url, self.valid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Get the ID from the response data structure
        patient_id = response.data['data']['id']  # Adjusted to match API response structure
        detail_url = reverse('patient-detail', args=[patient_id])
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('records_count', response.data)
        self.assertIn('last_visit', response.data)

    def test_patient_filters(self):
        Patient.objects.create(**self.valid_data)
        url = reverse('patient-list')
        
        # Test status filter
        response = self.client.get(url, {'status': 'active'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get('results', response.data)
        self.assertEqual(len([p for p in results if p['status'] == 'active']), 1)
        
        # Test waiting list filter
        response = self.client.get(url, {'is_waiting': 'false'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get('results', response.data)
        self.assertEqual(len([p for p in results if not p['is_waiting']]), 1)

class MedicineTests(BaseAPITest):
    def setUp(self):
        super().setUp()
        self.valid_data = {
            'name': 'Test Medicine',
            'dose': '500mg',
            'scientific_name': 'Testicum',
            'company': 'Test Pharma',
            'price': '9.99'
        }

    def test_medicine_validation(self):
        url = reverse('medicine-list')
        
        # Test price validation
        invalid_data = self.valid_data.copy()
        invalid_data['price'] = '-1.00'
        response = self.client.post(url, invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Test successful creation
        response = self.client.post(url, self.valid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_medicine_search(self):
        Medicine.objects.create(**self.valid_data)
        url = reverse('medicine-list')
        
        # Test name search
        response = self.client.get(url, {'search': 'Test Medicine'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Assuming response.data has a 'results' key containing the list of medicines
        results = response.data.get('results', response.data)
        self.assertTrue(len(results) > 0)
        self.assertTrue(
            any(m.get('name') == 'Test Medicine' for m in results)
        )
        
        # Test scientific name search
        response = self.client.get(url, {'search': 'Testicum'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get('results', response.data)
        self.assertTrue(
            any(m.get('scientific_name') == 'Testicum' for m in results)
        )

class RecordTests(BaseAPITest):
    def setUp(self):
        super().setUp()
        self.patient = Patient.objects.create(
            full_name='Test Patient',
            age=30,
            gender='male',
            area='Test Area',
            mobile_number='+1234567890'
        )
        self.doctor_user = CustomUser.objects.create_user(
            username='testdoctor',
            password='testpass123',
            role='doctor'
        )
        self.doctor = Doctor.objects.create(
            user=self.doctor_user,
            name='Dr. Test',
            specialization='Testing',
            mobile_number='+1234567890'
        )
        self.valid_data = {
            'patient': self.patient.id,
            'doctor': self.doctor.id,
            'vital_signs': {'temperature': '37.0', 'blood_pressure': '120/80'},
            'past_illnesses': ['Diabetes', 'Hypertension'],
            'issued_date': timezone.now().date().isoformat(),
            'is_default': False
        }

    def test_record_creation_with_medicines(self):
        url = reverse('records-list')  # Make sure this matches your URL pattern
        
        # Create record with prescribed medicine
        record_data = {
            'patient': self.patient.id,
            'doctor': self.doctor.id,
            'vital_signs': {
                'temperature': '37.0',
                'blood_pressure': '120/80',
                'pulse': '72',
                'respiratory_rate': '16'
            },
            'past_illnesses': ['Diabetes', 'Hypertension'],
            'issued_date': timezone.now().date().isoformat(),
            'is_default': False,
            'prescribed_medicines': [{
                'medicine': self.medicine.id,  # Use the medicine created in setUp
                'dosage': '1 tablet daily',
                'duration': '7 days',
                'notes': 'Take after meals'
            }]
        }
        
        response = self.client.post(url, data=record_data, format='json')
        
        if response.status_code != status.HTTP_201_CREATED:
            print("Response data:", response.data)  # Print error response for debugging
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify the record was created
        created_record = Record.objects.get(id=response.data['id'])
        self.assertEqual(created_record.patient.id, self.patient.id)
        self.assertEqual(created_record.doctor.id, self.doctor.id)
        
        # Verify prescribed medicines were created
        self.assertEqual(created_record.prescribed_medicines.count(), 1)
        prescribed_medicine = created_record.prescribed_medicines.first()
        self.assertEqual(prescribed_medicine.medicine.id, self.medicine.id)

class PrescribedMedicineTests(BaseAPITest):
    def setUp(self):
        super().setUp()
        # Setup similar to RecordTests
        self.patient = Patient.objects.create(
            full_name='Test Patient',
            age=30,
            gender='male',
            area='Test Area',
            mobile_number='+1234567890'
        )
        self.doctor_user = CustomUser.objects.create_user(
            username='testdoctor',
            password='testpass123',
            role='doctor'
        )
        self.doctor = Doctor.objects.create(
            user=self.doctor_user,
            name='Dr. Test',
            specialization='Testing',
            mobile_number='+1234567890'
        )
        self.record = Record.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            issued_date=timezone.now().date(),
            is_default=False
        )
        self.medicine = Medicine.objects.create(
            name='Test Medicine',
            dose='500mg',
            scientific_name='Testicum',
            company='Test Pharma',
            price='9.99'
        )

    def test_prescribed_medicine_creation(self):
        url = reverse('prescribedmedicine-list')
        data = {
            'record': self.record.id,
            'medicine': self.medicine.id,
            'dosage': '1 tablet daily',
            'duration': '7 days'
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify price calculations in the response data
        self.assertIn('medicine_price', response.data['data'])
        self.assertEqual(response.data['data']['medicine_price'], '9.99')

def test_health_check(self):
    """Test health check endpoint"""
    url = reverse('health-check')
    response = self.client.get(url)
    self.assertEqual(response.status_code, status.HTTP_200_OK)
    self.assertEqual(response.data, {'status': 'healthy'})
