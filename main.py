# main.py - Automated outreach workflow for multiple contacts per company
from outreach_ai.agents.read_excel import read_company_data
from outreach_ai.agents.find_ceo import find_key_contacts, parse_company_url
from outreach_ai.agents.find_email import find_email
from outreach_ai.agents.generate_email import generate_email
from outreach_ai.agents.select_resume import select_resume
from outreach_ai.agents.send_email import send_email
import json
import os
import logging
import time
import random
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create directories for results
os.makedirs("outreach_results", exist_ok=True)
os.makedirs("outreach_results/contacts", exist_ok=True)
os.makedirs("outreach_results/emails", exist_ok=True)

# Location filtering settings
# Load from environment or use defaults
EXCLUDED_LOCATIONS = os.getenv("EXCLUDED_LOCATIONS", "")
if EXCLUDED_LOCATIONS:
    try:
        EXCLUDED_LOCATIONS = json.loads(EXCLUDED_LOCATIONS)
    except:
        EXCLUDED_LOCATIONS = []
else:
    # Default locations to exclude
    EXCLUDED_LOCATIONS = ["New York", "NY", "Midwest"]
    
# Midwest states for filtering
MIDWEST_STATES = ["Ohio", "Michigan", "Illinois", "Wisconsin", "Minnesota", 
                 "Indiana", "Iowa", "Missouri", "Kansas", "Nebraska", 
                 "South Dakota", "North Dakota"]

def should_skip_company(company_data):
    """Check if company should be skipped based on location or other criteria"""
    # Skip if no location info
    if "Location" not in company_data and "location" not in company_data:
        return False
    
    # Get location (case insensitive)
    location = company_data.get("Location", company_data.get("location", "")).lower()
    
    # Skip New York companies
    if any(loc.lower() in location for loc in ["new york", "ny", "nyc", "manhattan", "brooklyn"]):
        logger.info(f"Skipping New York company: {company_data.get('Company Name')}")
        return True
    
    # Skip Midwest companies
    if "midwest" in location or any(state.lower() in location for state in MIDWEST_STATES):
        logger.info(f"Skipping Midwest company: {company_data.get('Company Name')}")
        return True
    
    # Skip other excluded locations
    for excluded in EXCLUDED_LOCATIONS:
        if excluded.lower() in location:
            logger.info(f"Skipping company in {excluded}: {company_data.get('Company Name')}")
            return True
    
    return False

def process_contact(company_data, contact_data):
    """Process outreach to a single contact"""
    try:
        company_name = company_data["Company Name"]
        website = company_data.get("Website", "")
        contact_name = contact_data["name"]
        contact_title = contact_data["title"]
        contact_category = contact_data.get("category", "other")
        
        logger.info(f"Processing contact: {contact_name} ({contact_title}) at {company_name}")
        
        # Extract domain from website if needed
        company_domain = website
        if website.startswith("http"):
            company_domain = website.split("//")[1].split("/")[0]
        if company_domain.startswith("www."):
            company_domain = company_domain[4:]
        
        # Find email address
        logger.info(f"Finding email address for {contact_name} at {company_domain}...")
        email_result = find_email(contact_name, company_domain)
        
        if not email_result.get("success"):
            logger.error(f"Could not find email: {email_result.get('error', 'Unknown error')}")
            return {
                "company": company_name,
                "contact": contact_name,
                "status": "email_failed",
                "error": email_result.get("error", "Email finding failed")
            }
        
        contact_email = email_result.get("most_likely_email")
        logger.info(f"Found email: {contact_email}")
        
        # Generate personalized email based on role
        logger.info("Generating personalized email...")
        
        # Adjust approach based on contact category
        role_hint = None
        if contact_category == "data_ai":
            role_hint = "data science"
        elif contact_category == "recruiting":
            role_hint = "recruiting"
            
        email_content = generate_email(
            recipient_name=contact_name,
            company_name=company_name,
            industry=company_data.get("Industry", ""),
            company_description=company_data.get("Description", ""),
            contact_role=contact_category
        )
        
        if not email_content.get("success"):
            logger.error(f"Could not generate email: {email_content.get('error', 'Unknown error')}")
            return {
                "company": company_name,
                "contact": contact_name,
                "email": contact_email,
                "status": "email_generation_failed",
                "error": "Email generation failed"
            }
        
        # Select best resume based on contact role
        logger.info(f"Selecting best resume for {contact_category} role...")
        resume_path, confidence = select_resume(
            company_name=company_name,
            company_website=website,
            ceo_name=contact_name,
            email_content=email_content.get("body", ""),
            role_hint=role_hint
        )
        
        logger.info(f"Selected resume: {os.path.basename(resume_path)} with confidence {confidence}")
        
        # Send email with resume
        logger.info(f"Sending email to {contact_email}...")
        send_result = send_email(
            recipient_email=contact_email,
            subject=email_content.get("subject", f"Interested in {company_name}"),
            body_text=email_content.get("body", ""),
            attachment_path=resume_path
        )
        
        status = "sent" if send_result else "send_failed"
        
        # Save the email content for reference
        email_record = {
            "to": contact_email,
            "subject": email_content.get("subject", ""),
            "body": email_content.get("body", ""),
            "resume": os.path.basename(resume_path),
            "status": status,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Create safe filename
        safe_name = f"{company_name}_{contact_name}".replace(' ', '_').replace('/', '_').replace('\\', '_')
        with open(f"outreach_results/emails/{safe_name}.json", "w") as f:
            json.dump(email_record, f, indent=2)
        
        # Return result
        return {
            "company": company_name,
            "contact": {
                "name": contact_name,
                "title": contact_title,
                "category": contact_category,
                "email": contact_email
            },
            "email_subject": email_content.get("subject"),
            "resume": os.path.basename(resume_path),
            "status": status,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
    except Exception as e:
        logger.error(f"Error processing contact {contact_data.get('name', 'unknown')}: {str(e)}")
        return {
            "company": company_data.get("Company Name", "unknown"),
            "contact": contact_data.get("name", "unknown"),
            "status": "error",
            "error": str(e)
        }

def process_company(company_data):
    """Process a single company through the full outreach workflow"""
    try:
        company_name = company_data["Company Name"]
        
        # Check if company should be skipped based on location
        if should_skip_company(company_data):
            return {
                "company": company_name,
                "status": "skipped",
                "reason": "location_filtered",
                "location": company_data.get("Location", company_data.get("location", "unknown"))
            }
            
        linkedin_url = company_data["LinkedIn URL"]
        
        if not linkedin_url:
            logger.error(f"No LinkedIn URL for {company_name}")
            return {
                "company": company_name,
                "status": "failed",
                "error": "No LinkedIn URL"
            }
        
        logger.info(f"Processing company: {company_name}")
        logger.info(f"LinkedIn URL: {linkedin_url}")
        
        # Step 1: Find key contacts (leadership, data/AI, recruiter)
        logger.info("Finding key contacts...")
        
        # Normalize LinkedIn URL
        linkedin_url = parse_company_url(linkedin_url)
        
        contacts_result = find_key_contacts(linkedin_url)
        
        if "error" in contacts_result:
            logger.error(f"Could not find contacts: {contacts_result['error']}")
            return {
                "company": company_name,
                "status": "contacts_failed",
                "error": contacts_result['error']
            }
        
        # Get the key contacts from the result
        key_contacts = contacts_result.get("key_contacts", [])
        
        if not key_contacts:
            logger.error("No contacts found")
            return {
                "company": company_name,
                "status": "no_contacts",
                "error": "No contacts found"
            }
            
        logger.info(f"Found {len(key_contacts)} contacts")
        
        # Save contacts for this company
        safe_name = company_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
        contacts_file = f"outreach_results/contacts/{safe_name}.json"
        
        with open(contacts_file, "w") as f:
            json.dump({
                "company": company_name,
                "linkedin_url": linkedin_url,
                "key_contacts": key_contacts
            }, f, indent=2)
        
        # Step 2: Process each contact (find email, generate email, select resume, send)
        contact_results = []
        
        for contact in key_contacts:
            # Add a small delay between contacts at the same company
            if contact_results:  # Not the first contact
                delay = random.uniform(2, 5)  # 2-5 seconds
                logger.info(f"Waiting {delay:.1f} seconds before next contact...")
                time.sleep(delay)
                
            contact_result = process_contact(company_data, contact)
            contact_results.append(contact_result)
        
        # Step 3: Compile results
        success_count = sum(1 for r in contact_results if r.get("status") == "sent")
        
        company_result = {
            "company": company_name,
            "website": company_data.get("Website", ""),
            "linkedin": linkedin_url,
            "location": company_data.get("Location", ""),
            "contacts_processed": len(contact_results),
            "contacts_successful": success_count,
            "status": "partial" if 0 < success_count < len(contact_results) else 
                    "success" if success_count == len(contact_results) else "failed",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "contact_results": contact_results
        }
        
        # Save individual company result
        with open(f"outreach_results/{safe_name}_result.json", "w") as f:
            json.dump(company_result, f, indent=2)
            
        return company_result
        
    except Exception as e:
        logger.error(f"Error processing {company_data.get('Company Name', 'unknown')}: {str(e)}")
        return {
            "company": company_data.get("Company Name", "unknown"),
            "status": "error",
            "error": str(e)
        }

def main():
    try:
        # Get the path to the Excel file
        script_dir = Path(__file__).parent
        excel_path = script_dir / "data" / "companies.xlsx"
        
        # Ensure the Excel file exists
        if not excel_path.exists():
            logger.error(f"Excel file not found: {excel_path}")
            alternative_path = Path("outreach_ai/data/companies.xlsx")
            if alternative_path.exists():
                excel_path = alternative_path
                logger.info(f"Using alternative path: {excel_path}")
            else:
                logger.error("Could not find Excel file in expected locations")
                return
        
        logger.info(f"Reading companies from: {excel_path}")
        
        # Get list of companies from Excel
        companies = read_company_data(str(excel_path))
        logger.info(f"Found {len(companies)} companies in Excel file")
        
        # Log excluded locations
        logger.info(f"Excluded locations: {EXCLUDED_LOCATIONS}")
        
        # Create/reset progress tracking files
        with open("outreach_results/progress.txt", "w") as progress_file:
            progress_file.write(f"Starting outreach to {len(companies)} companies at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            progress_file.write(f"Excluded locations: {', '.join(EXCLUDED_LOCATIONS)}\n\n")
        
        with open("outreach_results/all_results.json", "w") as f:
            json.dump([], f)
        
        # Process each company
        all_results = []
        skipped_count = 0
        
        for i, company in enumerate(companies):
            company_name = company.get('Company Name', f"Company {i+1}")
            logger.info(f"Processing company {i+1}/{len(companies)}: {company_name}")
            
            # Update progress file
            with open("outreach_results/progress.txt", "a") as progress_file:
                progress_file.write(f"Starting {company_name} at {time.strftime('%H:%M:%S')}\n")
            
            # Process the company
            result = process_company(company)
            all_results.append(result)
            
            # Count skipped companies
            if result.get("status") == "skipped":
                skipped_count += 1
            
            # Update progress file
            with open("outreach_results/progress.txt", "a") as progress_file:
                progress_file.write(f"Finished {company_name} with status: {result.get('status')}\n")
                if result.get("status") == "skipped":
                    progress_file.write(f"Reason: {result.get('reason')} - {result.get('location')}\n")
                if result.get('contacts_processed'):
                    progress_file.write(f"Contacts processed: {result.get('contacts_processed')}\n")
                if result.get('contacts_successful'):
                    progress_file.write(f"Successful contacts: {result.get('contacts_successful')}\n")
                if result.get('error'):
                    progress_file.write(f"Error: {result.get('error')}\n")
                progress_file.write("---\n")
            
            # Save all results so far
            with open("outreach_results/all_results.json", "w") as f:
                json.dump(all_results, f, indent=2)
            
            # Pause between companies to avoid rate limits
            if i < len(companies) - 1:
                delay = random.uniform(30, 60)  # 30-60 seconds
                logger.info(f"Pausing for {delay:.1f} seconds before next company...")
                time.sleep(delay)
        
        # Summarize results
        processed_companies = [r for r in all_results if r.get("status") != "skipped"]
        total_contacts = sum(r.get("contacts_processed", 0) for r in processed_companies)
        successful_contacts = sum(r.get("contacts_successful", 0) for r in processed_companies)
        successful_companies = sum(1 for r in processed_companies if r.get("status") in ["success", "partial"])
        failed_companies = sum(1 for r in processed_companies if r.get("status") not in ["success", "partial", "skipped"])
        
        logger.info(f"Completed outreach process:")
        logger.info(f"Total companies: {len(companies)}")
        logger.info(f"Skipped companies: {skipped_count}")
        logger.info(f"Processed companies: {len(processed_companies)}")
        logger.info(f"Successful companies: {successful_companies}")
        logger.info(f"Failed companies: {failed_companies}")
        logger.info(f"Total contacts processed: {total_contacts}")
        logger.info(f"Successful contacts: {successful_contacts}")
        
        with open("outreach_results/summary.txt", "w") as f:
            f.write(f"Outreach completed at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total companies: {len(companies)}\n")
            f.write(f"Skipped companies: {skipped_count}\n")
            f.write(f"Processed companies: {len(processed_companies)}\n")
            f.write(f"Successful companies: {successful_companies}\n")
            f.write(f"Failed companies: {failed_companies}\n")
            f.write(f"Total contacts processed: {total_contacts}\n")
            f.write(f"Successful contacts: {successful_contacts}\n\n")
            
            f.write("Excluded Locations:\n")
            for location in EXCLUDED_LOCATIONS:
                f.write(f"- {location}\n")
            f.write("\n")
            
            f.write("Company Details:\n")
            for result in all_results:
                if result.get("status") == "skipped":
                    f.write(f"- {result.get('company')}: SKIPPED ({result.get('location', '')})\n")
                else:
                    f.write(f"- {result.get('company')}: {result.get('status')}")
                    if result.get("contacts_processed"):
                        f.write(f" ({result.get('contacts_successful', 0)}/{result.get('contacts_processed', 0)} contacts)")
                    if result.get("error"):
                        f.write(f" (Error: {result.get('error')})")
                    f.write("\n")
        
        return all_results
        
    except Exception as e:
        logger.error(f"Critical error in main workflow: {str(e)}")
        # Take emergency backup of results so far
        emergency_file = f"outreach_results/emergency_backup_{time.strftime('%Y%m%d_%H%M%S')}.json"
        try:
            with open(emergency_file, "w") as f:
                json.dump({"error": str(e), "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')}, f)
            logger.info(f"Emergency backup saved to {emergency_file}")
        except:
            pass
        return {"error": str(e)}

if __name__ == "__main__":
    main()