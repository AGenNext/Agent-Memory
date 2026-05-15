#!/usr/bin/env python3
"""
SurrealDB USE CASE: Healthcare Agent

Based on SurrealDB healthcare industry solutions.
Live: https://surrealdb.com/use-cases/healthcare
"""

import asyncio
from surrealdb import Surreal


class HealthcareAgent:
    """Healthcare data agent using SurrealQL natively."""
    
    async def demo(self):
        """Run healthcare demo."""
        
        db = Surreal("ws://localhost:8000/rpc")
        await db.connect()
        await db.use({"namespace": "healthcare", "database": "patient"})
        await db.signin({"username": "root", "password": "root"})
        
        # ===== SCHEMA =====
        
        # Patients
        await db.query("""
            DEFINE TABLE patient SCHEMAFULL;
            DEFINE FIELD name ON patient TYPE string;
            DEFINE FIELD mrn ON patient TYPE string;
            DEFINE FIELD dob ON patient TYPE datetime;
            DEFINE FIELD insurance ON patient TYPE string;
            DEFINE FIELD allergies ON patient TYPE array<string>;
        """)
        
        # Encounters
        await db.query("""
            DEFINE TABLE encounter SCHEMAFULL;
            DEFINE FIELD patient ON encounter TYPE record(patient);
            DEFINE FIELD chief_complaint ON encounter TYPE string;
            DEFINE FIELD diagnosis ON encounter TYPE string;
            DEFINE FIELD vitals ON encounter TYPE object;
            DEFINE FIELD timestamp ON encounter TYPE datetime DEFAULT time::now();
        """)
        
        # Prescriptions
        await db.query("""
            DEFINE TABLE prescription SCHEMAFULL;
            DEFINE FIELD patient ON prescription TYPE record(patient);
            DEFINE FIELD medication ON prescription TYPE string;
            DEFINE FIELD dosage ON prescription TYPE string;
            DEFINE FIELD refills ON prescription TYPE int;
            DEFINE FIELD status ON prescription TYPE string DEFAULT 'active';
        """)
        
        # Alerts
        await db.query("""
            DEFINE TABLE alert SCHEMAFULL;
            DEFINE FIELD patient ON alert TYPE record(patient);
            DEFINE FIELD severity ON alert TYPE string;
            DEFINE FIELD message ON alert TYPE string;
            DEFINE FIELD acknowledged ON alert TYPE bool DEFAULT false;
        """)
        
        print("✅ Healthcare schema created")
        
        # ===== OPERATIONS =====
        
        # Add patient
        result = await db.query("""
            CREATE patient SET name='John Doe', mrn='MRN-001', 
            dob=d'1980-01-15', insurance='BlueCross',
            allergies=['penicillin', 'shellfish']
        """)
        patient_id = result[0][0]["id"]
        
        # Add encounter
        result = await db.query("""
            CREATE encounter SET patient=$p, chief_complaint='chest pain',
            diagnosis='angina', vitals={bp: '140/90', heart_rate: 95}
        """, {"p": patient_id})
        
        # Add prescription
        result = await db.query("""
            CREATE prescription SET patient=$p, medication='nitroglycerin',
            dosage='0.4mg', refills=3, status='active'
        """, {"p": patient_id})
        
        # Add alert (triggered event)
        result = await db.query("""
            CREATE alert SET patient=$p, severity='high', 
            message='Elevated blood pressure'
        """, {"p": patient_id})
        
        # ===== QUERIES =====
        
        # All patients with allergies
        result = await db.query("""
            SELECT name, mrn, allergies FROM patient WHERE allergies CONTAINS 'penicillin'
        """)
        print(f"🩺 Penicillin allergic: {len(result[0])} patients")
        
        # Recent encounters
        result = await db.query("""
            SELECT *, time::format(timestamp, '%Y-%m-%d') AS date 
            FROM encounter ORDER BY timestamp DESC LIMIT 10
        """)
        
        # Active prescriptions
        result = await db.query("""
            SELECT patient->{name} AS patient_name, medication, dosage
            FROM prescription WHERE status = 'active'
        """)
        
        # Unacknowledged alerts
        result = await db.query("""
            SELECT patient->{name} AS patient, severity, message
            FROM alert WHERE acknowledged = false
        """)
        
        # ===== GRAPH =====
        
        # Relate doctor to patient
        await db.query("RELATE doctor:dr_smith -> primary_care -> patient:john_doe")
        
        # Relate patient to conditions
        await db.query("RELATE patient:john_doe -> has_condition -> condition:heart_disease")
        
        print("✅ Healthcare demo complete!")


async def main():
    await HealthcareAgent().demo()

if __name__ == "__main__":
    asyncio.run(main())