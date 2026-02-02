from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Employeur, Employe, Transfert, Reference
from django import forms
import re
import requests
from datetime import datetime
from django.contrib.auth.decorators import login_required
from .forms import TransfertForm, ReferenceForm
from .forms import EmployeurForm
from django.contrib.auth.hashers import check_password
from random import randint
from django.core.mail import send_mail
from django.contrib.auth.hashers import make_password
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.core.mail import send_mail
from django.conf import settings
from django.core.mail import EmailMessage
from django.utils import timezone
from .models import HistoriqueAction
from django.db.models import Q
from django.utils.timezone import now
from django.db.models import Count
from django.db.models.functions import TruncMonth
import re



def index(request):
    return render(request, "index.html")
    
def register(request):
    if request.method == "POST":
        nom = request.POST.get("nom", "").strip()
        rue = request.POST.get("rue", "").strip()
        code_postal = request.POST.get("code_postal", "").upper().replace(" ", "")
        province = request.POST.get("province", "").strip()
        telephone = request.POST.get("telephone", "").strip()
        email = request.POST.get("email", "").lower().strip()
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")

        logo = request.FILES.get("logo")

        # ✅ Champs obligatoires (SANS GOOGLE)
        if not all([nom, rue, code_postal, province, telephone, email, password, confirm_password]):
            messages.error(request, "Tous les champs sont obligatoires.")
            return redirect("register")

        if password != confirm_password:
            messages.error(request, "Les mots de passe ne correspondent pas.")
            return redirect("register")

        if len(password) < 6:
            messages.error(request, "Le mot de passe doit contenir au moins 6 caractères.")
            return redirect("register")

        if Employeur.objects.filter(email=email).exists():
            messages.error(request, "Cet email est déjà utilisé.")
            return redirect("register")

        employeur = Employeur(
            nom=nom,
            rue=rue,
            code_postal=code_postal,
            province=province,
            telephone=telephone,
            email=email,
        )

        employeur.set_password(password)

        if logo:
            employeur.logo = logo

        try:
            employeur.full_clean()
            employeur.save()
        except ValidationError as e:
            for field, errors in e.message_dict.items():
                for error in errors:
                    messages.error(request, error)
            return redirect("register")

        messages.success(request, f"✅ Inscription réussie ! Bienvenue {nom}.")
        return redirect("login")

    return render(request, "register.html")




def login(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "").strip()

        # Vérifier si les champs sont remplis
        if not email or not password:
            messages.error(request, "Veuillez entrer votre email et votre mot de passe.")
            return redirect("login")

        try:
            # Chercher l'employeur
            employeur = Employeur.objects.get(email=email)

            # Vérifier le mot de passe haché
            if check_password(password, employeur.mot_de_passe):
                # Connexion réussie → stocker l'ID en session
                request.session["employeur_id"] = employeur.id
                messages.success(request, f"Bienvenue {employeur.nom} 👋")
                return redirect("profil_employeur")
            else:
                messages.error(request, "Mot de passe incorrect ❌")
                return redirect("login")

        except Employeur.DoesNotExist:
            messages.error(request, "Aucun compte trouvé avec cet email.")
            return redirect("login")

    return render(request, "login.html")


def profil_employeur(request):
    employeur_id = request.session.get("employeur_id")
    if not employeur_id:
        return redirect("login")

    employeur = get_object_or_404(Employeur, id=employeur_id)

    # ===============================
    # 🔹 MISE À JOUR DU PROFIL
    # ===============================
    if request.method == "POST":
        employeur.nom = request.POST.get("nom", employeur.nom)
        employeur.rue = request.POST.get("rue", employeur.rue)
        employeur.code_postal = request.POST.get("code_postal", employeur.code_postal)
        employeur.province = request.POST.get("province", employeur.province)
        employeur.telephone = request.POST.get("telephone", employeur.telephone)
        employeur.email = request.POST.get("email", employeur.email)

        if request.POST.get("mot_de_passe"):
            employeur.set_password(request.POST.get("mot_de_passe"))

        if request.FILES.get("logo"):
            employeur.logo = request.FILES.get("logo")

        employeur.save()

        # 🔹 Historique PROFIL
        HistoriqueAction.objects.create(
            type_action="profil",
            action="modifie",
            employeur=employeur,
            description="Profil de l’entreprise modifié",
            date_action=timezone.now()
        )

        messages.success(request, "Profil mis à jour avec succès")

    # ===============================
    # 🔹 TRANSFERTS (AFFICHAGE NORMAL)
    # ===============================
    transferts_envoyes = Transfert.objects.filter(
        ancienne_entreprise=employeur,
        supprime_pour_employeur=False
    )

    transferts_recus = Transfert.objects.filter(
        nouvelle_entreprise=employeur,
        supprime_pour_employeur=False
    )

    # ===============================
    # 🔹 INFOS PERSONNELLES EMPLOYÉ ✅ ICI
    # ===============================
    date_naissance_str = request.POST.get("date_naissance")
    statut_canadien = request.POST.get("statut_canadien")
    nas = request.POST.get("nas", "").strip()

    if date_naissance_str:
        try:
            employeur.date_naissance = datetime.strptime(
                date_naissance_str, "%Y-%m-%d"
            ).date()
        except ValueError:
            messages.error(
                request,
                "❌ Format de date de naissance invalide."
            )
            return redirect("profil_employeur")

    if statut_canadien:
        employeur.statut_canadien = statut_canadien

    if statut_canadien == "etranger":
        if not nas:
            messages.error(
                request,
                "❌ Le NAS est obligatoire pour une autre nationalité."
            )
            return redirect("profil_employeur")

        if not re.fullmatch(r"\d{3}\s?\d{3}\s?\d{3}", nas):
            messages.error(
                request,
                "❌ Format du NAS invalide (123 456 789)."
            )
            return redirect("profil_employeur")

        employeur.nas = nas
    else:
        employeur.nas = None
    

    # ===============================
    # 🔹 RÉFÉRENCES (AFFICHAGE NORMAL)
    # ===============================
    references_envoyees = Reference.objects.filter(
        ancienne_entreprise=employeur
    )

    references_recues = Reference.objects.filter(
        nouvelle_entreprise=employeur
    )

    transferts_envoyes = Transfert.objects.filter(
        ancienne_entreprise=employeur,
        supprime_pour_employeur=False
    ).order_by("-date_transfert")

    transferts_recus = Transfert.objects.filter(
        nouvelle_entreprise=employeur,
        supprime_pour_employeur=False
    ).order_by("-date_transfert")

    # ===============================
    # 🔹 RÉFÉRENCES (SANS SUPPRIMÉS) ✅ CORRECTION ICI
    # ===============================
    references_envoyees = Reference.objects.filter(
        ancienne_entreprise=employeur,
        supprime_pour_employeur=False
    ).order_by("-date_reference")

    references_recues = Reference.objects.filter(
        nouvelle_entreprise=employeur,
        supprime_pour_employeur=False
    ).order_by("-date_reference")

    # ===============================
    # 📊 STATISTIQUES PAR MOIS (GRAPHES)
    # ===============================
    references_stats = (
        Reference.objects
        .filter(ancienne_entreprise=employeur)
        .annotate(month=TruncMonth("date_reference"))
        .values("month")
        .annotate(total=Count("id"))
        .order_by("month")
    )

    transferts_stats = (
        Transfert.objects
        .filter(ancienne_entreprise=employeur)
        .annotate(month=TruncMonth("date_transfert"))
        .values("month")
        .annotate(total=Count("id"))
        .order_by("month")
    )


    # ===============================
    # 🔹 HISTORIQUE GLOBAL (MÊME SUPPRIMÉS)
    # ===============================
    historiques = HistoriqueAction.objects.filter(
        employeur=employeur
    ).order_by("-date_action")

    return render(request, "profil_employeur.html", {
        "employeur": employeur,

        "transferts_envoyes": transferts_envoyes,
        "transferts_recus": transferts_recus,

        "references_envoyees": references_envoyees,
        "references_recues": references_recues,

        # 🔹 HISTORIQUE FINAL
        "historiques": historiques,
    })







def admin_dashboard(request):
    employeurs = Employeur.objects.all()
    employes = Employe.objects.all()
    transferts = Transfert.objects.all()
    references = Reference.objects.all()

    return render(request, "admin_dashboard.html", {
        "employeurs": employeurs,
        "employes": employes,
        "transferts": transferts,
        "references": references,
    })



class EmployeurForm(forms.Form):
    code_postal = forms.CharField(
        max_length=7,
        label="Code postal",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Ex: G7S 5A9"})
    )

    def clean_code_postal(self):
        cp = self.cleaned_data['code_postal'].strip().upper()
        pattern = r'^[A-Z]\d[A-Z]\s?\d[A-Z]\d$'
        if not re.match(pattern, cp):
            raise forms.ValidationError("Veuillez entrer un code postal canadien valide (ex: G7S 5A9).")
        return cp



from datetime import datetime
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Employeur, Transfert

def envoyer_transfert(request):
    employeur_id = request.session.get("employeur_id")
    if not employeur_id:
        messages.error(request, "Session expirée.")
        return redirect("login")

    employeur_connecte = get_object_or_404(Employeur, id=employeur_id)

    if request.method == "POST":
        # 🔹 Données POST
        type_operation = request.POST.get("type_operation")
        nom_employe = request.POST.get("nom_employe", "").strip()
        prenom_employe = request.POST.get("prenom_employe", "").strip()
        poste = request.POST.get("poste", "").strip()
        numero_employe = request.POST.get("numero_employe", "").strip()
        nouvelle_entreprise_nom = request.POST.get("nouvelle_entreprise", "").strip()
        date_transfert_str = request.POST.get("date_transfert", "")
        date_naissance_str = request.POST.get("date_naissance", "")
        statut_canadien = request.POST.get("statut_canadien")
        nas = request.POST.get("nas", "").strip()
        message_text = request.POST.get("message", "").strip()

        # 🔴 Validation de base
        if not all([
            type_operation, nom_employe, prenom_employe, poste,
            nouvelle_entreprise_nom, date_transfert_str,
            date_naissance_str, statut_canadien
        ]):
            messages.error(request, "❌ Tous les champs obligatoires doivent être remplis.")
            return redirect("envoyer_transfert")

        # 🔴 NAS obligatoire si étranger
        if statut_canadien == "etranger" and not nas:
            messages.error(request, "❌ Le NAS est obligatoire pour une autre nationalité.")
            return redirect("envoyer_transfert")

        # 🔴 Gestion numéro employé
        if type_operation == "embauche":
            numero_employe = None

        elif type_operation == "transfert":
            if not numero_employe:
                messages.error(
                    request,
                    "❌ Le numéro employé est obligatoire pour un transfert."
                )
                return redirect("envoyer_transfert")

            if Transfert.objects.filter(numero_employe=numero_employe).exists():
                messages.error(
                    request,
                    "❌ Numéro employé déjà utilisé."
                )
                return redirect("envoyer_transfert")
        else:
            messages.error(request, "❌ Type d’opération invalide.")
            return redirect("envoyer_transfert")

        # 🔴 Conversion des dates
        try:
            date_transfert = datetime.strptime(date_transfert_str, "%Y-%m-%d").date()
            date_naissance = datetime.strptime(date_naissance_str, "%Y-%m-%d").date()
        except ValueError:
            messages.error(request, "❌ Format de date invalide.")
            return redirect("envoyer_transfert")

        # 🔴 Vérification âge (16–65 ans)
        today = date.today()
        age = today.year - date_naissance.year - (
            (today.month, today.day) < (date_naissance.month, date_naissance.day)
        )

        if age < 16 or age > 65:
            messages.error(
                request,
                "❌ L’âge de l’employé doit être compris entre 16 et 65 ans. "
                "Veuillez nous contacter directement pour un traitement spécial."
            )
            return redirect("envoyer_transfert")

        # 🔴 Entreprise destinataire
        try:
            nouvelle_entreprise = Employeur.objects.get(nom=nouvelle_entreprise_nom)
        except Employeur.DoesNotExist:
            messages.error(request, "❌ Entreprise destinataire introuvable.")
            return redirect("envoyer_transfert")

        if nouvelle_entreprise == employeur_connecte:
            messages.error(request, "❌ Transfert vers soi-même interdit.")
            return redirect("envoyer_transfert")

        # ✅ Création
        Transfert.objects.create(
            nom_employe=nom_employe,
            prenom_employe=prenom_employe,
            poste=poste,
            type_operation=type_operation,
            numero_employe=numero_employe,
            date_naissance=date_naissance,
            statut_canadien=statut_canadien,
            nas=nas if statut_canadien == "etranger" else None,
            ancienne_entreprise=employeur_connecte,
            nouvelle_entreprise=nouvelle_entreprise,
            date_transfert=date_transfert,
            message=message_text,
        )

        messages.success(request, "✅ Opération enregistrée avec succès.")
        return redirect("profil_employeur")

    entreprises = Employeur.objects.exclude(id=employeur_connecte.id)

    return render(request, "envoyer_transfert.html", {
        "employeur_connecte": employeur_connecte,
        "entreprises": entreprises,
    })


def envoyer_reference(request):
    # 🔹 Employeur connecté
    employeur_id = request.session.get("employeur_id")
    if not employeur_id:
        messages.error(request, "Session expirée. Veuillez vous reconnecter.")
        return redirect("login")

    employeur_connecte = get_object_or_404(Employeur, id=employeur_id)

    if request.method == "POST":
        # 🔹 Données formulaire
        nom_employe = request.POST.get("nom_employe", "").strip()
        prenom_employe = request.POST.get("prenom_employe", "").strip()
        poste = request.POST.get("poste", "").strip()
        numero_employe = request.POST.get("numero_employe", "").strip().upper()
        entreprise_reception_nom = request.POST.get("entreprise_reception", "").strip()
        message_text = request.POST.get("message", "").strip()

        # 🔴 Champs obligatoires
        if not all([
            nom_employe,
            prenom_employe,
            poste,
            numero_employe,
            entreprise_reception_nom
        ]):
            messages.error(
                request,
                "❌ Tous les champs obligatoires doivent être remplis."
            )
            return redirect("envoyer_reference")

        # 🔴 Numéro employé obligatoire (sans format strict)
        if not numero_employe:
            messages.error(
                request,
                "❌ Le numéro employé est obligatoire."
            )
            return redirect("envoyer_reference")

        # 🔴 Numéro déjà utilisé
        if Reference.objects.filter(numero_employe=numero_employe).exists():
            messages.error(
                request,
                f"❌ Le numéro employé {numero_employe} est déjà utilisé pour une référence."
            )
            return redirect("envoyer_reference")

        # 🔴 Vérifier entreprise destinataire
        try:
            nouvelle_entreprise = Employeur.objects.get(
                nom=entreprise_reception_nom
            )
        except Employeur.DoesNotExist:
            messages.error(
                request,
                f"❌ L’entreprise '{entreprise_reception_nom}' n’existe pas."
            )
            return redirect("envoyer_reference")

        # 🔴 INTERDIT : référence vers sa propre entreprise
        if nouvelle_entreprise.id == employeur_connecte.id:
            messages.error(
                request,
                "❌ Vous ne pouvez pas envoyer une référence à votre propre entreprise."
            )
            return redirect("envoyer_reference")

        # ✅ CRÉATION DE LA RÉFÉRENCE
        Reference.objects.create(
            nom_employe=nom_employe,
            prenom_employe=prenom_employe,
            poste=poste,
            numero_employe=numero_employe,
            ancienne_entreprise=employeur_connecte,
            nouvelle_entreprise=nouvelle_entreprise,
            message=message_text,
        )

        messages.success(
            request,
            f"✅ Référence envoyée avec succès pour "
            f"{nom_employe} {prenom_employe} "
            f"(Numéro : {numero_employe})."
        )
        return redirect("profil_employeur")

    # 🔹 GET → entreprises possibles (sans soi-même)
    entreprises = Employeur.objects.exclude(id=employeur_connecte.id)

    return render(
        request,
        "envoyer_reference.html",
        {
            "employeur_connecte": employeur_connecte,
            "entreprises": entreprises,
        }
    )

def modifier_profil(request, employeur_id):  # on récupère l'ID depuis l'URL
    employeur = get_object_or_404(Employeur, id=employeur_id)

    if request.method == 'POST':
        form = EmployeurForm(request.POST, instance=employeur)
        if form.is_valid():
            form.save()
            return redirect('profil')  # ou une autre page
    else:
        form = EmployeurForm(instance=employeur)

    return render(request, 'profil_modifier.html', {'form': form})







def mot_de_passe_oublie(request):
    if request.method == "POST":
        identifiant = request.POST.get("identifiant", "").strip()
        code = str(randint(100000, 999999))  # code à 6 chiffres

        # Vérifier si c’est un email ou un téléphone
        est_email = re.match(r"[^@]+@[^@]+\.[^@]+", identifiant)
        est_telephone = re.match(r"^\+?1?\d{10}$", identifiant.replace("-", "").replace(" ", ""))

        if not (est_email or est_telephone):
            messages.error(request, "Veuillez entrer un email ou un numéro de téléphone valide.")
            return redirect("mot_de_passe_oublie")

        # Vérifier que l'utilisateur existe
        employeur = None
        if est_email:
            employeur = Employeur.objects.filter(email=identifiant).first()
        elif est_telephone:
            employeur = Employeur.objects.filter(telephone=identifiant).first()

        if not employeur:
            messages.error(request, "Aucun compte trouvé avec cet identifiant.")
            return redirect("mot_de_passe_oublie")

        # Sauvegarde du code en session
        request.session["code"] = code
        request.session["identifiant"] = identifiant

        # ✅ ENVOI DU CODE PAR EMAIL
        if est_email:
            try:
                send_mail(
                    "Votre code de vérification - HexaQuébec",
                    f"Bonjour {employeur.nom},\n\nVoici votre code de vérification : {code}\n\nHexaQuébec.",
                    "hexaquebec.ca@gmail.com",  # expéditeur
                    [identifiant],  # destinataire
                    fail_silently=False,
                )
                messages.success(request, f"Un code a été envoyé à votre e-mail {identifiant}.")
            except Exception as e:
                messages.error(request, f"Erreur lors de l’envoi de l’e-mail : {e}")

        # ✅ (Optionnel) ENVOI DU CODE PAR SMS via Twilio
        elif est_telephone:
            # Exemple à activer si tu veux plus tard :
            # from twilio.rest import Client
            # client = Client('SID', 'TOKEN')
            # client.messages.create(
            #     body=f"Votre code HexaQuébec : {code}",
            #     from_='+1234567890',  # numéro Twilio
            #     to=f"+1{identifiant[-10:]}"
            # )
            messages.success(request, f"Un code a été envoyé par SMS au {identifiant}.")

        return redirect("verification_code")

    return render(request, "mot_de_passe_oublie.html")


def verification_code(request):
    if request.method == "POST":
        code = request.POST.get("code", "").strip()
        if code == request.session.get("code"):
            return redirect("nouveau_mot_de_passe")
        else:
            messages.error(request, "❌ Code incorrect.")
    return render(request, "verification_code.html")


def nouveau_mot_de_passe(request):
    if request.method == "POST":
        p1 = request.POST.get("password1")
        p2 = request.POST.get("password2")
        identifiant = request.session.get("identifiant")

        if p1 != p2:
            messages.error(request, "Les mots de passe ne correspondent pas.")
            return redirect("nouveau_mot_de_passe")

        employeur = Employeur.objects.filter(email=identifiant).first() or Employeur.objects.filter(telephone=identifiant).first()

        if employeur:
            employeur.mot_de_passe = p1  # ⚠️ stocke en clair — à remplacer par un hash sécurisé si possible
            employeur.save()
            messages.success(request, "✅ Mot de passe changé avec succès.")
            return redirect("login")
        else:
            messages.error(request, "Utilisateur introuvable.")

    return render(request, "nouveau_mot_de_passe.html")



def modifier_profil(request, employeur_id):
    employeur = get_object_or_404(Employeur, id=employeur_id)

    if request.method == "POST":
        employeur.email = request.POST.get("email")
        employeur.telephone = request.POST.get("telephone")
        employeur.rue = request.POST.get("rue")
        employeur.code_postal = request.POST.get("code_postal")
        employeur.save()
        return redirect("profil_employeur")  # 🔁 retour sur la même page

    return render(request, "profil_employeur.html", {"employeur": employeur})

def supprimer_transfert(request, id):
    employeur_id = request.session.get("employeur_id")
    if not employeur_id:
        return redirect("login")

    employeur = get_object_or_404(Employeur, id=employeur_id)
    transfert = get_object_or_404(Transfert, id=id)

    # ✅ Vérifie que l'employeur est concerné par le transfert
    if (
        transfert.ancienne_entreprise == employeur
        or transfert.nouvelle_entreprise == employeur
    ):
        transfert.supprime_pour_employeur = True
        transfert.save()

        messages.success(request, "Transfert supprimé de votre vue.")
    else:
        messages.error(request, "Action non autorisée.")

    return redirect("profil_employeur")

def supprimer_reference(request, id):
    employeur_id = request.session.get("employeur_id")
    if not employeur_id:
        return redirect("login")

    employeur = get_object_or_404(Employeur, id=employeur_id)
    reference = get_object_or_404(Reference, id=id)

    if (
        reference.ancienne_entreprise == employeur
        or reference.nouvelle_entreprise == employeur
    ):
        reference.supprime_pour_employeur = True
        reference.save()

        messages.success(request, "Référence supprimée de votre vue.")
    else:
        messages.error(request, "Action non autorisée.")

    return redirect("profil_employeur")



def logout_view(request):
    logout(request)
    return redirect('login')  # ou la page d'accueil publique




def accepter_transfert(request, id):
    t = get_object_or_404(Transfert, id=id)

    if request.method == "POST":
        signature_nom = request.POST.get("signature_nom", "").strip()

        if not signature_nom:
            messages.error(request, "❌ La signature électronique est obligatoire.")
            return redirect("profil_employeur")

        # 🔹 Mise à jour du statut
        t.statut = "accepte"
        t.save()

        # 🔹 Génération du PDF
        context = {
            "transfert": t,
            "signature_nom": signature_nom,
            "date_signature": now(),
            "entreprise": t.nouvelle_entreprise,
        }

        html = render_to_string("pdf/lettre_acceptation.html", context)
        pdf_file = weasyprint.HTML(string=html).write_pdf()

        pdf_path = f"media/acceptations/transfert_{t.id}.pdf"
        os.makedirs(os.path.dirname(pdf_path), exist_ok=True)

        with open(pdf_path, "wb") as f:
            f.write(pdf_file)

        # 🔹 Envoi email
        email = EmailMessage(
            subject="✅ Transfert accepté officiellement",
            body=(
                f"Bonjour,\n\n"
                f"La demande de transfert pour {t.nom_employe} {t.prenom_employe} "
                f"a été officiellement ACCEPTÉE.\n\n"
                f"Veuillez trouver en pièce jointe la lettre d’acceptation signée.\n\n"
                f"Cordialement,\n"
                f"{t.nouvelle_entreprise.nom}"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[t.ancienne_entreprise.email],
        )

        email.attach_file(pdf_path)
        email.send()

        messages.success(
            request,
            f"✅ Transfert accepté, signé et envoyé par email avec succès."
        )

    return redirect("profil_employeur")

def refuser_transfert(request, id):
    t = get_object_or_404(Transfert, id=id)
    if request.method == "POST":
        motif = request.POST.get("motif_refus")
        t.statut = "refuse"
        t.motif_refus = motif
        t.save()
        messages.warning(request, f"❌ Vous avez refusé le transfert de {t.nom_employe}.")
        return redirect('profil_employeur')
    return render(request, "refuser_transfert.html", {"transfert": t})

def repondre_reference(request, id):
    r = get_object_or_404(Reference, id=id)
    if request.method == "POST":
        reponse = request.POST.get("reponse_employeur")
        r.reponse_employeur = reponse
        r.save()
        messages.success(request, "Réponse envoyée avec succès ✅")
        return redirect('profil_employeur')

def accepter_transfert(request, id):

    if request.method != "POST":
        messages.error(request, "Action non autorisée.")
        return redirect("profil_employeur")

    t = get_object_or_404(Transfert, id=id)

    if t.statut == "accepte":
        messages.warning(request, "Ce transfert a déjà été accepté.")
        return redirect("profil_employeur")

    # 🔹 Récupération signature
    signature_nom = request.POST.get("signature_nom")
    signature_image = request.POST.get("signature_data")  # base64 canvas

    if not signature_nom or not signature_image:
        messages.error(request, "La signature est obligatoire pour accepter le transfert.")
        return redirect("profil_employeur")

    # 🔹 Mise à jour du transfert
    t.statut = "accepte"
    t.signature_nom = signature_nom
    t.signature_image = signature_image
    t.date_signature = timezone.now()
    t.save()

    # 🔹 Génération du PDF
    pdf_buffer = generer_pdf_transfert(t)
    pdf_buffer.seek(0)

    # 🔹 Email avec PDF
    subject = f"✅ Acceptation officielle de transfert – {t.nom_employe} {t.prenom_employe}"

    body = f"""
Bonjour {t.ancienne_entreprise.nom},

Nous vous confirmons que le transfert de :

{t.nom_employe} {t.prenom_employe}
Poste : {t.poste}
Numéro employé : {t.numero_employe}

a été officiellement ACCEPTÉ par :
{t.nouvelle_entreprise.nom}

Veuillez trouver en pièce jointe la lettre officielle signée électroniquement.

Cordialement,
HexaQuébec
Plateforme RH sécurisée
"""

    email = EmailMessage(
        subject,
        body,
        settings.DEFAULT_FROM_EMAIL,
        [t.ancienne_entreprise.email],
    )

    email.attach(
        f"acceptation_transfert_{t.numero_employe}.pdf",
        pdf_buffer.read(),
        "application/pdf",
    )

    email.send(fail_silently=False)

    messages.success(
        request,
        f"✅ Transfert accepté, signé et envoyé à {t.ancienne_entreprise.nom}."
    )

    return redirect("profil_employeur")


def refuser_transfert(request, id):
    t = get_object_or_404(Transfert, id=id)
    if request.method == "POST":
        motif = request.POST.get("motif_refus")
        t.statut = "refuse"
        t.motif_refus = motif
        t.save()

        # 📨 Envoi du mail de refus
        sujet = f"Transfert refusé - {t.nom_employe} {t.prenom_employe}"
        message = (
            f"Bonjour {t.ancienne_entreprise.nom},\n\n"
            f"Votre demande de transfert de {t.nom_employe} {t.prenom_employe} "
            f"a été refusée par {t.nouvelle_entreprise.nom}.\n\n"
            f"Motif du refus : {motif}\n\n"
            f"Cordialement,\n"
            f"L'équipe RH"
        )
        destinataire = [t.ancienne_entreprise.email]
        send_mail(sujet, message, settings.DEFAULT_FROM_EMAIL, destinataire, fail_silently=False)

        messages.warning(request, f"❌ Transfert refusé et notification envoyée à {t.ancienne_entreprise.nom}.")
        return redirect('profil_employeur')

    return render(request, "refuser_transfert.html", {"transfert": t})


import base64
import os
from io import BytesIO
from datetime import date
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors


def generer_pdf_transfert(transfert):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # 🟦 BORDURES + FOND TITRE
    p.setStrokeColor(colors.lightgrey)
    p.setLineWidth(2)
    p.rect(1*cm, 1*cm, width-2*cm, height-2*cm)  # Bordure principale

    # Petite barre colorée en haut
    p.setFillColor(colors.HexColor("#FFDEE9"))
    p.rect(1*cm, height - 2*cm, width-2*cm, 1*cm, fill=1)

    # 🟦 FLEURS DÉCORATIVES (images locales ou base64)
    # Exemple : si tu as une image "fleur.png" dans ton projet
    fleur_path = "static/images/fleur.png"
    if os.path.exists(fleur_path):
        try:
            img = ImageReader(fleur_path)
            # gauche
            p.drawImage(img, 1*cm, height/2, width=2*cm, height=2*cm, mask='auto')
            # droite
            p.drawImage(img, width-3*cm, height/2, width=2*cm, height=2*cm, mask='auto')
        except Exception as e:
            print("❌ Fleur PDF :", e)

    # 🟦 LOGO ENTREPRISE
    logo = transfert.nouvelle_entreprise.logo
    if logo and os.path.exists(logo.path):
        try:
            p.drawImage(
                logo.path,
                width/2 - 2*cm,
                height - 5*cm,
                width=4*cm,
                preserveAspectRatio=True,
                mask='auto'
            )
        except Exception as e:
            print("❌ Erreur logo PDF :", e)

    # 🟦 TITRE
    p.setFont("Helvetica-Bold", 16)
    p.setFillColor(colors.HexColor("#333333"))
    p.drawCentredString(width / 2, height - 6 * cm, "LETTRE OFFICIELLE D’ACCEPTATION DE TRANSFERT")

    # 🟦 TEXTE PRINCIPAL
    p.setFont("Helvetica", 11)
    p.setFillColor(colors.black)
    y = height - 7.5 * cm

    lignes = [
        f"Entreprise destinataire : {transfert.nouvelle_entreprise.nom}",
        f"Entreprise d’origine : {transfert.ancienne_entreprise.nom}",
        "",
        "Nous confirmons l’acceptation officielle du transfert de :",
        f"{transfert.nom_employe} {transfert.prenom_employe}",
        f"Poste : {transfert.poste}",
        f"Numéro employé : {transfert.numero_employe}",
    ]

    # Date de naissance
    if transfert.date_naissance:
        lignes.append(f"Date de naissance : {transfert.date_naissance.strftime('%d/%m/%Y')}")

    # NAS masqué
    if transfert.statut_canadien == "etranger" and transfert.nas:
        lignes.append(f"NAS : ... ... {transfert.nas[-3:]}")

    lignes += [
        "",
        "Ce document vaut accord officiel et légal.",
        "",
        f"Signé électroniquement par : {getattr(transfert, 'signature_nom', 'N/A')}",
        f"Date : {date.today().strftime('%d/%m/%Y')}",
    ]

    for ligne in lignes:
        p.drawString(3*cm, y, ligne)
        y -= 0.8*cm

    # 🟦 SIGNATURE MANUSCRITE
    if transfert.signature_image:
        try:
            signature_base64 = transfert.signature_image.split(",")[1]
            signature_bytes = base64.b64decode(signature_base64)
            signature_img = ImageReader(BytesIO(signature_bytes))
            p.drawImage(signature_img, 3*cm, y-3*cm, width=6*cm, height=2*cm, mask='auto')
        except Exception as e:
            print("❌ Erreur signature PDF :", e)

    # 🟦 FOOTER
    p.setFont("Helvetica-Oblique", 9)
    p.setFillColor(colors.grey)
    p.drawCentredString(
        width / 2,
        1.5*cm,
        f"Document signé électroniquement le {date.today().strftime('%d/%m/%Y')}"
    )

    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer


from django.core.mail import EmailMessage
from django.conf import settings


def envoyer_email_transfert(transfert):
    pdf_buffer = generer_pdf_transfert(transfert)

    email = EmailMessage(
        subject=f"✅ Acceptation officielle de transfert – {transfert.numero_employe}",
        body=f"""
Bonjour {transfert.ancienne_entreprise.nom},

Le transfert de :

{transfert.nom_employe} {transfert.prenom_employe}
Poste : {transfert.poste}
Numéro employé : {transfert.numero_employe}

a été officiellement ACCEPTÉ par :
{transfert.nouvelle_entreprise.nom}

Veuillez trouver en pièce jointe la lettre officielle signée électroniquement.

Cordialement,
HexaQuébec – Plateforme RH sécurisée
""",
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[transfert.ancienne_entreprise.email],
    )

    email.attach(
        f"acceptation_transfert_{transfert.numero_employe}.pdf",
        pdf_buffer.read(),
        "application/pdf"
    )

    email.send()


def historique_employeur(request):
    employeur_id = request.session.get("employeur_id")
    if not employeur_id:
        return redirect("login")

    employeur = get_object_or_404(Employeur, id=employeur_id)

    # 🔹 TRANSFERTS (même supprimés)
    transferts = Transfert.objects.filter(
        Q(ancienne_entreprise=employeur) |
        Q(nouvelle_entreprise=employeur)
    ).order_by("-date_transfert")

    # 🔹 RÉFÉRENCES (même supprimées)
    references = Reference.objects.filter(
        Q(ancienne_entreprise=employeur) |
        Q(nouvelle_entreprise=employeur)
    ).order_by("-date_reference")

    # 🔹 HISTORIQUE DES ACTIONS
    historiques = HistoriqueAction.objects.filter(
        employeur=employeur
    ).order_by("-date_action")

    return render(request, "historique_employeur.html", {
        "employeur": employeur,
        "transferts": transferts,
        "references": references,
        "historiques": historiques,
    })



def choisir_adresse(request):
    return render(request, 'choisir_adresse.html')