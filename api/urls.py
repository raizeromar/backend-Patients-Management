from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'patients', views.PatientViewSet)
router.register(r'medicines', views.MedicineViewSet)
router.register(r'records', views.RecordViewSet)
router.register(r'prescribed-medicines', views.PrescribedMedicineViewSet)
router.register(r'doctors', views.DoctorViewSet)
router.register(r'users', views.UserViewSet)

urlpatterns = [
    path('health/', views.health_check, name='health_check'),
    path('', include(router.urls)),
]
