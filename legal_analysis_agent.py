"""
Agentes de Análise Legal v4 - GENÉRICO
10 Agentes Especializados incluindo análise de relevância Dell

CORREÇÃO v4.4:
- REMOVIDA classe DateExtractionAgent duplicada (usava regex v4.3)
- Agora usa DateExtractionAgent de date_extraction_agent.py (v5.0 LLM reasoning)
- max_tokens já estava em 8000 (OK)
"""

from typing import List, Dict
from openai import OpenAI
import json
import re
from config import *


class BaseAgent:
    """Classe base para agentes"""
    
    def __init__(self):
        self.client = OpenAI(
            api_key=DEV_GENAI_API_KEY,
            base_url=DEV_GENAI_API_URL
        )
        self.model = MODEL_NAME
    
    def _call_api(self, prompt: str, temperature: float = 0.1) -> str:
        """Chama Dell GenAI API"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Você é um especialista em legislação brasileira com foco em análise tributária e corporativa."},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=8000
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"Erro na API: {str(e)}")


class RawExtractionAgent(BaseAgent):
    """Agente 4: Extração estruturada de dados"""
    
    def extract(self, web_results: List[Dict], query: str, legislation_type: str) -> Dict:
        """Extrai dados estruturados de qualquer tipo de legislação"""
        print("   🔄 Extraindo dados estruturados...")
        
        content = self._consolidate_content(web_results)
        
        prompt = GENERIC_EXTRACTION_PROMPT.format(
            content=content[:40000],
            query=query
        )
        
        result = self._call_api(prompt)
        
        extracted = {
            "raw_text": result,
            "content_length": len(content),
            "sources_count": len(web_results),
            "legislation_type": legislation_type
        }
        
        return extracted
    
    def _consolidate_content(self, web_results: List[Dict]) -> str:
        """Consolida conteúdo priorizando fontes oficiais"""
        parts = []
        
        # PDFs primeiro (geralmente são os documentos completos)
        for r in web_results:
            if r.get('content_type') == 'pdf':
                parts.append(f"\n===PDF: {r.get('title')}===\n")
                parts.append(r.get('content', ''))
        
        # HTML oficial
        for r in web_results:
            if r.get('is_official') and r.get('content_type') != 'pdf':
                parts.append(f"\n===OFICIAL: {r.get('title')}===\n")
                parts.append(r.get('content', ''))
        
        # Outras fontes
        for r in web_results:
            if not r.get('is_official') and r.get('content_type') != 'pdf':
                parts.append(f"\n==={r.get('title')}===\n")
                parts.append(r.get('content', ''))
        
        return "\n".join(parts)


class SectionExtractionAgent(BaseAgent):
    """Agente especializado em extrair seções específicas"""
    
    def extract_section(self, content: str, section_name: str, focus_areas: str) -> str:
        """Extrai uma seção específica da legislação"""
        print(f"      📋 Extraindo {section_name}...")
        
        prompt = SECTION_EXTRACTION_PROMPT.format(
            section_name=section_name,
            content=content[:30000],
            focus_areas=focus_areas
        )
        result = self._call_api(prompt, temperature=0.0)
        
        return result.strip()
    
    def extract_impact_analysis(self, content: str) -> Dict:
        """Analisa o impacto geral da legislação"""
        print("      🎯 Analisando impacto...")
        
        prompt = IMPACT_ANALYSIS_PROMPT.format(content=content[:35000])
        result = self._call_api(prompt, temperature=0.0)
        
        # Tenta estruturar a resposta
        impact = {
            "raw_analysis": result,
            "setores": self._extract_section_content(result, "SETORES"),
            "tipo_empresa": self._extract_section_content(result, "TIPO DE EMPRESA"),
            "abrangencia": self._extract_section_content(result, "ABRANGÊNCIA"),
            "tributos": self._extract_section_content(result, "TRIBUTOS")
        }
        
        return impact
    
    def _extract_section_content(self, text: str, section_marker: str) -> str:
        """Extrai conteúdo de uma seção marcada"""
        try:
            pattern = rf"{section_marker}[:\s]+(.*?)(?=\n\n|\Z)"
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1).strip()
        except:
            pass
        return "Informação não identificada"


# ============================================================================
# NOTA: DateExtractionAgent foi REMOVIDA deste arquivo!
# Use a versão v5.0 de date_extraction_agent.py que usa LLM reasoning
# ============================================================================


class QuantificationAgent(BaseAgent):
    """Agente 6: Extração de números e percentuais"""
    
    def extract(self, web_results: List[Dict], raw_extraction: Dict) -> Dict:
        """Extrai números e percentuais"""
        print("   🔢 Extraindo quantificação...")
        
        content = self._consolidate_content(web_results)
        
        # Regex para números
        percentuais = self._extract_percentages(content)
        
        # LLM para contexto
        numbers_llm = self._extract_numbers_llm(content)
        
        return {
            "percentuais": percentuais,
            "llm_analysis": numbers_llm,
            "total_encontrado": len(percentuais)
        }
    
    def _extract_numbers_llm(self, content: str) -> str:
        """Extração de números via LLM"""
        prompt = NUMBERS_EXTRACTION_PROMPT.format(content=content[:30000])
        try:
            result = self._call_api(prompt, temperature=0.0)
            return result
        except:
            return "Não foi possível extrair números via LLM"
    
    def _consolidate_content(self, web_results: List[Dict]) -> str:
        """Consolida conteúdo"""
        parts = []
        for r in web_results:
            if r.get('content'):
                parts.append(r['content'])
        return "\n\n".join(parts)
    
    def _extract_percentages(self, content: str) -> List[Dict]:
        """Extrai percentuais usando regex"""
        percentuais = []
        
        patterns = [
            r'(\d+(?:,\d+)?)\s*%',
            r'(\d+(?:,\d+)?)\s*por\s*cento',
            r'alíquota.*?(\d+(?:,\d+)?)\s*%',
            r'redução.*?(\d+(?:,\d+)?)\s*%',
            r'aumento.*?(\d+(?:,\d+)?)\s*%',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                try:
                    valor_str = match.group(1).replace(',', '.')
                    valor = float(valor_str)
                    contexto = content[max(0, match.start()-100):min(len(content), match.end()+100)]
                    
                    # Determina tipo
                    tipo = "geral"
                    if "redução" in contexto.lower() or "reduzir" in contexto.lower():
                        tipo = "reducao"
                    elif "aumento" in contexto.lower() or "elevar" in contexto.lower():
                        tipo = "aumento"
                    elif "alíquota" in contexto.lower():
                        tipo = "aliquota"
                    elif any(t in contexto.lower() for t in ["pis", "cofins", "ipi", "icms", "iss"]):
                        tipo = "tributo"
                    
                    percentuais.append({
                        "valor": valor,
                        "contexto": contexto,
                        "tipo": tipo
                    })
                except:
                    continue
        
        # Remove duplicatas
        seen = set()
        unique_percentuais = []
        for p in percentuais:
            key = (p['valor'], p['tipo'], p['contexto'][:50])
            if key not in seen:
                seen.add(key)
                unique_percentuais.append(p)
        
        return unique_percentuais[:20]  # Top 20


class StructureValidationAgent(BaseAgent):
    """Agente 7: Validação e estruturação"""
    
    def process(self, raw_extraction: Dict, date_extraction: Dict,
                quantification: Dict, legislation_type: str) -> tuple:
        """Estrutura e valida dados"""
        print("   ✅ Estruturando e validando...")
        
        structured = {
            "raw_extraction": raw_extraction,
            "date_extraction": date_extraction,
            "quantification": quantification,
            "legislation_type": legislation_type
        }
        
        # Calcula completude
        score = self._calculate_completeness(structured)
        
        validation = {
            "completeness_score": score,
            "needs_enhancement": score < 0.70,
            "missing_sections": self._identify_gaps(structured)
        }
        
        return structured, validation
    
    def _calculate_completeness(self, data: Dict) -> float:
        """Calcula score de completude"""
        scores = []
        
        # Verifica conteúdo
        if data.get("raw_extraction", {}).get("raw_text"):
            text_len = len(data["raw_extraction"]["raw_text"])
            scores.append(min(1.0, text_len / 1000))  # Normaliza por tamanho
        else:
            scores.append(0.0)
        
        # Verifica datas
        if data.get("date_extraction", {}).get("vigencias"):
            scores.append(1.0)
        else:
            scores.append(0.3)  # Nem sempre há datas
        
        # Verifica números
        if data.get("quantification", {}).get("percentuais"):
            scores.append(1.0)
        else:
            scores.append(0.3)  # Nem sempre há percentuais
        
        return sum(scores) / len(scores) if scores else 0.0
    
    def _identify_gaps(self, data: Dict) -> List[str]:
        """Identifica gaps"""
        gaps = []
        
        if not data.get("raw_extraction", {}).get("raw_text"):
            gaps.append("raw_extraction")
        
        if not data.get("date_extraction", {}).get("vigencias"):
            gaps.append("vigencias")
        
        if not data.get("quantification", {}).get("percentuais"):
            gaps.append("percentuais")
        
        return gaps


class EnhancementAgent(BaseAgent):
    """Agente 8: Enriquecimento de dados"""
    
    def enhance(self, structured_data: Dict, validation_results: Dict,
                web_results: List[Dict]) -> Dict:
        """Enriquece dados focando em gaps"""
        print("   🔧 Enriquecendo dados...")
        
        if not validation_results.get("needs_enhancement"):
            print("      ✓ Dados completos")
            return structured_data
        
        missing = validation_results.get("missing_sections", [])
        print(f"      ⚠️ Gaps detectados: {', '.join(missing) if missing else 'nenhum'}")
        
        enhanced = structured_data.copy()
        
        # Tentativa de melhorar extração se necessário
        if missing:
            print("      🔄 Aplicando enhancement...")
            # Aqui poderia haver lógica adicional de enhancement
        
        return enhanced


class ImpactAnalysisAgent(BaseAgent):
    """Agente 9: Análise de impacto geral"""
    
    def analyze(self, structured_data: Dict, web_results: List[Dict]) -> Dict:
        """Analisa impacto geral da legislação"""
        print("   🎯 Analisando impacto geral...")
        
        content = self._consolidate_content(web_results)
        
        section_agent = SectionExtractionAgent()
        impact = section_agent.extract_impact_analysis(content)
        
        print("      ✓ Análise de impacto concluída")
        
        return impact
    
    def _consolidate_content(self, web_results: List[Dict]) -> str:
        """Consolida conteúdo"""
        parts = []
        for r in web_results:
            if r.get('content'):
                parts.append(r['content'])
        return "\n\n".join(parts)


class DellRelevanceAgent(BaseAgent):
    """Agente 10: Análise de relevância específica para Dell Technologies Brazil"""
    
    def analyze(self, structured_data: Dict, impact_analysis: Dict, 
                web_results: List[Dict]) -> Dict:
        """Analisa relevância para Dell"""
        print("   🏢 Analisando relevância para Dell Technologies...")
        
        # Prepara resumo da legislação
        legislation_summary = self._prepare_legislation_summary(
            structured_data, impact_analysis
        )
        
        # Chama LLM para análise específica Dell
        prompt = DELL_RELEVANCE_PROMPT.format(
            dell_info=DELL_COMPANY_INFO,
            legislation_summary=legislation_summary
        )
        
        result = self._call_api(prompt, temperature=0.0)
        
        # Estrutura resultado
        dell_analysis = {
            "raw_analysis": result,
            "relevancia": self._extract_relevance_level(result),
            "justificativa": self._extract_section_from_analysis(result, "JUSTIFICATIVA"),
            "areas_impactadas": self._extract_section_from_analysis(result, "ÁREAS IMPACTADAS"),
            "acao_requerida": self._extract_section_from_analysis(result, "AÇÃO REQUERIDA"),
            "impacto_fiscal": self._extract_section_from_analysis(result, "IMPACTO FISCAL")
        }
        
        print(f"      ✓ Relevância: {dell_analysis['relevancia']}")
        
        return dell_analysis
    
    def _prepare_legislation_summary(self, structured_data: Dict, 
                                     impact_analysis: Dict) -> str:
        """Prepara resumo da legislação para análise"""
        parts = []
        
        # Extração raw
        if structured_data.get("raw_extraction", {}).get("raw_text"):
            parts.append("CONTEÚDO PRINCIPAL:")
            parts.append(structured_data["raw_extraction"]["raw_text"][:5000])
        
        # Impacto geral
        if impact_analysis:
            parts.append("\n\nIMPACTO GERAL:")
            parts.append(impact_analysis.get("raw_analysis", ""))
        
        # Datas
        if structured_data.get("date_extraction", {}).get("llm_analysis"):
            parts.append("\n\nDATAS E VIGÊNCIAS:")
            parts.append(structured_data["date_extraction"]["llm_analysis"][:1000])
        
        # Números
        if structured_data.get("quantification", {}).get("llm_analysis"):
            parts.append("\n\nQUANTIFICAÇÃO:")
            parts.append(structured_data["quantification"]["llm_analysis"][:1000])
        
        return "\n".join(parts)
    
    def _extract_relevance_level(self, text: str) -> str:
        """Extrai nível de relevância"""
        text_upper = text.upper()
        if "ALTA" in text_upper:
            return "ALTA"
        elif "MÉDIA" in text_upper or "MEDIA" in text_upper:
            return "MÉDIA"
        elif "BAIXA" in text_upper:
            return "BAIXA"
        return "NÃO DETERMINADA"
    
    def _extract_section_from_analysis(self, text: str, section_marker: str) -> str:
        """Extrai seção específica da análise"""
        try:
            # Procura por padrões como "**SEÇÃO:**" ou "SEÇÃO:"
            patterns = [
                rf"\*\*{section_marker}:\*\*\s*(.*?)(?=\n\n\*\*|\n\n[A-Z]|$)",
                rf"{section_marker}:\s*(.*?)(?=\n\n\*\*|\n\n[A-Z]|$)",
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
                if match:
                    content = match.group(1).strip()
                    # Remove markdown extra
                    content = content.replace("**", "").replace("*", "")
                    return content
        except:
            pass
        
        return "Informação não disponível"


class FinalAssemblyAgent(BaseAgent):
    """Agente final: Montagem do relatório completo"""
    
    def assemble(self, query: str, structured_data: Dict, date_extraction: Dict,
                 quantification: Dict, impact_analysis: Dict, dell_analysis: Dict,
                 legislation_type: str, web_results: List[Dict],
                 validation_results: Dict) -> str:
        """Monta relatório final formatado"""
        print("   📝 Montando relatório final...")
        
        # Identifica tipo e número da legislação
        tipo_leg, numero_leg, data_pub = self._identify_legislation_info(
            web_results, structured_data
        )
        
        # Extrai resumo da alteração
        resumo = self._extract_summary(structured_data)
        
        # Formata seções
        artigos = self._extract_articles(structured_data)
        vigencia = self._format_vigencia(date_extraction)
        beneficios_obrig = self._extract_benefits_obligations(structured_data)
        requisitos = self._extract_requirements(structured_data)
        
        # Prepara dados para o template
        template = get_template(legislation_type)
        
        report = template.format(
            tipo_legislacao=tipo_leg,
            numero_legislacao=numero_leg,
            data_publicacao=data_pub,
            resumo_alteracao=resumo,
            setores=impact_analysis.get("setores", "Não identificado"),
            tipo_empresa=impact_analysis.get("tipo_empresa", "Não identificado"),
            estados_regioes=impact_analysis.get("abrangencia", "Não identificado"),
            tributos=impact_analysis.get("tributos", "Não identificado"),
            relevancia_dell=dell_analysis.get("relevancia", "NÃO DETERMINADA"),
            justificativa=dell_analysis.get("justificativa", "Não disponível"),
            areas_impactadas=dell_analysis.get("areas_impactadas", "Não identificado"),
            acao_requerida=dell_analysis.get("acao_requerida", "Não determinada"),
            impacto_fiscal=dell_analysis.get("impacto_fiscal", "Não determinado"),
            artigos_principais=artigos,
            vigencia_prazos=vigencia,
            beneficios_obrigacoes=beneficios_obrig,
            requisitos=requisitos,
            fontes=self._format_fontes(web_results)
        )
        
        return report
    
    def _identify_legislation_info(self, web_results: List[Dict], 
                                   structured_data: Dict) -> tuple:
        """Identifica tipo, número e data da legislação"""
        tipo = "LEGISLAÇÃO"
        numero = "Número não identificado"
        data = "Data não identificada"
        
        # Tenta extrair do título da primeira fonte
        if web_results:
            title = web_results[0].get('title', '')
            
            # Medida Provisória
            if 'MP' in title or 'Medida Provisória' in title:
                tipo = "MEDIDA PROVISÓRIA"
                mp_match = re.search(r'MP[vV]?\s*n?º?\s*(\d+)', title, re.IGNORECASE)
                if mp_match:
                    numero = f"MP nº {mp_match.group(1)}"
            
            # Lei
            elif 'Lei' in title:
                tipo = "LEI"
                lei_match = re.search(r'Lei\s*n?º?\s*([\d.]+)', title, re.IGNORECASE)
                if lei_match:
                    numero = f"Lei nº {lei_match.group(1)}"
            
            # Decreto
            elif 'Decreto' in title:
                tipo = "DECRETO"
                dec_match = re.search(r'Decreto\s*n?º?\s*([\d.]+)', title, re.IGNORECASE)
                if dec_match:
                    numero = f"Decreto nº {dec_match.group(1)}"
            
            # Portaria
            elif 'Portaria' in title:
                tipo = "PORTARIA"
                port_match = re.search(r'Portaria\s*n?º?\s*([\d.]+)', title, re.IGNORECASE)
                if port_match:
                    numero = f"Portaria nº {port_match.group(1)}"
            
            # Tenta extrair data do título ou conteúdo
            date_match = re.search(r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})', title)
            if date_match:
                data = f"{date_match.group(1)}/{date_match.group(2)}/{date_match.group(3)}"
        
        return tipo, numero, data
    
    def _extract_summary(self, structured_data: Dict) -> str:
        """Extrai resumo da alteração"""
        raw_text = structured_data.get("raw_extraction", {}).get("raw_text", "")
        if raw_text:
            # Pega primeiros parágrafos como resumo
            lines = [l.strip() for l in raw_text.split('\n') if l.strip()]
            summary_lines = []
            char_count = 0
            for line in lines[:10]:  # Máximo 10 linhas
                if char_count > 800:  # Máximo ~800 caracteres
                    break
                summary_lines.append(line)
                char_count += len(line)
            return '\n'.join(summary_lines)
        return "Resumo não disponível"
    
    def _extract_articles(self, structured_data: Dict) -> str:
        """Extrai artigos principais"""
        raw_text = structured_data.get("raw_extraction", {}).get("raw_text", "")
        
        # Procura por artigos no texto
        articles = []
        art_pattern = r'(Art\.?\s*\d+[A-Z-]*\.?[^\n]{10,200})'
        matches = re.findall(art_pattern, raw_text, re.IGNORECASE)
        
        if matches:
            for i, match in enumerate(matches[:8], 1):  # Top 8 artigos
                articles.append(f"• {match.strip()}")
            return '\n'.join(articles)
        
        return "Artigos não identificados no formato padrão"
    
    def _format_vigencia(self, date_extraction: Dict) -> str:
        """Formata vigência e prazos"""
        vigencias = date_extraction.get("vigencias", [])
        llm_analysis = date_extraction.get("llm_analysis", "")
        
        if llm_analysis and len(llm_analysis) > 50:
            return llm_analysis
        
        if vigencias:
            lines = []
            for i, v in enumerate(vigencias[:5], 1):
                lines.append(f"{i}. {v.get('data', 'Data não especificada')}")
                ctx = v.get('contexto', '')[:150]
                if ctx:
                    lines.append(f"   Contexto: {ctx}...")
            return '\n'.join(lines)
        
        return "Vigência não identificada"
    
    def _extract_benefits_obligations(self, structured_data: Dict) -> str:
        """Extrai benefícios e obrigações"""
        raw_text = structured_data.get("raw_extraction", {}).get("raw_text", "")
        
        # Procura por termos-chave
        benefits = []
        keywords = ['suspensão', 'isenção', 'redução', 'benefício', 'alíquota zero', 
                   'crédito', 'desconto']
        
        for keyword in keywords:
            pattern = rf'[^\.]*{keyword}[^\.]*\.'
            matches = re.findall(pattern, raw_text, re.IGNORECASE)
            for match in matches[:2]:  # Máximo 2 por keyword
                if len(match) > 30 and match not in benefits:
                    benefits.append(f"• {match.strip()}")
        
        if benefits:
            return '\n'.join(benefits[:10])  # Top 10
        
        return "Benefícios/obrigações não identificados explicitamente"
    
    def _extract_requirements(self, structured_data: Dict) -> str:
        """Extrai requisitos e condições"""
        raw_text = structured_data.get("raw_extraction", {}).get("raw_text", "")
        
        # Procura por requisitos
        requirements = []
        keywords = ['requisito', 'condição', 'desde que', 'quando', 'se', 'deverá']
        
        for keyword in keywords:
            pattern = rf'[^\.]*{keyword}[^\.]*\.'
            matches = re.findall(pattern, raw_text, re.IGNORECASE)
            for match in matches[:2]:
                if len(match) > 30 and len(match) < 300 and match not in requirements:
                    requirements.append(f"• {match.strip()}")
        
        if requirements:
            return '\n'.join(requirements[:8])  # Top 8
        
        return "Requisitos e condições não identificados explicitamente"
    
    def _format_fontes(self, web_results: List[Dict]) -> str:
        """Formata lista de fontes"""
        lines = []
        
        for i, r in enumerate(web_results[:5], 1):
            lines.append(f"{i}. {r.get('title', 'Sem título')}")
            lines.append(f"   URL: {r.get('url', 'N/A')}")
            lines.append(f"   Tipo: {r.get('content_type', 'N/A').upper()}")
            if r.get('is_official'):
                lines.append(f"   ✓ Fonte Oficial")
            lines.append("")
        
        return '\n'.join(lines)