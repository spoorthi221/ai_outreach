import pandas as pd


def read_company_data(filepath):
   df = pd.read_excel(filepath, skiprows=3)
   df = df[['Company', 'Website', 'Company Linkedin Url']].dropna(subset=['Company'])
   df.columns = ['Company Name', 'Website', 'LinkedIn URL']
   return df.to_dict(orient='records')


# Example usage
if __name__ == "__main__":
   file = "outreach_ai/data/companies.xlsx"
   companies = read_company_data(file)
   for company in companies:
       print(company)