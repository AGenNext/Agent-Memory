# Assignment: Querying Fundamentals

## Instructions

Complete all exercises below using SurrealQL. You can use:
- SurrealSQL REPL: `surreal sql`
- Surrealist: `http://localhost:3000`
- Python SDK

## Prerequisites

```bash
# Start SurrealDB
docker-compose up -d surrealdb

# Or install and run
surreal start --user root --pass root memory
```

---

## Exercise 1: CREATE (2 points)

Create the following records:

### 1.1 User Records
Create 3 users with different profiles:

```sql
-- Create user:john with name 'John', role 'developer'
-- Create user:jane with name 'Jane', role 'designer'  
-- Create user:jack with name 'Jack', role 'manager'
```

### 1.2 Article Records
Create 2 articles:

```sql
-- article:intro with title 'Introduction to Agent Memory', category 'tutorial'
-- article:advanced with title 'Advanced Patterns', category 'advanced'
```

### 1.3 Nested Objects
Create 1 user with nested profile:

```sql
-- user:admin with:
--   name: 'Admin'
--   profile: { role: 'lead', team: 'engineering', skills: ['python', 'rust'] }
```

**Verification:**
```sql
SELECT * FROM user;
SELECT * FROM article;
```

---

## Exercise 2: SELECT (3 points)

### 2.1 Basic Queries
Write queries to:
- Get all users (1 point)
- Get only names from user table (1 point)

### 2.2 Filters
- Get users where role is 'developer' (1 point)

### 2.3 Ordering & Limits
- Get sessions ordered by started DESC, limit 5 (1 point)

### 2.4 Nested Access
- Get the city from nested profile (1 point)

**Verification:**
```sql
-- Run your queries and show results
SELECT * FROM user WHERE role = 'developer';
```

---

## Exercise 3: UPDATE (2 points)

### 3.1 Simple Updates
- Change user:john's role to 'senior developer'
- Increment article:intro's views by 1

### 3.2 Conditional Update
- Update all 'active' sessions to 'completed' with current time

### 3.3 Nested Update
- Change user:admin's team to 'product'

**Verification:**
```sql
SELECT * FROM user;
SELECT * FROM session;
```

---

## Exercise 4: DELETE (1 point)

### 4.1 Delete Records
- Delete article:advanced
- Delete sessions where started is older than 30 days

**Verification:**
```sql
SELECT * FROM article;
```

---

## Exercise 5: Data Types (2 points)

### 5.1 Type Conversions
Write queries using type functions:

- Convert number 42 to string and back
- Get the length of array [1,2,3,4,5]
- Convert 'HELLO' to lowercase

### 5.2 Date/Time
- Get current time
- Get time 1 hour from now

### 5.3 Math
- Calculate: (10 + 5) * 2
- Round 3.14159

**Verification:**
```sql
SELECT string::lower('HELLO');
SELECT math::round(3.14159);
```

---

## Bonus Challenge (2 points)

Create a complete session flow:

1. Create a session for user:john
2. Add 2 entities to the session
3. Trace 2 decisions
4. Update session status to 'completed'
5. Query back all data

```sql
-- Step 1: Create session
CREATE session SET user_id = 'user:john', status = 'active', started = time::now();

-- Step 2: Add entities (use the session ID)
CREATE entity SET session = 'session:YOUR_ID', type = 'person', name = 'John';
CREATE entity SET session = 'session:YOUR_ID', type = 'company', name = 'ACME';

-- Step 3: Trace decisions
CREATE decision SET session = 'session:YOUR_ID', action = 'search', tool = 'article';
CREATE decision SET session = 'session:YOUR_ID', action = 'respond', tool = 'llm';

-- Step 4: Complete session
UPDATE session:YOUR_ID SET status = 'completed', ended = time::now();

-- Step 5: Query all
SELECT * FROM session WHERE id = 'session:YOUR_ID';
SELECT * FROM entity WHERE session = 'session:YOUR_ID';
SELECT * FROM decision WHERE session = 'session:YOUR_ID';
```

---

## Grading

| Exercise | Points |
|----------|--------|
| Exercise 1: CREATE | 2 |
| Exercise 2: SELECT | 3 |
| Exercise 3: UPDATE | 2 |
| Exercise 4: DELETE | 1 |
| Exercise 5: Data Types | 2 |
| Bonus Challenge | 2 |
| **TOTAL** | **12** |

---

## Submit

Run all queries and capture output:

```bash
# Show all users
SELECT * FROM user;

# Show all articles
SELECT * FROM article;

# Show all sessions
SELECT * FROM session;
```

Take screenshots or copy the output and submit.