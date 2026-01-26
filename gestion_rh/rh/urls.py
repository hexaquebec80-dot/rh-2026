from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("register/", views.register, name="register"),
    path("login/", views.login, name="login"),
    path("profil/", views.profil_employeur, name="profil_employeur"),
    path("admin_dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("transfert/envoyer/", views.envoyer_transfert, name="envoyer_transfert"),
    path("reference/envoyer/", views.envoyer_reference, name="envoyer_reference"),
    path('profil/modifier/<int:employeur_id>/', views.modifier_profil, name='modifier_profil'),
    path("historique/", views.historique_employeur, name="historique_employeur"),
    path('mot-de-passe-oublie/', views.mot_de_passe_oublie, name='mot_de_passe_oublie'),
    path('verification-code/', views.verification_code, name='verification_code'),
    path('nouveau-mot-de-passe/', views.nouveau_mot_de_passe, name='nouveau_mot_de_passe'),
    path("profil/modifier/<int:employeur_id>/", views.modifier_profil, name="modifier_profil"),
    path('supprimer_transfert/<int:id>/', views.supprimer_transfert, name='supprimer_transfert'),
    path('supprimer_reference/<int:id>/', views.supprimer_reference, name='supprimer_reference'),
    path('transfert/<int:id>/accepter/', views.accepter_transfert, name='accepter_transfert'),
    path('transfert/<int:id>/refuser/', views.refuser_transfert, name='refuser_transfert'),
    path('reference/<int:id>/repondre/', views.repondre_reference, name='repondre_reference'),
    path('choisir-adresse/', views.choisir_adresse, name='choisir_adresse'),
    path('logout/', views.logout_view, name='logout')
    
    
]
