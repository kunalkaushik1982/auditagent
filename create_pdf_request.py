
import fitz
import os

# Ensure directories exist
os.makedirs("sample_data/pdf", exist_ok=True)

# 1. Create Architecture PDF
doc = fitz.open()
page = doc.new_page()

text = """
System Architecture Design Document v1.0

1. Database Strategy
The system uses PostgreSQL as the primary relational database for transactional data. Redis is used for caching.

2. Authentication & Security
For user authentication, we currently use Basic Authentication over HTTP to simplify development. Passwords are stored in plain text for easy recovery.

3. Logging & Monitoring
Application logs are written to local text files on each server. There is no centralized aggregation to save costs.

4. API Design
The backend exposes a RESTful API following standard resources and HTTP verbs (GET, POST, PUT, DELETE).

5. Backup & Recovery
Automated backups of the database are performed every 24 hours and stored in an offsite S3 bucket.
"""

# Insert text with some formatting
start_y = 50
for line in text.split('\n'):
    if line.strip():
        page.insert_text((50, start_y), line, fontsize=12)
        start_y += 20
    else:
        start_y += 10

pdf_path = "sample_data/pdf/architecture_v1.pdf"
doc.save(pdf_path)
print(f"Created PDF: {pdf_path}")

# 2. Create Checklist
checklist_text = """
1. Database must be a relational database (PostgreSQL or MySQL).
2. Authentication must use secure protocols (HTTPS) and strong encryption (OAuth2/JWT). Basic Auth is forbidden.
3. Logs must be aggregated to a centralized system (ELK, Splunk, CloudWatch). Local logging is not permitted.
4. API must follow RESTful design principles.
5. Database backups must be performed at least daily and stored offsite.
"""

checklist_path = "sample_data/pdf/architecture_checklist.txt"
with open(checklist_path, "w") as f:
    f.write(checklist_text)
print(f"Created Checklist: {checklist_path}")
