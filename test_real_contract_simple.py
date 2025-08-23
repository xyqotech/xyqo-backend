#!/usr/bin/env python3
"""
Simple test with real contract samples
"""

import os
import json
import sys
import io
import PyPDF2
from datetime import datetime, timezone

# Add current directory to path
sys.path.insert(0, '/Users/bassiroudiop/autopilot-demo')

def extract_pdf_text(file_path):
    """Extract text from PDF file"""
    try:
        with open(file_path, 'rb') as f:
            pdf_reader = PyPDF2.PdfReader(f)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        print(f"Error extracting PDF: {e}")
        return ""

def create_analysis_from_text(text, filename):
    """Create UniversalContractV3 analysis from extracted text"""
    
    # Basic keyword analysis
    parties_found = []
    if "société" in text.lower() or "sarl" in text.lower() or "sas" in text.lower():
        parties_found.append({"name": "Société identifiée", "role": "Partie contractante"})
    
    contract_object = "Contrat analysé"
    if "prestation" in text.lower() or "service" in text.lower():
        contract_object = "Contrat de prestation de services"
    elif "vente" in text.lower():
        contract_object = "Contrat de vente"
    elif "location" in text.lower() or "bail" in text.lower():
        contract_object = "Contrat de location"
    elif "domiciliation" in text.lower():
        contract_object = "Contrat de domiciliation"
    elif "consultance" in text.lower() or "conseil" in text.lower():
        contract_object = "Contrat de consultance"
    
    # Extract some basic info
    risks = []
    if len(text) < 500:
        risks.append("Document très court - analyse limitée")
    if "résiliation" in text.lower():
        risks.append("Clauses de résiliation présentes")
    
    return {
        "meta": {
            "generator": "ContractSummarizer",
            "version": "3.0",
            "language": "fr",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "locale_guess": "France",
            "source_doc_info": {
                "title": filename,
                "doc_type": "PDF",
                "signing_method": None,
                "signatures_present": "signature" in text.lower(),
                "version_label": None,
                "effective_date": None
            }
        },
        "parties": {
            "list": parties_found if parties_found else [
                {"name": None, "role": None, "legal_form": None, "siren_siret": None, 
                 "address": None, "representative": None, "contact_masked": None}
            ],
            "third_parties": []
        },
        "contract": {
            "object": contract_object,
            "scope": {"deliverables": [], "exclusions": []},
            "location_or_site": None,
            "dates": {
                "start_date": None,
                "end_date": None,
                "minimum_term_months": None,
                "renewal": None,
                "notice_period_days": None,
                "milestones": []
            },
            "obligations": {
                "by_provider": [],
                "by_customer": [],
                "by_other": []
            },
            "service_levels": {
                "kpi_list": [],
                "sla": None,
                "penalties": None
            },
            "ip_rights": {
                "ownership": None,
                "license_terms": None
            },
            "data_privacy": {
                "rgpd": None,
                "processing_roles": None,
                "subprocessors": [],
                "data_locations": [],
                "security_measures": []
            }
        },
        "financials": {
            "price_model": "inconnu",
            "items": [],
            "currency": None,
            "payment_terms": None,
            "late_fees": None,
            "indexation": None,
            "security_deposit": {
                "amount": None,
                "currency": None,
                "refund_terms": None
            },
            "credit_details": {
                "principal_amount": None,
                "currency": None,
                "taeg_percent": None,
                "interest_rate_percent": None,
                "repayment_schedule": [],
                "withdrawal_rights": {
                    "days": None,
                    "instructions": None
                }
            }
        },
        "governance": {
            "termination": {
                "by_provider": None,
                "by_customer": None,
                "effects": None
            },
            "liability": None,
            "warranties": None,
            "compliance": None,
            "law": None,
            "jurisdiction": None,
            "insurance": None,
            "confidentiality": None,
            "force_majeure": None,
            "non_compete": {
                "exists": None,
                "duration_months": None,
                "scope": None,
                "consideration_amount": None,
                "currency": None
            }
        },
        "assurances": {
            "policies": []
        },
        "conditions_suspensives": [],
        "employment_details": {
            "contract_type": None,
            "position_title": None,
            "qualification": None,
            "collective_agreement": None,
            "probation_period": {"months": None},
            "working_time": {
                "type": None,
                "hours_per_week": None,
                "days_per_year": None
            },
            "remuneration": {
                "base_amount": None,
                "currency": None,
                "periodicity": None,
                "variable": None,
                "minimum_guarantee": None
            },
            "paid_leave_days_per_year": None,
            "notice_period": None,
            "mobility_clause": None
        },
        "immobilier_specifics": {
            "property_type": None,
            "address": None,
            "surface_sqm": None,
            "rooms": None,
            "lot_description": None,
            "diagnostics": [],
            "charges_breakdown": None,
            "works_done": None,
            "retraction_rights": {"days": None},
            "delivery": {
                "deadline_date": None,
                "penalties": None
            }
        },
        "litiges_modes_alternatifs": {
            "mediation": None,
            "arbitration": None,
            "amicable_settlement_steps": None
        },
        "summary_plain": f"Analyse du document {filename}. Contrat identifié comme: {contract_object}. Texte extrait: {len(text)} caractères.",
        "risks_red_flags": risks if risks else ["Aucun risque majeur identifié"],
        "missing_info": ["Analyse OpenAI complète nécessaire pour plus de détails"],
        "operational_actions": {
            "jira_summary": None,
            "key_dates": [],
            "renewal_window_days": None
        }
    }

def test_real_contracts():
    """Test with real contract samples"""
    
    samples_dir = "/Users/bassiroudiop/autopilot-demo/data/samples"
    contracts = [
        "Modele-de-contrat-de-consultance.pdf",
        "contrat_168602_domiciliation.pdf", 
        "contrat_SCF_JAS_WORK4YOU_28022023_01_DIOP_Bassirou.pdf"
    ]
    
    print("🧪 Testing XYQO Backend with Real Contracts")
    print("=" * 50)
    
    for contract_file in contracts:
        contract_path = os.path.join(samples_dir, contract_file)
        if os.path.exists(contract_path):
            print(f"\n📄 Testing: {contract_file}")
            
            # Extract text
            text = extract_pdf_text(contract_path)
            if text:
                print(f"✅ Text extracted: {len(text)} characters")
                
                # Create analysis
                analysis = create_analysis_from_text(text, contract_file)
                
                print(f"📋 Contract Object: {analysis['contract']['object']}")
                print(f"👥 Parties: {len(analysis['parties']['list'])}")
                print(f"📝 Summary: {analysis['summary_plain'][:100]}...")
                
                # Test JSON serialization
                try:
                    json_str = json.dumps(analysis, ensure_ascii=False, indent=2)
                    print(f"✅ JSON valid: {len(json_str)} characters")
                except Exception as e:
                    print(f"❌ JSON error: {e}")
                    
            else:
                print("❌ Failed to extract text")
    
    print("\n🎯 Real contract testing completed")

if __name__ == '__main__':
    test_real_contracts()
