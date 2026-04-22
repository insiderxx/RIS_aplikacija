from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from datetime import date, timedelta, time
import datetime
from .models import Igrisca, Rezervacija, Oprema, User
from .forms import RezervacijaForm, RegistracijaForm

# Termini od 8:00 do 21:00 vsako uro
TERMINI = [time(h, 0) for h in range(8, 22)]

def grid(request):
    datum_str = request.GET.get('datum')
    try:
        datum = date.fromisoformat(datum_str)
    except (TypeError, ValueError):
        datum = date.today()

    igrisca_list = Igrisca.objects.filter(aktivno=True)
    rezervacije = Rezervacija.objects.filter(
        datum=datum,
        status__in=['potrjena', 'cakajoca']
    ).select_related('uporabnik', 'igrisca')

    # Slovar: {(igrisca_id, 'HH:MM'): rezervacija}
    zasedenost = {}
    for r in rezervacije:
        zasedenost[(r.igrisca_id, r.ura_zacetek.strftime('%H:%M'))] = r

    # Zgradimo grid kot seznam vrstic — template bo samo iteriral
    grid_rows = []
    for termin in TERMINI:
        ura_str = termin.strftime('%H:%M')
        celice = []
        for ig in igrisca_list:
            rez = zasedenost.get((ig.id, ura_str))
            if rez is None:
                stanje = 'prosto'
            elif request.user.is_authenticated and rez.uporabnik == request.user:
                stanje = 'moje'
            elif rez.status == 'cakajoca':
                stanje = 'cakajoca'
            else:
                stanje = 'zasedeno'
            celice.append({
                'igrisca': ig,
                'ura_str': ura_str,
                'stanje': stanje,
                'rezervacija': rez,
            })
        grid_rows.append({'termin': termin, 'ura_str': ura_str, 'celice': celice})

    koledar = [date.today() + timedelta(days=i) for i in range(14)]

    context = {
        'datum': datum,
        'igrisca': igrisca_list,
        'grid_rows': grid_rows,
        'koledar': koledar,
    }
    return render(request, 'grid.html', context)
@login_required
def rezerviraj(request, igrisca_id, datum, ura):
    igrisca = get_object_or_404(Igrisca, id=igrisca_id)
    datum_obj = date.fromisoformat(datum)
    ura_obj = datetime.datetime.strptime(ura, '%H:%M').time()
    ura_konec = (datetime.datetime.combine(datum_obj, ura_obj) + timedelta(hours=1)).time()

    # Preveri če je termin že zaseden
    if Rezervacija.objects.filter(igrisca=igrisca, datum=datum_obj, ura_zacetek=ura_obj,
                                   status__in=['potrjena', 'cakajoca']).exists():
        messages.error(request, 'Ta termin je žal že zaseden.')
        return redirect(f'/?datum={datum}')

    if request.method == 'POST':
        form = RezervacijaForm(request.POST)
        if form.is_valid():
            rez = form.save(commit=False)
            rez.uporabnik = request.user
            rez.igrisca = igrisca
            rez.datum = datum_obj
            rez.ura_zacetek = ura_obj
            rez.ura_konec = ura_konec
            # Če je izbran trener, status čaka na potrditev
            if rez.trener:
                rez.status = Rezervacija.Status.CAKAJOCA
            else:
                rez.status = Rezervacija.Status.POTRJENA
            rez.save()
            form.save_m2m()
            messages.success(request, 'Rezervacija uspešna! 🎾')
            return redirect(f'/?datum={datum}')
    else:
        form = RezervacijaForm()

    context = {
        'form': form,
        'igrisca': igrisca,
        'datum': datum_obj,
        'ura': ura,
        'ura_konec': ura_konec,
        'oprema_list': Oprema.objects.filter(aktivno=True),
    }
    return render(request, 'rezerviraj.html', context)


@login_required
def preklic(request, rezervacija_id):
    rez = get_object_or_404(Rezervacija, id=rezervacija_id, uporabnik=request.user)
    rez.status = Rezervacija.Status.PREKLICANA
    rez.save()
    messages.success(request, 'Rezervacija preklicana.')
    return redirect('moje_rezervacije')


@login_required
def moje_rezervacije(request):
    rezervacije = Rezervacija.objects.filter(
        uporabnik=request.user
    ).exclude(status='preklicana').order_by('datum', 'ura_zacetek')
    return render(request, 'moje_rezervacije.html', {'rezervacije': rezervacije})


def prijava(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('grid')
        else:
            messages.error(request, 'Napačno uporabniško ime ali geslo.')
    return render(request, 'prijava.html')


def odjava(request):
    logout(request)
    return redirect('prijava')


def registracija(request):
    if request.method == 'POST':
        form = RegistracijaForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('grid')
    else:
        form = RegistracijaForm()
    return render(request, 'registracija.html', {'form': form})

from django.core.exceptions import PermissionDenied

@login_required
def trener_panel(request):
    if not request.user.je_trener():
        raise PermissionDenied

    # Čakajoči termini — trener mora potrditi ali zavrniti
    cakajoci = Rezervacija.objects.filter(
        trener=request.user,
        status='cakajoca'
    ).select_related('uporabnik', 'igrisca').order_by('datum', 'ura_zacetek')

    # Potrjeni prihodnji termini
    potrjeni = Rezervacija.objects.filter(
        trener=request.user,
        status='potrjena',
        datum__gte=date.today()
    ).select_related('uporabnik', 'igrisca').order_by('datum', 'ura_zacetek')

    return render(request, 'trener_panel.html', {
        'cakajoci': cakajoci,
        'potrjeni': potrjeni,
    })


@login_required
def potrdi_trening(request, rezervacija_id):
    if not request.user.je_trener():
        raise PermissionDenied
    rez = get_object_or_404(Rezervacija, id=rezervacija_id, trener=request.user)
    rez.status = Rezervacija.Status.POTRJENA
    rez.save()
    messages.success(request, f'Trening {rez.datum} ob {rez.ura_zacetek.strftime("%H:%M")} potrjen! ✅')
    return redirect('trener_panel')


@login_required
def zavrni_trening(request, rezervacija_id):
    if not request.user.je_trener():
        raise PermissionDenied
    rez = get_object_or_404(Rezervacija, id=rezervacija_id, trener=request.user)
    rez.status = Rezervacija.Status.ZAVRNJENA
    rez.save()
    messages.warning(request, f'Trening {rez.datum} ob {rez.ura_zacetek.strftime("%H:%M")} zavrnjen.')
    return redirect('trener_panel')