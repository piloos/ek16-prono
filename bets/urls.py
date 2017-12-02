from django.conf.urls import patterns, url

from bets import views

urlpatterns = [
    url(r'^$', views.home, name='home'),
    url(r'^players/$', views.index, name='players'),
    url(r'^player/(?P<player_name>[\w-]+)/$', views.player, name='player'),
    url(r'^game/(?P<game_id>\d+)/$', views.game, name='game'),
    url(r'^games$', views.game_overview, name='game_overview'),
    url(r'^player/player_login$', views.player_login, name='player_login'),
    url(r'^player/player_logout$', views.player_logout, name='player_logout'),
    url(r'^change_bet$', views.change_bet, name='change_bet'),
    url(r'^change_phase_bet$', views.change_phase_bet, name='change_phase_bet'),
    url(r'^phases$', views.phases, name='phases'),
    url(r'^register$', views.register, name='register'),
    url(r'^confirmation$', views.confirmation, name='confirmation'),
]
