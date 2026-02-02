from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone
from django.core.exceptions import ValidationError

PROVINCES_CANADA = [
    ("QC", "Québec"),
    ("ON", "Ontario"),
    ("BC", "Colombie-Britannique"),
    ("AB", "Alberta"),
    ("MB", "Manitoba"),
    ("SK", "Saskatchewan"),
    ("NS", "Nouvelle-Écosse"),
    ("NB", "Nouveau-Brunswick"),
    ("PE", "Île-du-Prince-Édouard"),
    ("NL", "Terre-Neuve-et-Labrador"),
    ("NT", "Territoires du Nord-Ouest"),
    ("NU", "Nunavut"),
    ("YT", "Yukon"),
]

class Employeur(models.Model):
    nom = models.CharField(max_length=150)

    # Adresse sécurisée
    rue = models.CharField(
        max_length=200,
        validators=[RegexValidator(regex=r"^[0-9A-Za-zÀ-ÿ\s,'\-]+$", message="Adresse invalide")]
    )

    # Code postal canadien
    code_postal = models.CharField(
        max_length=7,
        validators=[RegexValidator(regex=r"^[A-Za-z]\d[A-Za-z][ -]?\d[A-Za-z]\d$", message="Code postal canadien invalide (ex: H1A 2B3)")]
    )

    # Province canadienne
    province = models.CharField(max_length=2, choices=PROVINCES_CANADA)

    # Téléphone canadien
    telephone = models.CharField(
        max_length=20,
        validators=[RegexValidator(regex=r"^\+?1?\s?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}$", message="Numéro de téléphone canadien invalide")]
    )

    email = models.EmailField(unique=True)
    mot_de_passe = models.CharField(max_length=128)

    # Logo entreprise
    logo = models.ImageField(upload_to="logos/", null=True, blank=True)
    

    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)


    def set_password(self, raw_password):
        self.mot_de_passe = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.mot_de_passe)

    def __str__(self):
        return self.nom


class Employe(models.Model):
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    poste = models.CharField(max_length=150)
    numero = models.CharField(max_length=50, default="TEMP")
    employeur = models.ForeignKey("Employeur", on_delete=models.CASCADE, related_name="employes")

    def __str__(self):
        return f"{self.nom} {self.prenom} ({self.numero})"



class Transfert(models.Model):

    TYPE_OPERATION_CHOICES = [
        ("transfert", "Transfert"),
        ("embauche", "Embauche"),
    ]

    STATUT_CHOICES = [
        ("canadien", "Canadien / Résident permanent"),
        ("etranger", "Autre nationalité"),
    ]

    # 🔹 NOUVEAU CHAMP
    type_operation = models.CharField(
        max_length=10,
        choices=TYPE_OPERATION_CHOICES,
        default="transfert"
    )

    nom_employe = models.CharField(max_length=100)
    prenom_employe = models.CharField(max_length=100)
    poste = models.CharField(max_length=150)

    numero_employe = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )

    date_naissance = models.DateField(null=True, blank=True)

    statut_canadien = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES
    )

    nas = models.CharField(
        max_length=11,
        blank=True,
        null=True,
        help_text="NAS requis uniquement si autre nationalité"
    )

    ancienne_entreprise = models.ForeignKey(
        Employeur,
        on_delete=models.CASCADE,
        related_name="transferts_envoyes"
    )

    nouvelle_entreprise = models.ForeignKey(
        Employeur,
        on_delete=models.CASCADE,
        related_name="transferts_recus"
    )

    date_transfert = models.DateField()
    message = models.TextField(blank=True, null=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    supprime_pour_employeur = models.BooleanField(default=False)

    statut = models.CharField(
        max_length=20,
        choices=[
            ("en_attente", "En attente"),
            ("accepte", "Accepté"),
            ("refuse", "Refusé"),
        ],
        default="en_attente",
    )

    motif_refus = models.TextField(blank=True, null=True)

    def clean(self):
        """Validation métier"""
        # NAS obligatoire si étranger
        if self.statut_canadien == "etranger" and not self.nas:
            raise ValidationError(
                {"nas": "Le NAS est obligatoire pour une autre nationalité."}
            )

        # Numéro employé obligatoire uniquement pour un transfert
        if self.type_operation == "transfert" and not self.numero_employe:
            raise ValidationError(
                {"numero_employe": "Le numéro employé est obligatoire pour un transfert."}
            )

        # Numéro employé interdit pour une embauche
        if self.type_operation == "embauche" and self.numero_employe:
            raise ValidationError(
                {"numero_employe": "Le numéro employé ne doit pas être renseigné pour une embauche."}
            )

    def __str__(self):
        return (
            f"{self.nom_employe} {self.prenom_employe} "
            f"({self.get_type_operation_display()}) ➝ "
            f"{self.nouvelle_entreprise.nom}"
        )


class Reference(models.Model):
    nom_employe = models.CharField(max_length=100)
    prenom_employe = models.CharField(max_length=100)
    poste = models.CharField(max_length=150)
    numero_employe = models.CharField(max_length=50)

    ancienne_entreprise = models.ForeignKey(
        Employeur, on_delete=models.CASCADE, related_name="references_donnees"
    )
    nouvelle_entreprise = models.ForeignKey(
        Employeur, on_delete=models.CASCADE, related_name="references_recues"
    )

    date_reference = models.DateField(auto_now_add=True)
    message = models.TextField(blank=True, null=True)

    # ✅ suppression logique côté employeur
    supprime_pour_employeur = models.BooleanField(default=False)

    # ✅ réponse possible de l’entreprise destinataire
    reponse_employeur = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Référence : {self.nom_employe} {self.prenom_employe} → {self.nouvelle_entreprise.nom}"


class HistoriqueAction(models.Model):

    TYPE_ACTION_CHOICES = [
        ("transfert", "Transfert"),
        ("reference", "Référence"),
        ("profil", "Profil"),
    ]

    ACTION_CHOICES = [
        ("cree", "Créé"),
        ("modifie", "Modifié"),
        ("supprime", "Supprimé"),
    ]

    employeur = models.ForeignKey(
        Employeur,
        on_delete=models.CASCADE,
        related_name="historiques"
    )

    type_action = models.CharField(
        max_length=20,
        choices=TYPE_ACTION_CHOICES
    )

    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES
    )

    description = models.TextField()

    date_action = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Historique"
        verbose_name_plural = "Historiques"

    def __str__(self):
        return f"{self.get_type_action_display()} - {self.get_action_display()}"
