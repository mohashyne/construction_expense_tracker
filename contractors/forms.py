from django import forms
from .models import Contractor

class ContractorForm(forms.ModelForm):
    class Meta:
        model = Contractor
        fields = [
            'name', 'company_name', 'contractor_type', 'email', 'phone', 
            'address', 'license_number', 'hourly_rate', 'rating', 'notes'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'John Smith',
                'required': True
            }),
            'company_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Smith Construction LLC'
            }),
            'contractor_type': forms.Select(attrs={
                'class': 'form-control form-select',
                'required': True
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'contractor@example.com'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+234 800 123 4567'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Full business address including city and state'
            }),
            'license_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'LIC-123456'
            }),
            'hourly_rate': forms.NumberInput(attrs={
                'class': 'form-control currency-value',
                'step': '0.01',
                'min': '0',
                'placeholder': '5000.00',
                'data-usd': '',
                'data-ngn': ''
            }),
            'rating': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.1',
                'min': '0',
                'max': '5',
                'placeholder': '4.5'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Additional notes about the contractor, specialties, or previous work history'
            }),
        }
    
    def clean_rating(self):
        rating = self.cleaned_data.get('rating')
        if rating is not None:
            if rating < 0 or rating > 5:
                raise forms.ValidationError("Rating must be between 0.0 and 5.0")
        return rating
    
    def clean_hourly_rate(self):
        hourly_rate = self.cleaned_data.get('hourly_rate')
        if hourly_rate is not None:
            if hourly_rate < 0:
                raise forms.ValidationError("Hourly rate cannot be negative")
        return hourly_rate
