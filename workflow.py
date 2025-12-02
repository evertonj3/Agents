"""
Workflow LangGraph v5.0 - COM VALIDATION AGENT
Pipeline com 13 Agentes especializados

NOVIDADES v5.0:
- ✅ NOVO: ValidationAgent para garantir consistência
- ✅ Corrige automaticamente SUSPENSÃO vs ISENÇÃO vs ALÍQUOTA 0%
- ✅ Valida tributos contra texto original
- ✅ Integração com reform_knowledge_base.py
- ✅ Passa known_law_key entre agentes
- ✅ Fallback automático para LC 214 e outras leis complexas
"""

from typing import TypedDict, List, Dict, Optional
from langgraph.graph import StateGraph, END
from web_search_agent import WebSearchAgent
from date_extraction_agent import DateExtractionAgent
from legal_analysis_agent import *
from system_changes_agent import SystemChangesAgent
from final_assembly_agent import FinalAssemblyAgent
from review_agent import ReviewAgent

# 🆕 v5.0: Importa ValidationAgent
try:
    from validation_agent import ValidationAgent
    HAS_VALIDATION_AGENT = True
except ImportError:
    HAS_VALIDATION_AGENT = False
    print("   ⚠️  ValidationAgent não disponível")


class WorkflowState(TypedDict):
    """Estado do workflow - v5.0 com validation_status"""
    query: str
    urls: List[str]
    web_results: List[Dict]
    legislation_type: str
    
    raw_extraction: Dict
    date_extraction: Dict
    quantification: Dict
    structured_data: Dict
    validation_results: Dict
    enhanced_data: Dict
    impact_analysis: Dict
    system_changes: Dict
    dell_analysis: Dict
    
    # v4.9: Chave da lei conhecida (LC_214, MPV_1318, etc.)
    known_law_key: Optional[str]
    
    # 🆕 v5.0: Status da validação
    validation_status: Optional[Dict]
    
    final_analysis: str
    workflow_complete: bool


class LegislacaoWorkflow:
    """Workflow com 13 agentes - VERSÃO v5.0 COM VALIDATION AGENT"""
    
    def __init__(self):
        print("\n🤖 Inicializando Workflow v5.0 - COM VALIDATION AGENT")
        print("="*80)
        print("🗃️  Arquitetura: 13 Agentes Especializados")
        print("🎯 Análise para Dell Technologies Brazil")
        print("📋 Suporta: Lei, LC, MP, Decreto, Portaria, etc.")
        print("🆕 v5.0: ValidationAgent para consistência de extrações")
        print("="*80)
        
        self.web_search = WebSearchAgent(
            follow_link_depth=1,
            max_links_per_page=5
        )
        self.raw_extraction = RawExtractionAgent()
        self.date_extraction = DateExtractionAgent()
        self.quantification = QuantificationAgent()
        self.structure_validation = StructureValidationAgent()
        self.enhancement = EnhancementAgent()
        self.impact_analysis = ImpactAnalysisAgent()
        self.system_changes = SystemChangesAgent()
        
        # 🆕 v5.0: Inicializa ValidationAgent
        if HAS_VALIDATION_AGENT:
            self.validation_agent = ValidationAgent()
            print("   ✅ ValidationAgent carregado")
        else:
            self.validation_agent = None
            print("   ⚠️  ValidationAgent não disponível")
        
        self.dell_relevance = DellRelevanceAgent()
        self.review_agent = ReviewAgent()
        self.final_assembly = FinalAssemblyAgent()
        
        self.workflow = self._build_workflow()
        print("✅ Workflow v5.0 pronto\n")
    
    def _build_workflow(self) -> StateGraph:
        """Constrói pipeline com 13 agentes"""
        wf = StateGraph(WorkflowState)
        
        # Define nós (13 agentes)
        wf.add_node("input", self.process_input)
        wf.add_node("search", self.search_web)
        wf.add_node("detect_type", self.detect_type)
        wf.add_node("raw_extract", self.extract_raw)
        wf.add_node("extract_dates", self.extract_dates)
        wf.add_node("extract_numbers", self.extract_numbers)
        wf.add_node("validate", self.validate)
        wf.add_node("enhance", self.enhance)
        wf.add_node("analyze_impact", self.analyze_impact)
        wf.add_node("system_changes", self.analyze_system_changes)
        wf.add_node("validation_check", self.run_validation)  # 🆕 v5.0
        wf.add_node("dell_relevance", self.dell_relevance_check)
        wf.add_node("review", self.review_outputs)
        wf.add_node("assemble", self.assemble)
        
        # Define fluxo
        wf.set_entry_point("input")
        wf.add_edge("input", "search")
        wf.add_edge("search", "detect_type")
        wf.add_edge("detect_type", "raw_extract")
        wf.add_edge("raw_extract", "extract_dates")
        wf.add_edge("extract_dates", "extract_numbers")
        wf.add_edge("extract_numbers", "validate")
        
        # Condicional: enhance se necessário
        wf.add_conditional_edges(
            "validate",
            lambda s: "enhance" if s["validation_results"].get("needs_enhancement") else "analyze_impact",
            {"enhance": "enhance", "analyze_impact": "analyze_impact"}
        )
        
        wf.add_edge("enhance", "analyze_impact")
        wf.add_edge("analyze_impact", "system_changes")
        wf.add_edge("system_changes", "validation_check")  # 🆕 v5.0: Roda validação após system_changes
        wf.add_edge("validation_check", "dell_relevance")
        wf.add_edge("dell_relevance", "review")
        wf.add_edge("review", "assemble")
        wf.add_edge("assemble", END)
        
        return wf.compile()
    
    def process_input(self, state: WorkflowState) -> WorkflowState:
        """Agente 1: Processamento de input"""
        print("\n📥 AGENTE 1: Input Processing")
        # Inicializa campos
        state["known_law_key"] = None
        state["validation_status"] = None  # 🆕 v5.0
        return state
    
    def search_web(self, state: WorkflowState) -> WorkflowState:
        """Agente 2: Web Search"""
        print("\n🔍 AGENTE 2: Web Search")
        urls = state.get("urls", [])
        
        if urls:
            results = self.web_search.fetch_multiple_urls(urls)
        else:
            results = self.web_search.search(state["query"], max_results=15)
        
        state["web_results"] = results
        print(f"   ✅ {len(results)} fontes extraídas")
        return state
    
    def detect_type(self, state: WorkflowState) -> WorkflowState:
        """Agente 3: Type Detection"""
        print("\n🔎 AGENTE 3: Legislation Type Detection")
        
        if state["web_results"]:
            first = state["web_results"][0]
            content = first.get("content", "")
            url = first.get("url", "")
            
            if content:
                leg_type = self.web_search.identify_legislation_type(content, url)
            else:
                leg_type = "default"
            
            state["legislation_type"] = leg_type
            print(f"   📋 Tipo identificado: {leg_type}")
            
            # Tenta detectar lei conhecida
            try:
                from reform_knowledge_base import detect_known_legislation
                known_key = detect_known_legislation(url, content, first.get("title", ""))
                if known_key:
                    state["known_law_key"] = known_key
                    print(f"   📚 Lei conhecida detectada: {known_key}")
            except ImportError:
                pass
        else:
            state["legislation_type"] = "default"
            print(f"   ⚠️  Sem resultados, usando tipo padrão")
        
        return state
    
    def extract_raw(self, state: WorkflowState) -> WorkflowState:
        """Agente 4: Raw Extraction"""
        print("\n📊 AGENTE 4: Raw Extraction")
        
        raw = self.raw_extraction.extract(
            state["web_results"],
            state["query"],
            state["legislation_type"]
        )
        state["raw_extraction"] = raw
        
        text_len = len(raw.get("raw_text", ""))
        print(f"   ✅ Extraído: {text_len:,} caracteres")
        return state
    
    def extract_dates(self, state: WorkflowState) -> WorkflowState:
        """Agente 5: Date Extraction"""
        print("\n📅 AGENTE 5: Date Extraction")
        
        dates = self.date_extraction.extract(
            state["web_results"],
            state["raw_extraction"]
        )
        state["date_extraction"] = dates
        
        # Atualiza known_law_key se o agente detectou
        if dates.get("known_law_key") and not state.get("known_law_key"):
            state["known_law_key"] = dates["known_law_key"]
            print(f"   📚 Lei conhecida detectada pelo DateExtraction: {dates['known_law_key']}")
        
        count = len(dates.get("vigencias", []))
        print(f"   ✅ {count} vigências extraídas")
        return state
    
    def extract_numbers(self, state: WorkflowState) -> WorkflowState:
        """Agente 6: Quantification"""
        print("\n🔢 AGENTE 6: Quantification")
        
        quant = self.quantification.extract(
            state["web_results"],
            state["raw_extraction"]
        )
        state["quantification"] = quant
        
        pcts = len(quant.get("percentuais", []))
        print(f"   ✅ {pcts} valores quantitativos encontrados")
        return state
    
    def validate(self, state: WorkflowState) -> WorkflowState:
        """Agente 7: Validation"""
        print("\n✅ AGENTE 7: Structure Validation")
        
        structured, validation = self.structure_validation.process(
            state["raw_extraction"],
            state["date_extraction"],
            state["quantification"],
            state["legislation_type"]
        )
        
        state["structured_data"] = structured
        state["validation_results"] = validation
        
        score = validation["completeness_score"] * 100
        print(f"   📊 Completude: {score:.1f}%")
        
        return state
    
    def enhance(self, state: WorkflowState) -> WorkflowState:
        """Agente 8: Enhancement"""
        print("\n🔧 AGENTE 8: Data Enhancement")
        
        enhanced = self.enhancement.enhance(
            state["structured_data"],
            state["validation_results"],
            state["web_results"]
        )
        state["enhanced_data"] = enhanced
        print("   ✅ Enhancement aplicado")
        return state
    
    def analyze_impact(self, state: WorkflowState) -> WorkflowState:
        """Agente 9: Impact Analysis"""
        print("\n🎯 AGENTE 9: Impact Analysis")
        
        data = state.get("enhanced_data") or state["structured_data"]
        
        impact = self.impact_analysis.analyze(
            data,
            state["web_results"]
        )
        state["impact_analysis"] = impact
        print("   ✅ Análise de impacto concluída")
        return state
    
    def analyze_system_changes(self, state: WorkflowState) -> WorkflowState:
        """Agente 10: System Changes Analysis"""
        print("\n⚙️  AGENTE 10: System Changes Analysis")
        
        data = state.get("enhanced_data") or state["structured_data"]
        
        # Passa known_law_key para o agente
        changes = self.system_changes.identify_changes(
            data,
            state["impact_analysis"],
            known_law_key=state.get("known_law_key")
        )
        state["system_changes"] = changes
        
        # Atualiza known_law_key se o agente detectou
        if changes.get("known_law_key") and not state.get("known_law_key"):
            state["known_law_key"] = changes["known_law_key"]
        
        print("   ✅ Mudanças no sistema identificadas")
        return state
    
    def run_validation(self, state: WorkflowState) -> WorkflowState:
        """
        🆕 Agente 11: Validation Agent (v5.0)
        Valida extrações contra texto original e corrige inconsistências
        """
        if self.validation_agent:
            state = self.validation_agent.validate(state)
        else:
            print("\n🔍 AGENTE 11: Validation Agent")
            print("   ⚠️  ValidationAgent não disponível, pulando validação")
        
        return state
    
    def dell_relevance_check(self, state: WorkflowState) -> WorkflowState:
        """Agente 12: Dell Relevance Analysis"""
        print("\n🏢 AGENTE 12: Dell Relevance Analysis")
        
        data = state.get("enhanced_data") or state["structured_data"]
        
        dell_analysis = self.dell_relevance.analyze(
            data,
            state["impact_analysis"],
            state["web_results"]
        )
        state["dell_analysis"] = dell_analysis
        
        relevance = dell_analysis.get("relevancia", "NÃO DETERMINADA")
        print(f"   ✅ Relevância Dell: {relevance}")
        return state
    
    def review_outputs(self, state: WorkflowState) -> WorkflowState:
        """Agente 12.5: Review & Quality Control"""
        return self.review_agent.review(state)
    
    def assemble(self, state: WorkflowState) -> WorkflowState:
        """Agente 13: Montagem final do relatório"""
        print("\n📝 AGENTE 13: Final Assembly (v5.0)")
        
        data = state.get("enhanced_data") or state["structured_data"]
        
        # Passa known_law_key para assembly
        report = self.final_assembly.assemble(
            state["query"],
            data,
            state["date_extraction"],
            state["quantification"],
            state["impact_analysis"],
            state["dell_analysis"],
            state["system_changes"],
            state["legislation_type"],
            state["web_results"],
            state["validation_results"],
            known_law_key=state.get("known_law_key")
        )
        
        state["final_analysis"] = report
        state["workflow_complete"] = True
        print("   ✅ Relatório estruturado gerado (v5.0)")
        return state
    
    def run(self, query: str = None, url: str = None, urls: List[str] = None) -> Dict:
        """Executa workflow completo"""
        print("\n" + "="*80)
        print("🚀 WORKFLOW v5.0 - COM VALIDATION AGENT")
        print("="*80)
        
        url_list = urls or ([url] if url else [])
        
        if not query and not url_list:
            raise ValueError("Forneça query ou URLs")
        
        if not query:
            query = f"Analisar legislação: {', '.join(url_list)}"
        
        state = {
            "query": query,
            "urls": url_list,
            "web_results": [],
            "legislation_type": "default",
            "raw_extraction": {},
            "date_extraction": {},
            "quantification": {},
            "structured_data": {},
            "validation_results": {},
            "enhanced_data": {},
            "impact_analysis": {},
            "system_changes": {},
            "dell_analysis": {},
            "known_law_key": None,
            "validation_status": None,  # 🆕 v5.0
            "final_analysis": "",
            "workflow_complete": False
        }
        
        final = self.workflow.invoke(state)
        
        print("\n" + "="*80)
        print("✅ WORKFLOW v5.0 CONCLUÍDO")
        if final.get("known_law_key"):
            print(f"📚 Knowledge Base utilizado: {final['known_law_key']}")
        
        # 🆕 v5.0: Mostra status da validação
        validation_status = final.get("validation_status", {})
        if validation_status:
            corrections = validation_status.get("corrections_made", 0)
            confidence = validation_status.get("confidence", "N/A")
            if corrections > 0:
                print(f"🔧 Correções aplicadas: {corrections}")
            print(f"📊 Confiança: {confidence}")
        
        print("="*80)
        
        return final