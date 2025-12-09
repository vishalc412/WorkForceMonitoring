"""
Script to create admin user for the application
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.models.user import User, UserRole
from app.security.password import hash_password
from app.config import settings
from datetime import datetime


async def create_admin():
    """Create admin user"""
    print("Creating admin user...")

    # Create engine and session
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Get admin details
        email = input("Enter admin email: ")
        full_name = input("Enter full name: ")
        password = input("Enter password: ")
        department = input("Enter department (optional): ") or None

        # Check if user already exists
        from sqlalchemy import select
        result = await session.execute(select(User).filter(User.email == email))
        existing_user = result.scalar_one_or_none()

        if existing_user:
            print(f"User with email {email} already exists!")
            return

        # Create admin user
        admin = User(
            email=email,
            full_name=full_name,
            password_hash=hash_password(password),
            role=UserRole.ADMIN,
            department=department,
            is_active=True,
            consent_gdpr=True,
            consent_timestamp=datetime.utcnow()
        )

        session.add(admin)
        await session.commit()

        print(f"\n✅ Admin user created successfully!")
        print(f"Email: {email}")
        print(f"Role: admin")
        print(f"\nYou can now login at http://localhost:8000/api/docs")

    await engine.dispose()


async def create_sample_employees():
    """Create sample employee users for testing"""
    print("\nCreating sample employees...")

    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    employees = [
        {
            "email": "john.doe@company.com",
            "full_name": "John Doe",
            "password": "employee123",
            "role": UserRole.EMPLOYEE,
            "department": "Sales"
        },
        {
            "email": "jane.smith@company.com",
            "full_name": "Jane Smith",
            "password": "employee123",
            "role": UserRole.EMPLOYEE,
            "department": "Marketing"
        },
        {
            "email": "manager@company.com",
            "full_name": "Mike Manager",
            "password": "manager123",
            "role": UserRole.MANAGER,
            "department": "Management"
        }
    ]

    async with async_session() as session:
        for emp_data in employees:
            # Check if exists
            from sqlalchemy import select
            result = await session.execute(select(User).filter(User.email == emp_data["email"]))
            if result.scalar_one_or_none():
                print(f"  ⏭️  {emp_data['email']} already exists, skipping...")
                continue

            user = User(
                email=emp_data["email"],
                full_name=emp_data["full_name"],
                password_hash=hash_password(emp_data["password"]),
                role=emp_data["role"],
                department=emp_data["department"],
                is_active=True,
                consent_gdpr=True,
                consent_timestamp=datetime.utcnow()
            )

            session.add(user)
            print(f"  ✅ Created {emp_data['role'].value}: {emp_data['email']}")

        await session.commit()

    await engine.dispose()
    print("\n✅ Sample users created successfully!")


async def create_sample_geofence():
    """Create a sample geofence"""
    print("\nCreating sample geofence...")

    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        from app.models.geofence import Geofence

        # Sample office location (Empire State Building, NYC)
        geofence = Geofence(
            name="Main Office",
            description="Primary office location in New York",
            latitude=40.748817,
            longitude=-73.985428,
            radius_meters=500,
            is_active=True
        )

        session.add(geofence)
        await session.commit()

        print(f"  ✅ Created geofence: {geofence.name}")
        print(f"     Location: {geofence.latitude}, {geofence.longitude}")
        print(f"     Radius: {geofence.radius_meters}m")

    await engine.dispose()


async def main():
    """Main function"""
    print("=" * 60)
    print("Workforce Monitoring - Admin Setup")
    print("=" * 60)

    # Create admin
    await create_admin()

    # Ask if user wants to create sample data
    create_samples = input("\nDo you want to create sample employees and geofence? (y/n): ")
    if create_samples.lower() == 'y':
        await create_sample_employees()
        await create_sample_geofence()

    print("\n" + "=" * 60)
    print("Setup complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
