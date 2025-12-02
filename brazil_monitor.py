#!/usr/bin/env python3
"""
Dell Brazil Tax Legislation Monitor
Automatically monitors Brazilian legislation sites and generates Dell-relevant reports
"""

import requests
import urllib3
import warnings
from bs4 import BeautifulSoup
from datetime import datetime
import re
import time
from typing import List, Dict
import httpx
from openai import OpenAI
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Suppress SSL warnings for internal Dell APIs
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings('ignore')

# =============================================================================
# API CONFIGURATION
# Loaded from environment variables or .env file
# =============================================================================
DEV_GENAI_API_URL = os.getenv("DEV_GENAI_API_URL", "https://genai-api-dev.dell.com/v1")
DEV_GENAI_API_KEY = os.getenv("DEV_GENAI_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "llama-3-3-70b-instruct")

# =============================================================================
# BRAZILIAN SITES CONFIGURATION
# Each site has: URL, CSS selectors for scraping, base URL for relative links
# =============================================================================
BRAZILIAN_SITES = {
    "LegiswWeb_Federal_P1": {
        "url": "https://www.legisweb.com.br/legislacao_ultimas/?data=6&abr=federal&acao=Filtrar&ord=dodesc&p=1",
        "selectors": {
            "articles": "h4.result-titulo, .ultimas_titulo, .result-item",
            "title": "a",
            "link": "a",
            "date": ".date, .data, time, .publicado",
            "content": "p, .texto, .resumo, .summary"
        },
        "base_url": "https://www.legisweb.com.br"
    },
    "LegiswWeb_Estado_P1": {
        "url": "https://www.legisweb.com.br/legislacao_ultimas/?data=6&abr=estado&estado=&acao=Filtrar&ord=dodesc&p=1",
        "selectors": {
            "articles": "h4.result-titulo, .ultimas_titulo, .result-item",
            "title": "a",
            "link": "a",
            "date": ".date, .data, time, .publicado",
            "content": "p, .texto, .resumo, .summary"
        },
        "base_url": "https://www.legisweb.com.br/"
    },
    "LegiswWeb_Geral_P1": {
        "url": "https://www.legisweb.com.br/legislacao_ultimas/?acao=Filtrar&ord=dodesc&p=1",
        "selectors": {
            "articles": "h4.result-titulo, .ultimas_titulo, .result-item,.result-datado",
            "title": "a",
            "link": "a",
            "date": ".date, .data, time, .publicado",
            "content": "p, .texto, .resumo, .summary"
        },
        "base_url": "https://www.legisweb.com.br"
    },
    "Receita_Federal": {
        "url": "https://www.gov.br/receitafederal/pt-br/assuntos/noticias",
        "selectors": {
            "articles": "h2.titulo, .callout, .item, .destaque, .noticia",
            "title": "h3 a,a, h2 a, .title a",
            "link": "a",
            "date": ".date, .published, time, .data, .datetime, .timestamp",
            "content": "p, .summary, .excerpt, .resumo, .lead, .descricao"
        },
        "base_url": "https://www.gov.br"
    }
}

# HTTP headers to mimic browser requests
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
}

# =============================================================================
# AI SYSTEM PROMPT
# Defines the AI's role and analysis framework for Dell Brazil
# =============================================================================
SYSTEM_PROMPT = """Você é um assistente IA especializado em análise de legislação tributária brasileira, com foco nas operações da Dell Technologies Brasil.

Perfil da Dell Technologies Brasil:
- Regime Tributário: Lucro Real
- Localizações: Hortolândia/SP, Eldorado do Sul/RS, São Paulo/SP, Barueri/SP, Santana do Parnaíba/SP, Cajamar/SP, Rio de Janeiro/RJ
- Atividades: Fabricação de computadores, servidores, importação/exportação, serviços de TI
- Tributos Relevantes: ICMS, IPI, PIS/COFINS, IRPJ/CSLL

Framework de Análise:
1. Avaliação de Relevância para a Dell
2. Resumo da Alteração Legal
3. Impacto Tributário para a Dell
4. Ações Recomendadas
5. Cronograma e prazos
6. Explicação de Irrelevância (se aplicável)

IMPORTANTE: Forneça análise completa e detalhada."""


# =============================================================================
# BRAZIL MONITOR CLASS
# Main class that orchestrates the monitoring process
# =============================================================================
class BrazilMonitor:
    """
    Monitor for Brazilian tax legislation relevant to Dell Technologies
    
    Workflow:
    1. Scrape configured Brazilian legislation sites
    2. Extract articles with title, URL, date, content
    3. Analyze each article with AI for Dell relevance
    4. Filter only relevant articles
    5. Generate consolidated report
    """
    
    def __init__(self):
        """Initialize HTTP session and AI client"""
        # Setup HTTP session with headers and SSL disabled
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.session.verify = False
        
        # Initialize OpenAI-compatible client for Dell GenAI API
        self.client = OpenAI(
            base_url=DEV_GENAI_API_URL,
            api_key=DEV_GENAI_API_KEY,
            http_client=httpx.Client(verify=False)
        )
        
        print("✅ Brazil Monitor initialized")
        print(f"📍 Monitoring {len(BRAZILIAN_SITES)} Brazilian sites")
    
    # =========================================================================
    # SCRAPING METHODS
    # Responsible for fetching and parsing HTML from legislation sites
    # =========================================================================
    def scrape_sites(self) -> List[Dict]:
        """
        Scrape all configured sites and collect articles
        
        Returns:
            List of article dictionaries with title, url, date, content
        """
        all_articles = []
        
        print(f"\n🔍 Starting Brazilian sites monitoring...")
        print("=" * 70)
        
        for site_name, site_config in BRAZILIAN_SITES.items():
            print(f"\n📡 Processing: {site_name}")
            articles = self._scrape_site(site_name, site_config)
            
            if articles:
                all_articles.extend(articles)
                print(f"✅ {len(articles)} articles found in {site_name}")
            else:
                print(f"⚠️ No articles found in {site_name}")
            
            time.sleep(2)  # Delay between sites to avoid rate limiting
        
        print(f"\n📊 Total articles collected: {len(all_articles)}")
        return all_articles
    
    def _scrape_site(self, site_name: str, site_config: Dict) -> List[Dict]:
        """
        Scrape a single site based on its configuration
        
        Args:
            site_name: Name identifier for the site
            site_config: Dictionary with URL and CSS selectors
        
        Returns:
            List of articles from this site
        """
        articles = []
        
        try:
            response = self.session.get(site_config['url'], timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Use site-specific extraction method
            if 'legisweb' in site_name.lower():
                articles = self._extract_legisweb_articles(soup, site_config)
            else:
                articles = self._extract_generic_articles(soup, site_config)
            
        except Exception as e:
            print(f"❌ Error processing {site_name}: {str(e)}")
        
        return articles
    
    def _extract_legisweb_articles(self, soup: BeautifulSoup, site_config: Dict) -> List[Dict]:
        """
        Extract articles from LegiswWeb sites
        Uses specific parsing logic for LegiswWeb HTML structure
        """
        articles = []
        base_url = site_config['base_url']
        
        # Find article elements using configured selectors
        title_elements = soup.select(site_config['selectors']['articles'])
        
        for element in title_elements[:20]:  # Limit to 20 articles per site
            try:
                # Extract link element
                link_elem = element.find('a')
                if not link_elem:
                    continue
                
                href = link_elem.get('href', '')
                if not href:
                    continue
                
                # Build absolute URL
                if href.startswith('http'):
                    url = href
                elif href.startswith('/'):
                    url = base_url + href
                else:
                    url = base_url + '/' + href
                
                # Extract title text
                title = link_elem.get_text(strip=True)
                if not title:
                    continue
                
                # Extract date from parent element
                date_text = ""
                parent = element.find_parent()
                if parent:
                    date_elem = parent.find(['time', 'span'], class_=re.compile(r'date|data|publicado'))
                    if date_elem:
                        date_text = date_elem.get_text(strip=True)
                
                # Get full article content by fetching the article page
                full_content = self._get_full_article_content(url)
                
                article = {
                    'title': title,
                    'url': url,
                    'date': self._parse_brazilian_date(date_text),
                    'content': full_content,
                    'source': 'LegiswWeb',
                    'dell_analysis': ''
                }
                
                articles.append(article)
                time.sleep(1)  # Delay between article fetches
                
            except Exception as e:
                print(f"⚠️ Error extracting article: {str(e)}")
                continue
        
        return articles
    
    def _extract_generic_articles(self, soup: BeautifulSoup, site_config: Dict) -> List[Dict]:
        """
        Generic article extraction for non-LegiswWeb sites
        Works with Receita Federal and similar government sites
        """
        articles = []
        base_url = site_config['base_url']
        selectors = site_config['selectors']
        
        # Find article elements
        article_elements = soup.select(selectors['articles'])
        
        for element in article_elements[:20]:
            try:
                # Extract title and link
                title_elem = element.select_one(selectors['title'])
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                href = title_elem.get('href', '')
                
                if not href:
                    continue
                
                # Build absolute URL
                if href.startswith('http'):
                    url = href
                elif href.startswith('/'):
                    url = base_url + href
                else:
                    url = base_url + '/' + href
                
                # Extract date
                date_text = ""
                date_elem = element.select_one(selectors['date'])
                if date_elem:
                    date_text = date_elem.get_text(strip=True)
                
                # Get full content
                full_content = self._get_full_article_content(url)
                
                article = {
                    'title': title,
                    'url': url,
                    'date': self._parse_brazilian_date(date_text),
                    'content': full_content,
                    'source': 'Receita Federal',
                    'dell_analysis': ''
                }
                
                articles.append(article)
                time.sleep(1)
                
            except Exception as e:
                print(f"⚠️ Error extracting article: {str(e)}")
                continue
        
        return articles
    
    def _get_full_article_content(self, url: str) -> str:
        """
        Fetch and extract full text content from an article page
        
        Args:
            url: Article URL to fetch
        
        Returns:
            Cleaned text content (max 5000 chars)
        """
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove unwanted elements (scripts, styles, navigation)
            for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'iframe']):
                element.decompose()
            
            # Try to find main content area
            main_content = None
            content_selectors = [
                'article', '.article-content', '.content', '.post-content',
                '.entry-content', 'main', '.main-content', '.texto-noticia'
            ]
            
            for selector in content_selectors:
                main_content = soup.select_one(selector)
                if main_content:
                    break
            
            if not main_content:
                main_content = soup.find('body')
            
            if main_content:
                # Extract and clean text
                text = main_content.get_text(separator=' ', strip=True)
                text = re.sub(r'\s+', ' ', text)
                return text[:5000]
            
        except Exception as e:
            print(f"⚠️ Error fetching content from {url}: {str(e)}")
        
        return ""
    
    def _parse_brazilian_date(self, date_text: str) -> str:
        """
        Parse Brazilian date formats (DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD)
        
        Returns:
            Parsed date string or current date if parsing fails
        """
        if not date_text:
            return datetime.now().strftime('%Y-%m-%d')
        
        date_patterns = [
            r'(\d{2})/(\d{2})/(\d{4})',
            r'(\d{2})-(\d{2})-(\d{4})',
            r'(\d{4})-(\d{2})-(\d{2})'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, date_text)
            if match:
                return match.group(0)
        
        return datetime.now().strftime('%Y-%m-%d')
    
    # =========================================================================
    # AI ANALYSIS METHODS
    # Uses LLM to analyze articles for Dell relevance
    # =========================================================================
    def analyze_articles_with_ai(self, articles: List[Dict]) -> List[Dict]:
        """
        Analyze articles with AI to determine Dell relevance
        
        Args:
            articles: List of article dictionaries
        
        Returns:
            List of articles that are relevant to Dell
        """
        print(f"\n🤖 Starting Dell relevance analysis with AI...")
        print("=" * 70)
        
        analyzed_articles = []
        
        for i, article in enumerate(articles, 1):
            print(f"\n[{i}/{len(articles)}] Analyzing: {article['title'][:60]}...")
            
            try:
                # Perform AI analysis
                analysis = self._perform_dell_analysis(article)
                article['dell_analysis'] = analysis
                
                # Check if relevant
                if self._is_dell_relevant(analysis):
                    analyzed_articles.append(article)
                    print("✅ Relevant to Dell")
                else:
                    print("❌ Not relevant to Dell")
                
                time.sleep(2)  # Rate limiting for API
                
            except Exception as e:
                print(f"⚠️ Analysis error: {str(e)}")
                continue
        
        print(f"\n📊 Analysis complete:")
        print(f"  • Total analyzed: {len(articles)}")
        print(f"  • Dell relevant: {len(analyzed_articles)}")
        print(f"  • Relevance rate: {(len(analyzed_articles)/len(articles)*100):.1f}%")
        
        return analyzed_articles
    
    def _perform_dell_analysis(self, article: Dict) -> str:
        """
        Send article to AI for Dell relevance analysis
        
        Args:
            article: Article dictionary with title, content, etc.
        
        Returns:
            AI-generated analysis text
        """
        content = f"""
Título: {article['title']}
Data: {article['date']}
Fonte: {article['source']}
URL: {article['url']}

Conteúdo:
{article['content'][:3000]}
"""
        
        try:
            response = self.client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Analise a seguinte legislação brasileira e determine sua relevância para Dell Technologies Brasil:\n\n{content}"}
                ],
                max_tokens=2000,
                temperature=0.3
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"❌ AI analysis error: {str(e)}")
            return "Analysis error"
    
    def _is_dell_relevant(self, analysis: str) -> bool:
        """
        Determine if AI analysis indicates Dell relevance
        
        Args:
            analysis: AI-generated analysis text
        
        Returns:
            True if article is relevant to Dell
        """
        if not analysis:
            return False
        
        analysis_lower = analysis.lower()
        
        # Non-relevance indicators
        non_relevant = [
            "não relevante", "não aplicável", "not relevant",
            "não se aplica", "sem impacto direto"
        ]
        
        for indicator in non_relevant:
            if indicator in analysis_lower:
                return False
        
        # Relevance indicators
        relevant = [
            "relevante", "aplicável", "impacta", "dell",
            "tecnologia", "manufatura", "icms", "ipi",
            "pis", "cofins", "benefício fiscal"
        ]
        
        for indicator in relevant:
            if indicator in analysis_lower:
                return True
        
        return False
    
    # =========================================================================
    # REPORT GENERATION METHODS
    # Creates formatted reports from analysis results
    # =========================================================================
    def generate_report(self, articles: List[Dict]) -> str:
        """
        Generate consolidated report from analyzed articles
        
        Args:
            articles: List of relevant article dictionaries
        
        Returns:
            Formatted report string
        """
        print(f"\n📄 Generating report...")
        
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("BRAZILIAN LEGISLATION MONITORING REPORT")
        report_lines.append("Dell Technologies Brazil")
        report_lines.append("=" * 80)
        report_lines.append(f"Date: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        report_lines.append(f"Total relevant articles: {len(articles)}")
        report_lines.append("=" * 80)
        report_lines.append("")
        
        for i, article in enumerate(articles, 1):
            report_lines.append(f"\n{'=' * 80}")
            report_lines.append(f"ARTICLE {i} OF {len(articles)}")
            report_lines.append(f"{'=' * 80}")
            report_lines.append(f"\nTitle: {article['title']}")
            report_lines.append(f"Source: {article['source']}")
            report_lines.append(f"Date: {article['date']}")
            report_lines.append(f"URL: {article['url']}")
            report_lines.append(f"\n{'=' * 80}")
            report_lines.append("DELL ANALYSIS:")
            report_lines.append(f"{'=' * 80}")
            report_lines.append(article['dell_analysis'])
            report_lines.append(f"\n{'=' * 80}\n")
        
        report_lines.append("\n" + "=" * 80)
        report_lines.append("END OF REPORT")
        report_lines.append("=" * 80)
        
        return "\n".join(report_lines)
    
    def save_report(self, report: str, filename: str = None, output_dir: str = None):
        """
        Save report to file
        
        Args:
            report: Report content
            filename: Optional filename (auto-generated if not provided)
            output_dir: Optional output directory
        
        Returns:
            Filepath of saved file
        """
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"brazil_monitor_{timestamp}.txt"
        
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            filepath = os.path.join(output_dir, filename)
        else:
            filepath = filename
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(report)
            
            print(f"\n✅ Report saved: {filepath}")
            return filepath
            
        except Exception as e:
            print(f"❌ Error saving report: {str(e)}")
            return None
    
    # =========================================================================
    # MAIN EXECUTION METHOD
    # Orchestrates the complete monitoring workflow
    # =========================================================================
    def run(self, output_dir: str = None):
        """
        Execute complete monitoring workflow
        
        Workflow:
        1. Scrape all configured sites
        2. Analyze articles with AI
        3. Filter Dell-relevant articles
        4. Generate and save report
        
        Args:
            output_dir: Directory to save report
        
        Returns:
            Dictionary with results or None if no relevant articles
        """
        print("\n" + "=" * 80)
        print("🚀 DELL BRAZIL TAX LEGISLATION MONITOR")
        print("=" * 80)
        
        # Step 1: Scrape sites
        articles = self.scrape_sites()
        
        if not articles:
            print("\n❌ No articles found. Exiting...")
            return None
        
        # Step 2: AI analysis
        relevant_articles = self.analyze_articles_with_ai(articles)
        
        if not relevant_articles:
            print("\n⚠️ No Dell-relevant articles found.")
            return None
        
        # Step 3: Generate report
        report = self.generate_report(relevant_articles)
        
        # Step 4: Display report
        print("\n" + "=" * 80)
        print("📋 GENERATED REPORT:")
        print("=" * 80)
        print(report)
        
        # Step 5: Save report
        filename = self.save_report(report, output_dir=output_dir)
        
        print("\n" + "=" * 80)
        print("✅ MONITORING COMPLETE!")
        print("=" * 80)
        
        return {
            "articles": relevant_articles,
            "report": report,
            "saved_file": filename
        }


# =============================================================================
# STANDALONE EXECUTION
# Allows running the monitor directly from command line
# =============================================================================
def main():
    """Main function for standalone execution"""
    if not DEV_GENAI_API_KEY:
        print("❌ ERROR: DEV_GENAI_API_KEY not configured!")
        print("Configure the environment variable or .env file")
        return
    
    try:
        monitor = BrazilMonitor()
        monitor.run()
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Execution interrupted by user")
    except Exception as e:
        print(f"\n❌ Fatal error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
