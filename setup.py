import os


# Folder structure
folders = [
   "outreach_ai/data",
   "outreach_ai/agents",
   "outreach_ai/resumes"  # For Agent 5
]


# Files and their starter content
files = {
   "outreach_ai/data/companies.xlsx": None,  # Add manually
   "outreach_ai/agents/read_excel.py": '''import pandas as pd


def read_company_data(filepath):
   df = pd.read_excel(filepath, skiprows=3)
   df = df[['Company', 'Website', 'Company Linkedin Url']].dropna(subset=['Company'])
   df.columns = ['Company Name', 'Website', 'LinkedIn URL']
   return df.to_dict(orient='records')


# Example usage
if __name__ == "__main__":
   file = "data/companies.xlsx"
   companies = read_company_data(file)
   for company in companies:
       print(company)
''',
   "outreach_ai/agents/find_ceo.py": "# TODO: Scrape LinkedIn or website to find CEO/founder\n",
   "outreach_ai/agents/find_email.py": "# TODO: Predict or find email address using Hunter API\n",
   "outreach_ai/agents/generate_email.py": "# TODO: Use LLM (Ollama/Mistral or GPT) to generate personalized email\n",
   "outreach_ai/agents/send_email.py": "# TODO: Send email with or without attachment\n",
   "outreach_ai/agents/select_resume.py": '''# TODO: Agent 5 - Select the best resume based on company site and email context


def select_resume(company_website, ceo_name, role_hint=None):
   """
   Inputs:
   - company_website: str
   - ceo_name: str
   - role_hint: str (optional)


   Returns:
   - best_fit_resume: str (filename from /resumes/)
   """
   # Step 1: Scrape or summarize website
   # Step 2: Compare with keywords in resume filenames
   # Step 3: Return best match
   pass
''',
   "outreach_ai/main.py": '''from agents.read_excel import read_company_data


def main():
   companies = read_company_data("data/companies.xlsx")
   for company in companies:
       print(company)


if __name__ == "__main__":
   main()
''',
   "outreach_ai/requirements.txt": '''pandas
openpyxl
playwright
beautifulsoup4
requests
jinja2
email-validator
python-dotenv
'''
}


# Create folders
for folder in folders:
   os.makedirs(folder, exist_ok=True)


# Create files with content
for path, content in files.items():
   with open(path, "w", encoding="utf-8") as f:
       if content:
           f.write(content)


print("✅ Project structure created!")
print("📂 Place your Excel file in: 'outreach_ai/data/companies.xlsx'")
print("📄 Place your 5 resumes in:   'outreach_ai/resumes/'")