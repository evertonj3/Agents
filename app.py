#!/usr/bin/env python3
"""
Dell Brazil Tax Legislation Analysis System - FastAPI Web Interface v5.3
With real-time terminal streaming via SSE
"""

import sys
import os
import re
import json
import asyncio
import queue
import threading
from datetime import datetime
from typing import Optional, Dict, List, Generator
from pathlib import Path
from contextlib import redirect_stdout
import io

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# =============================================================================
# APP CONFIGURATION
# =============================================================================
app = FastAPI(title="Dell Brazil Tax Legislation Analysis", version="5.3")
templates = Jinja2Templates(directory="templates")

OUTPUT_DIR = "/mnt/user-data/outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Global queue for streaming logs
log_queues: Dict[str, queue.Queue] = {}

# =============================================================================
# MODULE IMPORTS
# =============================================================================
HAS_WORKFLOW = False
HAS_BRAZIL_MONITOR = False

try:
    from config import validate_config, DEV_GENAI_API_KEY
    from workflow import LegislacaoWorkflow
    HAS_WORKFLOW = True
except ImportError as e:
    print(f"⚠️ Workflow not available: {e}")

try:
    from brazil_monitor import BrazilMonitor
    HAS_BRAZIL_MONITOR = True
except ImportError as e:
    print(f"⚠️ Brazil Monitor not available: {e}")

# =============================================================================
# TRANSLATIONS
# =============================================================================
TRANSLATIONS = {
    "en": {
        "page_title": "Dell Tax Legislation Analysis",
        "header_title": "Legal Change Mapping Agent",
        "header_subtitle": "Dell Technologies Brazil | AI-Powered Analysis",
        "nav_analyze": "Analyze",
        "mode_url": "URL Analysis",
        "mode_search": "Web Search",
        "mode_monitor": "Auto Monitor",
        "url_placeholder": "Enter legislation URL...",
        "search_placeholder": "Search keywords (e.g., 'MP 1318 2025', 'ICMS technology')",
        "btn_analyze": "Analyze",
        "btn_search": "Search",
        "btn_start_monitor": "Start Monitoring",
        "loading": "Analyzing legislation...",
        "relevance": "Dell Relevance",
        "high": "HIGH",
        "medium": "MEDIUM",
        "low": "LOW",
        "fiscal_changes": "Fiscal Changes",
        "system_changes": "System Changes Required",
        "deadlines": "Critical Deadlines",
        "compliance_risks": "Compliance Risks",
        "actions_required": "Actions Required",
        "executive_summary": "Executive Summary",
        "tax_impact": "Tax Impact by Tribute",
        "sources": "Sources Consulted",
        "download_report": "Download Report",
        "error_occurred": "An error occurred",
        "config_error": "Configuration incomplete",
        "workflow_unavailable": "Analysis workflow unavailable",
        "footer_text": "Dell GenAI v5.3 | 13 Specialized Agents",
        "transition_schedule": "Transition Schedule",
    },
    "pt": {
        "page_title": "Análise de Legislação Tributária Dell",
        "header_title": "Sistema de Análise de Legislação Tributária",
        "header_subtitle": "Dell Technologies Brazil | Análise com IA",
        "nav_analyze": "Analisar",
        "mode_url": "Análise de URL",
        "mode_search": "Busca Web",
        "mode_monitor": "Monitoramento",
        "url_placeholder": "Digite a URL da legislação...",
        "search_placeholder": "Palavras-chave (ex: 'MP 1318 2025', 'ICMS tecnologia')",
        "btn_analyze": "Analisar",
        "btn_search": "Buscar",
        "btn_start_monitor": "Iniciar Monitoramento",
        "loading": "Analisando legislação...",
        "relevance": "Relevância para Dell",
        "high": "ALTA",
        "medium": "MÉDIA",
        "low": "BAIXA",
        "fiscal_changes": "Alterações Fiscais",
        "system_changes": "Mudanças no Sistema",
        "deadlines": "Prazos Críticos",
        "compliance_risks": "Riscos de Compliance",
        "actions_required": "Ações Necessárias",
        "executive_summary": "Resumo Executivo",
        "tax_impact": "Impacto por Tributo",
        "sources": "Fontes Consultadas",
        "download_report": "Baixar Relatório",
        "error_occurred": "Ocorreu um erro",
        "config_error": "Configuração incompleta",
        "workflow_unavailable": "Workflow indisponível",
        "footer_text": "Dell GenAI v5.3 | 13 Agentes Especializados",
        "transition_schedule": "Cronograma de Transição",
    }
}

def get_translations(lang: str = "en") -> Dict:
    return TRANSLATIONS.get(lang, TRANSLATIONS["en"])


# =============================================================================
# LOG CAPTURE CLASS
# =============================================================================
class LogCapture:
    """Captures print output and sends to queue"""
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.original_stdout = sys.stdout
        
    def write(self, text):
        self.original_stdout.write(text)
        if text.strip() and self.session_id in log_queues:
            log_queues[self.session_id].put(text)
    
    def flush(self):
        self.original_stdout.flush()


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================
def parse_analysis_report(report: str) -> Dict:
    """Parse the analysis report into structured sections"""
    sections = {
        "header": {},
        "executive_summary": "",
        "relevance": "MEDIUM",
        "relevance_class": "medium",
        "justification": "",
        "fiscal_changes": [],
        "system_changes": [],
        "tax_impact": [],
        "deadlines": [],
        "compliance_risks": [],
        "actions": {"main": "", "technical": [], "fiscal": []},
        "sources": [],
        "transition_schedule": [],
        "raw_report": report
    }
    
    if not report:
        return sections
    
    # Extract header info
    type_match = re.search(r'🏛️\s*(.+?)(?:\n|$)', report)
    if type_match:
        sections["header"]["type"] = type_match.group(1).strip()
    
    number_match = re.search(r'📄\s*(.+?)(?:\n|$)', report)
    if number_match:
        sections["header"]["number"] = number_match.group(1).strip()
    
    date_match = re.search(r'📅\s*Data:\s*(.+?)(?:\n|$)', report)
    if date_match:
        sections["header"]["date"] = date_match.group(1).strip()
    
    # Extract relevance
    relevance_match = re.search(r'RELEVÂNCIA\s*(?:PARA\s*)?DELL[:\s]*\*?\*?\s*(ALTA|MÉDIA|MEDIA|BAIXA|HIGH|MEDIUM|LOW)', report, re.IGNORECASE)
    if relevance_match:
        rel = relevance_match.group(1).upper()
        if rel in ["ALTA", "HIGH"]:
            sections["relevance"] = "HIGH"
            sections["relevance_class"] = "high"
        elif rel in ["MÉDIA", "MEDIA", "MEDIUM"]:
            sections["relevance"] = "MEDIUM"
            sections["relevance_class"] = "medium"
        else:
            sections["relevance"] = "LOW"
            sections["relevance_class"] = "low"
    
    # Extract executive summary
    exec_match = re.search(r'RESUMO EXECUTIVO\s*={3,}(.*?)(?:={3,}|2️⃣)', report, re.DOTALL | re.IGNORECASE)
    if exec_match:
        sections["executive_summary"] = exec_match.group(1).strip()
    
    # Extract justification
    just_match = re.search(r'Justificativa[:\s]*(.*?)(?:\n\n|={3,})', report, re.DOTALL | re.IGNORECASE)
    if just_match:
        sections["justification"] = just_match.group(1).strip()[:300]
    
    # Extract fiscal changes
    fiscal_match = re.search(r'ALTERAÇÕES\s*FISCAIS\s*={3,}(.*?)(?:={3,}|3️⃣)', report, re.DOTALL | re.IGNORECASE)
    if fiscal_match:
        items = re.findall(r'[•-]\s*(.+?)(?=\n[•-]|\n\n|$)', fiscal_match.group(1))
        sections["fiscal_changes"] = [i.strip() for i in items[:8] if i.strip()]
    
    # Extract system changes
    system_match = re.search(r'MUDANÇAS.*?SISTEMA\s*={3,}(.*?)(?:={3,}|4️⃣)', report, re.DOTALL | re.IGNORECASE)
    if system_match:
        items = re.findall(r'[•-]\s*(.+?)(?=\n[•-]|\n\n|$)', system_match.group(1))
        sections["system_changes"] = [i.strip() for i in items[:8] if i.strip()]
    
    # Extract tax impact - Enhanced extraction
    tax_match = re.search(r'IMPACTO.*?TRIBUT[AÁ]RIO\s*={3,}(.*?)(?:={3,}|5️⃣|CRONOGRAMA)', report, re.DOTALL | re.IGNORECASE)
    if tax_match:
        tax_content = tax_match.group(1)
        # Try to find specific tribute mentions with details
        tributes = re.findall(r'(IPI|ICMS|PIS|COFINS|IRPJ|CSLL|ISS|IOF|II|IE|CBS|IBS|IS|CIDE)[:\s•\-]+([^\n•]+(?:\n(?![A-Z]{2,})[^\n•]+)*)', tax_content)
        for tribute, details in tributes:
            clean_details = re.sub(r'\s+', ' ', details.strip())[:300]
            if clean_details:
                sections["tax_impact"].append({"tribute": tribute.strip(), "details": clean_details})
        
        # Also look for bullet points with tax names
        if not sections["tax_impact"]:
            items = re.findall(r'[•-]\s*((?:IPI|ICMS|PIS|COFINS|IRPJ|CSLL|ISS|IOF|II|CBS|IBS|IS|CIDE)[^•\n]+)', tax_content)
            for item in items:
                tax_name = re.match(r'(IPI|ICMS|PIS|COFINS|IRPJ|CSLL|ISS|IOF|II|CBS|IBS|IS|CIDE)', item)
                if tax_name:
                    sections["tax_impact"].append({
                        "tribute": tax_name.group(1),
                        "details": item[len(tax_name.group(1)):].strip()[:300]
                    })
    
    # Also check for tax mentions in system changes section
    if not sections["tax_impact"]:
        system_section = re.search(r'MUDANÇAS.*?SISTEMA\s*={3,}(.*?)(?:={3,})', report, re.DOTALL | re.IGNORECASE)
        if system_section:
            tax_mentions = re.findall(r'(IPI|ICMS|PIS|COFINS|IRPJ|CSLL|CBS|IBS)[:\s]+([^•\n]+)', system_section.group(1))
            for tribute, details in tax_mentions[:6]:
                sections["tax_impact"].append({"tribute": tribute.strip(), "details": details.strip()[:200]})
    
    # Extract deadlines
    deadline_match = re.search(r'PRAZOS.*?CR[ÍI]TICOS\s*={3,}(.*?)(?:={3,}|6️⃣)', report, re.DOTALL | re.IGNORECASE)
    if deadline_match:
        items = re.findall(r'[•-]\s*(.+?)(?=\n[•-]|\n\n|$)', deadline_match.group(1))
        sections["deadlines"] = [i.strip() for i in items[:6] if i.strip()]
    
    # Extract compliance risks
    risk_match = re.search(r'RISCOS.*?COMPLIANCE\s*={3,}(.*?)(?:={3,}|7️⃣)', report, re.DOTALL | re.IGNORECASE)
    if risk_match:
        items = re.findall(r'[•-]\s*(.+?)(?=\n[•-]|\n\n|$)', risk_match.group(1))
        sections["compliance_risks"] = [i.strip() for i in items[:6] if i.strip()]
    
    # Extract sources
    sources_match = re.search(r'FONTES\s*CONSULTADAS\s*={3,}(.*?)(?:={3,}|⚙️)', report, re.DOTALL | re.IGNORECASE)
    if sources_match:
        source_blocks = re.findall(r'\d+\.\s*(.+?)\n\s*URL:\s*(\S+)', sources_match.group(1))
        for title, url in source_blocks[:5]:
            sections["sources"].append({"title": title.strip(), "url": url.strip()})
    
    # Extract transition schedule
    transition_match = re.search(r'CRONOGRAMA.*?TRANSIÇÃO\s*={3,}(.*?)(?:={3,}|\d️⃣)', report, re.DOTALL | re.IGNORECASE)
    if transition_match:
        year_items = re.findall(r'(202\d)[:\s-]+(.+?)(?=\n202|\n\n|$)', transition_match.group(1), re.DOTALL)
        for year, details in year_items[:8]:
            sections["transition_schedule"].append({"year": year, "details": details.strip()[:200]})
    
    return sections


def save_report(report: str, prefix: str = "analysis") -> str:
    """Save report to file"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filepath = f"{OUTPUT_DIR}/{prefix}_{timestamp}.txt"
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report)
        return filepath
    except Exception as e:
        print(f"Error saving report: {e}")
        return ""


# =============================================================================
# ROUTES
# =============================================================================
@app.get("/", response_class=HTMLResponse)
async def home(request: Request, lang: str = "en"):
    """Main page"""
    t = get_translations(lang)
    is_valid = False
    if HAS_WORKFLOW:
        is_valid, _ = validate_config()
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "t": t,
        "lang": lang,
        "workflow_available": HAS_WORKFLOW,
        "monitor_available": HAS_BRAZIL_MONITOR,
        "config_valid": is_valid,
        "results": None,
        "error": None
    })


@app.post("/analyze", response_class=HTMLResponse)
async def analyze(
    request: Request,
    mode: str = Form(...),
    url: str = Form(None),
    query: str = Form(None),
    lang: str = Form("en")
):
    """Process analysis request"""
    t = get_translations(lang)
    error = None
    results = None
    
    if not HAS_WORKFLOW:
        error = t["workflow_unavailable"]
    else:
        is_valid, missing = validate_config()
        if not is_valid:
            error = f"{t['config_error']}: {', '.join(missing)}"
    
    if not error:
        try:
            workflow = LegislacaoWorkflow()
            
            if mode == "url" and url:
                if not url.startswith('http'):
                    error = "Invalid URL"
                else:
                    result = workflow.run(url=url)
                    if "error" in result:
                        error = result["error"]
                    else:
                        results = parse_analysis_report(result.get("final_analysis", ""))
                        filepath = save_report(result["final_analysis"], "url_analysis")
                        if filepath:
                            results["saved_file"] = filepath
            
            elif mode == "search" and query:
                result = workflow.run(query=query)
                if "error" in result:
                    error = result["error"]
                else:
                    results = parse_analysis_report(result.get("final_analysis", ""))
                    filepath = save_report(result["final_analysis"], "search_analysis")
                    if filepath:
                        results["saved_file"] = filepath
            else:
                error = "Invalid request"
                
        except Exception as e:
            error = str(e)
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "t": t,
        "lang": lang,
        "workflow_available": HAS_WORKFLOW,
        "monitor_available": HAS_BRAZIL_MONITOR,
        "config_valid": HAS_WORKFLOW,
        "results": results,
        "error": error,
        "submitted_url": url,
        "submitted_query": query,
        "submitted_mode": mode
    })


@app.post("/monitor", response_class=HTMLResponse)
async def monitor(request: Request, lang: str = Form("en")):
    """Run automatic monitoring"""
    t = get_translations(lang)
    error = None
    results = None
    
    if not HAS_BRAZIL_MONITOR:
        error = "Brazil Monitor not available"
    else:
        try:
            mon = BrazilMonitor()
            result = mon.run(output_dir=OUTPUT_DIR)
            
            if result and "error" not in result:
                results = {
                    "monitor_results": result,
                    "articles_found": result.get("articles_found", 0),
                    "relevant_articles": result.get("relevant_articles", []),
                    "saved_file": result.get("saved_file", "")
                }
            else:
                error = result.get("error", "No results found") if result else "No results"
        except Exception as e:
            error = str(e)
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "t": t,
        "lang": lang,
        "workflow_available": HAS_WORKFLOW,
        "monitor_available": HAS_BRAZIL_MONITOR,
        "config_valid": HAS_WORKFLOW,
        "results": results,
        "error": error,
        "submitted_mode": "monitor"
    })


@app.get("/download/{filename}")
async def download_file(filename: str):
    """Download report file"""
    filepath = os.path.join(OUTPUT_DIR, filename)
    if not os.path.abspath(filepath).startswith(os.path.abspath(OUTPUT_DIR)):
        raise HTTPException(status_code=403, detail="Access denied")
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path=filepath, filename=filename, media_type="text/plain")


@app.get("/api/status")
async def api_status():
    """API status endpoint"""
    is_valid, missing = validate_config() if HAS_WORKFLOW else (False, [])
    return JSONResponse({
        "status": "ok" if is_valid else "degraded",
        "workflow_available": HAS_WORKFLOW,
        "monitor_available": HAS_BRAZIL_MONITOR,
        "config_valid": is_valid,
        "version": "5.3"
    })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

