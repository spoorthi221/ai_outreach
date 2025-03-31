from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
import os
import time
import random
import json

# Load .env credentials
load_dotenv()
EMAIL = os.getenv("LINKEDIN_EMAIL")
PASSWORD = os.getenv("LINKEDIN_PASSWORD")

# Check if credentials are available
if not EMAIL or not PASSWORD:
    raise ValueError("LinkedIn credentials not found in .env file. Please set LINKEDIN_EMAIL and LINKEDIN_PASSWORD.")

# Key roles we're looking for (in priority order)
TARGET_ROLES = [
    {"category": "leadership", "keywords": ["ceo", "chief executive officer", "founder", "co-founder", "cofounder", "president"]},
    {"category": "data_ai", "keywords": ["head of data", "data science", "machine learning", "ai", "artificial intelligence", "chief data", "data officer"]},
    {"category": "recruiting", "keywords": ["talent", "recruit", "hiring", "hr", "human resources", "people operations"]}
]

def random_sleep(min_seconds=1, max_seconds=2):
    """Add random delay to mimic human behavior but shorter to avoid timeouts"""
    delay = random.uniform(min_seconds, max_seconds)
    time.sleep(delay)

def login_linkedin(page):
    """Login to LinkedIn"""
    print("🔐 Navigating to LinkedIn login page...")
    page.goto("https://www.linkedin.com/login", timeout=30000)
    random_sleep()
    
    # Fill in login form
    try:
        print("🧾 Entering credentials...")
        page.fill("input#username", EMAIL)
        random_sleep()
        page.fill("input#password", PASSWORD)
        random_sleep()
        page.click("button[type=submit]")
        
        # Wait for navigation
        page.wait_for_load_state("networkidle", timeout=20000)
        random_sleep(2, 3)
        
        # Check login status
        if page.url.startswith("https://www.linkedin.com/feed"):
            print("✅ Login successful")
            return True
        else:
            print(f"⚠️ Current URL after login: {page.url}")
            if "challenge" in page.url or "checkpoint" in page.url:
                print("⚠️ LinkedIn security check detected - manual intervention may be needed")
                # Wait a bit longer for potential manual intervention
                time.sleep(15)
                if page.url.startswith("https://www.linkedin.com/feed"):
                    print("✅ Login successful after security check")
                    return True
            
            # Try to continue anyway - sometimes we're logged in despite not being on the feed page
            try:
                is_logged_in = page.is_visible("nav.global-nav", timeout=5000)
                if is_logged_in:
                    print("✅ Global navigation detected. Login confirmed.")
                    return True
            except:
                pass
                
            print("❌ Login may have failed but continuing anyway")
            return True
    except Exception as e:
        print(f"❌ Login error: {str(e)}")
        # Take a screenshot of the login page for debugging
        try:
            page.screenshot(path="login_error.png")
            print("📸 Saved screenshot of login error")
        except:
            pass
        return False

def get_role_category(title):
    """Determine role category based on title keywords"""
    title_lower = title.lower()
    
    for role in TARGET_ROLES:
        if any(keyword in title_lower for keyword in role["keywords"]):
            return role["category"]
    
    return "other"

def extract_people_data(page):
    """Extract people data using JavaScript"""
    try:
        # Take screenshot for debugging
        page.screenshot(path="people_page_debug.png")
        print("📸 Saved screenshot of people page")
        
        # This JavaScript will extract people based on visible UI elements
        people_data = page.evaluate("""
            () => {
                // Keywords to look for in titles
                const leadershipTitles = ["ceo", "chief executive", "founder", "co-founder", "cofounder", "president", "owner"];
                const dataTitles = ["head of data", "data science", "machine learning", "ai", "artificial intelligence", "chief data", "data officer"];
                const recruitingTitles = ["talent", "recruit", "hiring", "hr", "human resources", "people operations"];
                
                // Helper function to check if title matches our target categories
                const getRoleCategory = (title) => {
                    if (!title) return "other";
                    const lowerTitle = title.toLowerCase();
                    
                    if (leadershipTitles.some(t => lowerTitle.includes(t))) return "leadership";
                    if (dataTitles.some(t => lowerTitle.includes(t))) return "data_ai";
                    if (recruitingTitles.some(t => lowerTitle.includes(t))) return "recruiting";
                    
                    return "other";
                };
                
                // Look for all people cards and list items
                const results = [];
                
                // Method 1: Find people cards on the people page
                const peopleCards = Array.from(document.querySelectorAll('.org-people-profile-card, .artdeco-entity-lockup, li.reusable-search__result-container'));
                console.log(`Found ${peopleCards.length} people cards`);
                
                peopleCards.forEach(card => {
                    try {
                        // Different selectors for different types of pages
                        const nameElem = card.querySelector('.artdeco-entity-lockup__title, .org-people-profile-card__profile-title, .entity-result__title-text a, .app-aware-link');
                        const titleElem = card.querySelector('.artdeco-entity-lockup__subtitle, .org-people-profile-card__profile-position, .entity-result__primary-subtitle');
                        
                        if (nameElem && titleElem) {
                            const name = nameElem.textContent.trim();
                            const title = titleElem.textContent.trim();
                            const category = getRoleCategory(title);
                            const profileUrl = nameElem.href || nameElem.querySelector('a')?.href || '';
                            
                            // Only add if it seems like a valid person (not a company)
                            if (name && title && name !== title) {
                                results.push({
                                    name,
                                    title,
                                    profileUrl,
                                    category,
                                    source: 'people_card'
                                });
                            }
                        }
                    } catch (e) {
                        // Ignore individual card errors
                    }
                });
                
                // Method 2: Look for individual profiles in search results 
                const searchResults = Array.from(document.querySelectorAll('.search-result, .reusable-search__result-container, .entity-result'));
                console.log(`Found ${searchResults.length} search results`);
                
                searchResults.forEach(result => {
                    try {
                        const nameElement = result.querySelector('span.actor-name, .entity-result__title-text a, a.app-aware-link');
                        const titleElement = result.querySelector('.subline-level-1, .entity-result__primary-subtitle');
                        
                        if (nameElement && titleElement) {
                            const name = nameElement.textContent.trim();
                            const title = titleElement.textContent.trim();
                            const category = getRoleCategory(title);
                            const profileUrl = nameElement.href || nameElement.closest('a')?.href || '';
                            
                            if (name && title && name !== title) {
                                results.push({
                                    name,
                                    title,
                                    profileUrl,
                                    category,
                                    source: 'search_result'
                                });
                            }
                        }
                    } catch (e) {
                        // Ignore individual result errors
                    }
                });
                
                // Method 3: Look specifically for "People you may know" section
                const peopleCards2 = Array.from(document.querySelectorAll('.discover-entity-card, .discover-entity-card__content'));
                console.log(`Found ${peopleCards2.length} "People you may know" cards`);
                
                peopleCards2.forEach(card => {
                    try {
                        const nameElement = card.querySelector('.discover-person-card__name, .EntityLockup-title, h3');
                        const titleElement = card.querySelector('.discover-person-card__occupation, .EntityLockup-subtitle');
                        
                        if (nameElement && titleElement) {
                            const name = nameElement.textContent.trim();
                            const title = titleElement.textContent.trim();
                            const category = getRoleCategory(title);
                            // Try to find profile URL 
                            const profileUrl = card.querySelector('a')?.href || '';
                            
                            if (name && title && name !== title) {
                                results.push({
                                    name,
                                    title,
                                    profileUrl,
                                    category, 
                                    source: 'people_you_may_know'
                                });
                            }
                        }
                    } catch (e) {
                        // Ignore individual card errors
                    }
                });
                
                // Remove obvious duplicates
                const uniqueResults = results.filter((person, index, self) => 
                    index === self.findIndex(p => p.name === person.name && p.title === person.title)
                );
                
                return uniqueResults;
            }
        """)
        
        # Filter out company listings
        filtered_people = []
        known_company_names = ['headway', 'spring health', 'lyra health', 'sub-zero', 'anthropic', 
                          'adobe', 'spotify', 'td securities', 'grow therapy']
        
        for person in people_data:
            name = person.get('name', '')
            
            # Skip if name is a known company
            is_company = any(company in name.lower() for company in known_company_names)
            if is_company:
                print(f"Skipping company: {name}")
                continue
            
            # Make sure it's a person name (contains space, not just a company name)
            if ' ' in name and person.get('name') != person.get('title'):
                filtered_people.append(person)
                print(f"Found: {person.get('name')} - {person.get('title')} [{person.get('category')}]")
            
        return filtered_people
    except Exception as e:
        print(f"❌ Error extracting people data: {str(e)}")
        return []

def prioritize_by_role(people):
    """Sort people by role category and title importance"""
    category_priority = {
        "leadership": 1,
        "data_ai": 2,
        "recruiting": 3,
        "other": 4
    }
    
    # First by category, then by presence of key terms in title
    def get_priority(person):
        category = person.get('category', 'other')
        title = person.get('title', '').lower()
        
        # Basic category priority
        base_priority = category_priority.get(category, 10)
        
        # Specialized leadership roles
        if 'ceo' in title:
            return base_priority - 0.5
        if 'founder' in title:
            return base_priority - 0.4
        if 'head of data' in title or 'chief data' in title:
            return base_priority - 0.3
        if 'lead' in title:
            return base_priority - 0.2
        
        return base_priority
    
    return sorted(people, key=get_priority)

def find_key_contacts(company_url):
    """Find top 3 key contacts: CEO/Founder, Head of Data/AI, and Recruiter"""
    with sync_playwright() as p:
        # Launch browser with persistent context for cookies
        browser_context = p.chromium.launch_persistent_context(
            user_data_dir="./linkedin-data",
            headless=False,  # Set to True in production
            viewport={"width": 1280, "height": 800}
        )
        
        # Create new page
        page = browser_context.new_page()
        page.set_default_timeout(30000)  # 30 second timeout
        
        try:
            # First check if already logged in
            print("🔑 Checking login status...")
            page.goto("https://www.linkedin.com/feed/", timeout=20000)
            random_sleep()
            
            if not page.url.startswith("https://www.linkedin.com/feed"):
                # Not logged in, so login
                if not login_linkedin(page):
                    browser_context.close()
                    return {"error": "Login failed"}
            else:
                print("✅ Already logged in")
            
            # Process company URL
            if not company_url.endswith('/'):
                company_url += '/'
            
            # Track all the people we find across different pages
            all_people = []
            
            # 1. Try searching for CEO/founder directly
            search_terms = ["CEO", "founder", "head of data", "recruiter"]
            for term in search_terms:
                try:
                    search_url = f"{company_url}people/?keywords={term}"
                    print(f"🔍 Searching for {term} at {search_url}")
                    page.goto(search_url, timeout=30000)
                    random_sleep(2, 3)
                    
                    # Extract people data
                    people = extract_people_data(page)
                    all_people.extend(people)
                except Exception as e:
                    print(f"⚠️ Error searching for {term}: {str(e)}")
            
            # 2. Also try the main people page
            try:
                print(f"🌐 Navigating to main people page: {company_url}people/")
                page.goto(f"{company_url}people/", timeout=30000)
                random_sleep(2, 3)
                
                people = extract_people_data(page)
                all_people.extend(people)
            except Exception as e:
                print(f"⚠️ Error navigating to people page: {str(e)}")
            
            # 3. Also try About page
            try:
                print(f"🌐 Checking About page: {company_url}about/")
                page.goto(f"{company_url}about/", timeout=30000)
                random_sleep(2, 3)
                
                people = extract_people_data(page)
                all_people.extend(people)
            except Exception as e:
                print(f"⚠️ Error navigating to About page: {str(e)}")
            
            # Remove duplicates by name
            unique_people = []
            seen_names = set()
            for person in all_people:
                name = person.get('name')
                if name and name not in seen_names:
                    seen_names.add(name)
                    unique_people.append(person)
            
            # Prioritize by role
            prioritized_people = prioritize_by_role(unique_people)
            
            # Get top contacts per category
            leadership_contact = next((p for p in prioritized_people if p.get('category') == 'leadership'), None)
            data_ai_contact = next((p for p in prioritized_people if p.get('category') == 'data_ai'), None)
            recruiting_contact = next((p for p in prioritized_people if p.get('category') == 'recruiting'), None)
            
            # Create result dictionary with top contacts
            result = {
                "company": company_url,
                "key_contacts": []
            }
            
            # Add contacts if found
            if leadership_contact:
                result["key_contacts"].append({
                    "role": "CEO/Founder",
                    "name": leadership_contact.get('name'),
                    "title": leadership_contact.get('title'),
                    "profile_url": leadership_contact.get('profileUrl', '')
                })
            
            if data_ai_contact:
                result["key_contacts"].append({
                    "role": "Data/AI Leader",
                    "name": data_ai_contact.get('name'),
                    "title": data_ai_contact.get('title'),
                    "profile_url": data_ai_contact.get('profileUrl', '')
                })
            
            if recruiting_contact:
                result["key_contacts"].append({
                    "role": "Recruiter/HR",
                    "name": recruiting_contact.get('name'),
                    "title": recruiting_contact.get('title'),
                    "profile_url": recruiting_contact.get('profileUrl', '')
                })
            
            # If we didn't find specific roles, take top 3 contacts overall
            if len(result["key_contacts"]) < 3 and len(prioritized_people) > 0:
                for person in prioritized_people:
                    # Skip if already added
                    if any(contact["name"] == person.get('name') for contact in result["key_contacts"]):
                        continue
                    
                    # Add this person
                    result["key_contacts"].append({
                        "role": "Other",
                        "name": person.get('name'),
                        "title": person.get('title'),
                        "profile_url": person.get('profileUrl', '')
                    })
                    
                    # Stop once we have 3 contacts
                    if len(result["key_contacts"]) >= 3:
                        break
            
            print("\n" + "="*50)
            print(f"✅ FOUND {len(result['key_contacts'])} KEY CONTACTS:")
            
            for i, contact in enumerate(result["key_contacts"]):
                print(f"\n{i+1}. {contact['role']}: {contact['name']}")
                print(f"   TITLE: {contact['title']}")
                if contact['profile_url']:
                    print(f"   PROFILE: {contact['profile_url']}")
            
            print("="*50 + "\n")
            
            # Save results
            with open("key_contacts.json", "w") as f:
                json.dump(result, f, indent=2)
            
            # Also save as simple text file
            with open("key_contacts.txt", "w") as f:
                f.write(f"COMPANY: {company_url}\n\n")
                for i, contact in enumerate(result["key_contacts"]):
                    f.write(f"{i+1}. {contact['role']}: {contact['name']}\n")
                    f.write(f"   TITLE: {contact['title']}\n")
                    if contact['profile_url']:
                        f.write(f"   PROFILE: {contact['profile_url']}\n")
                    f.write("\n")
            
            print("💾 Results saved to key_contacts.json and key_contacts.txt")
            
            browser_context.close()
            return result
            
        except Exception as e:
            print(f"❌ Script error: {str(e)}")
            # Take a screenshot for debugging
            try:
                page.screenshot(path="error_screenshot.png")
                print("📸 Saved error screenshot")
            except:
                pass
            
            browser_context.close()
            return {"error": str(e)}

def parse_company_url(url):
    """Parse and normalize LinkedIn company URL"""
    # Handle various formats of LinkedIn URLs
    if not url.startswith("http"):
        url = f"https://{url}"
    
    if "linkedin.com" not in url:
        # Assume this is a company name or handle
        url = f"https://www.linkedin.com/company/{url}"
    
    # Ensure URL points to company page
    if "/company/" not in url and "linkedin.com" in url:
        parts = url.split("linkedin.com/")
        if len(parts) > 1:
            path = parts[1].strip("/")
            url = f"https://www.linkedin.com/company/{path}"
    
    return url

if __name__ == "__main__":
    import sys
    
    # Get company URL from command line or use default
    company_url = "https://www.linkedin.com/company/grow-therapy"
    if len(sys.argv) > 1:
        company_url = sys.argv[1]
    
    # Parse and normalize company URL
    company_url = parse_company_url(company_url)
    print(f"🔍 Looking for key contacts at: {company_url}")
    
    # Find company key contacts
    result = find_key_contacts(company_url)
    
    if not result or "error" in result:
        error_msg = result.get('error', 'Unknown error') if result else "No results found"
        print(f"❌ Failed to find key contacts: {error_msg}")