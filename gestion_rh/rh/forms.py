from django import forms
from .models import Transfert, Reference
from .models import Employeur



class EmployeurForm(forms.ModelForm):
    mot_de_passe = forms.CharField(
        label="Mot de passe",
        widget=forms.PasswordInput,
        required=False,
        help_text="Laissez vide pour ne pas changer le mot de passe existant."
    )

    class Meta:
        model = Employeur
        fields = ["nom", "rue", "code_postal", "province", "telephone", "email", "mot_de_passe", "logo", "latitude", "longitude"]

    def save(self, commit=True):
        employeur = super().save(commit=False)
        raw_password = self.cleaned_data.get("mot_de_passe")
        if raw_password:
            employeur.mot_de_passe = make_password(raw_password)
        if commit:
            employeur.save()
        return employeur



# 🔹 Formulaire de Transfert d'Employé
class TransfertForm(forms.ModelForm):
    class Meta:
        model = Transfert
        fields = [
            "nom_employe",
            "prenom_employe",
            "poste",
            "numero_employe",
            "ancienne_entreprise",
            "nouvelle_entreprise",
            "date_transfert",
            "message",
        ]
        widgets = {
            "date_transfert": forms.DateInput(attrs={"type": "date"}),
            "message": forms.Textarea(attrs={"rows": 4}),
        }


# 🔹 Formulaire de Référence d'Employé
class ReferenceForm(forms.ModelForm):
    class Meta:
        model = Reference
        fields = [
            "nom_employe",
            "prenom_employe",
            "poste",
            "numero_employe",
            "ancienne_entreprise",
            "nouvelle_entreprise",
            "message",
        ]
        widgets = {
            "message": forms.Textarea(attrs={"rows": 4}),
        }
