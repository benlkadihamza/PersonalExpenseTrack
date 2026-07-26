import random
from datetime import date, timedelta
from app import create_app
from models import db, Transaction

def seed_database():
    app = create_app()
    with app.app_context():
        # Clear existing transactions for fresh seed
        db.session.query(Transaction).delete()
        
        descriptions_revenus = [
            "Salaire mensuel",
            "Projet Freelance Web",
            "Prime de performance",
            "Vente matériel occasion",
            "Remboursement frais"
        ]
        
        descriptions_depenses = [
            "Courses supermarché Carrefour",
            "Facture d'électricité et eau",
            "Abonnement Internet Fibre",
            "Plein de carburant voiture",
            "Restaurant & Café",
            "Loyer mensuel",
            "Pharmacie & Médicaments",
            "Abonnement Salle de sport",
            "Achats vêtements"
        ]

        today = date.today()
        transactions = []

        # Generate 45 realistic transactions over the last 90 days
        for i in range(45):
            days_ago = random.randint(0, 90)
            tx_date = today - timedelta(days=days_ago)
            
            # 30% revenues, 70% expenses
            is_revenue = random.random() < 0.30
            
            if is_revenue:
                description = random.choice(descriptions_revenus)
                revenu = round(random.uniform(1500, 18000), 2)
                depense = 0.0
            else:
                description = random.choice(descriptions_depenses)
                revenu = 0.0
                depense = round(random.uniform(80, 2500), 2)

            tx = Transaction(
                date=tx_date,
                description=description,
                revenu=revenu,
                depense=depense
            )
            transactions.append(tx)

        db.session.add_all(transactions)
        db.session.commit()
        print(f"Successfully seeded database with {len(transactions)} sample transactions!")

if __name__ == '__main__':
    seed_database()
