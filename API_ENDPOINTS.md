# API Endpoints Documentation

## Patients

### Patient Management
- `GET /api/patients/` - List all patients
- `GET /api/patients/{id}/` - Get patient details
- `POST /api/patients/` - Create patient
- `PUT /api/patients/{id}/` - Update patient
- `DELETE /api/patients/{id}/` - Delete patient

### Patient Related Data
- `GET /api/patients/{id}/prescribed_medicines/` - Get patient's prescribed medicines
- `GET /api/patients/{id}/records/` - Get patient's records
- `GET /api/patients/{id}/records/{record_id}/` - Get specific record detail
- `GET /api/patients/{id}/total_medicine_price/` - Get total medicine price for patient

## Medicines

### Medicine Management
- `GET /api/medicines/` - List all medicines (supports search by name and scientific name)
- `GET /api/medicines/{id}/` - Get medicine details
- `POST /api/medicines/` - Create medicine
- `PUT /api/medicines/{id}/` - Update medicine
- `DELETE /api/medicines/{id}/` - Delete medicine

## Medical Records

### Record Management
- `GET /api/records/` - List all records (can filter by patient and doctor specialization)
- `GET /api/records/{id}/` - Get record details
- `POST /api/records/` - Create record
- `PUT /api/records/{id}/` - Update record
- `DELETE /api/records/{id}/` - Delete record

### Record Related Data
- `GET /api/records/{id}/prescribed_medicines/` - Get record's prescribed medicines
- `GET /api/records/{id}/total_medicine_price/` - Get total medicine price for record

## Prescribed Medicines

### Prescribed Medicine Management
- `GET /api/prescribed-medicines/` - List all prescribed medicines
- `GET /api/prescribed-medicines/{id}/` - Get prescribed medicine details
- `POST /api/prescribed-medicines/` - Create prescribed medicine
- `PUT /api/prescribed-medicines/{id}/` - Update prescribed medicine
- `DELETE /api/prescribed-medicines/{id}/` - Delete prescribed medicine

### Reporting
- `GET /api/prescribed-medicines/report/` - Get medicines report
  - Supports date filtering with `from_date` and `to_date` parameters
  - Returns medicine usage summary and total prices

## Doctors

### Doctor Management
- `GET /api/doctors/` - List all doctors (supports search by name and specialization)
- `GET /api/doctors/{id}/` - Get doctor details
- `POST /api/doctors/` - Create doctor
- `PUT /api/doctors/{id}/` - Update doctor
- `DELETE /api/doctors/{id}/` - Delete doctor

## Notes

- All list endpoints support pagination
- Search and filter capabilities:
  - Medicines: Search by name and scientific name
  - Records: Filter by patient and doctor specialization
  - Doctors: Search by name and specialization
  - Prescribed medicines report: Filter by date range