from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from datetime import timedelta
from django.db.models.signals import post_save, m2m_changed
from django.core.mail import send_mail
from django.conf import settings

def winner(s1, s2):
    if s1 == s2:
        return 3
    elif s1 > s2:
        return 1
    else:
        return 2

# Create your models here.
class Player(models.Model):
    name = models.CharField(max_length=200, unique=True)

    user = models.OneToOneField(User)

    @property
    def points(self):
        bets = self.bet_game_set.all()
        points = 0
        for b in bets:
            points = points + b.points
        bets = self.bet_phase_set.all()
        for b in bets:
            points = points + b.points
        return points

    def __unicode__(self):
        return self.name

    @property
    def bet_warnings(self):
        warnings = []
        #check for bet_phases that are urgent
        urgent_bet_phases = [b.phase.name for b in self.bet_phase_set.all() if b.urgent ==  True]
        if len(urgent_bet_phases) != 0:
            warnings.append("Je hebt minder dan 48 uur om de %s in te vullen" % ', '.join(urgent_bet_phases))
        #check for bet_games that are not placed yet for games that will start in 49 hours
        urgent_bet_games = Game.objects.filter(playtime__gt = timezone.now() + timedelta(hours=1), playtime__lt = timezone.now() + timedelta(hours=49)).exclude(pk__in=self.bet_game_set.values_list('game'))
        if len(urgent_bet_games) != 0:
            warnings.append("Je heb minder dan 48 uur om te pronostiekeren op volgende wedstrijden: %s" % ', '.join([str(u.name) for u in urgent_bet_games]))
        return warnings

class Phase(models.Model):
    name = models.CharField(max_length=40)
    nr_teams = models.IntegerField()
    bets_allowed_until = models.DateTimeField()
    order = models.IntegerField()
    score = models.IntegerField()

    def __unicode__(self):
        return unicode(str(self.name) + ": " + ', '.join([str(team) for team in self.team_set.all()]), 'UTF-8')

class Bet_phase(models.Model):
    player = models.ForeignKey(Player)
    phase = models.ForeignKey(Phase)
    points = models.IntegerField(default=0)

    @property
    def complete(self):
        return self.team_set.count() == self.phase.nr_teams

    @property
    def urgent(self):
        if not self.complete and self.phase.bets_allowed_until - timedelta(hours=48) < timezone.now() and self.phase.bets_allowed_until > timezone.now():
            return True
        else:
            return False

    @property
    def bets_changeable(self):
        if self.phase.bets_allowed_until > timezone.now():
            return True
        else:
            return False

    def recalculate_points(self):
        points = 0
        for team in self.team_set.all():
            if team in self.phase.team_set.all():
                points += self.phase.score
        self.points = points
        self.save()

    def __unicode__(self):
        return unicode(str(self.phase.name) + ", betted by " + str(self.player) + ": " + ', '.join([str(team) for team in self.team_set.all()]), 'UTF-8')

class Team(models.Model):
    name = models.CharField(max_length=200, unique=True)
    phases = models.ManyToManyField(Phase, blank=True)
    bet_phases = models.ManyToManyField(Bet_phase)
    still_in_the_running = models.BooleanField(default=True)

    def __unicode__(self):
        return self.name

class Game(models.Model):
    team1 = models.ForeignKey(Team, related_name='team1')
    team2 = models.ForeignKey(Team, related_name='team2')
    playtime = models.DateTimeField()
    game_id = models.IntegerField(primary_key=True)
    score_team1 = models.IntegerField(null=True, blank=True)
    score_team2 = models.IntegerField(null=True, blank=True)
    extra_score_info = models.CharField(max_length=10, blank=True)
    needs_winner = models.BooleanField()
    winner_in_case_of_draw = models.IntegerField(blank=True, null=True)
    gametype = models.CharField(max_length=40, blank=True)

    @property
    def result(self):
        if self.results_are_in:
            result = str(self.score_team1) + " - " + str(self.score_team2)
            if self.extra_score_info != "":
                return result + " (" + self.extra_score_info + ")"
            else:
                return result
        else:
            return ""

    @property
    def winner(self):
        if self.results_are_in:
            if self.score_team1 > self.score_team2:
                return 1
            elif self.score_team2 > self.score_team1:
                return 2
            else:
                if self.needs_winner == True:
                    return self.winner_in_case_of_draw
                else:
                    return 3
        else:
            return 0

    @property
    def bets_changeable(self):
        if self.playtime > timezone.now() + timedelta(hours=1):
            return True
        else:
            return False

    @property
    def results_are_in(self):
        if self.score_team1 != None and self.score_team1 != None:
            if self.score_team1 == self.score_team2 and self.needs_winner == True and self.winner_in_case_of_draw == None:
                return False
            else:
                return True
        else:
            return False

    @property
    def name(self):
        return str(self.team1) + " - " + str(self.team2)

    def __unicode__(self):
        return unicode(str(self.team1) + " - " + str(self.team2) + " (" + str(self.game_id) + ")", 'UTF-8')

class Bet_game(models.Model):
    game = models.ForeignKey(Game)
    betted_score1 = models.IntegerField()
    betted_score2 = models.IntegerField()
    player = models.ForeignKey(Player)
    bettime = models.DateTimeField()
    winner_in_case_of_draw = models.IntegerField(blank=True, null=True)
    points = models.IntegerField(default=0)

    @property
    def winner(self):
        if self.betted_score1 > self.betted_score2:
            return 1
        elif self.betted_score2 > self.betted_score1:
            return 2
        else:
            if self.game.needs_winner == True:
                return self.winner_in_case_of_draw
            else:
                return 3

    def recalculate_points(self):
        points = 0
        if self.winner == self.game.winner:
            if self.betted_score1 == self.game.score_team1 and self.betted_score2 == self.game.score_team2:
                points = 7
            else:
                points = 3
        else:
            points = 0
        self.points = points
        self.save()

    @property
    def betted_result(self):
        ret = str(self.betted_score1) + " - " + str(self.betted_score2)
        if self.game.needs_winner and self.betted_score1 == self.betted_score2:
            ret += " (%s wint)" % ( self.game.team1 if  self.winner_in_case_of_draw == 1 else self.game.team2 )
        return ret

    def __unicode__(self):
        return unicode(str(self.game) + " betted by " + str(self.player), 'UTF-8')

def recalculate_bet_game_points(instance, **kwargs):
    bgs = instance.bet_game_set.all()
    for bg in bgs:
        bg.recalculate_points()

def recalculate_bet_phase_points(instance, action, **kwargs):
    if action == "post_add" or action == "post_clear":
        bfs = instance.bet_phases.all()
        for bf in bfs:
            bf.recalculate_points()

# register the signal
post_save.connect(recalculate_bet_game_points, sender=Game)
m2m_changed.connect(recalculate_bet_phase_points, Team.phases.through)

activation_mail = """
<h3>Je account van de Legkip EK 2016 pronostiek is geactiveerd!</h3>
<p>Gebruikersnaam: name_here</p>
<p>Plaats je pronostieken op https://ek16.nu</p>
<br>
<p>Veel plezier!</p>
"""

def send_activation_mail(instance, created, **kwargs):
    if created:
        send_mail('Activatie Legkip EK 2016 pronostiek', '', settings.DEFAULT_FROM_EMAIL, [instance.user.email], fail_silently=True,
                  html_message=activation_mail.replace('name_here', instance.name))

post_save.connect(send_activation_mail, sender=Player)
