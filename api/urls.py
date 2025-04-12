from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'patients', views.PatientViewSet)
router.register(r'medicines', views.MedicineViewSet)
router.register(r'records', views.RecordViewSet)
router.register(r'prescribed-medicines', views.PrescribedMedicineViewSet)
router.register(r'doctors', views.DoctorViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
