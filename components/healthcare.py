#!/usr/bin/env python3
"""
Component: Healthcare

Healthcare application component with SurrealDB.
Based on: https://surrealdb.com/solutions (Healthcare use case)
"""

import asyncio
from surrealdb import Surreal
from datetime import datetime


class HealthcareDB:
    """Healthcare database component."""
    
    def __init__(self, url: str = "ws://localhost:8000/rpc"):
        self.url = url
        self.db = None
    
    async def connect(self):
        """Connect to database."""
        self.db = Surreal(self.url)
        await self.db.connect()
        await self.db.use({"namespace": "healthcare", "database": "patient"})
        await self.db.signin({"username": "root", "password": "root"})
        return self
    
    async def setup_schema(self):
        """Create healthcare schema."""
        schemas = [
            """
            DEFINE TABLE patient SCHEMAFULL;
            DEFINE FIELD name ON patient TYPE string;
            DEFINE FIELD dob ON patient TYPE datetime;
            DEFINE FIELD mrn ON patient TYPE string; -- Medical Record Number
            DEFINE FIELD conditions ON patient TYPE array<string>;
            DEFINE FIELD medications ON patient TYPE array<object>;
            DEFINE FIELD allergies ON patient TYPE array<string>;
            DEFINE FIELD vitals ON patient TYPE array<object>;
            DEFINE FIELD encounters ON patient TYPE array<object>;
            """,
            """
            DEFINE TABLE encounter SCHEMAFULL;
            DEFINE FIELD patient ON encounter TYPE record(patient);
            DEFINE FIELD date ON encounter TYPE datetime;
            DEFINE FIELD type ON encounter TYPE string; -- visit, telehealth, emergency
            DEFINE FIELD provider ON encounter TYPE string;
            DEFINE FIELD notes ON encounter TYPE string;
            DEFINE FIELD diagnosis ON encounter TYPE array<string>;
            """,
            """
            DEFINE TABLE vital_signs SCHEMAFULL;
            DEFINE FIELD patient ON vital_signs TYPE record(patient);
            DEFINE FIELD timestamp ON vital_signs TYPE datetime;
            DEFINE FIELD heart_rate ON vital_signs TYPE int;
            DEFINE FIELD blood_pressure_systolic ON vital_signs TYPE int;
            DEFINE FIELD blood_pressure_diastolic ON vital_signs TYPE int;
            DEFINE FIELD temperature ON vital_signs TYPE float;
            DEFINE FIELD oxygen_saturation ON vital_signs TYPE int;
            """,
            """
            DEFINE TABLE alert SCHEMAFULL;
            DEFINE FIELD patient ON alert TYPE record(patient);
            DEFINE FIELD timestamp ON alert TYPE datetime;
            DEFINE FIELD type ON alert TYPE string; -- critical, warning, info
            DEFINE FIELD message ON alert TYPE string;
            DEFINE FIELD acknowledged ON alert TYPE bool DEFAULT false;
            """,
        ]
        
        for schema in schemas:
            await self.db.query(schema)
        
        print("✅ Healthcare schema created")
    
    # ----- Patient Operations -----
    
    async def register_patient(self, name: str, mrn: str, dob: str, 
                               conditions: list = None, allergies: list = None):
        """Register new patient."""
        result = await self.db.query(
            """CREATE patient SET name=$name, mrn=$mrn, dob=$dob, 
            conditions=$conditions, allergies=$allergies""",
            {"name": name, "mrn": mrn, "dob": dob, 
             "conditions": conditions or [], "allergies": allergies or []}
        )
        return result[0][0] if result else None
    
    async def record_vitals(self, patient_id: str, vitals: dict):
        """Record patient vitals."""
        result = await self.db.query(
            """CREATE vital_signs SET patient=$patient, timestamp=time::now(),
            heart_rate=$heart_rate, blood_pressure_systolic=$bp_sys,
            blood_pressure_diastolic=$bp_dia, temperature=$temp,
            oxygen_saturation=$o2""",
            {"patient": patient_id, 
             "heart_rate": vitals.get("heart_rate"),
             "bp_sys": vitals.get("bp_systolic"),
             "bp_dia": vitals.get("bp_diastolic"),
             "temp": vitals.get("temperature"),
             "o2": vitals.get("oxygen_saturation")}
        )
        
        # Check for alerts
        await self._check_vital_alerts(patient_id, vitals)
        
        return result[0][0] if result else None
    
    async def create_encounter(self, patient_id: str, encounter_type: str,
                           provider: str, notes: str, diagnosis: list = None):
        """Create clinical encounter."""
        result = await self.db.query(
            """CREATE encounter SET patient=$patient, date=time::now(),
            type=$type, provider=$provider, notes=$notes, diagnosis=$diagnosis""",
            {"patient": patient_id, "type": encounter_type,
             "provider": provider, "notes": notes, "diagnosis": diagnosis or []}
        )
        return result[0][0] if result else None
    
    async def _check_vital_alerts(self, patient_id: str, vitals: dict):
        """Check vitals and create alerts."""
        alerts = []
        
        if vitals.get("heart_rate", 0) > 100:
            alerts.append({"type": "warning", "message": "Tachycardia detected"})
        if vitals.get("heart_rate", 0) < 60:
            alerts.append({"type": "warning", "message": "Bradycardia detected"})
        if vitals.get("bp_systolic", 0) > 180:
            alerts.append({"type": "critical", "message": "Hypertensive crisis"})
        if vitals.get("oxygen_saturation", 100) < 90:
            alerts.append({"type": "critical", "message": "Low oxygen saturation"})
        
        for alert in alerts:
            await self.db.query(
                """CREATE alert SET patient=$patient, timestamp=time::now(),
                type=$type, message=$message""",
                {"patient": patient_id, "type": alert["type"], "message": alert["message"]}
            )
    
    async def get_patient_summary(self, patient_id: str):
        """Get patient summary."""
        # Get patient
        patient = await self.db.query(
            "SELECT * FROM patient WHERE id = $id", {"id": patient_id}
        )
        
        # Get recent vitals
        vitals = await self.db.query(
            "SELECT * FROM vital_signs WHERE patient = $patient ORDER BY timestamp DESC LIMIT 5",
            {"patient": patient_id}
        )
        
        # Get recent encounters
        encounters = await self.db.query(
            "SELECT * FROM encounter WHERE patient = $patient ORDER BY date DESC LIMIT 10",
            {"patient": patient_id}
        )
        
        # Get active alerts
        alerts = await self.db.query(
            "SELECT * FROM alert WHERE patient = $patient AND acknowledged = false",
            {"patient": patient_id}
        )
        
        return {
            "patient": patient[0][0] if patient and patient[0] else None,
            "vitals": vitals[0] if vitals else [],
            "encounters": encounters[0] if encounters else [],
            "alerts": alerts[0] if alerts else [],
        }
    
    async def search_patients(self, query: str, k: int = 10):
        """Semantic search patients."""
        # In real implementation, would use embeddings
        result = await self.db.query(
            "SELECT * FROM patient WHERE name CONTAINS $query OR mrn CONTAINS $query LIMIT $k",
            {"query": query, "k": k}
        )
        return result[0] if result else []


async def demo():
    """Healthcare demo."""
    db = HealthcareDB()
    await db.connect()
    await db.setup_schema()
    
    # Register patient
    patient = await db.register_patient(
        name="John Smith",
        mrn="MRN-001",
        dob="1980-05-15",
        conditions=["diabetes", "hypertension"],
        allergies=["penicillin"]
    )
    print(f"Patient: {patient}")
    
    # Record vitals
    vitals = await db.record_vitals(patient["id"], {
        "heart_rate": 95,
        "bp_systolic": 145,
        "bp_diastolic": 90,
        "temperature": 98.6,
        "oxygen_saturation": 97
    })
    print(f"Vitals: {vitals}")
    
    # Get summary
    summary = await db.get_patient_summary(patient["id"])
    print(f"Summary: {summary}")


if __name__ == "__main__":
    asyncio.run(demo())