from django.contrib.auth.models import AbstractUser
from django.db import models

#  UPORABNIKI
class User(AbstractUser):
    class Role(models.TextChoices):
        UPORABNIK    = 'uporabnik',    'Uporabnik'
        TRENER       = 'trener',       'Trener'
        ADMINISTRATOR = 'administrator', 'Administrator'

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.UPORABNIK)
    telefon = models.CharField(max_length=20, blank=True)

    def je_trener(self):
        return self.role == self.Role.TRENER

    def je_admin(self):
        return self.role == self.Role.ADMINISTRATOR


# IGRIŠČA
class Igrisca(models.Model):
    class Povrsina(models.TextChoices):
        PESEK  = 'pesek',  'Pesek'
        TRAVA  = 'trava',  'Trava'
        TRDA   = 'trda',   'Trda podlaga'

    ime       = models.CharField(max_length=50)
    povrsina  = models.CharField(max_length=20, choices=Povrsina.choices, default=Povrsina.TRDA)
    aktivno   = models.BooleanField(default=True)        # admin lahko deaktivira
    cena_ura = models.DecimalField(max_digits=6, decimal_places=2, default=10.00)

    def __str__(self):
        return self.ime


# OPREMA
class Oprema(models.Model):
    ime        = models.CharField(max_length=100)
    kolicina   = models.PositiveIntegerField(default=1)
    cena_ura   = models.DecimalField(max_digits=6, decimal_places=2)
    aktivno    = models.BooleanField(default=True)

    def __str__(self):
        return self.ime


# REZERVACIJE
class Rezervacija(models.Model):
    class Status(models.TextChoices):
        CAKAJOCA  = 'cakajoca',  'Čakajoča'
        POTRJENA  = 'potrjena',  'Potrjena'
        ZAVRNJENA = 'zavrnjena', 'Zavrnjena'
        PREKLICANA = 'preklicana', 'Preklicana'

    uporabnik  = models.ForeignKey(User, on_delete=models.CASCADE, related_name='rezervacije')
    igrisca    = models.ForeignKey(Igrisca, on_delete=models.CASCADE)
    datum      = models.DateField()
    ura_zacetek = models.TimeField()
    ura_konec   = models.TimeField()
    status     = models.CharField(max_length=20, choices=Status.choices, default=Status.POTRJENA)
    ustvarjena = models.DateTimeField(auto_now_add=True)

    # najem trenerja in opreme
    trener     = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='treningi', limit_choices_to={'role': 'trener'}
    )
    oprema     = models.ManyToManyField(Oprema, blank=True)

    class Meta:
        # prepreci dvojno rezervacijo istega igrišča ob istem času
        unique_together = ['igrisca', 'datum', 'ura_zacetek']

    def __str__(self):
        return f"{self.igrisca} | {self.datum} {self.ura_zacetek} | {self.uporabnik}"