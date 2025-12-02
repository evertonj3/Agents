"""
Review Agent - VERSÃO v4.5 COM SUPORTE A TIPOS DE VIGÊNCIA
Validação com ano dinâmico, sem manutenção futura
CORREÇÕES v4.5:
- ✅ NOVO: Suporte a tipos de vigência (prazo_aquisicao, duracao_beneficio, etc.)
- ✅ NOVO: Validação de compliance_risks
- Fix truncagem de texto (bug crítico)
- Deduplicação semântica de tributos
- Melhor limpeza de markdown
"""

from typing import Dict, List
import re
from datetime import datetime


class ReviewAgent:
    """Agente de Revisão v4.5 com suporte a tipos de vigência"""
    
    def __init__(self):
        self.current_year = datetime.now().year
        self.min_year_allowed = self.current_year  # Dinâmico!
        self.max_dates_allowed = 6
    
    def review(self, state: Dict) -> Dict:
        """Revisa e limpa outputs"""
        print("\n🔍 AGENTE 11.5: Review & Quality Control")
        print("   Revisando e validando outputs...")
        
        # 1. Limpa vigências
        if "date_extraction" in state and state["date_extraction"]:
            state["date_extraction"] = self._review_dates(state["date_extraction"])
        
        # 2. Valida system changes
        if "system_changes" in state and state["system_changes"]:
            state["system_changes"] = self._review_system_changes(state["system_changes"])
        
        # 3. Limpa impact analysis
        if "impact_analysis" in state and state["impact_analysis"]:
            state["impact_analysis"] = self._review_impact_analysis(state["impact_analysis"])
        
        print("   ✅ Revisão concluída")
        return state
    
    def _review_dates(self, date_extraction: Dict) -> Dict:
        """
        Revisa vigências - v4.5 COM SUPORTE A TIPOS
        Remove datas < ano atual mas mantém citações legais relevantes
        """
        vigencias = date_extraction.get("vigencias", [])
        
        if not vigencias:
            return date_extraction
        
        cleaned_vigencias = []
        
        for v in vigencias:
            data = v.get("data", "")
            contexto = v.get("contexto", "")
            tipo = v.get("tipo", "")  # ✅ v4.5: Novo campo
            
            # Se é prazo em anos (duração/permanência), sempre mantém
            if 'ano' in data.lower() or tipo in ['duracao_beneficio', 'prazo_permanencia']:
                # ✅ v4.5: Garante que tipo está presente
                if not tipo:
                    v['tipo'] = 'duracao_beneficio'
                cleaned_vigencias.append(v)
                continue
            
            # Extrai ano da data
            year_match = re.search(r'20\d{2}', data)
            
            if not year_match:
                continue
            
            year = int(year_match.group(0))
            
            # Valida ano >= atual OU é citação de lei base
            if year < self.min_year_allowed:
                # Verifica se é citação de lei base (contexto legal)
                contexto_lower = contexto.lower()
                legal_reference_markers = [
                    'lei', 'decreto', 'mp', 'portaria', 'medida provisória',
                    'conforme', 'nos termos', 'de acordo com', 'previsto'
                ]
                
                is_legal_reference = any(
                    marker in contexto_lower 
                    for marker in legal_reference_markers
                )
                
                if is_legal_reference:
                    # Mantém mas marca como referência legal
                    v['contexto'] = f"📜 Referência legal: {contexto[:150]}"
                    cleaned_vigencias.append(v)
                    if len(cleaned_vigencias) >= self.max_dates_allowed:
                        break
                    continue
                else:
                    # Remove se é apenas data histórica sem contexto legal
                    continue
            
            # Verifica se contexto não menciona leis antigas de forma irrelevante
            contexto_lower = contexto.lower()
            
            # Padrões históricos a evitar
            historical_patterns = [
                r'lei.*\d+.*de.*(?:19\d{2}|200\d|201\d)',
                r'decreto.*\d+.*de.*(?:19\d{2}|200\d|201\d)',
            ]
            
            is_historical = any(
                re.search(pattern, contexto_lower) 
                for pattern in historical_patterns
            )
            
            if is_historical:
                # Permite se menciona legislação atual
                current_markers = ['mpv', '1.318', '1318', 'redata', str(self.current_year), '2025']
                if not any(marker in contexto_lower for marker in current_markers):
                    continue
            
            # Limpa contexto de quebras de linha ruins
            contexto_clean = ' '.join(contexto.split())
            v['contexto'] = contexto_clean[:180]
            
            # ✅ v4.5: Infere tipo se não presente
            if not v.get('tipo'):
                v['tipo'] = self._infer_vigencia_type(data, contexto_clean)
            
            cleaned_vigencias.append(v)
            
            if len(cleaned_vigencias) >= self.max_dates_allowed:
                break
        
        # Atualiza resultado
        date_extraction["vigencias"] = cleaned_vigencias
        date_extraction["count"] = len(cleaned_vigencias)
        
        if cleaned_vigencias:
            dates_text = "\n".join([
                f"{v['data']}: {v['contexto']}"
                for v in cleaned_vigencias
            ])
            date_extraction["dates_text"] = dates_text
        
        original_count = len(vigencias)
        cleaned_count = len(cleaned_vigencias)
        
        if original_count != cleaned_count:
            removed = original_count - cleaned_count
            print(f"   🧹 Vigências: {original_count} → {cleaned_count} (removidas {removed} datas não relevantes)")
        else:
            print(f"   ✓ Vigências: {cleaned_count} datas válidas")
        
        return date_extraction
    
    def _infer_vigencia_type(self, data: str, contexto: str) -> str:
        """
        ✅ v4.5 NOVO: Infere o tipo de vigência com base no contexto
        """
        contexto_lower = contexto.lower()
        
        # Início de vigência
        if any(term in contexto_lower for term in ['início', 'começa', 'entra em vigor', 'a partir de']):
            return 'inicio_vigencia'
        
        # Prazo de aquisição/operação
        if any(term in contexto_lower for term in ['prazo', 'limite', 'até', 'máximo para']):
            return 'prazo_aquisicao'
        
        # Duração do benefício
        if any(term in contexto_lower for term in ['duração', 'período', 'vigência do benefício']):
            return 'duracao_beneficio'
        
        # Permanência
        if any(term in contexto_lower for term in ['permanência', 'mínimo', 'ativo imobilizado']):
            return 'prazo_permanencia'
        
        # Se tem "ano" na data, provavelmente é duração
        if 'ano' in data.lower():
            return 'duracao_beneficio'
        
        return 'prazo_final'
    
    def _review_system_changes(self, system_changes: Dict) -> Dict:
        """
        Revisa system changes e corrige textos cortados
        ✅ v4.5: Também valida compliance_risks
        """
        aliquotas = system_changes.get("aliquotas", [])
        
        if not aliquotas:
            return system_changes
        
        cleaned_aliquotas = []
        seen_tributos = set()
        
        for aliq in aliquotas:
            tributo = aliq.get("tributo", "")
            
            # Remove duplicatas
            if tributo in seen_tributos:
                continue
            
            # Valida que tem informação mínima
            tipo_mudanca = aliq.get("tipo_mudanca", "")
            
            if not tipo_mudanca or tipo_mudanca == "Análise manual necessária":
                continue
            
            # Limpa campos mal formatados SEM truncar
            for key in ["situacao_nova", "condicoes", "vigencia", "descricao_completa", "compliance_risks"]:
                if key in aliq and aliq[key]:
                    text = aliq[key]
                    
                    # Remove markdown
                    text = re.sub(r'\*\*+', '', text)
                    text = re.sub(r'~~.*?~~', '', text)  # Remove strikethrough
                    
                    # Corrige truncamento de forma inteligente
                    text = self._fix_truncated_text(text, max_length=600)
                    
                    # Limpa espaços
                    text = ' '.join(text.split())
                    aliq[key] = text
            
            cleaned_aliquotas.append(aliq)
            seen_tributos.add(tributo)
        
        system_changes["aliquotas"] = cleaned_aliquotas
        
        # ✅ v4.5: Valida compliance_risks
        if "compliance_risks" in system_changes:
            risks = system_changes["compliance_risks"]
            cleaned_risks = []
            for risk in risks:
                risk_clean = self._fix_truncated_text(risk, max_length=300)
                if risk_clean and len(risk_clean) > 20:
                    cleaned_risks.append(risk_clean)
            system_changes["compliance_risks"] = list(dict.fromkeys(cleaned_risks))[:6]
        
        if len(aliquotas) != len(cleaned_aliquotas):
            print(f"   🧹 System Changes: {len(aliquotas)} → {len(cleaned_aliquotas)} mudanças")
        else:
            print(f"   ✓ System Changes: {len(cleaned_aliquotas)} mudanças válidas")
        
        return system_changes
    
    def _fix_truncated_text(self, text: str, max_length: int = 1500) -> str:
        """
        Corrige textos truncados de forma inteligente
        """
        if not text:
            return text
        
        # Se texto é curto, apenas limpa
        if len(text) <= max_length:
            return text
        
        # Se termina com pontuação adequada, está completo
        if text.strip()[-1] in '.!?':
            return text
        
        # Se está truncado (termina sem pontuação)
        # Procura o último período completo ANTES do limite
        last_period = text[:max_length].rfind('.')
        last_exclamation = text[:max_length].rfind('!')
        last_question = text[:max_length].rfind('?')
        
        # Pega a pontuação mais próxima do fim
        last_punct = max(last_period, last_exclamation, last_question)
        
        # Se encontrou pontuação razoavelmente perto do fim (>70% do max)
        if last_punct > max_length * 0.7:
            return text[:last_punct + 1]
        
        # Se não tem pontuação próxima, corta na última palavra e adiciona reticências
        text_cut = text[:max_length].rsplit(' ', 1)[0]
        
        # Verifica se a frase faz sentido mínimo
        if len(text_cut) > 50:  # Pelo menos 50 chars
            return text_cut + '...'
        
        # Se muito curto, retorna o original (melhor truncado que muito curto)
        return text
    
    def _review_impact_analysis(self, impact_analysis: Dict) -> Dict:
        """
        Revisa análise de impacto
        ✅ v4.5: Deduplicação semântica de tributos
        """
        tributos_text = impact_analysis.get("tributos", "")
        
        if tributos_text:
            # Deduplicação semântica
            tributos_text = self._deduplicate_tributos(tributos_text)
            impact_analysis["tributos"] = tributos_text
        
        print(f"   ✓ Impact Analysis: revisado")
        
        return impact_analysis
    
    def _deduplicate_tributos(self, tributos_text: str) -> str:
        """
        Deduplicação semântica de tributos
        Remove duplicatas inteligentemente (PIS + COFINS vs PIS/COFINS)
        """
        if not tributos_text:
            return tributos_text
        
        lines = [l.strip() for l in tributos_text.split('\n') if l.strip()]
        
        # Mapa de equivalências
        seen_tributos = set()
        deduplicated = []
        
        for line in lines:
            line_lower = line.lower()
            
            # Extrai tributo principal da linha
            tributo_key = None
            
            # Identifica o tributo
            if 'pis' in line_lower and 'cofins' in line_lower:
                tributo_key = 'pis_cofins'
            elif 'pis' in line_lower:
                tributo_key = 'pis'
            elif 'cofins' in line_lower:
                tributo_key = 'cofins'
            elif 'ipi' in line_lower:
                tributo_key = 'ipi'
            elif re.search(r'\b(ii|imposto de importação)\b', line_lower):
                tributo_key = 'ii'
            elif 'icms' in line_lower:
                tributo_key = 'icms'
            elif 'iss' in line_lower:
                tributo_key = 'iss'
            elif 'irpj' in line_lower or 'imposto de renda' in line_lower:
                tributo_key = 'ir'
            elif 'csll' in line_lower:
                tributo_key = 'csll'
            
            # Lógica de deduplicação inteligente
            if tributo_key == 'pis_cofins':
                # Se já viu PIS/COFINS junto, ignora individuais posteriores
                # E remove individuais anteriores
                if 'pis' in seen_tributos:
                    seen_tributos.remove('pis')
                    deduplicated = [l for l in deduplicated 
                                  if not ('pis' in l.lower() and 'cofins' not in l.lower())]
                if 'cofins' in seen_tributos:
                    seen_tributos.remove('cofins')
                    deduplicated = [l for l in deduplicated 
                                  if not ('cofins' in l.lower() and 'pis' not in l.lower())]
                
                seen_tributos.add('pis_cofins')
                deduplicated.append(line)
                
            elif tributo_key in ['pis', 'cofins']:
                # Se já viu PIS/COFINS junto, não adiciona individual
                if 'pis_cofins' not in seen_tributos:
                    if tributo_key not in seen_tributos:
                        seen_tributos.add(tributo_key)
                        deduplicated.append(line)
                # Senão, ignora (já foi processado junto)
                
            elif tributo_key:
                # Outros tributos: simples deduplicação
                if tributo_key not in seen_tributos:
                    seen_tributos.add(tributo_key)
                    deduplicated.append(line)
            else:
                # Linha sem tributo identificado, mantém
                deduplicated.append(line)
        
        return '\n'.join(deduplicated)