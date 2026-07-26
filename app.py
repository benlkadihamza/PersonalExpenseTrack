import os
import shutil
from datetime import datetime, date
from calendar import month_name
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify, make_response
from flask_wtf.csrf import CSRFProtect
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from sqlalchemy import func, extract, or_, desc, asc

from models import db, User, Transaction, Setting
from forms import LoginForm, ChangePasswordForm, TransactionForm, SettingsForm, RestoreDatabaseForm
from utils import generate_excel_export, generate_pdf_report

FRENCH_MONTHS = {
    1: "Janvier", 2: "Février", 3: "Mars", 4: "Avril",
    5: "Mai", 6: "Juin", 7: "Juillet", 8: "Août",
    9: "Septembre", 10: "Octobre", 11: "Novembre", 12: "Décembre"
}

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'dev-expense-tracker-secret-key-french-2026'
    
    # Database configuration (SQLite locally / PostgreSQL on Render)
    database_url = os.getenv("DATABASE_URL")

    if database_url:
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    else:
        db_path = os.path.join(app.instance_path, "expense_tracker.db")
        os.makedirs(app.instance_path, exist_ok=True)
        database_url = f"sqlite:///{db_path}"

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    CSRFProtect(app)

    login_manager = LoginManager()
    login_manager.login_view = 'login'
    login_manager.login_message = "Veuillez vous connecter pour accéder à cette page."
    login_manager.login_message_category = "danger"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    with app.app_context():
        db.create_all()
        # Seed default settings if empty
        if not db.session.get(Setting, 'app_name'):
            Setting.set_val('app_name', 'Mon Suivi Financier')
        if not db.session.get(Setting, 'currency'):
            Setting.set_val('currency', 'DH')
        if not db.session.get(Setting, 'dark_mode'):
            Setting.set_val('dark_mode', 'false')

        # Seed default admin user if no users exist
        if User.query.count() == 0:
            default_admin = User(username='admin')
            default_admin.set_password('admin123')
            db.session.add(default_admin)
            db.session.commit()

    @app.context_processor
    def inject_global_settings():
        return {
            'app_name': Setting.get_val('app_name', 'Mon Suivi Financier'),
            'currency': Setting.get_val('currency', 'DH'),
            'dark_mode': Setting.get_val('dark_mode', 'false') == 'true',
            'french_months': FRENCH_MONTHS,
            'current_year': datetime.now().year,
            'today_date': date.today().strftime('%Y-%m-%d')
        }

    # Authentication Routes
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))

        form = LoginForm()
        if form.validate_on_submit():
            username = form.username.data.strip()
            password = form.password.data
            user = User.query.filter_by(username=username).first()

            if user and user.check_password(password):
                login_user(user, remember=form.remember_me.data)
                flash(f"Bienvenue, {user.username} !", "success")
                next_page = request.args.get('next')
                return redirect(next_page or url_for('dashboard'))
            else:
                flash("Nom d'utilisateur ou mot de passe incorrect.", "danger")

        return render_template('login.html', form=form)

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        flash("Vous avez été déconnecté avec succès.", "info")
        return redirect(url_for('login'))

    # 1. Dashboard Route
    @app.route('/')
    @app.route('/dashboard')
    @login_required
    def dashboard():
        # Overall Statistics
        tot_rev = db.session.query(func.coalesce(func.sum(Transaction.revenu), 0.0)).scalar()
        tot_dep = db.session.query(func.coalesce(func.sum(Transaction.depense), 0.0)).scalar()
        solde = tot_rev - tot_dep
        count_tx = Transaction.query.count()

        # Last 10 Transactions
        recent_txs = Transaction.query.order_by(Transaction.date.desc(), Transaction.id.desc()).limit(10).all()

        # Chart Data Aggregation (Monthly for the last 12 months)
        monthly_stats = db.session.query(
            extract('year', Transaction.date).label('year'),
            extract('month', Transaction.date).label('month'),
            func.sum(Transaction.revenu).label('total_rev'),
            func.sum(Transaction.depense).label('total_dep')
        ).group_by('year', 'month').order_by('year', 'month').all()

        chart_labels = []
        chart_expenses = []
        chart_revenues = []

        for stat in monthly_stats[-12:]: # Last 12 recorded months
            y, m = int(stat.year), int(stat.month)
            month_label = f"{FRENCH_MONTHS.get(m, m)} {y}"
            chart_labels.append(month_label)
            chart_revenues.append(round(float(stat.total_rev or 0), 2))
            chart_expenses.append(round(float(stat.total_dep or 0), 2))

        return render_template(
            'dashboard.html',
            tot_rev=tot_rev,
            tot_dep=tot_dep,
            solde=solde,
            count_tx=count_tx,
            recent_txs=recent_txs,
            chart_labels=chart_labels,
            chart_expenses=chart_expenses,
            chart_revenues=chart_revenues
        )

    # Helper function to build transaction filter query
    def get_filtered_transactions_query():
        query = Transaction.query

        search = request.args.get('search', '').strip()
        selected_month = request.args.get('month', '', type=str)
        selected_year = request.args.get('year', '', type=str)
        exact_date = request.args.get('date', '').strip()
        sort_by = request.args.get('sort', 'date_desc')

        if search:
            query = query.filter(Transaction.description.ilike(f'%{search}%'))

        if exact_date:
            try:
                dt = datetime.strptime(exact_date, '%Y-%m-%d').date()
                query = query.filter(Transaction.date == dt)
            except ValueError:
                pass
        else:
            if selected_year and selected_year.isdigit():
                query = query.filter(extract('year', Transaction.date) == int(selected_year))
            if selected_month and selected_month.isdigit():
                query = query.filter(extract('month', Transaction.date) == int(selected_month))

        if sort_by == 'date_asc':
            query = query.order_by(Transaction.date.asc(), Transaction.id.asc())
        elif sort_by == 'amount_desc':
            query = query.order_by((Transaction.revenu + Transaction.depense).desc())
        elif sort_by == 'amount_asc':
            query = query.order_by((Transaction.revenu + Transaction.depense).asc())
        else: # date_desc
            query = query.order_by(Transaction.date.desc(), Transaction.id.desc())

        return query

    # 2. Transactions List Route
    @app.route('/transactions')
    @login_required
    def transactions_list():
        page = request.args.get('page', 1, type=int)
        per_page = 10

        query = get_filtered_transactions_query()
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        # Available years for dropdown
        years_query = db.session.query(extract('year', Transaction.date)).distinct().all()
        years = sorted([int(y[0]) for y in years_query if y[0] is not None], reverse=True)
        if datetime.now().year not in years:
            years.insert(0, datetime.now().year)

        return render_template(
            'transactions/list.html',
            transactions=pagination.items,
            pagination=pagination,
            years=years
        )

    # 3. Add Transaction Route
    @app.route('/transactions/add', methods=['GET', 'POST'])
    @login_required
    def transaction_add():
        form = TransactionForm()
        if form.validate_on_submit():
            tx = Transaction(
                date=form.date.data,
                description=form.description.data.strip() if form.description.data else None,
                revenu=float(form.revenu.data or 0.0),
                depense=float(form.depense.data or 0.0)
            )
            db.session.add(tx)
            db.session.commit()
            flash("Transaction ajoutée avec succès !", "success")
            return redirect(url_for('transactions_list'))

        return render_template('transactions/form.html', form=form, title="Ajouter une transaction")

    # Edit Transaction Route
    @app.route('/transactions/edit/<int:id>', methods=['GET', 'POST'])
    @login_required
    def transaction_edit(id):
        tx = db.get_or_404(Transaction, id)
        form = TransactionForm(obj=tx)

        if form.validate_on_submit():
            tx.date = form.date.data
            tx.description = form.description.data.strip() if form.description.data else None
            tx.revenu = float(form.revenu.data or 0.0)
            tx.depense = float(form.depense.data or 0.0)
            db.session.commit()
            flash("Transaction modifiée avec succès !", "success")
            return redirect(url_for('transactions_list'))

        return render_template('transactions/form.html', form=form, title="Modifier la transaction", tx=tx)

    # Delete Transaction Route
    @app.route('/transactions/delete/<int:id>', methods=['POST'])
    @login_required
    def transaction_delete(id):
        tx = db.get_or_404(Transaction, id)
        db.session.delete(tx)
        db.session.commit()
        flash("La transaction a été supprimée.", "info")
        return redirect(url_for('transactions_list'))

    # Export Transactions to Excel
    @app.route('/transactions/export/excel')
    @login_required
    def transactions_export_excel():
        query = get_filtered_transactions_query()
        txs = query.all()
        currency = Setting.get_val('currency', 'DH')
        excel_buf = generate_excel_export(txs, title="Export_Transactions", currency=currency, is_monthly_report=False)
        filename = f"Transactions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        return send_file(
            excel_buf,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=filename
        )

    # Export Transactions to PDF
    @app.route('/transactions/export/pdf')
    @login_required
    def transactions_export_pdf():
        query = get_filtered_transactions_query()
        txs = query.all()
        app_name = Setting.get_val('app_name', 'Mon Suivi Financier')
        currency = Setting.get_val('currency', 'DH')
        include_summary = request.args.get('include_summary', '0') == '1'
        pdf_buf = generate_pdf_report(
            txs,
            month_str="Sélection",
            year_str=datetime.now().strftime("%Y"),
            app_name=app_name,
            currency=currency,
            include_summary=include_summary
        )
        filename = f"Transactions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        return send_file(
            pdf_buf,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=filename
        )

    # 4. Rapport Mensuel Route
    @app.route('/rapport')
    @login_required
    def rapport():
        now = datetime.now()
        month = request.args.get('month', now.month, type=int)
        year = request.args.get('year', now.year, type=int)

        # Get monthly transactions
        txs = Transaction.query.filter(
            extract('year', Transaction.date) == year,
            extract('month', Transaction.date) == month
        ).order_by(Transaction.date.asc(), Transaction.id.asc()).all()

        tot_rev = sum(t.revenu for t in txs)
        tot_dep = sum(t.depense for t in txs)
        net_mois = tot_rev - tot_dep
        count_tx = len(txs)

        month_label = FRENCH_MONTHS.get(month, f"Mois {month}")

        # Available years for dropdown selector
        years_query = db.session.query(extract('year', Transaction.date)).distinct().all()
        years = sorted([int(y[0]) for y in years_query if y[0] is not None], reverse=True)
        if year not in years:
            years.append(year)
            years.sort(reverse=True)

        return render_template(
            'rapport.html',
            transactions=txs,
            month=month,
            year=year,
            month_label=month_label,
            tot_rev=tot_rev,
            tot_dep=tot_dep,
            net_mois=net_mois,
            count_tx=count_tx,
            years=years
        )

    # Export Monthly Report to PDF
    @app.route('/rapport/export/pdf')
    @login_required
    def rapport_export_pdf():
        now = datetime.now()
        month = request.args.get('month', now.month, type=int)
        year = request.args.get('year', now.year, type=int)
        include_summary = request.args.get('include_summary', '0') == '1'

        txs = Transaction.query.filter(
            extract('year', Transaction.date) == year,
            extract('month', Transaction.date) == month
        ).order_by(Transaction.date.asc(), Transaction.id.asc()).all()

        app_name = Setting.get_val('app_name', 'Mon Suivi Financier')
        currency = Setting.get_val('currency', 'DH')
        month_label = FRENCH_MONTHS.get(month, f"Mois_{month}")

        pdf_buf = generate_pdf_report(
            txs,
            month_str=month_label,
            year_str=str(year),
            app_name=app_name,
            currency=currency,
            include_summary=include_summary
        )
        filename = f"Rapport_{month_label}_{year}.pdf"
        return send_file(
            pdf_buf,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=filename
        )

    # Export Monthly Report to Excel
    @app.route('/rapport/export/excel')
    @login_required
    def rapport_export_excel():
        now = datetime.now()
        month = request.args.get('month', now.month, type=int)
        year = request.args.get('year', now.year, type=int)

        txs = Transaction.query.filter(
            extract('year', Transaction.date) == year,
            extract('month', Transaction.date) == month
        ).order_by(Transaction.date.asc(), Transaction.id.asc()).all()

        currency = Setting.get_val('currency', 'DH')
        month_label = FRENCH_MONTHS.get(month, f"Mois_{month}")

        excel_buf = generate_excel_export(
            txs,
            title=f"Rapport_{month_label}_{year}",
            currency=currency,
            is_monthly_report=True
        )
        filename = f"Rapport_{month_label}_{year}.xlsx"
        return send_file(
            excel_buf,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=filename
        )

    # 5. Settings Route
    @app.route('/settings', methods=['GET', 'POST'])
    @login_required
    def settings():
        settings_form = SettingsForm(
            app_name=Setting.get_val('app_name', 'Mon Suivi Financier'),
            currency=Setting.get_val('currency', 'DH'),
            dark_mode=(Setting.get_val('dark_mode', 'false') == 'true')
        )
        password_form = ChangePasswordForm()
        restore_form = RestoreDatabaseForm()

        if request.method == 'POST':
            if 'app_name' in request.form:
                if settings_form.validate_on_submit():
                    Setting.set_val('app_name', settings_form.app_name.data.strip())
                    Setting.set_val('currency', settings_form.currency.data.strip())
                    Setting.set_val('dark_mode', 'true' if settings_form.dark_mode.data else 'false')
                    flash("Paramètres mis à jour avec succès !", "success")
                    return redirect(url_for('settings'))

            elif 'old_password' in request.form:
                if password_form.validate_on_submit():
                    if not current_user.check_password(password_form.old_password.data):
                        flash("Ancien mot de passe incorrect.", "danger")
                    else:
                        current_user.set_password(password_form.new_password.data)
                        db.session.commit()
                        flash("Votre mot de passe a été modifié avec succès !", "success")
                        return redirect(url_for('settings'))

        return render_template(
            'settings.html',
            settings_form=settings_form,
            password_form=password_form,
            restore_form=restore_form
        )

    # Backup Database Route
    @app.route('/settings/backup')
    @login_required
    def backup_db():
        db_path = os.path.join(app.instance_path, 'expense_tracker.db')
        if not os.path.exists(db_path):
            flash("La base de données n'existe pas encore.", "danger")
            return redirect(url_for('settings'))
        
        filename = f"expense_tracker_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        return send_file(
            db_path,
            as_attachment=True,
            download_name=filename,
            mimetype="application/octet-stream"
        )

    # Restore Database Route
    @app.route('/settings/restore', methods=['POST'])
    @login_required
    def restore_db():
        restore_form = RestoreDatabaseForm()
        if restore_form.validate_on_submit():
            f = restore_form.db_file.data
            db_path = os.path.join(app.instance_path, 'expense_tracker.db')
            
            # Temporary file write & validation
            temp_path = os.path.join(app.instance_path, 'temp_restore.db')
            f.save(temp_path)

            # Verify SQLite magic header
            with open(temp_path, 'rb') as check_f:
                header = check_f.read(16)
                if not header.startswith(b'SQLite format 3'):
                    os.remove(temp_path)
                    flash("Fichier invalide : Le fichier fourni n'est pas une base de données SQLite valide.", "danger")
                    return redirect(url_for('settings'))

            # Close database session before replacing DB file
            db.session.remove()
            db.engine.dispose()

            shutil.copyfile(temp_path, db_path)
            os.remove(temp_path)

            flash("La base de données a été restaurée avec succès !", "success")
            return redirect(url_for('settings'))
        else:
            for field, errors in restore_form.errors.items():
                for error in errors:
                    flash(f"Erreur de restauration: {error}", "danger")
            return redirect(url_for('settings'))

    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
