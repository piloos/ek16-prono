from django.contrib import admin
from bets.models import Team, Player, Game, Bet_game, Phase, Bet_phase
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

# Register your models here.

def recalculate_bet_phase_points(modeladmin, request, queryset):
    for q in queryset:
        for bf in q.bet_phase_set.all():
            bf.recalculate_points()

def recalculate_bet_game_points(modeladmin, request, queryset):
    for q in queryset:
        for bg in q.bet_game_set.all():
            bg.recalculate_points()

def clear_points(modeladmin, request, queryset):
    queryset.update(points=0)

class PlayerAdmin(admin.ModelAdmin):
    fields = ['name', 'user']
    list_display = ['name', 'points']

class GameAdmin(admin.ModelAdmin):
    list_display = ['game_id', 'team1', 'team2', 'playtime', 'result', 'gametype', 'needs_winner']
    actions = [recalculate_bet_game_points]

class PhaseAdmin(admin.ModelAdmin):
    actions = [recalculate_bet_phase_points]

class Bet_phaseAdmin(admin.ModelAdmin):
    actions = [clear_points]

class Bet_gameAdmin(admin.ModelAdmin):
    list_display = ['game', 'player', 'bettime', 'betted_result', 'points']
    actions = [clear_points]

class TeamAdmin(admin.ModelAdmin):
    fields = ['name', 'still_in_the_running', 'phases']

admin.site.register(Team, TeamAdmin)
admin.site.register(Player, PlayerAdmin)
admin.site.register(Game, GameAdmin)
admin.site.register(Bet_game, Bet_gameAdmin)
admin.site.register(Phase, PhaseAdmin)
admin.site.register(Bet_phase, Bet_phaseAdmin)
