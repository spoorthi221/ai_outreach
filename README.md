# Outreach AI

An intelligent system that automates the process of finding contacts at target companies, generating personalized outreach emails, and selecting the most appropriate resume for each contact.

## Overview

Outreach AI is an end-to-end automation tool that handles the entire job application outreach process:

1. **Contact Discovery**: Finds CEOs/founders, data/AI leaders, and recruiters at target companies
2. **Email Discovery**: Determines email addresses for each contact
3. **Personalized Emails**: Generates custom emails tailored to each contact's role
4. **Smart Resume Selection**: Chooses the most relevant resume for each contact from multiple versions
5. **Automated Sending**: Handles email delivery with proper attachments
6. **Progress Tracking**: Monitors the entire process with detailed logs

The system is built with Python and uses a combination of web scraping, local AI models, and email automation to create a seamless outreach workflow.

## Features

- **LinkedIn Scraping**: Automatically finds 3 key people at each company (leadership, data/AI, recruiter)
- **Email Pattern Detection**: Predicts email addresses using various common patterns and verification
- **Location Filtering**: Skips companies in specific locations (e.g., New York, Midwest)
- **Local AI**: Uses Mistral via Ollama for generating personalized messages
- **Resume Intelligence**: Selects the appropriate resume version based on company and role
- **Dashboard**: Streamlit-based monitoring and control interface

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/outreach-ai.git
cd outreach-ai
```

2. Install dependencies:
```bash
pip install -r outreach_ai/requirements.txt
```

3. Set up environment variables:
```
# Create a .env file with:
EMAIL_ADDRESS=your.email@gmail.com
EMAIL_PASSWORD=your_app_password
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
USE_LOCAL_LLM=true
LOCAL_LLM_MODEL=mistral:latest
```

4. Install Ollama (for local AI):
   - Visit [ollama.ai](https://ollama.ai) to download and install
   - Pull the Mistral model: `ollama pull mistral`

## Usage

### Prepare Your Data

1. Create an Excel file with target companies:
   - Save it to `outreach_ai/data/companies.xlsx`
   - Required columns: `Company Name`, `Website`, `LinkedIn URL`, `Industry`
   - Optional: `Location`, `Description`

2. Add multiple versions of your resume:
   - Save them to `outreach_ai/resumes/`
   - Use descriptive filenames (e.g., `data_science_resume.pdf`, `ml_engineer_resume.pdf`)

### Run the System

For command line usage:
```bash
# Run the full outreach process
python -m outreach_ai.main

# Test individual components
python -m outreach_ai.agents.find_ceo "https://www.linkedin.com/company/example"
python -m outreach_ai.agents.generate_email --name "John Doe" --company "Example Inc" --industry "Tech"
```

For the dashboard interface:
```bash
streamlit run app.py
```

## Configuration

### Location Filtering

By default, the system excludes companies in New York and the Midwest. To customize this:

1. Edit the `EXCLUDED_LOCATIONS` list in `main.py`
2. Or set the environment variable:
```bash
export EXCLUDED_LOCATIONS='["New York", "California", "Remote"]'
```

### Resume Selection

The system selects resumes based on:
- Company industry
- Contact's role
- Content matching between resume and company

Customize the selection by adding more resumes and ensuring their filenames reflect their focus.

## Dashboard

The Streamlit dashboard provides:
- Real-time progress monitoring
- Company and contact listing
- Email content previews
- Process controls (start/stop)
- Configuration settings

## Components

- `find_ceo.py`: LinkedIn scraper to find key contacts
- `find_email.py`: Email discovery and verification
- `generate_email.py`: Personalized email generator
- `select_resume.py`: Intelligent resume selection
- `send_email.py`: Email delivery with attachments
- `read_excel.py`: Data import from Excel
- `main.py`: Overall workflow orchestration
- `app.py`: Streamlit dashboard

## Privacy and Ethics

This tool is designed for legitimate job search activities. Please use responsibly:
- Respect LinkedIn's terms of service
- Comply with email sending best practices
- Honor rate limits to avoid being flagged as spam
- Only use for personal job search purposes

## License

MIT License

## Acknowledgments

- [Playwright](https://playwright.dev/) for web automation
- [Mistral AI](https://mistral.ai/) for the LLM model
- [Ollama](https://ollama.ai/) for local AI inference
- [Streamlit](https://streamlit.io/) for the dashboard interface
