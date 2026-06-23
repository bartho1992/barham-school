import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from models import Ecole

class Mailer:
    @staticmethod
    def send_email(destinataire, sujet, corps, is_html=False):
        """
        Envoie un email en utilisant les paramètres SMTP de la base de données
        """
        ecole = Ecole.query.first()
        if not ecole or not ecole.smtp_server:
            return False, "Serveur SMTP non configuré"
            
        try:
            # Création du message
            msg = MIMEMultipart()
            msg['From'] = ecole.email_expediteur or ecole.smtp_user
            msg['To'] = destinataire
            msg['Subject'] = sujet
            
            # Corps du message
            msg.attach(MIMEText(corps, 'html' if is_html else 'plain'))
            
            # Connexion au serveur
            server = smtplib.SMTP(ecole.smtp_server, ecole.smtp_port)
            if ecole.smtp_use_tls:
                server.starttls()
                
            if ecole.smtp_user and ecole.smtp_password:
                server.login(ecole.smtp_user, ecole.smtp_password)
                
            # Envoi
            server.send_message(msg)
            server.quit()
            
            return True, "Email envoyé avec succès"
        except Exception as e:
            return False, str(e)

mailer = Mailer()
