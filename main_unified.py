#!/usr/bin/env python3
"""
Dell Brazil Tax Legislation Analysis System v5.1
Main entry point with interactive menu
"""

import sys
import os
import argparse
from datetime import datetime
from typing import List, Dict, Optional

# Add current directory to path for module imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# =============================================================================
# MODULE IMPORTS
# Try to import workflow module (handles URL analysis and web search)
# =============================================================================
try:
    from config import validate_config, DEV_GENAI_API_KEY
    from workflow import LegislacaoWorkflow
    HAS_WORKFLOW = True
except ImportError as e:
    HAS_WORKFLOW = False
    print(f"⚠️  Workflow not available: {e}")

# Try to import Brazil Monitor module (handles automatic site monitoring)
try:
    from brazil_monitor import BrazilMonitor
    HAS_BRAZIL_MONITOR = True
except ImportError as e:
    HAS_BRAZIL_MONITOR = False
    print(f"⚠️  Brazil Monitor not available: {e}")

# =============================================================================
# CONFIGURATION
# =============================================================================
OUTPUT_DIR = "/mnt/user-data/outputs"


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================
def print_header():
    """Display system header with version info"""
    print("\n" + "="*80)
    print("🏛️  DELL BRAZIL TAX LEGISLATION ANALYSIS SYSTEM v5.1")
    print("🏢 Dell Technologies Brazil - Tax Analysis")
    print("🗃️  Architecture: 12 Specialized Agents")
    print("📋 Support: Lei, LC, MP, Decreto, Portaria, IN, Convênio ICMS")
    print("="*80)


def print_menu():
    """Display main menu options"""
    print("\n📌 SELECT OPERATION MODE:")
    print()
    print("   1️⃣  URL ANALYSIS   - Analyze a specific URL")
    print("   2️⃣  WEB SEARCH     - Search legislation by keywords")
    print("   3️⃣  MONITORING     - Auto-monitor Brazilian sites")
    print("   0️⃣  EXIT")
    print()


def save_report(report: str, prefix: str = "analysis") -> str:
    """
    Save analysis report to file
    
    Args:
        report: Report content to save
        prefix: Filename prefix for the output file
    
    Returns:
        Filepath of saved file or empty string on error
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filepath = f"{OUTPUT_DIR}/{prefix}_{timestamp}.txt"
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report)
        return filepath
    except Exception as e:
        print(f"❌ Save error: {e}")
        return ""


# =============================================================================
# MODE 1: URL ANALYSIS
# Analyzes a single URL using the multi-agent workflow
# Flow: URL -> Web Scraping -> Legal Analysis -> Dell Impact -> Report
# =============================================================================
def run_url_mode(url: str) -> Dict:
    """
    Execute analysis for a specific URL
    
    Args:
        url: URL of the legislation to analyze
    
    Returns:
        Dictionary with analysis results or error
    """
    print(f"\n🔗 MODE: URL ANALYSIS")
    print(f"   URL: {url}")
    
    if not HAS_WORKFLOW:
        print("❌ Workflow not available")
        return {"error": "Workflow not available"}
    
    # Validate API configuration
    is_valid, missing = validate_config()
    if not is_valid:
        print(f"❌ Incomplete configuration: {missing}")
        return {"error": f"Incomplete configuration: {missing}"}
    
    # Initialize workflow orchestrator
    try:
        workflow = LegislacaoWorkflow()
    except Exception as e:
        print(f"❌ Initialization error: {e}")
        return {"error": str(e)}
    
    # Execute multi-agent analysis pipeline
    try:
        result = workflow.run(url=url)
        
        # Display report
        print("\n" + "="*80)
        print("📄 ANALYSIS REPORT")
        print("="*80)
        print("\n" + result["final_analysis"])
        
        # Save to file
        filepath = save_report(result["final_analysis"], "url_analysis")
        if filepath:
            print(f"\n✅ Report saved: {filepath}")
            result["saved_file"] = filepath
        
        return result
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return {"error": str(e)}


# =============================================================================
# MODE 2: WEB SEARCH
# Searches for legislation using keywords and analyzes results
# Flow: Query -> Web Search -> Filter Results -> Analysis -> Report
# =============================================================================
def run_search_mode(query: str) -> Dict:
    """
    Execute web search and analyze results
    
    Args:
        query: Search keywords for legislation
    
    Returns:
        Dictionary with search and analysis results or error
    """
    print(f"\n🔍 MODE: WEB SEARCH")
    print(f"   Query: {query}")
    
    if not HAS_WORKFLOW:
        print("❌ Workflow not available")
        return {"error": "Workflow not available"}
    
    # Validate API configuration
    is_valid, missing = validate_config()
    if not is_valid:
        print(f"❌ Incomplete configuration: {missing}")
        return {"error": f"Incomplete configuration: {missing}"}
    
    # Initialize workflow orchestrator
    try:
        workflow = LegislacaoWorkflow()
    except Exception as e:
        print(f"❌ Initialization error: {e}")
        return {"error": str(e)}
    
    # Execute search and analysis pipeline
    try:
        result = workflow.run(query=query)
        
        # Display report
        print("\n" + "="*80)
        print("📄 ANALYSIS REPORT")
        print("="*80)
        print("\n" + result["final_analysis"])
        
        # Save to file
        filepath = save_report(result["final_analysis"], "search_analysis")
        if filepath:
            print(f"\n✅ Report saved: {filepath}")
            result["saved_file"] = filepath
        
        return result
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return {"error": str(e)}


# =============================================================================
# MODE 3: AUTOMATIC MONITORING
# Monitors pre-configured Brazilian legislation sites
# Sites: LegiswWeb (Federal, State, General) + Receita Federal
# Flow: Scrape Sites -> Extract Articles -> AI Analysis -> Filter Relevant -> Report
# =============================================================================
def run_monitoring_mode() -> Dict:
    """
    Execute automatic monitoring of Brazilian legislation sites
    
    Returns:
        Dictionary with monitoring results or error
    """
    print(f"\n📡 MODE: MONITORING")
    print("   Monitoring Brazilian legislation sites...")
    
    if not HAS_BRAZIL_MONITOR:
        print("❌ Brazil Monitor not available")
        return {"error": "Brazil Monitor not available"}
    
    try:
        # Initialize and run monitor
        monitor = BrazilMonitor()
        result = monitor.run(output_dir=OUTPUT_DIR)
        
        if result:
            return result
        else:
            return {"message": "No relevant articles found"}
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}


# =============================================================================
# INTERACTIVE MODE
# Main menu loop for user interaction
# =============================================================================
def run_interactive_mode():
    """Interactive mode with menu selection"""
    print_header()
    
    # Validate configuration on startup
    is_valid, missing = validate_config()
    if is_valid:
        print("✅ Configuration validated")
    else:
        print(f"⚠️  Incomplete configuration: {missing}")
        print("   Some features may not be available.")
    
    # Main menu loop
    while True:
        print_menu()
        
        try:
            choice = input("👉 Option: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\n👋 Exiting...")
            break
        
        if choice == "0":
            print("\n👋 Exiting...")
            break
        
        elif choice == "1":
            # URL ANALYSIS MODE
            print("\n🔗 URL ANALYSIS MODE")
            url = input("   URL: ").strip()
            
            if not url or not url.startswith('http'):
                print("   ❌ Invalid URL")
                continue
            
            run_url_mode(url)
        
        elif choice == "2":
            # WEB SEARCH MODE
            print("\n🔍 WEB SEARCH MODE")
            print("   Search examples:")
            print("   - 'MP 1318 2025'")
            print("   - 'ICMS tecnologia São Paulo'")
            print("   - 'Lei de Informática benefícios'")
            print()
            query = input("   Search query: ").strip()
            
            if not query:
                print("   ❌ Empty query")
                continue
            
            run_search_mode(query)
        
        elif choice == "3":
            # MONITORING MODE
            print("\n📡 MONITORING MODE")
            print("   This will automatically monitor:")
            print("   - LegiswWeb (Federal, State, General)")
            print("   - Receita Federal")
            print()
            confirm = input("   Start monitoring? (Y/n): ").strip().lower()
            
            if confirm == 'n':
                print("   ❌ Monitoring cancelled")
                continue
            
            run_monitoring_mode()
        
        else:
            print("   ❌ Invalid option")
        
        # Pause before returning to menu
        print()
        input("   Press ENTER to continue...")


# =============================================================================
# CLI ENTRY POINT
# Handles command-line arguments for non-interactive usage
# =============================================================================
def main():
    global OUTPUT_DIR
    parser = argparse.ArgumentParser(
        description="Dell Brazil Tax Legislation Analysis System v5.1",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
USAGE MODES:

  # Interactive menu (default):
  python main_unified.py

  # Single URL analysis:
  python main_unified.py --url https://planalto.gov.br/...

  # Web search:
  python main_unified.py --search "MP 1318 2025"

  # Automatic monitoring:
  python main_unified.py --monitor

SUPPORTED LEGISLATION:
  Lei, Lei Complementar, MP, Decreto, Portaria, IN,
  Convênio ICMS, Protocolo ICMS, Ajuste SINIEF
        """
    )
    
    # Mutually exclusive operation modes
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument('--url', '-u', metavar='URL',
                           help='Single URL for analysis')
    mode_group.add_argument('--search', '-s', metavar='QUERY',
                           help='Web search query')
    mode_group.add_argument('--monitor', '-m', action='store_true',
                           help='Run automatic monitoring')
    
    # Additional options
    parser.add_argument('--output', '-o', metavar='DIR',
                       help=f'Output directory (default: {OUTPUT_DIR})')
    
    # Positional query for backwards compatibility
    parser.add_argument('query', nargs='?',
                       help='Direct query (alternative to --search)')
    
    args = parser.parse_args()
    
    # Update output directory if specified
    if args.output:
        OUTPUT_DIR = args.output
    
    print_header()
    
    try:
        # Determine operation mode based on arguments
        if args.url:
            result = run_url_mode(args.url)
        
        elif args.search:
            result = run_search_mode(args.search)
        
        elif args.monitor:
            result = run_monitoring_mode()
        
        elif args.query:
            # Positional argument: detect if URL or search query
            if args.query.startswith('http'):
                result = run_url_mode(args.query)
            else:
                result = run_search_mode(args.query)
        
        else:
            # No arguments: run interactive mode
            run_interactive_mode()
            return 0
        
        # Check for errors in result
        if "error" in result:
            print(f"\n❌ Error: {result['error']}")
            return 1
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Operation cancelled by user")
        return 130
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
