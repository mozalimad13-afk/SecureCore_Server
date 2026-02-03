import sys
import os

# Add server directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
server_dir = os.path.dirname(script_dir)
sys.path.append(server_dir)

from app import create_app
from app.extensions import db
from app.models.company import Company
from app.models.subscription import Subscription

def migrate():
    app = create_app()
    with app.app_context():
        print("--- Migrating Subscriptions ---")
        companies = Company.query.all()
        for c in companies:
            sub = Subscription.query.filter_by(company_id=c.id).first()
            if not sub:
                print(f"Creating trial subscription for company: {c.name}")
                sub = Subscription(
                    company_id=c.id,
                    plan_name='Free Trial',
                    plan_price=0.0,
                    status='trial'
                )
                db.session.add(sub)
            else:
                print(f"Company {c.name} already has subscription: {sub.plan_name} ({sub.status})")
        
        db.session.commit()
        print("Migration completed.")

if __name__ == "__main__":
    migrate()
