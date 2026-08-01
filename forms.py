from datetime import date
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import StringField, PasswordField, TextAreaField, DecimalField, DateField, SelectField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Optional, NumberRange, Length, EqualTo, ValidationError

class LoginForm(FlaskForm):
    username = StringField("Nom d'utilisateur", validators=[DataRequired(message="Le nom d'utilisateur est requis.")])
    password = PasswordField("Mot de passe", validators=[DataRequired(message="Le mot de passe est requis.")])
    remember_me = BooleanField("Se souvenir de moi")
    submit = SubmitField("Se connecter")

class ChangePasswordForm(FlaskForm):
    old_password = PasswordField("Ancien mot de passe", validators=[
        DataRequired(message="L'ancien mot de passe est requis.")
    ])
    new_password = PasswordField("Nouveau mot de passe", validators=[
        DataRequired(message="Le nouveau mot de passe est requis."),
        Length(min=6, message="Le mot de passe doit contenir au moins 6 caractères.")
    ])
    confirm_password = PasswordField("Confirmer le nouveau mot de passe", validators=[
        DataRequired(message="Veuillez confirmer le nouveau mot de passe."),
        EqualTo('new_password', message="Les nouveaux mots de passe ne correspondent pas.")
    ])
    submit = SubmitField("Changer le mot de passe")

class TransactionForm(FlaskForm):
    date = DateField('Date', default=date.today, validators=[DataRequired(message="La date est obligatoire.")])
    description = TextAreaField('Description', validators=[Optional()])
    revenu = DecimalField('Revenu (DH)', default=None, validators=[
        Optional(), NumberRange(min=0, message="Le revenu ne peut pas être négatif.")
    ])
    depense = DecimalField('Dépense (DH)', default=None, validators=[
        Optional(), NumberRange(min=0, message="La dépense ne peut pas être négative.")
    ])
    submit = SubmitField('Enregistrer')

    def validate(self, extra_validators=None):
        initial_validation = super(TransactionForm, self).validate(extra_validators=extra_validators)
        if not initial_validation:
            return False

        rev = float(self.revenu.data or 0.0)
        dep = float(self.depense.data or 0.0)

        if rev < 0 or dep < 0:
            self.revenu.errors.append("Les montants négatifs sont interdits.")
            return False

        if rev == 0 and dep == 0:
            self.revenu.errors.append("Le revenu OU la dépense doit être supérieur à 0 (les deux ne peuvent pas être zéro).")
            return False

        return True

class SettingsForm(FlaskForm):
    app_name = StringField("Nom de l'application", validators=[DataRequired(message="Le nom de l'application est requis.")])
    currency = StringField("Devise", validators=[DataRequired(message="La devise est requise.")])
    dark_mode = BooleanField("Mode Sombre par défaut")
    submit = SubmitField("Enregistrer les modifications")

class RestoreDatabaseForm(FlaskForm):
    db_file = FileField('Fichier de base de données (.db)', validators=[
        FileRequired(message="Veuillez sélectionner un fichier .db à restaurer."),
        FileAllowed(['db', 'sqlite', 'sqlite3'], message="Seuls les fichiers .db ou .sqlite sont autorisés.")
    ])
    submit = SubmitField('Restaurer la base de données')
