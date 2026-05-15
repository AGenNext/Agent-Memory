#!/usr/bin/env python3
"""
SurrealDB USE CASE: Finance Agent

Based on SurrealDB finance industry solutions.
Live: https://surrealdb.com/use-cases/finance
"""

import asyncio
from surrealdb import Surreal


class FinanceAgent:
    """Finance data agent using SurrealQL natively."""
    
    async def demo(self):
        """Run finance demo."""
        
        db = Surreal("ws://localhost:8000/rpc")
        await db.connect()
        await db.use({"namespace": "finance", "database": "banking"})
        await db.signin({"username": "root", "password": "root"})
        
        # ===== SCHEMA =====
        
        # Accounts
        await db.query("""
            DEFINE TABLE account SCHEMAFULL;
            DEFINE FIELD account_id ON account TYPE string;
            DEFINE FIELD type ON account TYPE string; -- checking, savings, credit
            DEFINE FIELD balance ON account TYPE float;
            DEFINE FIELD owner ON account TYPE string;
            DEFINE FIELD status ON account TYPE string DEFAULT 'active';
        """)
        
        # Transactions
        await db.query("""
            DEFINE TABLE transaction SCHEMAFULL;
            DEFINE FIELD from_account ON transaction TYPE record(account);
            DEFINE FIELD to_account ON transaction TYPE record(account);
            DEFINE FIELD amount ON transaction TYPE float;
            DEFINE FIELD type ON transaction TYPE string; -- debit, credit, transfer
            DEFINE FIELD timestamp ON transaction TYPE datetime DEFAULT time::now();
        """)
        
        # Holdings
        await db.query("""
            DEFINE TABLE holding SCHEMAFULL;
            DEFINE FIELD account ON holding TYPE record(account);
            DEFINE FIELD symbol ON holding TYPE string;
            DEFINE FIELD shares ON holding TYPE float;
            DEFINE FIELD avg_price ON holding TYPE float;
        """)
        
        # Prices
        await db.query("""
            DEFINE TABLE price SCHEMAFULL;
            DEFINE FIELD symbol ON price TYPE string;
            DEFINE FIELD price ON price TYPE float;
            DEFINE FIELD timestamp ON price TYPE datetime DEFAULT time::now();
        """)
        
        print("✅ Finance schema created")
        
        # ===== OPERATIONS =====
        
        # Create accounts
        await db.query("""
            CREATE account SET account_id='ACC-001', type='checking', 
            balance=10000.00, owner='John Doe'
        """)
        
        await db.query("""
            CREATE account SET account_id='ACC-002', type='savings', 
            balance=50000.00, owner='John Doe'
        """)
        
        # Transactions
        await db.query("""
            CREATE transaction SET from_account=account:acc_001, to_account=account:acc_002,
            amount=1000.00, type='transfer'
        """)
        
        # Holdings
        await db.query("""
            CREATE holding SET account=account:acc_001, symbol='AAPL', 
            shares=100.00, avg_price=150.00
        """)
        
        # Prices
        await db.query("""
            CREATE price SET symbol='AAPL', price=175.50
        """)
        
        # ===== QUERIES =====
        
        # Account balances
        result = await db.query("""
            SELECT account_id, type, balance FROM account 
            WHERE owner = 'John Doe'
        """)
        
        # Transaction history
        result = await db.query("""
            SELECT *, math::round(amount, 2) AS amount 
            FROM transaction ORDER BY timestamp DESC LIMIT 20
        """)
        
        # Portfolio value
        result = await db.query("""
            SELECT h.symbol, h.shares, p.price AS current_price,
            (h.shares * p.price) AS value, 
            ((p.price - h.avg_price) / h.avg_price * 100) AS gain_pct
            FROM holding AS h
            JOIN price AS p ON h.symbol = p.symbol
        """)
        
        print("✅ Finance demo complete!")


async def main():
    await FinanceAgent().demo()

if __name__ == "__main__":
    asyncio.run(main())