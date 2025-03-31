import os
import sys
import json
from pathlib import Path
import subprocess
import tempfile
from typing import Dict, List, Optional, Tuple
import logging
import re
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Resume directory - adjusted for your project structure
RESUME_DIR = os.getenv("RESUME_DIR", os.path.join(os.path.dirname(os.path.dirname(__file__)), "resumes"))

# LLM Configuration
USE_LOCAL_LLM = os.getenv("USE_LOCAL_LLM", "true").lower() == "true"
LOCAL_LLM_MODEL = os.getenv("LOCAL_LLM_MODEL", "mistral:latest")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

class ResumeSelector:
    """Select the best resume based on company info and job requirements"""
    
    def __init__(self, resume_dir=RESUME_DIR):
        self.resume_dir = Path(resume_dir)
        self.use_local_llm = USE_LOCAL_LLM
        self.local_model = LOCAL_LLM_MODEL
        self.openai_api_key = OPENAI_API_KEY
        
        # Ensure resume directory exists
        if not self.resume_dir.exists():
            logger.warning(f"Resume directory not found: {self.resume_dir}")
            os.makedirs(self.resume_dir, exist_ok=True)
            logger.info(f"Created resume directory: {self.resume_dir}")
    
    def get_available_resumes(self) -> List[Path]:
        """Get list of available resume files"""
        resume_files = list(self.resume_dir.glob("*.pdf"))
        resume_files.extend(self.resume_dir.glob("*.docx"))
        logger.info(f"Found {len(resume_files)} resume files: {[f.name for f in resume_files]}")
        return resume_files
    
    def analyze_website(self, website_url: str) -> Dict:
        """Scrape and analyze company website for relevant information"""
        try:
            logger.info(f"Analyzing website: {website_url}")
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            
            # Check if URL has protocol
            if not website_url.startswith('http'):
                website_url = f"https://{website_url}"
            
            response = requests.get(website_url, headers=headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract main content and remove script/style tags
            for script in soup(['script', 'style']):
                script.extract()
                
            # Get text content
            text = soup.get_text(separator=' ', strip=True)
            
            # Clean up whitespace
            text = re.sub(r'\s+', ' ', text).strip()
            
            # Extract job-related keywords
            keywords = self._extract_job_keywords(text)
            
            # Limit text to reasonable length for LLM processing
            if len(text) > 8000:
                text = text[:8000] + "..."
            
            logger.info(f"Website analysis complete. Extracted {len(keywords)} keywords.")
            
            return {
                "text": text,
                "keywords": keywords
            }
        except Exception as e:
            logger.error(f"Error analyzing website: {str(e)}")
            return {
                "text": "",
                "keywords": []
            }
    
    def _extract_job_keywords(self, text: str) -> List[str]:
        """Extract job-related keywords from website text"""
        # Common tech stack and job skill keywords
        tech_keywords = [
            "python", "javascript", "java", "c++", "golang", "ruby", "php",
            "react", "angular", "vue", "node.js", "django", "flask", "spring",
            "aws", "azure", "gcp", "cloud", "docker", "kubernetes", "ci/cd",
            "machine learning", "artificial intelligence", "data science", 
            "deep learning", "neural networks", "nlp", "computer vision",
            "sql", "nosql", "mongodb", "postgresql", "mysql", "database",
            "data engineering", "etl", "data warehouse", "big data", "hadoop", "spark",
            "devops", "sre", "systems", "linux", "unix", "microservices",
            "agile", "scrum", "kanban", "product management"
        ]
        
        # Find all matches in text (case insensitive)
        found_keywords = []
        text_lower = text.lower()
        
        for keyword in tech_keywords:
            if keyword.lower() in text_lower:
                found_keywords.append(keyword)
        
        return found_keywords
    
    def extract_resume_texts(self, resume_files: List[Path]) -> Dict[str, str]:
        """Extract text content from resume files"""
        resume_texts = {}
        
        for resume_file in resume_files:
            filename = resume_file.name
            file_extension = resume_file.suffix.lower()
            
            try:
                if file_extension == '.pdf':
                    text = self._extract_pdf_text(resume_file)
                    resume_texts[filename] = text
                elif file_extension == '.docx':
                    text = self._extract_docx_text(resume_file)
                    resume_texts[filename] = text
                else:
                    logger.warning(f"Unsupported file format: {file_extension}")
                    continue
                    
                logger.info(f"Successfully extracted text from {filename}")
                
            except Exception as e:
                logger.error(f"Error extracting text from {filename}: {str(e)}")
                resume_texts[filename] = f"[Error extracting content from {filename}]"
        
        return resume_texts
    
    def _extract_pdf_text(self, pdf_path: Path) -> str:
        """Extract text from PDF file using PyPDF2"""
        try:
            # Using simple filename-based analysis if PyPDF2 not installed
            try:
                import PyPDF2
                text = ""
                with open(pdf_path, 'rb') as file:
                    reader = PyPDF2.PdfReader(file)
                    for page_num in range(len(reader.pages)):
                        text += reader.pages[page_num].extract_text() + "\n"
                return text
            except ImportError:
                # Fall back to using filename for keywords if PyPDF2 not installed
                logger.warning("PyPDF2 not installed. Using filename for analysis.")
                return pdf_path.stem.replace("_", " ").replace("-", " ")
        except Exception as e:
            logger.error(f"Error in PDF extraction: {str(e)}")
            return pdf_path.stem.replace("_", " ").replace("-", " ")
    
    def _extract_docx_text(self, docx_path: Path) -> str:
        """Extract text from DOCX file using python-docx"""
        try:
            # Using simple filename-based analysis if docx not installed
            try:
                import docx
                doc = docx.Document(docx_path)
                text = "\n".join([para.text for para in doc.paragraphs])
                return text
            except ImportError:
                # Fall back to using filename for keywords if docx not installed
                logger.warning("python-docx not installed. Using filename for analysis.")
                return docx_path.stem.replace("_", " ").replace("-", " ")
        except Exception as e:
            logger.error(f"Error in DOCX extraction: {str(e)}")
            return docx_path.stem.replace("_", " ").replace("-", " ")
    
    def check_ollama_available(self) -> bool:
        """Check if Ollama is available and running"""
        try:
            result = subprocess.run(
                ["ollama", "list"], 
                capture_output=True, 
                text=True, 
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
    
    def select_best_resume(self, 
                          company_name: str,
                          industry: str = "",
                          job_keywords: List[str] = None,
                          email_content: str = "",
                          ceo_name: str = "") -> Tuple[Path, float]:
        """
        Select the best resume based on company info and job requirements
        
        Args:
            company_name: Name of the company
            industry: Industry of the company
            job_keywords: Keywords extracted from job description
            email_content: Content of the email to be sent
            ceo_name: Name of the CEO/founder
            
        Returns:
            Tuple of (selected resume file path, confidence score)
        """
        # Get available resumes
        resume_files = self.get_available_resumes()
        if not resume_files:
            logger.error(f"No resume files found in {self.resume_dir}")
            raise ValueError(f"No resume files found in {self.resume_dir}")
        
        # If only one resume available, return it
        if len(resume_files) == 1:
            logger.info(f"Only one resume available, selecting: {resume_files[0].name}")
            return (resume_files[0], 1.0)
        
        # Extract text from resumes - simplified approach if extraction libraries not installed
        try:
            resume_texts = self.extract_resume_texts(resume_files)
        except Exception as e:
            logger.error(f"Error extracting resume texts: {str(e)}")
            # Fallback to simple filename-based matching
            resume_texts = {f.name: f.stem.replace("_", " ").replace("-", " ") for f in resume_files}
        
        if not job_keywords:
            job_keywords = []
        
        # Prepare prompt for LLM
        resume_options = "\n\n".join([
            f"RESUME {i+1}: {filename}\n{text[:500]}..." 
            for i, (filename, text) in enumerate(resume_texts.items())
        ])
        
        prompt = f"""
I need to select the most appropriate resume to send to {company_name} from several options.

COMPANY: {company_name}
INDUSTRY: {industry}
CEO/FOUNDER: {ceo_name}
RELEVANT KEYWORDS: {', '.join(job_keywords)}

EMAIL CONTENT TO BE SENT:
{email_content[:500]}...

AVAILABLE RESUMES:
{resume_options}

Based on the company's industry, keywords, and the email content, which resume would be the MOST appropriate to send?
Analyze how well each resume matches the company's needs and industry.

Your response must be in this exact format:
SELECTED: [filename]
CONFIDENCE: [score between 0.0-1.0]
"""
        
        # Get response from LLM
        response_text = self._get_llm_response(prompt)
        
        # Parse response to extract selected resume
        if response_text:
            try:
                # Extract selected resume
                selected_match = re.search(r'SELECTED:\s*([\w\s\.\-]+\.(?:pdf|docx))', response_text, re.IGNORECASE)
                confidence_match = re.search(r'CONFIDENCE:\s*(0\.\d+|1\.0)', response_text)
                
                if selected_match:
                    selected_filename = selected_match.group(1).strip()
                    confidence = float(confidence_match.group(1)) if confidence_match else 0.5
                    
                    # Find the matching resume file
                    for resume_file in resume_files:
                        if resume_file.name.lower() == selected_filename.lower():
                            logger.info(f"Selected resume: {resume_file.name} with confidence {confidence}")
                            return (resume_file, confidence)
                    
                    # If exact filename not found, try partial match
                    for resume_file in resume_files:
                        if selected_filename.lower() in resume_file.name.lower():
                            logger.info(f"Selected resume (partial match): {resume_file.name}")
                            return (resume_file, confidence)
            except Exception as e:
                logger.error(f"Error parsing LLM response: {str(e)}")
        
        # Fallback: If we couldn't select a specific resume with LLM, try keyword matching
        if job_keywords:
            # Simple keyword matching fallback
            scores = []
            for resume_file in resume_files:
                filename_text = resume_file.stem.lower().replace("_", " ").replace("-", " ")
                score = sum(1 for keyword in job_keywords if keyword.lower() in filename_text)
                scores.append((resume_file, score))
            
            # Get resume with highest keyword match
            if scores:
                best_match = max(scores, key=lambda x: x[1])
                if best_match[1] > 0:
                    logger.info(f"Selected resume using keyword matching: {best_match[0].name}")
                    return (best_match[0], 0.6)
        
        # If all else fails, return the first resume
        logger.warning("Could not determine best resume, selecting first available")
        return (resume_files[0], 0.5)
    
    def _get_llm_response(self, prompt: str) -> str:
        """Get response from LLM using either local Ollama or OpenAI API"""
        response_text = None
        
        # Try local LLM first if available
        if self.use_local_llm and self.check_ollama_available():
            try:
                logger.info(f"Using local LLM ({self.local_model}) to select resume...")
                result = subprocess.run(
                    ["ollama", "run", self.local_model, prompt],
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                
                if result.returncode == 0:
                    response_text = result.stdout.strip()
                    logger.info("Successfully got response from local LLM")
                else:
                    logger.error(f"Error from local LLM: {result.stderr}")
            except Exception as e:
                logger.error(f"Error using local LLM: {str(e)}")
        
        # Fall back to OpenAI if needed and configured
        if not response_text and self.openai_api_key:
            try:
                import requests
                logger.info("Falling back to OpenAI API...")
                
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.openai_api_key}"
                }
                
                payload = {
                    "model": "gpt-3.5-turbo",
                    "messages": [
                        {"role": "system", "content": "You are a helpful assistant that selects the most appropriate resume for a job application."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 500
                }
                
                response = requests.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=payload
                )
                
                if response.status_code == 200:
                    result = response.json()
                    response_text = result["choices"][0]["message"]["content"].strip()
                    logger.info("Successfully got response from OpenAI")
                else:
                    logger.error(f"Error from OpenAI API: {response.text}")
            except Exception as e:
                logger.error(f"Error using OpenAI: {str(e)}")
        
        if not response_text:
            logger.warning("Could not get LLM response, will use default selection")
            
        return response_text


def select_resume(company_name, company_website=None, ceo_name=None, industry=None, email_content=None, role_hint=None):
    """
    Select the best resume based on company information
    
    Inputs:
    - company_name: str
    - company_website: str (optional)
    - ceo_name: str (optional)
    - industry: str (optional)
    - email_content: str (optional)
    - role_hint: str (optional) - e.g., "data science", "frontend", etc.
    
    Returns:
    - best_fit_resume: str (path to resume file)
    - confidence: float (0.0-1.0 score of match confidence)
    """
    selector = ResumeSelector()
    
    # Extract keywords from website if available
    job_keywords = []
    if role_hint:
        job_keywords.append(role_hint)
        
    if company_website:
        try:
            website_info = selector.analyze_website(company_website)
            if website_info["keywords"]:
                job_keywords.extend(website_info["keywords"])
        except Exception as e:
            logger.error(f"Error analyzing website: {str(e)}")
    
    # Add role hint as a keyword if provided
    if role_hint:
        keywords = role_hint.split()
        job_keywords.extend(keywords)
    
    # Select best resume
    resume_path, confidence = selector.select_best_resume(
        company_name=company_name,
        industry=industry or "",
        job_keywords=job_keywords,
        email_content=email_content or "",
        ceo_name=ceo_name or ""
    )
    
    return str(resume_path), confidence


# Command-line interface
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Select the best resume for a job application")
    parser.add_argument("--company", required=True, help="Company name")
    parser.add_argument("--website", help="Company website URL")
    parser.add_argument("--ceo", help="CEO/Founder name")
    parser.add_argument("--industry", help="Company industry")
    parser.add_argument("--email", help="Path to the email content file")
    parser.add_argument("--role", help="Role hint (e.g., 'data science', 'frontend')")
    
    args = parser.parse_args()
    
    # Read email content if provided
    email_content = ""
    if args.email and os.path.exists(args.email):
        with open(args.email, 'r') as f:
            email_content = f.read()
    
    # Select resume
    resume_path, confidence = select_resume(
        company_name=args.company,
        company_website=args.website,
        ceo_name=args.ceo,
        industry=args.industry,
        email_content=email_content,
        role_hint=args.role
    )
    
    print(f"\n{'='*50}")
    print(f"Selected Resume: {os.path.basename(resume_path)}")
    print(f"Confidence Score: {confidence:.2f}")
    print(f"Full Path: {resume_path}")
    print(f"{'='*50}\n")
    
    # Output as JSON for easy integration
    result = {
        "resume_path": resume_path,
        "resume_name": os.path.basename(resume_path),
        "confidence": confidence
    }
    
    print(json.dumps(result))