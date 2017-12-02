from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, HttpResponseRedirect, Http404
from bets.models import Player, Game, Team, Bet_game, Phase, Bet_phase
from django.contrib.auth.models import Permission, User
from django.contrib.auth import authenticate, login, logout
from django.core.urlresolvers import reverse
from django.utils import timezone
from django.contrib import messages
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.mail import send_mail
from django.conf import settings
import copy
import json

# Create your views here.

GAME_GRID = [{'name': 'Groep A', 'game_ids': [1, 2, 14, 15, 25, 26], 'offset': 1, 'break': 3, 'centered': False},
             {'name': 'Groep B', 'game_ids': [3, 4, 13, 16, 27, 28], 'offset': 1, 'break': 3, 'centered': False},
             {'name': 'Groep C', 'game_ids': [6, 7, 17, 18, 29, 30], 'offset': 1, 'break': 3, 'centered': False},
             {'name': 'Groep D', 'game_ids': [5, 8, 20, 21, 31, 32], 'offset': 1, 'break': 3, 'centered': False},
             {'name': 'Groep E', 'game_ids': [9, 10, 19, 22, 35, 36], 'offset': 1, 'break': 3, 'centered': False},
             {'name': 'Groep F', 'game_ids': [11, 12, 23, 24, 33, 34], 'offset': 1, 'break': 3, 'centered': False},
             {'name': 'Achtstefinales', 'game_ids': [37, 38, 39, 40, 41, 42, 43, 44], 'offset': 0, 'break': 8, 'centered': False},
             {'name': 'Kwartfinales', 'game_ids': [45, 46, 47, 48], 'offset': 0, 'break': 4, 'centered': False},
             {'name': 'Halve Finales', 'game_ids': [49, 50], 'offset': 3, 'break': 2, 'centered': False},
             {'name': 'Finale', 'game_ids': [51], 'offset': 0, 'break': 1, 'centered': True},
            ]

confirmation_mail = """
<h3>Welkom bij de Legkip EK 2016 pronostiek</h3>
<p>Om je inschrijving af te ronden, gelieve 5 euro over te schrijven op BEXXX met in de mededeling je gebruikersnaam.</p>
<p>Van zodra het geld ontvangen is, zal je account worden geactiveerd.  Je ontvangt hiervan een emailbevestiging</p>
<p>De prijzenpot: de winnaar ontvangt 50% van de pot, de nummer 2 ontvangt 30% en de nummer 3 ontvangt nog 20%.</p>
<br>
<p>Veel plezier!</p>
"""

class MyUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def save(self, commit=True):
        user = super(MyUserCreationForm, self).save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user

def register(request):
    if request.method == 'POST':
        form = MyUserCreationForm(request.POST)
        if form.is_valid():
            new_user = form.save()
            #send confirmation email
            send_mail('Inschrijving Legkip EK 2016 pronostiek', '', settings.DEFAULT_FROM_EMAIL, [new_user.email], fail_silently=True,
                       html_message=confirmation_mail)
            send_mail('EK 2016 pronostiek', 'Nieuwe inschrijving: ' + new_user.username, settings.DEFAULT_FROM_EMAIL, ['lode.cools1@gmail.com'], fail_silently=True)
            return HttpResponseRedirect(reverse('bets:confirmation'))
    else:
        form = MyUserCreationForm()
    return render(request, "bets/register.html", {
        'form': form,
    })

def confirmation(request):
    return render(request, "bets/confirmation.html", {})

def home(request):
    #print("IP Address for debug-toolbar: " + request.META['REMOTE_ADDR'])
    player_list_unordered = Player.objects.all()
    player_list = sorted(player_list_unordered, key=lambda x: x.points, reverse=True)[:5]
    next_games = Game.objects.filter(playtime__gte=timezone.now()).order_by('playtime')[:5]
    prev_games = Game.objects.filter(playtime__lte=timezone.now()).order_by('playtime').reverse()[:5]
    context = {
        'player_list': player_list,
        'next_games': next_games,
        'prev_games': prev_games,
    }
    return render(request, 'bets/home.html', context)

def index(request):
    player_list_unordered = Player.objects.all()
    player_list = sorted(player_list_unordered, key=lambda x: x.points, reverse=True)
    context = {
        'player_list': player_list,
    }
    return render(request, 'bets/index.html', context)

def player_login(request):
    logout(request)
    username = password = ''
    if request.POST:
        player_name = request.POST['player_name']
        current_page = request.POST['current_page']
        try:
            player = Player.objects.get(name=player_name)
        except Player.DoesNotExist:
            messages.error(request, 'Ongekende of nog niet geactiveerde gebruiker')
            return HttpResponseRedirect(current_page)
        username = player.user.username
        password = request.POST['password']
        user = authenticate(username = username, password = password)
        if user is not None:
            login(request, user)
        else:
            messages.error(request, "Probleem om deze gebruiker aan te melden. Correct wachtwoord?")
            return HttpResponseRedirect(current_page)
    return HttpResponseRedirect(current_page)

def player_logout(request):
    logout(request)
    current_page = request.POST['current_page']
    return HttpResponseRedirect(current_page)

def change_bet(request):
    if request.POST:
        try:
            player = Player.objects.get(name=request.POST['player'])
            game = Game.objects.get(game_id=int(request.POST['game']))
            score = request.POST['score']
            t = score.split('(')
            s = t[0].split('-')
            score1 = int(s[0].replace(' ', ''))
            score2 = int(s[1].replace(' ', ''))
            winner_in_case_of_draw = None
            if game.needs_winner and score1 == score2:
                try:
                    winner_in_case_of_draw = int(t[1][0])
                    if winner_in_case_of_draw not in [1, 2]:
                        ajax_vars = {'success': False, 'error': "Deze wedstrijd heeft een winnaar nodig! Geef tussen haakjes aan welk team zal winnen. Vb: 1-1 (2)"}
                        return HttpResponse(json.dumps(ajax_vars), content_type='application/javascript')
                except:
                    ajax_vars = {'success': False, 'error': "Deze wedstrijd heeft een winnaar nodig! Geef tussen haakjes aan welk team zal winnen. Vb: 1-1 (2)"}
                    return HttpResponse(json.dumps(ajax_vars), content_type='application/javascript')
        except:
            ajax_vars = {'success': False, 'error': "Geen geldige pronostiek ingegeven!"}
            return HttpResponse(json.dumps(ajax_vars), content_type='application/javascript')

        #verify if the bets are still changeable at the moment of posting
        if not request.user.is_authenticated() or not game.bets_changeable or request.user.player != player:
            ajax_vars = {'success': False, 'error': "Je bent niet meer ingelogd of de tijd is verstreken om te pronostiekeren"}
            return HttpResponse(json.dumps(ajax_vars), content_type='application/javascript')

        betlist = Bet_game.objects.filter(game=game, player=player)
        if len(betlist) > 0:
            #change the existing bet
            bet = betlist[0]
            bet.betted_score1 = score1
            bet.betted_score2 = score2
            bet.winner_in_case_of_draw = winner_in_case_of_draw
            bet.bettime = timezone.now()
            bet.save()
        else:
            #create the bet
            bet = Bet_game(player=player, bettime=timezone.now(), betted_score1=score1,
                betted_score2=score2, game=game, winner_in_case_of_draw=winner_in_case_of_draw)
            bet.save()
        ajax_vars = {'success': True, 'error': "", 'new_bet': bet.betted_result}
        return HttpResponse(json.dumps(ajax_vars), content_type='application/javascript')
    else:
        raise Http404

def player(request, player_name):
    player = get_object_or_404(Player, name = player_name)

    game_grid_filled = copy.deepcopy(GAME_GRID)
    for group in game_grid_filled:
        group['games'] = []
        for id in group['game_ids']:
            game = Game.objects.filter(game_id = id).first()
            bet = game.bet_game_set.filter(player = player).first() if game != None else None
            group['games'].append({'game': game, 'bet': bet})
    context = {
        'game_grid': game_grid_filled,
    }

    #create bet_phases for player if it doesnt exist yet
    for phase in Phase.objects.all():
        Bet_phase.objects.get_or_create(player=player, phase=phase)

    phase_bets = []
    for b in Bet_phase.objects.filter(player = player).order_by('phase__order'):
        phase = {'phase_bet': b,
                 'teams': list(b.team_set.all()) + list(Team.objects.filter(name='leeg'))*(b.phase.nr_teams - b.team_set.count()),
                 'team_choices': list(set(Team.objects.exclude(name='leeg')) - set(b.team_set.all())),
                 'teams_chosen': b.team_set.all(),
                }
        phase_bets.append(phase)

    context = {
        'game_grid': game_grid_filled,
        'player': player,
        'phase_bets': phase_bets,
    }
    return render(request, 'bets/player.html', context)

def game(request, game_id):
    game = get_object_or_404(Game, game_id = game_id)
    bets = game.bet_game_set.all()
    bets_sorted = sorted(bets, key=lambda x: x.points, reverse=True)
    context = {
        'game': game,
        'bets': bets_sorted,
    }
    return render(request, 'bets/game.html', context)

def game_overview(request):
    game_grid_filled = copy.deepcopy(GAME_GRID)
    for group in game_grid_filled:
        group['games'] = [Game.objects.filter(game_id = id).first() for id in group['game_ids']]
    context = {
        'game_grid': game_grid_filled,
    }
    return render(request, 'bets/game_overview.html', context)

def phases(request):
    context = {
        'phases': Phase.objects.order_by('order'),
    }
    return render(request, 'bets/phases.html', context)

def change_phase_bet(request):
    if request.POST:
        try:
            player = Player.objects.get(name=request.POST['player'])
            bet_phase = Bet_phase.objects.get(pk=request.POST['phase-bet'])
            old_team = Team.objects.get(pk=request.POST['old-team'])
            new_team = Team.objects.get(pk=request.POST['new-team'])
        except:
            ajax_vars = {'success': False, 'error': "Geen geldige ingave!"}
            return HttpResponse(json.dumps(ajax_vars), content_type='application/javascript')

        #verify if the bets are still changeable at the moment of posting
        if not request.user.is_authenticated() or not bet_phase.bets_changeable or request.user.player != player:
            ajax_vars = {'success': False, 'error': "Je bent niet meer ingelogd of de tijd is verstreken om te pronostiekeren"}
            return HttpResponse(json.dumps(ajax_vars), content_type='application/javascript')

        bet_phase.team_set.remove(old_team)
        bet_phase.team_set.add(new_team)

        ajax_vars = {'success': True, 'error': "", 'new_team': new_team.name}
        return HttpResponse(json.dumps(ajax_vars), content_type='application/javascript')
    else:
        raise Http404

