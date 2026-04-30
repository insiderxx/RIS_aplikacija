from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from datetime import date, timedelta, time
import datetime
from .models import Igrisca, Rezervacija, Oprema, User
from .forms import RezervacijaForm, RegistracijaForm

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

    zasedenost = {}
    for r in rezervacije:
        # Označi vse ure ki jih rezervacija pokriva
        zacetek = datetime.datetime.combine(datum, r.ura_zacetek)
        konec = datetime.datetime.combine(datum, r.ura_konec)
        trenutna = zacetek
        while trenutna < konec:
            zasedenost[(r.igrisca_id, trenutna.strftime('%H:%M'))] = r
            trenutna += timedelta(hours=1)

    zdaj = datetime.datetime.now()

    grid_rows = []
    for termin in TERMINI:
        ura_str = termin.strftime('%H:%M')
        termin_dt = datetime.datetime.combine(datum, termin)
        je_preteklost = termin_dt < zdaj

        celice = []
        for ig in igrisca_list:
            rez = zasedenost.get((ig.id, ura_str))
            if je_preteklost:
                stanje = 'preteklost'
            elif rez is None:
                stanje = 'prosto'
            elif request.user.is_authenticated and rez.uporabnik == request.user:
                stanje = 'moje'
            elif rez.status == 'cakajoca':
                stanje = 'cakajoca'
                if request.user.is_authenticated and request.user.je_trener() and rez.trener == request.user:
                    stanje = 'trener_caka'
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

    # prepreci rezervacijo v preteklosti
    if datetime.datetime.combine(datum_obj, ura_obj) < datetime.datetime.now():
        messages.error(request, 'Ne moreš rezervirati termina v preteklosti.')
        return redirect(f'/?datum={datum}')

    if request.method == 'POST':
        form = RezervacijaForm(request.POST)
        if form.is_valid():
            trajanje = int(form.cleaned_data['trajanje'])
            ura_konec = (datetime.datetime.combine(datum_obj, ura_obj) + timedelta(hours=trajanje)).time()

            # preveri vse ure ki jih rezervacija pokriva
            zasedene = []
            for i in range(trajanje):
                ura_preverba = (datetime.datetime.combine(datum_obj, ura_obj) + timedelta(hours=i)).time()
                if Rezervacija.objects.filter(
                    igrisca=igrisca,
                    datum=datum_obj,
                    ura_zacetek=ura_preverba,
                    status__in=['potrjena', 'cakajoca']
                ).exists():
                    zasedene.append(ura_preverba.strftime('%H:%M'))

            # preveri tudi z zasedenostjo
            rezervacije_ta_dan = Rezervacija.objects.filter(
                igrisca=igrisca,
                datum=datum_obj,
                status__in=['potrjena', 'cakajoca']
            )
            for r in rezervacije_ta_dan:
                zacetek = datetime.datetime.combine(datum_obj, r.ura_zacetek)
                konec = datetime.datetime.combine(datum_obj, r.ura_konec)
                for i in range(trajanje):
                    preverba_dt = datetime.datetime.combine(datum_obj, ura_obj) + timedelta(hours=i)
                    if zacetek <= preverba_dt < konec:
                        zasedene.append(preverba_dt.strftime('%H:%M'))

            if zasedene:
                messages.error(request, f'Naslednje ure so zasedene: {", ".join(set(zasedene))}')
            else:
                rez = form.save(commit=False)
                rez.uporabnik = request.user
                rez.igrisca = igrisca
                rez.datum = datum_obj
                rez.ura_zacetek = ura_obj
                rez.ura_konec = ura_konec
                rez.status = Rezervacija.Status.CAKAJOCA if rez.trener else Rezervacija.Status.POTRJENA
                rez.save()
                form.save_m2m()
                messages.success(request, f'Rezervacija uspešna! 🎾 ({trajanje} {"ura" if trajanje == 1 else "uri" if trajanje == 2 else "ure"})')
                return redirect(f'/?datum={datum}')
    else:
        form = RezervacijaForm()

    ura_konec_privzeto = (datetime.datetime.combine(datum_obj, ura_obj) + timedelta(hours=1)).time()

    context = {
        'form': form,
        'igrisca': igrisca,
        'datum': datum_obj,
        'ura': ura,
        'ura_konec': ura_konec_privzeto,
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


def cenik(request):
    igrisca = Igrisca.objects.filter(aktivno=True)
    oprema = Oprema.objects.filter(aktivno=True)
    return render(request, 'cenik.html', {'igrisca': igrisca, 'oprema': oprema})


@login_required
def trener_panel(request):
    if not request.user.je_trener():
        raise PermissionDenied
    cakajoci = Rezervacija.objects.filter(
        trener=request.user,
        status='cakajoca'
    ).select_related('uporabnik', 'igrisca').order_by('datum', 'ura_zacetek')
    potrjeni = Rezervacija.objects.filter(
        trener=request.user,
        status='potrjena',
        datum__gte=date.today()
    ).select_related('uporabnik', 'igrisca').order_by('datum', 'ura_zacetek')
    return render(request, 'trener_panel.html', {'cakajoci': cakajoci, 'potrjeni': potrjeni})


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