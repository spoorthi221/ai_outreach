# TODO: Use LLM (Ollama/Mistral or GPT) to generate personalized email
import os
import sys
import json
import subprocess
import requests
from typing import Dict, List, Optional
import random
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
USE_LOCAL_LLM = os.getenv("USE_LOCAL_LLM", "true").lower() == "true"
LOCAL_LLM_MODEL = os.getenv("LOCAL_LLM_MODEL", "mistral:latest")

class EmailGenerator:
    """Generate personalized cold outreach emails using local LLM or GPT fallback"""
    
    def __init__(self):
        """Initialize the email generator with configuration"""
        self.use_local_llm = USE_LOCAL_LLM
        self.local_model = LOCAL_LLM_MODEL
        self.openai_api_key = OPENAI_API_KEY
        
    def check_ollama_available(self) -> bool:
        """Check if Ollama is available and running"""
        try:
            # Try to run a simple Ollama command
            result = subprocess.run(
                ["ollama", "list"], 
                capture_output=True, 
                text=True, 
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
    
    def generate_with_ollama(self, prompt: str) -> str:
        """Generate email using Ollama with local LLM"""
        try:
            print(f"Using local LLM: {self.local_model}")
            
            # Run the Ollama command
            result = subprocess.run(
                ["ollama", "run", self.local_model, prompt],
                capture_output=True,
                text=True,
                timeout=60  # 60 second timeout
            )
            
            if result.returncode != 0:
                print(f"Ollama error: {result.stderr}")
                return None
                
            return result.stdout.strip()
            
        except subprocess.SubprocessError as e:
            print(f"Ollama subprocess error: {str(e)}")
            return None
    
    def generate_with_api(self, prompt: str) -> str:
        """Generate email using OpenAI API (fallback)"""
        if not self.openai_api_key:
            raise ValueError("OpenAI API key not configured")
            
        try:
            print("Using OpenAI API as fallback")
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.openai_api_key}"
            }
            
            payload = {
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant that generates personalized, warm, and natural-sounding cold outreach emails that feel like they were written by a human job applicant. Avoid buzzwords like 'excited', 'passionate', or 'resonate'. Write in a conversational, warm tone with specific personal details."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 1000
            }
            
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload
            )
            
            if response.status_code != 200:
                print(f"OpenAI API error: {response.text}")
                return None
                
            result = response.json()
            return result["choices"][0]["message"]["content"].strip()
            
        except Exception as e:
            print(f"OpenAI API error: {str(e)}")
            return None
    
    def generate_email(self, 
                      recipient_name: str,
                      company_name: str, 
                      industry: str,
                      company_description: str = "",
                      candidate_name: str = "Spoorthi",
                      candidate_skills: List[str] = None,
                      include_resume: bool = False,
                      resume_filename: str = "resume.pdf") -> Dict:
        """
        Generate a personalized cold outreach email
        
        Args:
            recipient_name: Name of the recipient (CEO/founder)
            company_name: Name of the company
            industry: Industry the company operates in
            company_description: Brief description of what the company does
            candidate_name: Name of the sender (job applicant)
            candidate_skills: List of candidate's relevant skills/achievements
            include_resume: Whether to mention a resume attachment
            resume_filename: Filename of the resume to mention
            
        Returns:
            Dict containing the generated email and metadata
        """
        if not candidate_skills:
            candidate_skills = [
                "Built 2 AI agents for automated data analysis and predictive modeling",
                "Developed data science pipelines that improved business insights by 32%",
                "Created advanced analytics dashboards for real-time decision making",
                "Implemented machine learning solutions that optimized key business processes"
            ]
        
        # Format skills as bullet points for prompt
        skills_text = "\n".join([f"- {skill}" for skill in candidate_skills])
        
        # Add resume attachment instruction
        resume_instruction = ""
        if include_resume:
            resume_instruction = f"Include a brief mention that you've attached your resume ('{resume_filename}') for more details."
        
        # Create prompt
        prompt = f"""
Write a short, warm, personalized cold outreach email from a job applicant named {candidate_name} to {recipient_name}, 
the CEO/founder of {company_name}, which is in the {industry} industry.

Company description: {company_description}

The email should include:
1. A warm, personal greeting
2. A specific comment showing knowledge of the company
3. Brief mention of these relevant skills/achievements:
{skills_text}
4. A clear ask for an interview opportunity for a data science, AI, or analytics role
5. {resume_instruction}
6. A brief sign-off with the applicant's name
7. A short P.S. that adds a personal touch

Make the email sound natural and human, as if written by a real person. It should be conversational and warm, but professional.
Avoid buzzwords like "excited," "passionate," or "resonate." 
Keep the email between 150-200 words.
Make sure it includes bullet points for skills similar to the example.
Don't use formal HR language - this should feel like a genuine personal email.

The format should look like:
Subject: [Short attention-grabbing subject line]

Hi [Name],
[Opening with specific knowledge about company]

Here's what I've built:
• [Skill point 1]
• [Skill point 2]
• [Skill point 3]

[Brief connection to company mission]

[Clear ask for interview]
[Mention resume attachment if included]
Best,
[Candidate name]

P.S. [Brief personal note]
"""
        
        # Try to generate with local LLM first
        email_text = None
        
        if self.use_local_llm and self.check_ollama_available():
            email_text = self.generate_with_ollama(prompt)
        
        # Fall back to API if local generation fails
        if not email_text and self.openai_api_key:
            email_text = self.generate_with_api(prompt)
        
        if not email_text:
            return {
                "success": False,
                "error": "Failed to generate email with available methods"
            }
        
        # Extract subject line if present
        subject = ""
        body = email_text
        
        if "Subject:" in email_text:
            parts = email_text.split("Subject:", 1)
            if len(parts) > 1:
                subject_and_body = parts[1].strip()
                if "\n" in subject_and_body:
                    subject, body = subject_and_body.split("\n", 1)
                    subject = subject.strip()
                    body = body.strip()
        
        return {
            "success": True,
            "subject": subject,
            "body": body,
            "full_email": email_text,
            "metadata": {
                "recipient": recipient_name,
                "company": company_name,
                "industry": industry,
                "includes_resume": include_resume
            }
        }

# Wrapper function for EmailGenerator.generate_email to make it easier to import
def generate_email(recipient_name, company_name, industry, company_description="", contact_role=None, candidate_name="Spoorthi"):
    """
    Wrapper function for EmailGenerator.generate_email to make it easier to import
    
    Args:
        recipient_name: Name of the recipient
        company_name: Name of the company
        industry: Industry of the company
        company_description: Description of the company (optional)
        contact_role: Role of the contact (leadership, data_ai, recruiting) (optional)
        candidate_name: Name of the sender (optional)
        
    Returns:
        Dict with email content
    """
    # Create an instance of EmailGenerator
    generator = EmailGenerator()
    
    # Determine skills based on contact role
    skills = None
    if contact_role == "data_ai":
        skills = [
            "Built custom AI models for predictive analytics and pattern recognition",
            "Developed end-to-end data science workflows reducing analysis time by 40%",
            "Created interactive visualization tools for complex data interpretation",
            "Implemented advanced statistical methods that improved forecast accuracy by 28%"
        ]
    elif contact_role == "recruiting":
        skills = [
            "Built data-driven talent analytics platforms",
            "Developed AI-powered candidate assessment tools",
            "Created predictive models for recruitment success metrics",
            "Implemented analytics dashboards for optimizing hiring processes"
        ]
    
    # Generate email using class method
    result = generator.generate_email(
        recipient_name=recipient_name,
        company_name=company_name,
        industry=industry,
        company_description=company_description,
        candidate_name=candidate_name,
        candidate_skills=skills,
        include_resume=False
    )
    
    return result

def main():
    """Main function to run from command line"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate personalized outreach emails")
    parser.add_argument("--name", required=True, help="Recipient's name (CEO/founder)")
    parser.add_argument("--company", required=True, help="Company name")
    parser.add_argument("--industry", required=True, help="Company industry")
    parser.add_argument("--description", help="Company description", default="")
    parser.add_argument("--sender", help="Sender's name", default="Spoorthi")
    parser.add_argument("--skills", nargs="+", help="List of sender's skills/achievements")
    parser.add_argument("--resume", help="Resume filename to mention in email", default="resume.pdf")
    parser.add_argument("--include-resume", action="store_true", help="Include resume attachment mention")
    parser.add_argument("--output", help="Output file (if not specified, prints to console)")
    
    args = parser.parse_args()
    
    # Initialize generator
    generator = EmailGenerator()
    
    # Generate email
    result = generator.generate_email(
        recipient_name=args.name,
        company_name=args.company,
        industry=args.industry,
        company_description=args.description,
        candidate_name=args.sender,
        candidate_skills=args.skills,
        include_resume=args.include_resume,
        resume_filename=args.resume
    )
    
    if not result["success"]:
        print(f"Error: {result['error']}")
        sys.exit(1)
    
    # Print or save output
    if args.output:
        with open(args.output, "w") as f:
            f.write(f"Subject: {result['subject']}\n\n")
            f.write(result['body'])
        print(f"Email saved to {args.output}")
    else:
        print("\n" + "="*50)
        print(f"Subject: {result['subject']}")
        print("="*50 + "\n")
        print(result['body'])
        print("\n" + "="*50)


if __name__ == "__main__":
    main()