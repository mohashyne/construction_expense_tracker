from django import forms
from django.contrib.auth.models import User
from .models import Project, ProjectContractor
from contractors.models import Contractor

class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = [
            'name', 'description', 'location', 'status', 'priority',
            'start_date', 'end_date', 'expected_completion_date',
            'total_budget', 'client_name', 'client_email', 'client_phone',
            'progress_percentage', 'image'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter project name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Project description...'
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Project location'
            }),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'expected_completion_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'total_budget': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00'
            }),
            'client_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Client name'
            }),
            'client_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'client@example.com'
            }),
            'client_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Phone number'
            }),
            'progress_percentage': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'max': '100',
                'placeholder': '0'
            }),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'})
        }

    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        
        # Make some fields optional
        self.fields['description'].required = False
        self.fields['location'].required = False
        self.fields['start_date'].required = False
        self.fields['end_date'].required = False
        self.fields['expected_completion_date'].required = False
        self.fields['client_name'].required = False
        self.fields['client_email'].required = False
        self.fields['client_phone'].required = False
        self.fields['image'].required = False

    def save(self, commit=True):
        project = super().save(commit=False)
        if self.user:
            project.user = self.user
        if commit:
            project.save()
        return project

class ProjectContractorForm(forms.ModelForm):
    class Meta:
        model = ProjectContractor
        fields = ['contractor', 'role', 'start_date', 'end_date', 'hourly_rate', 'is_active']
        widgets = {
            'contractor': forms.Select(attrs={'class': 'form-select'}),
            'role': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Role in project'
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'hourly_rate': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00'
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }

    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields['contractor'].queryset = Contractor.objects.filter(
                user=user, is_active=True
            ).order_by('name')
        
        # Make fields optional
        self.fields['start_date'].required = False
        self.fields['end_date'].required = False
        self.fields['hourly_rate'].required = False

class ProjectFilterForm(forms.Form):
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search projects...'
        })
    )
    
    status = forms.ChoiceField(
        required=False,
        choices=[('', 'All Status')] + Project.STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    priority = forms.ChoiceField(
        required=False,
        choices=[('', 'All Priorities')] + Project.PRIORITY_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
