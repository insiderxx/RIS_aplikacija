from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Rezervacija, User, Oprema

class RezervacijaForm(forms.ModelForm):
    TRAJANJE_CHOICES = [
        (1, '1 ura'),
        (2, '2 uri'),
        (3, '3 ure'),
    ]
    trajanje = forms.ChoiceField(
        choices=TRAJANJE_CHOICES,
        initial=1,
        label='Trajanje',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = Rezervacija
        fields = ['trajanje', 'trener', 'oprema']
        widgets = {
            'oprema': forms.CheckboxSelectMultiple(),
            'trener': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'trener': 'Najemi trenerja (opcijsko)',
            'oprema': 'Najemi opremo (opcijsko)',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['trener'].queryset = User.objects.filter(role='trener')
        self.fields['trener'].empty_label = 'Brez trenerja'
        self.fields['trener'].required = False
        self.fields['oprema'].queryset = Oprema.objects.filter(aktivno=True)
        self.fields['oprema'].required = False

class RegistracijaForm(UserCreationForm):
    email = forms.EmailField(required=True)
    telefon = forms.CharField(max_length=20, required=False)

    class Meta:
        model = User
        fields = ['username', 'email', 'telefon', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'