from django.contrib import admin
from django import forms
from .models import Employeur, Employe, Transfert, Reference,HistoriqueAction
from django.contrib.auth.hashers import make_password
from .forms import EmployeurForm 

class EmployeurForm(forms.ModelForm):
    mot_de_passe = forms.CharField(
        label="Mot de passe",
        widget=forms.PasswordInput,
        required=False,
        help_text="Laissez vide pour ne pas changer le mot de passe existant."
    )

    class Meta:
        model = Employeur
        fields = [
            "nom", "rue", "code_postal", "province",
            "telephone", "email", "mot_de_passe",
            "logo", "latitude", "longitude"
        ]

    def save(self, commit=True):
        employeur = super().save(commit=False)
        raw_password = self.cleaned_data.get("mot_de_passe")
        if raw_password:
            employeur.mot_de_passe = make_password(raw_password)
        # 🔹 Assurer que le logo est enregistré
        if self.cleaned_data.get("logo"):
            employeur.logo = self.cleaned_data["logo"]
        if commit:
            employeur.save()
        return employeur


@admin.register(Employeur)
class EmployeurAdmin(admin.ModelAdmin):
    form = EmployeurForm
    list_display = ("nom", "email", "telephone", "province", "code_postal", "logo_tag")
    readonly_fields = ("logo_tag",)
    search_fields = ("nom", "email", "code_postal")

    def logo_tag(self, obj):
        try:
            if obj.logo and hasattr(obj.logo, 'url'):
                return format_html(
                    '<img src="{}" width="50" height="50" style="border-radius:50%; object-fit:cover; border:1px solid #ccc;"/>',
                    obj.logo.url
                )
        except Exception:
            return "-"
        return "-"
    logo_tag.short_description = "Logo"


@admin.register(Employe)
class EmployeAdmin(admin.ModelAdmin):
    list_display = ("nom", "prenom", "poste", "employeur")
    search_fields = ("nom", "prenom", "poste")


@admin.register(Transfert)
class TransfertAdmin(admin.ModelAdmin):
    list_display = (
        "nom_employe",
        "prenom_employe",
        "poste",
        "numero_employe",
        "statut_canadien",
        "date_naissance",
        "nas_masque",
        "ancienne_entreprise",
        "nouvelle_entreprise",
        "date_transfert",
    )

    list_filter = (
        "statut_canadien",
        "ancienne_entreprise",
        "nouvelle_entreprise",
        "date_transfert",
    )

    search_fields = (
        "nom_employe",
        "prenom_employe",
        "numero_employe",
        "nas",
    )

    readonly_fields = ("nas",)

    def nas_masque(self, obj):
        if obj.nas:
            return "••• ••• " + obj.nas[-3:]
        return "—"

    nas_masque.short_description = "NAS"


@admin.register(Reference)
class ReferenceAdmin(admin.ModelAdmin):
    list_display = (
        "nom_employe",
        "prenom_employe",
        "poste",
        "numero_employe",
        "ancienne_entreprise",
        "nouvelle_entreprise",
        "date_reference",
    )
    list_filter = ("ancienne_entreprise", "nouvelle_entreprise", "date_reference")
    search_fields = ("nom_employe", "prenom_employe", "numero_employe")

@admin.register(HistoriqueAction)
class HistoriqueActionAdmin(admin.ModelAdmin):
    list_display = ("type_action", "action", "employeur", "date_action")
    list_filter = ("type_action", "action", "date_action")
    search_fields = ("employeur__nom", "description")
    readonly_fields = ("type_action", "action", "employeur", "description", "date_action")
    ordering = ("-date_action",)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False
