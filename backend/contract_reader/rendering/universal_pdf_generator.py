"""
Générateur PDF pour UniversalContractV2
Conversion du JSON structuré vers un PDF professionnel sans métadonnées techniques
"""

import os
import tempfile
from typing import Dict, Any, Optional, List
from pathlib import Path
import weasyprint
from weasyprint import HTML, CSS
from datetime import datetime
import hashlib
import logging

logger = logging.getLogger(__name__)

class UniversalPDFGenerator:
    """Générateur PDF pour le schéma UniversalContractV2"""
    
    def __init__(self):
        self.temp_dir = Path(tempfile.gettempdir()) / "contract_reader_pdfs"
        self.temp_dir.mkdir(exist_ok=True)
        
        # Configuration WeasyPrint
        self.pdf_options = {
            'presentational_hints': True,
            'optimize_images': True,
            'pdf_version': '1.7',
            'pdf_forms': False
        }
    
    def generate_contract_summary_pdf(self, summary_data: Dict[str, Any], 
                                    filename: str = "resume_contrat.pdf") -> bytes:
        """
        Génère un PDF professionnel à partir du JSON UniversalContractV2
        
        Args:
            summary_data: Données JSON du résumé (section 'summary' uniquement)
            filename: Nom du fichier PDF
            
        Returns:
            bytes: PDF généré
        """
        try:
            # Génération HTML à partir du JSON
            html_content = self._generate_html_from_json(summary_data)
            
            # Conversion HTML vers PDF
            pdf_bytes = self._render_html_to_pdf(html_content)
            
            logger.info(f"PDF généré: {len(pdf_bytes)} bytes pour {filename}")
            return pdf_bytes
            
        except Exception as e:
            logger.error(f"Erreur génération PDF: {e}")
            raise
    
    def _generate_html_from_json(self, data: Dict[str, Any]) -> str:
        """Génère le HTML à partir du JSON UniversalContractV2"""
        
        # Extraction des sections principales
        meta = data.get('meta', {})
        parties = data.get('parties', {})
        contract = data.get('contract', {})
        financials = data.get('financials', {})
        governance = data.get('governance', {})
        summary_plain = data.get('summary_plain', '')
        risks_red_flags = data.get('risks_red_flags', [])
        missing_info = data.get('missing_info', [])
        operational_actions = data.get('operational_actions', {})
        
        # Construction du HTML
        html_content = f"""
        <!DOCTYPE html>
        <html lang="fr">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Résumé de Contrat</title>
            {self._get_pdf_css()}
        </head>
        <body>
            <div class="container">
                <!-- En-tête -->
                {self._generate_header(meta)}
                
                <!-- Résumé exécutif -->
                {self._generate_executive_summary(summary_plain)}
                
                <!-- Parties contractantes -->
                {self._generate_parties_section(parties)}
                
                <!-- Détails du contrat -->
                {self._generate_contract_details(contract)}
                
                <!-- Aspects financiers -->
                {self._generate_financial_section(financials)}
                
                <!-- Gouvernance et juridique -->
                {self._generate_governance_section(governance)}
                
                <!-- Points d'attention -->
                {self._generate_risks_section(risks_red_flags)}
                
                <!-- Informations manquantes -->
                {self._generate_missing_info_section(missing_info)}
                
                <!-- Actions recommandées -->
                {self._generate_actions_section(operational_actions)}
                
                <!-- Saut de page pour section technique -->
                <div class="page-break"></div>
                
                <!-- Section technique : JSON complet -->
                {self._generate_technical_json_section(data)}
                
                <!-- Pied de page -->
                {self._generate_footer()}
            </div>
        </body>
        </html>
        """
        
        return html_content
    
    def _get_pdf_css(self) -> str:
        """CSS optimisé pour PDF professionnel"""
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
            font-size: 14px;
        }
        
        .container {
            max-width: 210mm;
            margin: 0 auto;
            padding: 15mm;
            background: white;
        }
        
        .header {
            text-align: center;
            border-bottom: 3px solid #3b82f6;
            padding-bottom: 1.5rem;
            margin-bottom: 2rem;
        }
        
        .title {
            font-size: 28px;
            font-weight: 700;
            color: #1e40af;
            margin-bottom: 0.5rem;
        }
        
        .subtitle {
            font-size: 16px;
            color: #6b7280;
            font-weight: 500;
        }
        
        .section {
            margin-bottom: 2rem;
            page-break-inside: avoid;
        }
        
        .section-title {
            font-size: 20px;
            font-weight: 600;
            color: #1f2937;
            margin-bottom: 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid #e5e7eb;
            display: flex;
            align-items: center;
        }
        
        .section-icon {
            margin-right: 0.5rem;
            font-size: 24px;
        }
        
        .summary-box {
            background: #f0f9ff;
            border-left: 4px solid #0ea5e9;
            padding: 1.5rem;
            border-radius: 8px;
            margin-bottom: 1.5rem;
        }
        
        .summary-text {
            font-size: 16px;
            line-height: 1.7;
            color: #0f172a;
        }
        
        .info-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 1rem;
            margin-bottom: 1.5rem;
        }
        
        .info-card {
            background: #f8fafc;
            padding: 1rem;
            border-radius: 8px;
            border-left: 4px solid #3b82f6;
        }
        
        .info-label {
            font-size: 12px;
            font-weight: 600;
            color: #6b7280;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 0.5rem;
        }
        
        .info-value {
            font-size: 14px;
            font-weight: 500;
            color: #1f2937;
        }
        
        .party-card {
            background: #fefefe;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 1rem;
        }
        
        .party-name {
            font-size: 16px;
            font-weight: 600;
            color: #1e40af;
            margin-bottom: 0.5rem;
        }
        
        .party-role {
            display: inline-block;
            background: #dbeafe;
            color: #1e40af;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 500;
            margin-bottom: 0.5rem;
        }
        
        .party-details {
            font-size: 13px;
            color: #4b5563;
            line-height: 1.5;
        }
        
        .list-item {
            background: #f9fafb;
            border-left: 3px solid #10b981;
            padding: 0.75rem 1rem;
            margin-bottom: 0.5rem;
            border-radius: 0 6px 6px 0;
        }
        
        .risk-item {
            background: #fef2f2;
            border-left: 4px solid #ef4444;
            padding: 0.75rem 1rem;
            margin-bottom: 0.5rem;
            border-radius: 0 6px 6px 0;
        }
        
        .risk-item::before {
            content: "⚠️ ";
            font-weight: bold;
            margin-right: 0.5rem;
        }
        
        .missing-item {
            background: #fffbeb;
            border-left: 4px solid #f59e0b;
            padding: 0.75rem 1rem;
            margin-bottom: 0.5rem;
            border-radius: 0 6px 6px 0;
        }
        
        .missing-item::before {
            content: "📋 ";
            font-weight: bold;
            margin-right: 0.5rem;
        }
        
        .financial-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 1rem;
            margin-bottom: 1rem;
        }
        
        .amount-card {
            background: #ecfdf5;
            border: 1px solid #d1fae5;
            border-radius: 8px;
            padding: 1rem;
            text-align: center;
        }
        
        .amount-label {
            font-size: 12px;
            color: #065f46;
            font-weight: 500;
            margin-bottom: 0.5rem;
        }
        
        .amount-value {
            font-size: 18px;
            font-weight: 700;
            color: #047857;
        }
        
        .footer {
            margin-top: 3rem;
            padding-top: 1.5rem;
            border-top: 2px solid #e5e7eb;
            text-align: center;
            font-size: 12px;
            color: #6b7280;
        }
        
        .disclaimer {
            background: #fffbeb;
            border: 1px solid #fbbf24;
            border-radius: 8px;
            padding: 1.5rem;
            margin: 2rem 0;
        }
        
        .disclaimer-title {
            font-weight: 600;
            color: #92400e;
            margin-bottom: 0.5rem;
            font-size: 16px;
        }
        
        .disclaimer-text {
            font-size: 13px;
            color: #78350f;
            line-height: 1.6;
        }
        
        .technical-section {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 1.5rem;
            margin: 2rem 0;
        }
        
        .json-container {
            background: #1e293b;
            color: #e2e8f0;
            padding: 1.5rem;
            border-radius: 8px;
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
            font-size: 11px;
            line-height: 1.4;
            overflow-x: auto;
            white-space: pre-wrap;
            word-break: break-all;
        }
        
        .json-key {
            color: #7dd3fc;
        }
        
        .json-string {
            color: #86efac;
        }
        
        .json-number {
            color: #fbbf24;
        }
        
        .json-boolean {
            color: #f472b6;
        }
        
        .json-null {
            color: #94a3b8;
        }
        
        @page {
            size: A4;
            margin: 2cm;
            @top-center {
                content: "Résumé de Contrat - AUTOPILOT";
                font-size: 10px;
                color: #6b7280;
            }
            @bottom-center {
                content: "Page " counter(page) " sur " counter(pages);
                font-size: 10px;
                color: #6b7280;
            }
        }
        
        .page-break {
            page-break-before: always;
        }
        
        .no-break {
            page-break-inside: avoid;
        }
        
        h1, h2, h3 {
            page-break-after: avoid;
        }
        </style>
        """
    
    def _generate_header(self, meta: Dict[str, Any]) -> str:
        """Génère l'en-tête du document"""
        doc_title = meta.get('source_doc_info', {}).get('title', 'Contrat')
        doc_type = meta.get('source_doc_info', {}).get('doc_type', 'Document')
        generated_date = datetime.now().strftime('%d/%m/%Y à %H:%M')
        
        return f"""
        <div class="header">
            <h1 class="title">📄 Résumé de {doc_title}</h1>
            <p class="subtitle">{doc_type} • Analyse générée le {generated_date}</p>
        </div>
        """
    
    def _generate_executive_summary(self, summary_plain: str) -> str:
        """Génère le résumé exécutif structuré avec 9 rubriques universelles"""
        if not summary_plain:
            summary_plain = "Aucun résumé disponible."
        
        # Formatage du résumé en paragraphes structurés
        formatted_summary = self._format_structured_summary(summary_plain)
        
        return f"""
        <div class="section">
            <h2 class="section-title">
                <span class="section-icon">📋</span>
                Résumé Exécutif Board-Ready V2.3
            </h2>
            <div class="summary-box">
                <div class="summary-text">{formatted_summary}</div>
            </div>
        </div>
        """
    
    def _format_structured_summary(self, summary_plain: str) -> str:
        """Formate le résumé avec structure lisible et paragraphes"""
        if not summary_plain:
            return "Aucun résumé disponible."
        
        # Divise le texte en lignes et regroupe par paragraphes logiques
        lines = [line.strip() for line in summary_plain.split('\n') if line.strip()]
        
        # Structure en paragraphes avec espacement
        formatted_lines = []
        for i, line in enumerate(lines):
            # Ajoute un espacement après certaines sections clés
            if any(keyword in line.lower() for keyword in ['nature et objet', 'parties et rôles', 'durée et renouvellement', 'obligations principales', 'aspects financiers', 'risques identifiés', 'clauses rgpd', 'gouvernance juridique', 'points d\'attention']):
                if i > 0:
                    formatted_lines.append('<br>')
                formatted_lines.append(f'<strong>{line}</strong>')
            else:
                formatted_lines.append(line)
        
        return '<br>'.join(formatted_lines)
    
    def _generate_parties_section(self, parties: Dict[str, Any]) -> str:
        """Génère la section des parties contractantes"""
        parties_list = parties.get('list', [])
        
        if not parties_list:
            return f"""
            <div class="section">
                <h2 class="section-title">
                    <span class="section-icon">👥</span>
                    Parties Contractantes
                </h2>
                <p>Aucune partie identifiée.</p>
            </div>
            """
        
        parties_html = ""
        for party in parties_list:
            name = party.get('name', 'Non spécifié')
            role = party.get('role', 'Non spécifié')
            legal_form = party.get('legal_form', '')
            siren_siret = party.get('siren_siret', '')
            address = party.get('address', '')
            representative = party.get('representative', '')
            
            details = []
            if legal_form:
                details.append(f"Forme juridique: {legal_form}")
            if siren_siret:
                details.append(f"SIREN/SIRET: {siren_siret}")
            if address:
                details.append(f"Adresse: {address}")
            if representative:
                details.append(f"Représentant: {representative}")
            
            details_html = "<br>".join(details) if details else "Aucun détail disponible"
            
            parties_html += f"""
            <div class="party-card">
                <div class="party-name">{name}</div>
                <div class="party-role">{role}</div>
                <div class="party-details">{details_html}</div>
            </div>
            """
        
        return f"""
        <div class="section">
            <h2 class="section-title">
                <span class="section-icon">👥</span>
                Parties Contractantes
            </h2>
            {parties_html}
        </div>
        """
    
    def _generate_contract_details(self, contract: Dict[str, Any]) -> str:
        """Génère les détails du contrat"""
        object_desc = contract.get('object', 'Non spécifié')
        location = contract.get('location_or_site', 'Non spécifié')
        dates = contract.get('dates', {})
        obligations = contract.get('obligations', {})
        
        # Dates
        start_date = dates.get('start_date', 'Non spécifiée')
        end_date = dates.get('end_date', 'Non spécifiée')
        minimum_term = dates.get('minimum_term_months', 'Non spécifiée')
        notice_period = dates.get('notice_period_days', 'Non spécifiée')
        
        # Obligations
        provider_obligations = obligations.get('by_provider', [])
        customer_obligations = obligations.get('by_customer', [])
        
        provider_html = ""
        if provider_obligations:
            for obligation in provider_obligations:
                provider_html += f'<div class="list-item">{obligation}</div>'
        else:
            provider_html = "<p>Aucune obligation spécifiée.</p>"
        
        customer_html = ""
        if customer_obligations:
            for obligation in customer_obligations:
                customer_html += f'<div class="list-item">{obligation}</div>'
        else:
            customer_html = "<p>Aucune obligation spécifiée.</p>"
        
        return f"""
        <div class="section">
            <h2 class="section-title">
                <span class="section-icon">📋</span>
                Détails du Contrat
            </h2>
            
            <div class="info-grid">
                <div class="info-card">
                    <div class="info-label">Objet</div>
                    <div class="info-value">{object_desc}</div>
                </div>
                <div class="info-card">
                    <div class="info-label">Lieu d'exécution</div>
                    <div class="info-value">{location}</div>
                </div>
                <div class="info-card">
                    <div class="info-label">Date de début</div>
                    <div class="info-value">{start_date}</div>
                </div>
                <div class="info-card">
                    <div class="info-label">Date de fin</div>
                    <div class="info-value">{end_date}</div>
                </div>
                <div class="info-card">
                    <div class="info-label">Durée minimale</div>
                    <div class="info-value">{minimum_term} mois</div>
                </div>
                <div class="info-card">
                    <div class="info-label">Préavis</div>
                    <div class="info-value">{notice_period} jours</div>
                </div>
            </div>
            
            <h3 style="font-size: 16px; margin: 1.5rem 0 1rem 0; color: #1f2937;">Obligations du Prestataire</h3>
            {provider_html}
            
            <h3 style="font-size: 16px; margin: 1.5rem 0 1rem 0; color: #1f2937;">Obligations du Client</h3>
            {customer_html}
        </div>
        """
    
    def _generate_financial_section(self, financials: Dict[str, Any]) -> str:
        """Génère la section financière"""
        price_model = financials.get('price_model', 'Non spécifié')
        currency = financials.get('currency', 'EUR')
        payment_terms = financials.get('payment_terms', 'Non spécifiées')
        items = financials.get('items', [])
        
        items_html = ""
        if items:
            for item in items:
                label = item.get('label', 'Montant')
                amount = item.get('amount')
                period = item.get('period', 'unique')
                
                if amount is not None:
                    amount_display = f"{amount:.2f} {currency}"
                    period_display = f"({period})" if period != 'unique' else ""
                    
                    items_html += f"""
                    <div class="amount-card">
                        <div class="amount-label">{label}</div>
                        <div class="amount-value">{amount_display}</div>
                        <div style="font-size: 11px; color: #065f46; margin-top: 0.25rem;">{period_display}</div>
                    </div>
                    """
        
        if not items_html:
            items_html = "<p>Aucun montant spécifié dans le contrat.</p>"
        
        return f"""
        <div class="section">
            <h2 class="section-title">
                <span class="section-icon">💰</span>
                Aspects Financiers
            </h2>
            
            <div class="info-grid">
                <div class="info-card">
                    <div class="info-label">Modèle tarifaire</div>
                    <div class="info-value">{price_model}</div>
                </div>
                <div class="info-card">
                    <div class="info-label">Modalités de paiement</div>
                    <div class="info-value">{payment_terms}</div>
                </div>
            </div>
            
            <h3 style="font-size: 16px; margin: 1.5rem 0 1rem 0; color: #1f2937;">Montants Identifiés</h3>
            <div class="financial-grid">
                {items_html}
            </div>
        </div>
        """
    
    def _generate_governance_section(self, governance: Dict[str, Any]) -> str:
        """Génère la section gouvernance"""
        law = governance.get('law', 'Non spécifiée')
        jurisdiction = governance.get('jurisdiction', 'Non spécifiée')
        liability = governance.get('liability', 'Non spécifiée')
        confidentiality = governance.get('confidentiality', None)
        
        confidentiality_text = "Oui" if confidentiality else "Non" if confidentiality is False else "Non spécifiée"
        
        return f"""
        <div class="section">
            <h2 class="section-title">
                <span class="section-icon">⚖️</span>
                Gouvernance et Juridique
            </h2>
            
            <div class="info-grid">
                <div class="info-card">
                    <div class="info-label">Droit applicable</div>
                    <div class="info-value">{law}</div>
                </div>
                <div class="info-card">
                    <div class="info-label">Juridiction</div>
                    <div class="info-value">{jurisdiction}</div>
                </div>
                <div class="info-card">
                    <div class="info-label">Responsabilité</div>
                    <div class="info-value">{liability}</div>
                </div>
                <div class="info-card">
                    <div class="info-label">Confidentialité</div>
                    <div class="info-value">{confidentiality_text}</div>
                </div>
            </div>
        </div>
        """
    
    def _generate_risks_section(self, risks: List[str]) -> str:
        """Génère la section des risques"""
        if not risks:
            return f"""
            <div class="section">
                <h2 class="section-title">
                    <span class="section-icon">⚠️</span>
                    Points d'Attention
                </h2>
                <p>Aucun point d'attention particulier identifié.</p>
            </div>
            """
        
        risks_html = ""
        for risk in risks:
            risks_html += f'<div class="risk-item">{risk}</div>'
        
        return f"""
        <div class="section">
            <h2 class="section-title">
                <span class="section-icon">⚠️</span>
                Points d'Attention
            </h2>
            {risks_html}
        </div>
        """
    
    def _generate_missing_info_section(self, missing_info: List[str]) -> str:
        """Génère la section des informations manquantes"""
        if not missing_info:
            return ""
        
        missing_html = ""
        for info in missing_info:
            missing_html += f'<div class="missing-item">{info}</div>'
        
        return f"""
        <div class="section">
            <h2 class="section-title">
                <span class="section-icon">📋</span>
                Informations Manquantes
            </h2>
            {missing_html}
        </div>
        """
    
    def _generate_actions_section(self, actions: Dict[str, Any]) -> str:
        """Génère la section des actions recommandées"""
        key_dates = actions.get('key_dates', [])
        
        if not key_dates:
            return ""
        
        dates_html = ""
        for date in key_dates:
            dates_html += f'<div class="list-item">📅 {date}</div>'
        
        return f"""
        <div class="section">
            <h2 class="section-title">
                <span class="section-icon">🎯</span>
                Dates Importantes
            </h2>
            {dates_html}
        </div>
        """
    
    def _generate_technical_json_section(self, data: Dict[str, Any]) -> str:
        """Génère la section technique avec le JSON complet"""
        import json
        
        # Formatage JSON avec indentation
        json_formatted = json.dumps(data, indent=2, ensure_ascii=False, default=str)
        
        return f"""
        <div class="technical-section">
            <h2 class="section-title">
                <span class="section-icon">🔧</span>
                Données Techniques (JSON UniversalContractV3)
            </h2>
            <p style="margin-bottom: 1rem; color: #6b7280; font-size: 13px;">
                Cette section contient l'intégralité des données extraites au format JSON structuré, 
                conforme au schéma UniversalContractV3. Ces données peuvent être utilisées pour 
                l'intégration avec d'autres systèmes ou pour des analyses approfondies.
            </p>
            <div class="json-container">{json_formatted}</div>
        </div>
        """
    
    def _generate_footer(self) -> str:
        """Génère le pied de page"""
        return f"""
        <div class="disclaimer">
            <div class="disclaimer-title">⚖️ Avertissement Juridique</div>
            <div class="disclaimer-text">
                Ce document a été généré automatiquement par intelligence artificielle à partir de l'analyse du contrat fourni. 
                Il s'agit d'un résumé à titre informatif uniquement et ne constitue pas un conseil juridique. 
                Pour toute décision importante, consultez un professionnel du droit qualifié.
                <br><br>
                Les informations présentées sont basées sur l'analyse automatique du document et peuvent contenir des erreurs ou des omissions.
                Vérifiez toujours les informations importantes directement dans le contrat original.
            </div>
        </div>
        
        <div class="footer">
            <p><strong>Généré par AUTOPILOT Contract Reader</strong> • xyqo.ai • Conforme RGPD</p>
            <p>Document généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')} • Version 3.0 - UniversalContractV3</p>
        </div>
        """
    
    def _render_html_to_pdf(self, html_content: str) -> bytes:
        """Convertit le HTML en PDF avec WeasyPrint"""
        try:
            # CSS pour optimisation PDF
            pdf_css = CSS(string="""
                @page {
                    size: A4;
                    margin: 2cm;
                }
                .page-break {
                    page-break-before: always;
                }
                .no-break {
                    page-break-inside: avoid;
                }
                h1, h2, h3 {
                    page-break-after: avoid;
                }
                .section {
                    page-break-inside: avoid;
                }
            """)
            
            # Création du document HTML
            html_doc = HTML(string=html_content)
            
            # Génération PDF
            pdf_bytes = html_doc.write_pdf(
                stylesheets=[pdf_css],
                **self.pdf_options
            )
            
            return pdf_bytes
            
        except Exception as e:
            logger.error(f"Erreur rendu WeasyPrint: {e}")
            raise
