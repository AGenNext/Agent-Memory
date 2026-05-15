# Course: Querying Fundamentals
# SurrealDB Basics

## Overview

Welcome to the first course in Agent Memory! This course teaches you the fundamentals of SurrealQL - SurrealDB's powerful query language.

**Duration:** 2 hours  
**Level:** Beginner  
**Prerequisites:** None

---

## Learning Objectives

By the end of this course, you will:
- [ ] Understand SurrealQL basics
- [ ] Insert data with CREATE
- [ ] Read data with SELECT
- [ ] Modify data with UPDATE
- [ ] Delete data with DELETE
- [ ] Use basic数据类型

---

## Lesson 1.1: Introduction to SurrealQL

### What is SurrealQL?

SurrealQL is SurrealDB's query language. It combines:
- **SQL simplicity** - Familiar SELECT, CREATE, UPDATE syntax
- **NoSQL flexibility** - Dynamic schemas, nested documents
- **Graph power** - Native relationship traversal

### Why SurrealQL?

```sql
-- Looks like SQL
SELECT * FROM user WHERE name = 'Alice';

-- But handles nested
SELECT profile.bio FROM user;

-- And graphs
SELECT <-authored<-article FROM user;
```

### Code Examples

```sql
-- Print current time
SELECT time::now();

-- Simple math
SELECT 2 + 2 AS result;

-- String operations
SELECT string::upper('hello') AS greeting;
```

### Your Turn

Try these in the SurrealSQL REPL:

```bash
surreal sql
```

1. Print current time
2. Calculate 10 * 5
3. Print your name in uppercase

---

## Lesson 1.2: CREATE - Inserting Data

The CREATE statement adds new records to the database.

### Basic Syntax

```sql
CREATE table_name SET field = value, field2 = value2;
```

### Example 1: Simple Record

```sql
-- Create a session
CREATE session SET 
    user_id = 'user:alice',
    status = 'active';
```

**Result:**
```json
{
    "id": "session:abc123",
    "user_id": "user:alice",
    "status": "active"
}
```

### Example 2: With Specific ID

```sql
-- Create with your own ID
CREATE user:alice SET 
    name = 'Alice',
    role = 'developer';
```

### Example 3: Nested Objects

```sql
-- Store profile
CREATE user:bob SET 
    name = 'Bob',
    profile = {
        bio: 'Software engineer',
        city: 'San Francisco',
        tags: ['python', 'ai']
    };
```

### Example 4: Arrays

```sql
-- Create with arrays
CREATE article SET 
    title = 'Getting Started',
    tags = ['tutorial', 'beginner', 'guide'],
    ratings = [4, 5, 3, 4, 5];
```

### Example 5: Date/Time

```sql
-- Create with timestamp
CREATE session SET 
    user_id = 'user:charlie',
    started = time::now();
```

### Exercise 1

Create the following records:

```sql
-- 1. A user named 'diana' who is a 'manager'
CREATE user:diana SET name = 'Diana', role = 'manager';

-- 2. An article about database security
CREATE article:security SET 
    title = 'Database Security Guide',
    category = 'security',
    content = 'Best practices for DB security';
```

### Exercise 2

Create a user with a nested profile:

```sql
CREATE user:evans SET 
    name = 'Evans',
    profile = {
        company: 'TechCorp',
        position: 'CTO',
        location: { city: 'NYC', country: 'USA' }
    };
```

### Solution

```sql
-- Exercise 1
CREATE user:diana SET name = 'Diana', role = 'manager';
CREATE article:security SET title = 'Database Security Guide', category = 'security', content = 'Best practices for DB security';

-- Exercise 2
CREATE user:evans SET name = 'Evans', profile = { company: 'TechCorp', position: 'CTO', location: { city: 'NYC', country: 'USA' } };
```

---

## Lesson 1.3: SELECT - Reading Data

The SELECT statement retrieves data from the database.

### Basic Syntax

```sql
SELECT fields FROM table [WHERE condition];
```

### Example 1: Select All

```sql
-- Get all users
SELECT * FROM user;
```

### Example 2: Specific Fields

```sql
-- Get only name and role
SELECT name, role FROM user;
```

### Example 3: With WHERE

```sql
-- Filter by role
SELECT * FROM user WHERE role = 'developer';
```

### Example 4: Ordering

```sql
-- Newest sessions first
SELECT * FROM session ORDER BY started DESC;
```

### Example 5: Limit Results

```sql
-- Get first 10
SELECT * FROM session LIMIT 10;
```

### Example 6: Nested Field Access

```sql
-- Access nested object
SELECT profile.city, profile.country FROM user;
```

### Example 7: Array Index

```sql
-- Get first tag
SELECT tags[0] FROM article;
```

### Exercise 1

1. Select all fields from the user table
2. Select only name from user where role is 'manager'
3. Select articles ordered by title

### Solutions

```sql
-- 1
SELECT * FROM user;

-- 2
SELECT name FROM user WHERE role = 'manager';

-- 3
SELECT * FROM article ORDER BY title;
```

---

## Lesson 1.4: UPDATE - Modifying Data

The UPDATE statement modifies existing records.

### Basic Syntax

```sql
UPDATE record_id SET field = new_value;
```

### Example 1: Simple Update

```sql
-- Change user role
UPDATE user:alice SET role = 'admin';
```

### Example 2: Multiple Fields

```sql
-- Update multiple
UPDATE user:alice SET 
    role = 'admin',
    status = 'active';
```

### Example 3: Conditional Update

```sql
-- Update based on condition
UPDATE session SET 
    status = 'completed',
    ended = time::now() 
WHERE status = 'active';
```

### Example 4: Increment

```sql
-- Increment counter
UPDATE article SET views = views + 1;
```

### Example 5: Nested Update

```sql
-- Update nested field
UPDATE user:bob SET profile.city = 'LA';
```

### Exercise 1

1. Update user:alice role to 'superadmin'
2. Increment views on article:security
3. Close all active sessions

### Solutions

```sql
-- 1
UPDATE user:alice SET role = 'superadmin';

-- 2
UPDATE article:security SET views = views + 1;

-- 3
UPDATE session SET status = 'completed', ended = time::now() WHERE status = 'active';
```

---

## Lesson 1.5: DELETE - Removing Data

The DELETE statement removes records.

### Basic Syntax

```sql
DELETE FROM table WHERE condition;
-- Or
DELETE record_id;
```

### Example 1: Delete Specific

```sql
-- Delete specific record
DELETE user:alice;
```

### Example 2: Delete with Condition

```sql
-- Delete old sessions
DELETE FROM session WHERE started < time::now() - 30d;
```

### Example 3: Delete by Field Value

```sql
-- Delete cancelled tickets
DELETE FROM ticket WHERE status = 'cancelled';
```

### Exercise 1

1. Delete user named 'diana'
2. Delete sessions older than 7 days

### Solutions

```sql
-- 1
DELETE FROM user WHERE name = 'diana';

-- 2
DELETE FROM session WHERE started < time::now() - 7d;
```

---

## Lesson 1.6: Data Types

SurrealDB supports rich data types.

### Basic Types

```sql
-- Strings
SELECT 'hello' AS string;

-- Numbers
SELECT 42 AS integer;
SELECT 3.14 AS float;

-- Booleans
SELECT true AS enabled;
SELECT false AS disabled;

-- Dates
SELECT time::now() AS now;

-- Durations
SELECT 1h AS hour;
SELECT 30m AS minutes;
```

### Type Functions

```sql
-- String functions
SELECT string::upper('hello');  -- HELLO
SELECT string::lower('HELLO');  -- hello
SELECT string::len('hello');    -- 5

-- Math functions
SELECT math::round(3.7);  -- 4
SELECT math::floor(3.7);   -- 3
SELECT math::sqrt(16);    -- 4

-- Array functions
SELECT array::len([1, 2, 3]);  -- 3
```

### Exercise 1

1. Print 'agent memory' in uppercase
2. Round 3.14159
3. Get the length of the array [1, 2, 3, 4, 5]

### Solutions

```sql
-- 1
SELECT string::upper('agent memory');

-- 2
SELECT math::round(3.14159);

-- 3
SELECT array::len([1, 2, 3, 4, 5]);
```

---

## Summary

In this course, you learned:

| Command | Purpose |
|--------|---------|
| CREATE | Insert records |
| SELECT | Read records |
| UPDATE | Modify records |
| DELETE | Remove records |

### Next Course

[Course 2: Advanced Querying →](../02-advanced-querying/README.md)

Learn about LIVE queries, full-text search, and vector similarity!

---

## Additional Resources

- [SurrealDB Docs: Sample Queries](https://surrealdb.com/docs/sample-queries)
- [SurrealQL Reference](https://surrealdb.com/docs/surrealql)
- [Interactive Playground](https://surrealist.com)