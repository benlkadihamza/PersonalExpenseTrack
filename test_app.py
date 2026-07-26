import os
import unittest
import io
from datetime import date
from app import create_app
from models import db, User, Transaction, Setting

class PersonalExpenseTrackerTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.client = self.app.test_client()

        with self.app.app_context():
            db.create_all()
            # Seed sample transactions
            t1 = Transaction(
                date=date(2026, 7, 10),
                description="Salaire du mois",
                revenu=15000.0,
                depense=0.0
            )
            t2 = Transaction(
                date=date(2026, 7, 15),
                description="Loyer appartement",
                revenu=0.0,
                depense=4000.0
            )
            t3 = Transaction(
                date=date(2026, 7, 20),
                description="Achats supermarché",
                revenu=0.0,
                depense=850.0
            )
            db.session.add_all([t1, t2, t3])
            db.session.commit()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def login(self, username='admin', password='admin123'):
        return self.client.post('/login', data={
            'username': username,
            'password': password
        }, follow_redirects=True)

    def logout(self):
        return self.client.get('/logout', follow_redirects=True)

    def test_unauthenticated_redirect(self):
        response = self.client.get('/dashboard')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.location)

    def test_valid_login(self):
        response = self.login('admin', 'admin123')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Tableau de Bord", response.data)
        self.assertIn(b"admin", response.data)

    def test_invalid_login(self):
        response = self.login('admin', 'wrongpassword')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"incorrect", response.data)

    def test_logout(self):
        self.login('admin', 'admin123')
        response = self.logout()
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Se Connecter", response.data)

    def test_change_password_success(self):
        self.login('admin', 'admin123')
        response = self.client.post('/settings', data={
            'old_password': 'admin123',
            'new_password': 'newsecretpassword',
            'confirm_password': 'newsecretpassword'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"modifi\xc3\xa9 avec succ\xc3\xa8s", response.data)

        # Logout and verify login with new password
        self.logout()
        login_response = self.login('admin', 'newsecretpassword')
        self.assertEqual(login_response.status_code, 200)
        self.assertIn(b"Tableau de Bord", login_response.data)

    def test_dashboard_route(self):
        self.login()
        response = self.client.get('/dashboard')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Tableau de Bord", response.data)

    def test_monthly_report_route(self):
        self.login()
        response = self.client.get('/rapport?month=7&year=2026')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Rapport financier", response.data)
        self.assertIn(b"10150.00", response.data)

    def test_pdf_export_without_summary_default(self):
        self.login()
        response = self.client.get('/rapport/export/pdf?month=7&year=2026')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'application/pdf')
        self.assertTrue(response.data.startswith(b'%PDF'))

    def test_pdf_export_with_summary_toggled_on(self):
        self.login()
        response = self.client.get('/rapport/export/pdf?month=7&year=2026&include_summary=1')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'application/pdf')
        self.assertTrue(response.data.startswith(b'%PDF'))

if __name__ == '__main__':
    unittest.main()
