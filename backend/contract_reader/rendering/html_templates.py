"""
Templates HTML pour génération PDF avec Tailwind CSS
Templates optimisés pour impression et rendu WeasyPrint
"""

from typing import Dict, Any, List
from datetime import datetime
from ..models import ContractSummary

class HTMLTemplates:
    """Générateur de templates HTML pour PDF"""
    
    @staticmethod
    def get_base_css() -> str:
        """CSS de base optimisé pour PDF"""
        return """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            line-height: 1.6;
            color: #1f2937;
            background: white;
        }
        
        .container {
            max-width: 210mm;
            margin: 0 auto;
            padding: 20mm;
            background: white;
        }
        
        .header {
            border-bottom: 3px solid #3b82f6;
            padding-bottom: 1rem;
            margin-bottom: 2rem;
        }
        
        .title {
            font-size: 24px;
            font-weight: 700;
            color: #1e40af;
            margin-bottom: 0.5rem;
        }
        
        .subtitle {
            font-size: 14px;
            color: #6b7280;
            font-weight: 500;
        }
        
        .section {
            margin-bottom: 2rem;
            page-break-inside: avoid;
        }
        
        .section-title {
            font-size: 18px;
            font-weight: 600;
            color: #1f2937;
            margin-bottom: 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid #e5e7eb;
        }
        
        .meta-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 1rem;
            margin-bottom: 1.5rem;
        }
        
        .meta-item {
            background: #f8fafc;
            padding: 1rem;
            border-radius: 8px;
            border-left: 4px solid #3b82f6;
        }
        
        .meta-label {
            font-size: 12px;
            font-weight: 600;
            color: #6b7280;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 0.25rem;
        }
        
        .meta-value {
            font-size: 14px;
            font-weight: 500;
            color: #1f2937;
        }
        
        .tldr-list {
            list-style: none;
            padding: 0;
        }
        
        .tldr-item {
            background: #ecfdf5;
            border-left: 4px solid #10b981;
            padding: 0.75rem 1rem;
            margin-bottom: 0.5rem;
            border-radius: 0 6px 6px 0;
        }
        
        .clause {
            background: #fefbff;
            border: 1px solid #e0e7ff;
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 1rem;
        }
        
        .clause-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.5rem;
        }
        
        .clause-name {
            font-weight: 600;
            color: #1e40af;
        }
        
        .clause-importance {
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 500;
            text-transform: uppercase;
        }
        
        .importance-high {
            background: #fee2e2;
            color: #dc2626;
        }
        
        .importance-medium {
            background: #fef3c7;
            color: #d97706;
        }
        
        .importance-low {
            background: #e0f2fe;
            color: #0369a1;
        }
        
        .red-flag {
            background: #fef2f2;
            border-left: 4px solid #ef4444;
            padding: 0.75rem 1rem;
            margin-bottom: 0.5rem;
            border-radius: 0 6px 6px 0;
        }
        
        .red-flag::before {
            content: "⚠️ ";
            font-weight: bold;
        }
        
        .glossary-term {
            margin-bottom: 1rem;
        }
        
        .term-name {
            font-weight: 600;
            color: #1e40af;
            margin-bottom: 0.25rem;
        }
        
        .term-definition {
            color: #4b5563;
            font-size: 14px;
        }
        
        .citation {
            font-size: 11px;
            color: #6b7280;
            font-style: italic;
            margin-left: 0.5rem;
        }
        
        .footer {
            margin-top: 3rem;
            padding-top: 1rem;
            border-top: 1px solid #e5e7eb;
            font-size: 12px;
            color: #6b7280;
            text-align: center;
        }
        
        .disclaimer {
            background: #fffbeb;
            border: 1px solid #fbbf24;
            border-radius: 8px;
            padding: 1rem;
            margin: 2rem 0;
        }
        
        .disclaimer-title {
            font-weight: 600;
            color: #92400e;
            margin-bottom: 0.5rem;
        }
        
        .disclaimer-text {
            font-size: 13px;
            color: #78350f;
        }
        
        @media print {
            .container {
                margin: 0;
                padding: 15mm;
            }
            
            .section {
                page-break-inside: avoid;
            }
        }
        </style>
        """
    
    @staticmethod
    def generate_summary_html(summary: ContractSummary, citations: Dict[str, str] = None, 
                             validation_notes: List[str] = None) -> str:
        """Génère le HTML complet du résumé"""
        
        citations = citations or {}
        validation_notes = validation_notes or []
        
        # Métadonnées
        meta_html = HTMLTemplates._generate_meta_section(summary.meta)
        
        # TL;DR avec citations
        tldr_html = HTMLTemplates._generate_tldr_section(summary.tldr, citations)
        
        # Clauses avec citations
        clauses_html = HTMLTemplates._generate_clauses_section(summary.clauses, citations)
        
        # Red flags
        redflags_html = HTMLTemplates._generate_redflags_section(summary.red_flags, citations)
        
        # Glossaire
        glossary_html = HTMLTemplates._generate_glossary_section(summary.glossary)
        
        # Notes de validation
        validation_html = HTMLTemplates._generate_validation_section(validation_notes)
        
        return f"""
        <!DOCTYPE html>
        <html lang="fr">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{summary.title}</title>
            {HTMLTemplates.get_base_css()}
        </head>
        <body>
            <div class="container">
                <!-- En-tête -->
                <div class="header">
                    <h1 class="title">{summary.title}</h1>
                    <p class="subtitle">Résumé généré automatiquement • {datetime.now().strftime('%d/%m/%Y à %H:%M')}</p>
                </div>
                
                <!-- Métadonnées -->
                {meta_html}
                
                <!-- Points clés -->
                <div class="section">
                    <h2 class="section-title">📋 Points Clés (TL;DR)</h2>
                    {tldr_html}
                </div>
                
                <!-- Clauses importantes -->
                <div class="section">
                    <h2 class="section-title">📄 Clauses Importantes</h2>
                    {clauses_html}
                </div>
                
                <!-- Points d'attention -->
                <div class="section">
                    <h2 class="section-title">⚠️ Points d'Attention</h2>
                    {redflags_html}
                </div>
                
                <!-- Glossaire -->
                <div class="section">
                    <h2 class="section-title">📚 Glossaire</h2>
                    {glossary_html}
                </div>
                
                <!-- Validation -->
                {validation_html}
                
                <!-- Disclaimer -->
                <div class="disclaimer">
                    <div class="disclaimer-title">⚖️ Avertissement Juridique</div>
                    <div class="disclaimer-text">
                        {summary.disclaimer}
                        <br><br>
                        Ce document a été généré automatiquement avec un score de confiance de {summary.confidence_score:.0%}.
                        Pour toute décision importante, consultez un professionnel du droit.
                    </div>
                </div>
                
                <!-- Pied de page -->
                <div class="footer">
                    <p>Généré par AUTOPILOT Contract Reader • xyqo.ai • Conforme RGPD</p>
                    <p>Document généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')} • Validité: 24h</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    @staticmethod
    def _generate_meta_section(meta) -> str:
        """Génère la section métadonnées"""
        contract_type = getattr(meta, 'contract_type', 'Non spécifié')
        date_signed = getattr(meta, 'date_signed', 'Non spécifiée')
        duration = getattr(meta, 'duration', 'Non spécifiée')
        amount = getattr(meta, 'amount', 'Non spécifié')
        parties = getattr(meta, 'parties', [])
        
        parties_html = ""
        if parties:
            parties_list = "</li><li>".join(parties[:4])  # Max 4 parties
            parties_html = f"<ul><li>{parties_list}</li></ul>"
        else:
            parties_html = "Non spécifiées"
        
        return f"""
        <div class="section">
            <h2 class="section-title">📊 Informations Générales</h2>
            <div class="meta-grid">
                <div class="meta-item">
                    <div class="meta-label">Type de contrat</div>
                    <div class="meta-value">{contract_type}</div>
                </div>
                <div class="meta-item">
                    <div class="meta-label">Date de signature</div>
                    <div class="meta-value">{date_signed}</div>
                </div>
                <div class="meta-item">
                    <div class="meta-label">Durée</div>
                    <div class="meta-value">{duration}</div>
                </div>
                <div class="meta-item">
                    <div class="meta-label">Montant</div>
                    <div class="meta-value">{amount}</div>
                </div>
            </div>
            <div class="meta-item">
                <div class="meta-label">Parties contractantes</div>
                <div class="meta-value">{parties_html}</div>
            </div>
        </div>
        """
    
    @staticmethod
    def _generate_tldr_section(tldr: List[str], citations: Dict[str, str]) -> str:
        """Génère la section TL;DR"""
        if not tldr:
            return "<p>Aucun point clé identifié.</p>"
        
        items_html = ""
        for point in tldr:
            citation = HTMLTemplates._find_citation_for_text(point, citations)
            citation_html = f'<span class="citation">[{citation}]</span>' if citation else ""
            items_html += f'<li class="tldr-item">{point}{citation_html}</li>'
        
        return f'<ul class="tldr-list">{items_html}</ul>'
    
    @staticmethod
    def _generate_clauses_section(clauses: List, citations: Dict[str, str]) -> str:
        """Génère la section clauses"""
        if not clauses:
            return "<p>Aucune clause importante identifiée.</p>"
        
        clauses_html = ""
        for clause in clauses:
            name = getattr(clause, 'name', 'Clause')
            text = getattr(clause, 'text', '')
            importance = getattr(clause, 'importance', 'medium')
            
            citation = HTMLTemplates._find_citation_for_text(text, citations)
            citation_html = f'<span class="citation">[{citation}]</span>' if citation else ""
            
            clauses_html += f"""
            <div class="clause">
                <div class="clause-header">
                    <div class="clause-name">{name}</div>
                    <div class="clause-importance importance-{importance}">{importance}</div>
                </div>
                <div>{text}{citation_html}</div>
            </div>
            """
        
        return clauses_html
    
    @staticmethod
    def _generate_redflags_section(red_flags: List[str], citations: Dict[str, str]) -> str:
        """Génère la section red flags"""
        if not red_flags:
            return "<p>Aucun point d'attention particulier identifié.</p>"
        
        flags_html = ""
        for flag in red_flags:
            citation = HTMLTemplates._find_citation_for_text(flag, citations)
            citation_html = f'<span class="citation">[{citation}]</span>' if citation else ""
            flags_html += f'<div class="red-flag">{flag}{citation_html}</div>'
        
        return flags_html
    
    @staticmethod
    def _generate_glossary_section(glossary: List) -> str:
        """Génère la section glossaire"""
        if not glossary:
            return "<p>Aucun terme technique à définir.</p>"
        
        terms_html = ""
        for term in glossary:
            term_name = getattr(term, 'term', '')
            simple_explanation = getattr(term, 'simple_explanation', '')
            
            terms_html += f"""
            <div class="glossary-term">
                <div class="term-name">{term_name}</div>
                <div class="term-definition">{simple_explanation}</div>
            </div>
            """
        
        return terms_html
    
    @staticmethod
    def _generate_validation_section(validation_notes: List[str]) -> str:
        """Génère la section validation"""
        if not validation_notes:
            return ""
        
        notes_html = "<br>".join(validation_notes)
        
        return f"""
        <div class="section">
            <h2 class="section-title">✅ Notes de Validation</h2>
            <div style="font-size: 13px; color: #6b7280; background: #f8fafc; padding: 1rem; border-radius: 6px;">
                {notes_html}
            </div>
        </div>
        """
    
    @staticmethod
    def _find_citation_for_text(text: str, citations: Dict[str, str]) -> str:
        """Trouve la citation correspondant à un texte"""
        text_lower = text.lower()
        
        for fact, citation in citations.items():
            if fact.lower() in text_lower:
                return citation
        
        return ""
