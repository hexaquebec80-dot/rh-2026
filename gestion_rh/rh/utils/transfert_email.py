from django.core.mail import EmailMessage
from django.conf import settings


def envoyer_email_transfert(transfert, pdf_buffer):
    subject = "✅ Acceptation officielle de transfert – HexaQuébec"

    body = f"""
Bonjour {transfert.ancienne_entreprise.nom},

Nous vous confirmons que le transfert de :

{transfert.nom_employe} {transfert.prenom_employe}
Poste : {transfert.poste}
Numéro : {transfert.numero_employe}

a été officiellement ACCEPTÉ par :
{transfert.nouvelle_entreprise.nom}

Veuillez trouver en pièce jointe la lettre officielle signée électroniquement.

Cordialement,
HexaQuébec
Plateforme RH sécurisée
"""

    email = EmailMessage(
        subject,
        body,
        settings.DEFAULT_FROM_EMAIL,
        [transfert.ancienne_entreprise.email],
    )

    email.attach(
        f"acceptation_transfert_{transfert.numero_employe}.pdf",
        pdf_buffer.read(),
        "application/pdf"
    )

    email.send(fail_silently=False)
