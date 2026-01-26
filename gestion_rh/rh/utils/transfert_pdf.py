import base64
from io import BytesIO
from datetime import date

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader


def generer_pdf_transfert(transfert):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # 🏢 LOGO ENTREPRISE
    if transfert.nouvelle_entreprise.logo:
        try:
            logo = ImageReader(transfert.nouvelle_entreprise.logo.path)
            p.drawImage(
                logo,
                2 * cm,
                height - 4 * cm,
                width=4 * cm,
                preserveAspectRatio=True,
                mask="auto"
            )
        except Exception:
            pass  # ne bloque jamais le PDF

    # 📝 TITRE
    p.setFont("Helvetica-Bold", 16)
    p.drawCentredString(
        width / 2,
        height - 5 * cm,
        "LETTRE OFFICIELLE D’ACCEPTATION DE TRANSFERT"
    )

    p.setFont("Helvetica", 11)
    y = height - 7 * cm

    texte = [
        f"Entreprise destinataire : {transfert.nouvelle_entreprise.nom}",
        f"Entreprise d’origine : {transfert.ancienne_entreprise.nom}",
        "",
        "Nous confirmons l’acceptation officielle du transfert de :",
        f"{transfert.nom_employe} {transfert.prenom_employe}",
        f"Poste : {transfert.poste}",
        f"Numéro employé : {transfert.numero_employe}",
        "",
        "Cette acceptation vaut engagement officiel entre les parties.",
        "",
        f"Signé électroniquement par : {transfert.signature_nom}",
        f"Date : {date.today().strftime('%d/%m/%Y')}",
    ]

    for line in texte:
        p.drawString(2 * cm, y, line)
        y -= 0.7 * cm

    # ✍️ SIGNATURE MANUSCRITE
    if transfert.signature_image:
        try:
            image_data = base64.b64decode(
                transfert.signature_image.split(",")[1]
            )
            img = ImageReader(BytesIO(image_data))
            p.drawImage(
                img,
                2 * cm,
                y - 3 * cm,
                width=6 * cm,
                height=2 * cm,
                mask="auto"
            )
        except Exception:
            pass

    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer
