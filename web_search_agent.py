"""
Agente de Busca Web - ULTRA ROBUSTO
Correção definitiva do erro 'NoneType'
"""

import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional, Set
import time
from ddgs import DDGS
import PyPDF2
import io
from urllib.parse import urljoin, urlparse, urlunparse
import re


class WebSearchAgent:
    """Agente de busca web ultra-robusto"""
    
    def __init__(self, timeout: int = 15, max_content_length: int = 100000,
                 follow_link_depth: int = 0, max_links_per_page: int = 3):
        self.timeout = timeout
        self.max_content_length = max_content_length
        self.link_follow_depth = max(0, follow_link_depth)
        self.max_links_per_page = max(1, max_links_per_page)
        
        self.priority_domains = [
            'planalto.gov.br',
            'senado.leg.br',
            'camara.leg.br',
            'receita.fazenda.gov.br',
            'in.gov.br',
            'gov.br',
            'leg.br',
            'jus.br'
        ]
        
        self.relevant_link_keywords = [
            'exposicao', 'motivos', 'exm', 'anexo', 
            'justificativa', 'ementa', 'texto', 'integra',
            'lei 11.196', 'lei 11196', '11196', '11.196',
            'redata', 'regime', 'tributario', 'datacenter',
            'art', 'artigo', 'dispositivo'
        ]
    
    def search(self, query: str, max_results: int = 15) -> List[Dict]:
        """Busca na web com foco em fontes oficiais brasileiras"""
        print(f"\n🔍 Analisando entrada: '{query[:100]}...'")
        
        urls_in_query = self._extract_urls_from_text(query)
        if urls_in_query:
            print(f"   ✓ Detectadas {len(urls_in_query)} URL(s) na query")
            question = self._extract_question_from_mixed_query(query, urls_in_query)
            if question:
                print(f"   ℹ️  Pergunta identificada: {question}")
            return self.fetch_multiple_urls(urls_in_query)
        
        print("   🔍 Realizando busca web")
        
        try:
            query_oficial = f"{query} site:planalto.gov.br OR site:senado.leg.br OR site:camara.leg.br OR site:in.gov.br"
            
            resultados = DDGS().text(
                query_oficial,
                region='br-pt',
                max_results=max_results
            )
            
            if not resultados:
                print("   ⚠️  Tentando busca mais ampla...")
                resultados = DDGS().text(query, region='br-pt', max_results=max_results)
            
            formatted_results = []
            
            for i, resultado in enumerate(resultados, 1):
                url = resultado.get('href', '')
                
                result_dict = {
                    'title': resultado.get('title', 'Sem título'),
                    'url': url,
                    'snippet': resultado.get('body', ''),
                    'source': self._get_source_name(url),
                    'is_official': self._is_official_source(url),
                    'content': '',
                    'content_type': 'unknown'
                }
                
                print(f"   [{i}/{len(resultados)}] {result_dict['title'][:60]}...")
                
                content, content_type = self.fetch_url_content(url)
                if content:
                    result_dict['content'] = content
                    result_dict['content_type'] = content_type
                    print(f"        ✓ Extraído ({content_type}): {len(content):,} caracteres")
                else:
                    print(f"        ⚠️  Falha ao extrair")
                
                formatted_results.append(result_dict)
                time.sleep(0.3)
            
            formatted_results.sort(key=lambda x: (not x['is_official'], x['title']))
            
            oficial_count = sum(1 for r in formatted_results if r['is_official'])
            pdf_count = sum(1 for r in formatted_results if r['content_type'] == 'pdf')
            
            print(f"\n   ✅ Total: {len(formatted_results)} resultados")
            print(f"      • Oficiais: {oficial_count}")
            print(f"      • PDFs: {pdf_count}")
            
            return formatted_results
            
        except Exception as e:
            print(f"   ❌ Erro na busca: {str(e)}")
            return []
    
    def _extract_urls_from_text(self, text: str) -> List[str]:
        """Extrai todas as URLs de um texto"""
        url_pattern = re.compile(
            r'https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&/=]*)',
            re.IGNORECASE
        )
        urls = url_pattern.findall(text)
        return list(set(urls))
    
    def _extract_question_from_mixed_query(self, query: str, urls: List[str]) -> str:
        """Extrai a pergunta de uma query que contém URLs"""
        text = query
        for url in urls:
            text = text.replace(url, '')
        text = ' '.join(text.split())
        return text.strip() if len(text.strip()) > 5 else ''
    
    def fetch_multiple_urls(self, urls: List[str]) -> List[Dict]:
        """Faz scraping de múltiplas URLs específicas"""
        print(f"\n🔗 Processando {len(urls)} URL(s) específica(s)...")
        
        results = []
        
        for i, url in enumerate(urls, 1):
            print(f"\n   [{i}/{len(urls)}] {url}")
            
            # Remove âncora se houver
            url_sem_ancora = url.split('#')[0] if '#' in url else url
            
            content, content_type = self.fetch_url_content(url_sem_ancora)
            
            if content:
                result_dict = {
                    'title': self._extract_title_from_content(content, content_type),
                    'url': url,
                    'snippet': content[:300],
                    'source': self._get_source_name(url),
                    'is_official': self._is_official_source(url),
                    'content': content,
                    'content_type': content_type
                }
                
                print(f"        ✓ Extraído ({content_type}): {len(content):,} caracteres")
                results.append(result_dict)
            else:
                print(f"        ⚠️  Falha ao extrair")
            
            time.sleep(0.5)
        
        print(f"\n   ✅ {len(results)}/{len(urls)} URL(s) processada(s) com sucesso")
        
        return results
    
    def fetch_url_content(self, url: str, depth: int = 0,
                          visited: Optional[Set[str]] = None) -> tuple:
        """
        Faz scraping de uma URL específica - VERSÃO ULTRA ROBUSTA
        """
        if visited is None:
            visited = set()
        
        # CRÍTICO: Normalização segura
        try:
            normalized_url = self._normalize_url(url)
        except Exception as e:
            print(f"        ❌ Erro ao normalizar URL: {str(e)}")
            return "", "unknown"
        
        if normalized_url in visited:
            return "", "unknown"
        visited.add(normalized_url)

        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=self.timeout, allow_redirects=True)
            response.raise_for_status()
            
            content_type_header = response.headers.get('Content-Type', '').lower()
            
            # Se for PDF
            if 'pdf' in content_type_header or url.lower().endswith('.pdf'):
                pdf_text = self._extract_pdf_text(response.content)
                return (pdf_text or "", 'pdf')
            
            # Se for HTML
            # CRÍTICO: BeautifulSoup pode retornar None em casos extremos
            try:
                soup = BeautifulSoup(response.content, 'html.parser')
                if soup is None:
                    print(f"        ⚠️  BeautifulSoup retornou None")
                    return "", "unknown"
            except Exception as e:
                print(f"        ❌ Erro no BeautifulSoup: {str(e)}")
                return "", "unknown"
            
            self._clean_html(soup)
            texto_limpo = self._extract_clean_text(soup)
            
            if not texto_limpo:
                print(f"        ⚠️  Texto vazio após extração")
                return "", "html"
            
            linked_sections = []

            # Segue links relevantes
            if depth < self.link_follow_depth:
                try:
                    follow_links = self._collect_relevant_follow_links(soup, url)
                    if follow_links:
                        print(f"        ℹ️  {len(follow_links)} links relevantes encontrados")
                    
                    for follow_url in follow_links[:self.max_links_per_page]:
                        print(f"        -> Seguindo link relevante: {follow_url}")
                        
                        # CRÍTICO: Recursão segura
                        try:
                            linked_content, linked_type = self.fetch_url_content(
                                follow_url,
                                depth + 1,
                                visited
                            )
                            
                            # Verifica se retornou conteúdo válido
                            if linked_content and len(linked_content) > 100:
                                header = f"\n\n{'='*80}\n[DOCUMENTO RELACIONADO: {follow_url}]\n{'='*80}\n"
                                linked_sections.append(f"{header}{linked_content}")
                            else:
                                print(f"           ⚠️  Conteúdo vazio ou muito curto")
                        except Exception as e:
                            print(f"           ❌ Erro ao seguir link: {str(e)}")
                            continue
                            
                except Exception as e:
                    print(f"        ❌ Erro ao coletar links: {str(e)}")
            
            # Monta resultado final
            if linked_sections:
                texto_limpo = texto_limpo + "\n\n" + "\n\n".join(linked_sections)
                content_type = 'html+linked'
            else:
                content_type = 'html'
            
            # Limita tamanho
            if len(texto_limpo) > self.max_content_length:
                texto_limpo = texto_limpo[:self.max_content_length] + "\n\n[CONTEÚDO TRUNCADO]"
            
            return texto_limpo, content_type
            
        except requests.exceptions.Timeout:
            print(f"        ❌ Timeout ao acessar URL")
            return "", "unknown"
        except requests.exceptions.RequestException as e:
            print(f"        ❌ Erro de requisição: {str(e)}")
            return "", "unknown"
        except Exception as e:
            print(f"        ❌ Erro inesperado: {str(e)}")
            return "", "unknown"
    
    def _collect_relevant_follow_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """
        Coleta apenas links RELEVANTES - VERSÃO ULTRA ROBUSTA
        """
        # CRÍTICO: Verifica se soup é válido
        if soup is None:
            return []
        
        try:
            base_domain = urlparse(base_url).netloc.lower()
        except Exception:
            return []
        
        relevant_links = []
        
        try:
            anchors = soup.find_all('a', href=True)
            if not anchors:
                return []
        except Exception as e:
            print(f"           ⚠️  Erro ao buscar anchors: {str(e)}")
            return []
        
        for anchor in anchors:
            try:
                # CRÍTICO: Verifica se anchor é válido
                if anchor is None:
                    continue
                
                # CRÍTICO: .get() pode retornar None
                href = anchor.get('href')
                if href is None:
                    continue
                
                href = href.strip()
                if not href or href.startswith('#') or href.lower().startswith('javascript:'):
                    continue
                
                # Remove âncora do href
                href_sem_ancora = href.split('#')[0] if '#' in href else href
                
                try:
                    absolute = urljoin(base_url, href_sem_ancora)
                except Exception:
                    continue
                
                if not self._should_follow_link(absolute, base_domain):
                    continue
                
                # Verifica relevância
                link_text = (anchor.get_text() or '').lower()
                href_lower = href.lower()
                
                is_relevant = any(keyword in link_text or keyword in href_lower 
                                for keyword in self.relevant_link_keywords)
                
                generic_keywords = ['constituicao', 'home', 'inicio', 'portal', 'institucional', 
                                  'biblioteca', 'sobre', 'contato', 'menu']
                is_generic = any(keyword in href_lower for keyword in generic_keywords)
                
                if is_relevant or (not is_generic and 'pdf' in href_lower):
                    relevant_links.append(absolute)
                    
            except Exception:
                # Ignora erros em links individuais
                continue
        
        # Remove duplicatas de forma segura
        unique_links = []
        seen: Set[str] = set()
        for link in relevant_links:
            try:
                norm = self._normalize_url(link)
                if norm not in seen:
                    seen.add(norm)
                    unique_links.append(link)
            except:
                continue
        
        return unique_links
    
    def _extract_pdf_text(self, pdf_content: bytes) -> Optional[str]:
        """Extrai texto de PDF - VERSÃO ROBUSTA"""
        try:
            pdf_file = io.BytesIO(pdf_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            if not pdf_reader.pages:
                return None
            
            texto_completo = []
            max_pages = min(len(pdf_reader.pages), 100)
            
            for page_num in range(max_pages):
                try:
                    page = pdf_reader.pages[page_num]
                    texto = page.extract_text()
                    if texto:
                        texto_completo.append(texto)
                except Exception:
                    continue
            
            if not texto_completo:
                return None
            
            texto_final = "\n\n".join(texto_completo)
            
            if len(texto_final) > self.max_content_length:
                texto_final = texto_final[:self.max_content_length] + "\n\n[CONTEÚDO TRUNCADO]"
            
            return texto_final
            
        except Exception as e:
            print(f"        ❌ Erro ao extrair PDF: {str(e)}")
            return None
    
    def _extract_title_from_content(self, content: str, content_type: str) -> str:
        """Extrai título do conteúdo"""
        if not content:
            return "Sem título"
        
        try:
            lines = [l.strip() for l in content.split('\n') if l.strip()]
            
            if lines:
                title = lines[0]
                if len(title) > 100:
                    title = title[:100] + "..."
                return title
        except Exception:
            pass
        
        return "Documento sem título"
    
    def _is_official_source(self, url: str) -> bool:
        """Verifica se URL é de fonte oficial"""
        if not url:
            return False
        url_lower = url.lower()
        return any(domain in url_lower for domain in self.priority_domains)
    
    def _get_source_name(self, url: str) -> str:
        """Extrai nome da fonte da URL"""
        if not url:
            return 'Desconhecido'
            
        if 'planalto.gov.br' in url:
            return 'Planalto'
        elif 'senado.leg.br' in url:
            return 'Senado Federal'
        elif 'camara.leg.br' in url:
            return 'Câmara dos Deputados'
        elif 'receita.fazenda.gov.br' in url:
            return 'Receita Federal'
        elif 'in.gov.br' in url:
            return 'Diário Oficial da União'
        elif 'stf.jus.br' in url:
            return 'STF'
        elif 'stj.jus.br' in url:
            return 'STJ'
        elif 'gov.br' in url:
            return 'Governo Federal'
        elif 'leg.br' in url:
            return 'Legislativo'
        else:
            try:
                domain = urlparse(url).netloc
                return domain.replace('www.', '')
            except:
                return 'Web'
    
    def identify_legislation_type(self, content: str, url: str = "") -> str:
        """Identifica o tipo de legislação"""
        if not content:
            return 'default'
            
        content_lower = content.lower()
        url_lower = url.lower() if url else ""
        
        if any(term in content_lower for term in ['redata', 'regime especial', 'regime tributário', 'benefício fiscal', 'regime de tributação']):
            return 'regime_tributario'
        
        if 'medida provisória' in content_lower or 'mp n' in content_lower or '/mpv/' in url_lower or '/mp-' in url_lower:
            return 'medida_provisoria'
        
        if 'lei n' in content_lower or '/lei/' in url_lower:
            return 'lei'
        
        if 'decreto n' in content_lower or '/decreto/' in url_lower:
            return 'decreto'
        
        return 'default'

    def _clean_html(self, soup: BeautifulSoup) -> None:
        """Remove elementos irrelevantes - VERSÃO ROBUSTA"""
        if soup is None:
            return
        
        try:
            for elemento in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'iframe']):
                try:
                    elemento.decompose()
                except:
                    continue
            
            for strike in soup.find_all(['strike', 's', 'del']):
                try:
                    strike.decompose()
                except:
                    continue
            
            for element in soup.find_all(style=True):
                try:
                    style_value = element.get('style', '').lower().replace(' ', '')
                    if 'line-through' in style_value or 'text-decoration:line-through' in style_value:
                        element.decompose()
                except:
                    continue
            
            for element in soup.find_all(class_=True):
                try:
                    class_value = ' '.join(element.get('class', [])).lower()
                    if 'strike' in class_value:
                        element.decompose()
                except:
                    continue
        except Exception:
            pass

    def _extract_clean_text(self, soup: BeautifulSoup) -> str:
        """Extrai texto limpo do HTML - VERSÃO ROBUSTA"""
        if soup is None:
            return ""
        
        try:
            texto = soup.get_text()
            if not texto:
                return ""
            
            linhas = (linha.strip() for linha in texto.splitlines())
            chunks = (frase.strip() for linha in linhas for frase in linha.split("  "))
            return '\n'.join(chunk for chunk in chunks if chunk)
        except Exception:
            return ""

    def _should_follow_link(self, url: str, base_domain: str) -> bool:
        """Determina se devemos seguir determinado hyperlink"""
        if not url:
            return False
        
        try:
            parsed = urlparse(url)
            if parsed.scheme not in ('http', 'https'):
                return False
            
            target_domain = parsed.netloc.lower()
            
            if url.lower().endswith('.pdf'):
                return True
            
            if not target_domain or target_domain == base_domain or target_domain.endswith('.' + base_domain):
                return True
            
            return self._is_official_source(url)
        except Exception:
            return False

    def _normalize_url(self, url: str) -> str:
        """Normaliza URL para evitar loops"""
        if not url:
            return ""
        
        try:
            parsed = urlparse(url)
            sanitized = parsed._replace(fragment='')
            return urlunparse(sanitized)
        except Exception:
            return url
