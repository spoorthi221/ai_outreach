# TODO: Predict or find email address using Hunter API
import os
import requests
import json
import time
import smtplib
import dns.resolver
import logging
from dotenv import load_dotenv
from email.utils import parseaddr

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# API Keys
HUNTER_API_KEY = os.getenv("HUNTER_API_KEY")
APOLLO_API_KEY = os.getenv("APOLLO_API_KEY")

class EmailFinder:
    def __init__(self):
        self.hunter_api_key = HUNTER_API_KEY
        self.apollo_api_key = APOLLO_API_KEY
        
    def find_email(self, full_name, domain):
        """Main method to find a CEO's email using multiple methods"""
        logger.info(f"Starting email search for {full_name} at {domain}")
        
        if not full_name or not domain:
            return {"error": "Full name and domain are required"}
        
        # Clean inputs
        full_name = full_name.strip()
        domain = domain.strip().lower()
        if domain.startswith("http"):
            domain = domain.split("//")[1]
        if domain.startswith("www."):
            domain = domain.replace("www.", "")
        if "/" in domain:
            domain = domain.split("/")[0]
            
        # Split the name
        name_parts = full_name.split()
        if len(name_parts) < 2:
            return {"error": "Full name must include first and last name"}
            
        first_name = name_parts[0]
        last_name = name_parts[-1]
        
        results = {
            "full_name": full_name,
            "domain": domain,
            "first_name": first_name, 
            "last_name": last_name,
            "sources": {},
            "valid_emails": []
        }
        
        # Method 1: Try Hunter.io API
        hunter_result = self.try_hunter_io(first_name, last_name, domain)
        results["sources"]["hunter"] = hunter_result
        
        # Method 2: Try Apollo.io API
        apollo_result = self.try_apollo_io(first_name, last_name, domain)
        results["sources"]["apollo"] = apollo_result
        
        # Method 3: Generate email permutations and verify them
        permutation_results = self.generate_and_verify_emails(first_name, last_name, domain)
        results["sources"]["permutations"] = permutation_results
        
        # Combine and rank results
        all_emails = []
        
        # Add Hunter.io emails if found
        if hunter_result.get("emails"):
            all_emails.extend(hunter_result["emails"])
            
        # Add Apollo emails if found
        if apollo_result.get("emails"):
            all_emails.extend(apollo_result["emails"])
            
        # Add valid permutation emails
        if permutation_results.get("valid_emails"):
            all_emails.extend(permutation_results["valid_emails"])
            
        # Remove duplicates while preserving order
        unique_emails = []
        for email in all_emails:
            if email not in unique_emails:
                unique_emails.append(email)
        
        results["valid_emails"] = unique_emails
        
        # Determine the most likely email
        if unique_emails:
            # Prioritize verified emails
            verified_emails = [e for e in unique_emails if self.is_deliverable(e)]
            if verified_emails:
                results["most_likely_email"] = verified_emails[0]
            else:
                results["most_likely_email"] = unique_emails[0]
        else:
            # If no emails found, generate a best guess
            results["most_likely_email"] = f"{first_name.lower()}.{last_name.lower()}@{domain}"
            results["note"] = "No verified emails found. This is a best guess based on common patterns."
            
        return results
            
    def try_hunter_io(self, first_name, last_name, domain):
        """Use Hunter.io API to find email"""
        result = {
            "status": "unknown",
            "emails": []
        }
        
        if not self.hunter_api_key:
            result["status"] = "skipped"
            result["message"] = "Hunter.io API key not configured"
            return result
            
        try:
            # Try domain search first to find pattern
            domain_search_url = f"https://api.hunter.io/v2/domain-search?domain={domain}&api_key={self.hunter_api_key}"
            domain_response = requests.get(domain_search_url)
            domain_data = domain_response.json()
            
            if domain_response.status_code == 200 and domain_data.get("data"):
                # Extract email pattern if available
                pattern = domain_data["data"].get("pattern")
                
                # Look for the specific person in the results
                if domain_data["data"].get("emails"):
                    for email_data in domain_data["data"]["emails"]:
                        if email_data.get("first_name", "").lower() == first_name.lower() and \
                           email_data.get("last_name", "").lower() == last_name.lower():
                            result["emails"].append(email_data["value"])
                
                # If not found in results, try email finder endpoint
                if not result["emails"]:
                    finder_url = f"https://api.hunter.io/v2/email-finder?domain={domain}&first_name={first_name}&last_name={last_name}&api_key={self.hunter_api_key}"
                    finder_response = requests.get(finder_url)
                    finder_data = finder_response.json()
                    
                    if finder_response.status_code == 200 and finder_data.get("data"):
                        email = finder_data["data"].get("email")
                        if email:
                            result["emails"].append(email)
                            result["confidence"] = finder_data["data"].get("score", 0)
            
            result["status"] = "success" if result["emails"] else "no_results"
            return result
                
        except Exception as e:
            logger.error(f"Hunter.io API error: {str(e)}")
            result["status"] = "error"
            result["message"] = str(e)
            return result
    
    def try_apollo_io(self, first_name, last_name, domain):
        """Use Apollo.io API to find email"""
        result = {
            "status": "unknown",
            "emails": []
        }
        
        if not self.apollo_api_key:
            result["status"] = "skipped"
            result["message"] = "Apollo.io API key not configured"
            return result
            
        try:
            # Endpoint for Apollo's People Search API
            url = "https://api.apollo.io/v1/people/search"
            
            # Build the query to search for the person
            payload = {
                "api_key": self.apollo_api_key,
                "q_organization_domains": domain,
                "q_first_name": first_name,
                "q_last_name": last_name,
                "page": 1,
                "per_page": 5  # Limit to 5 results
            }
            
            response = requests.post(url, json=payload)
            data = response.json()
            
            if response.status_code == 200 and data.get("people"):
                for person in data["people"]:
                    if person.get("email"):
                        result["emails"].append(person["email"])
                    
                    # Also check for email pattern
                    if not result["emails"] and person.get("organization") and person["organization"].get("email_pattern"):
                        pattern = person["organization"]["email_pattern"]
                        # Apply pattern to generate email
                        email = self._apply_pattern(pattern, first_name, last_name, domain)
                        if email:
                            result["emails"].append(email)
                            result["note"] = "Generated from company email pattern"
            
            result["status"] = "success" if result["emails"] else "no_results"
            return result
                
        except Exception as e:
            logger.error(f"Apollo.io API error: {str(e)}")
            result["status"] = "error"
            result["message"] = str(e)
            return result
    
    def generate_and_verify_emails(self, first_name, last_name, domain):
        """Generate common email permutations and verify them"""
        result = {
            "status": "unknown",
            "permutations": [],
            "valid_emails": []
        }
        
        try:
            # Clean and normalize names
            first = first_name.lower().strip()
            last = last_name.lower().strip()
            first_initial = first[0] if first else ""
            last_initial = last[0] if last else ""
            
            # Common email patterns
            patterns = [
                f"{first}@{domain}",                     # john@example.com
                f"{first}.{last}@{domain}",              # john.doe@example.com
                f"{first}{last}@{domain}",               # johndoe@example.com
                f"{last}.{first}@{domain}",              # doe.john@example.com
                f"{first_initial}{last}@{domain}",       # jdoe@example.com
                f"{first}{last_initial}@{domain}",       # johnd@example.com
                f"{first_initial}.{last}@{domain}",      # j.doe@example.com
                f"{first}-{last}@{domain}",              # john-doe@example.com
                f"{last}{first}@{domain}",               # doejohn@example.com
                f"{first}_{last}@{domain}",              # john_doe@example.com
                f"{first_initial}{last_initial}@{domain}" # jd@example.com
            ]
            
            result["permutations"] = patterns
            
            # Verify each pattern with a basic check first
            mx_records_exist = self._check_mx_records(domain)
            
            if not mx_records_exist:
                result["status"] = "no_mx_records"
                return result
                
            # Verify each email
            for email in patterns:
                if self.is_deliverable(email):
                    result["valid_emails"].append(email)
                    
            result["status"] = "success" if result["valid_emails"] else "no_valid_emails"
            return result
                
        except Exception as e:
            logger.error(f"Email permutation error: {str(e)}")
            result["status"] = "error"
            result["message"] = str(e)
            return result
    
    def _check_mx_records(self, domain):
        """Check if domain has MX records (required for email)"""
        try:
            mx_records = dns.resolver.resolve(domain, 'MX')
            return len(mx_records) > 0
        except Exception:
            return False
    
    def is_deliverable(self, email):
        """Check if an email is potentially deliverable using SMTP verification"""
        # Basic validation
        if not self._is_valid_email_format(email):
            return False
            
        # Extract domain
        _, domain = email.split('@', 1)
        
        # Skip SMTP check in testing
        if os.getenv("SKIP_SMTP_CHECK") == "true":
            return True
            
        # Check deliverability with SMTP
        try:
            # Try to get MX records for the domain
            mx_records = dns.resolver.resolve(domain, 'MX')
            mx_host = str(mx_records[0].exchange)
            
            # Connect to the mail server
            smtp = smtplib.SMTP(timeout=10)
            smtp.connect(mx_host)
            smtp.helo(domain)
            smtp.mail('')
            code, _ = smtp.rcpt(email)
            smtp.quit()
            
            # Return True if email exists (250 is success code)
            return code == 250
        except Exception:
            # If any error occurs, we can't verify
            # But don't rule it out completely
            return None  # Uncertain
    
    def _is_valid_email_format(self, email):
        """Check if email has valid format"""
        if not email or '@' not in email:
            return False
            
        # Use parseaddr to validate format
        name, addr = parseaddr(email)
        return addr == email and '.' in addr.split('@')[1]
    
    def _apply_pattern(self, pattern, first_name, last_name, domain):
        """Apply an email pattern to generate an email address"""
        if not pattern:
            return None
            
        # Normalize names
        first = first_name.lower()
        last = last_name.lower()
        f_initial = first[0] if first else ""
        l_initial = last[0] if last else ""
        
        # Replace patterns with actual values
        email = pattern.lower()
        email = email.replace("{first}", first)
        email = email.replace("{last}", last)
        email = email.replace("{f}", first)
        email = email.replace("{l}", last)
        email = email.replace("{fi}", f_initial)
        email = email.replace("{li}", l_initial)
        email = email.replace("{f1}", f_initial)
        email = email.replace("{l1}", l_initial)
        
        # Add domain if missing
        if "@" not in email:
            email = f"{email}@{domain}"
        elif not email.endswith(f"@{domain}"):
            email_parts = email.split("@")
            email = f"{email_parts[0]}@{domain}"
            
        return email


def find_email(full_name, company_domain):
    """Main function to find email address for a person at a company"""
    finder = EmailFinder()
    result = finder.find_email(full_name, company_domain)
    
    # Format the output
    if "error" in result:
        return {
            "success": False,
            "error": result["error"]
        }
    
    output = {
        "success": True,
        "person": {
            "full_name": result["full_name"],
            "first_name": result["first_name"],
            "last_name": result["last_name"]
        },
        "company_domain": result["domain"],
        "most_likely_email": result.get("most_likely_email", ""),
        "confidence": "high" if result.get("sources", {}).get("hunter", {}).get("emails") or 
                            result.get("sources", {}).get("apollo", {}).get("emails") else "medium",
        "all_possible_emails": result.get("valid_emails", [])
    }
    
    if "note" in result:
        output["note"] = result["note"]
        
    return output


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 3:
        print("Usage: python email_finder.py 'Full Name' company_domain.com")
        sys.exit(1)
        
    full_name = sys.argv[1]
    company_domain = sys.argv[2]
    
    result = find_email(full_name, company_domain)
    print(json.dumps(result, indent=2))
    
    # Print user-friendly output
    print(f"\n{'='*50}")
    print(f"Email Finder Results for {full_name} at {company_domain}")
    print(f"{'='*50}")
    
    if result["success"]:
        print(f"\n✅ MOST LIKELY EMAIL: {result['most_likely_email']}")
        print(f"   CONFIDENCE: {result['confidence'].upper()}")
        
        if len(result['all_possible_emails']) > 1:
            print("\nOther possible email formats:")
            for i, email in enumerate(result['all_possible_emails']):
                if email != result['most_likely_email']:
                    print(f"  - {email}")
        
        if "note" in result:
            print(f"\nNote: {result['note']}")
    else:
        print(f"\n❌ ERROR: {result['error']}")
    
    print(f"\n{'='*50}")


def process_bulk_csv(input_csv, output_csv):
    """Process a CSV file containing names and domains to find emails"""
    import csv
    
    try:
        with open(input_csv, 'r') as infile:
            reader = csv.DictReader(infile)
            fieldnames = reader.fieldnames + ['most_likely_email', 'confidence', 'all_possible_emails']
            
            with open(output_csv, 'w', newline='') as outfile:
                writer = csv.DictWriter(outfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for row in reader:
                    full_name = row.get('full_name') or f"{row.get('first_name', '')} {row.get('last_name', '')}".strip()
                    domain = row.get('domain') or row.get('company_domain')
                    
                    if not full_name or not domain:
                        logger.warning(f"Skipping row: Missing name or domain: {row}")
                        continue
                    
                    logger.info(f"Processing: {full_name} at {domain}")
                    
                    # Find email
                    result = find_email(full_name, domain)
                    
                    # Update row with results
                    if result["success"]:
                        row['most_likely_email'] = result['most_likely_email']
                        row['confidence'] = result['confidence']
                        row['all_possible_emails'] = ','.join(result['all_possible_emails'])
                    else:
                        row['most_likely_email'] = 'ERROR'
                        row['confidence'] = 'low'
                        row['all_possible_emails'] = result.get('error', 'Unknown error')
                    
                    # Write to output file
                    writer.writerow(row)
                    
                    # Avoid rate limits
                    time.sleep(1)
        
        logger.info(f"Bulk processing complete. Results saved to {output_csv}")
        return {"success": True, "output_file": output_csv}
                    
    except Exception as e:
        logger.error(f"Error processing bulk CSV: {str(e)}")
        return {"success": False, "error": str(e)}


# Command line interface
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Find email addresses for business contacts")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Single email finder
    single_parser = subparsers.add_parser("find", help="Find email for a single person")
    single_parser.add_argument("full_name", help="Full name of the person")
    single_parser.add_argument("domain", help="Company domain name")
    
    # Bulk CSV processor
    bulk_parser = subparsers.add_parser("bulk", help="Process a CSV file of contacts")
    bulk_parser.add_argument("input_csv", help="Input CSV file with full_name and domain columns")
    bulk_parser.add_argument("--output", help="Output CSV file path", default="emails_output.csv")
    
    args = parser.parse_args()
    
    if args.command == "find":
        result = find_email(args.full_name, args.domain)
        print(json.dumps(result, indent=2))
        
        # Print user-friendly output
        print(f"\n{'='*50}")
        print(f"Email Finder Results for {args.full_name} at {args.domain}")
        print(f"{'='*50}")
        
        if result["success"]:
            print(f"\n✅ MOST LIKELY EMAIL: {result['most_likely_email']}")
            print(f"   CONFIDENCE: {result['confidence'].upper()}")
            
            if len(result['all_possible_emails']) > 1:
                print("\nOther possible email formats:")
                for i, email in enumerate(result['all_possible_emails']):
                    if email != result['most_likely_email']:
                        print(f"  - {email}")
            
            if "note" in result:
                print(f"\nNote: {result['note']}")
        else:
            print(f"\n❌ ERROR: {result['error']}")
        
        print(f"\n{'='*50}")
        
    elif args.command == "bulk":
        result = process_bulk_csv(args.input_csv, args.output)
        if result["success"]:
            print(f"✅ Successfully processed contacts. Results saved to {result['output_file']}")
        else:
            print(f"❌ Error: {result['error']}")
    else:
        parser.print_help()