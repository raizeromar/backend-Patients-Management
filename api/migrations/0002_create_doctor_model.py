from django.db import migrations, models
import django.db.models.deletion

def create_doctors_from_records(apps, schema_editor):
    Record = apps.get_model('api', 'Record')
    Doctor = apps.get_model('api', 'Doctor')
    
    # Get unique combinations of doctor specializations
    specializations = Record.objects.values_list('doctor_specialization', flat=True).distinct()
    
    # Create a doctor for each specialization
    for specialization in specializations:
        if specialization:  # Skip empty values
            Doctor.objects.create(
                name=f"Doctor ({specialization})",  # Default name
                specialization=specialization
            )

def link_records_to_doctors(apps, schema_editor):
    Record = apps.get_model('api', 'Record')
    Doctor = apps.get_model('api', 'Doctor')
    
    for record in Record.objects.all():
        if record.doctor_specialization:
            doctor = Doctor.objects.filter(specialization=record.doctor_specialization).first()
            if doctor:
                record.doctor = doctor
                record.save()

class Migration(migrations.Migration):

    dependencies = [
        ('api', '0001_initial'),  # Replace with actual previous migration
    ]

    operations = [
        migrations.CreateModel(
            name='Doctor',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('specialization', models.CharField(max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.RunPython(create_doctors_from_records),
        migrations.AddField(
            model_name='record',
            name='doctor',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='records', to='api.doctor'),
        ),
        migrations.RunPython(link_records_to_doctors),
        migrations.AlterField(
            model_name='record',
            name='doctor',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='records', to='api.doctor'),
        ),
        migrations.RemoveField(
            model_name='record',
            name='doctor_specialization',
        ),
    ]