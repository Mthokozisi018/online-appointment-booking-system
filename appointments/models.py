from django.db import models


class Appointment(models.Model):
    client_name = models.CharField(max_length=100)
    client_email = models.EmailField()
    appointment_date = models.DateField()
    appointment_time = models.TimeField()
    service = models.CharField(max_length=100)
    notes = models.TextField(blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('confirmed', 'Confirmed'),
            ('completed', 'Completed'),
            ('cancelled', 'Cancelled'),
        ],        default='pending'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.client_name} - {self.service} on {self.appointment_date}"