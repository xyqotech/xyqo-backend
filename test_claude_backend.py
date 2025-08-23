#!/usr/bin/env python3
"""
Simple test backend to verify Claude integration works
"""

import json
import os
from datetime import datetime, timezone

# Test Claude integration
try:
    import anthropic
    CLAUDE_AVAILABLE = True
    print("✅ Claude package available")
except ImportError:
    CLAUDE_AVAILABLE = False
    print("❌ Claude package not available")

def test_claude_analysis():
    """Test Claude AI contract analysis"""
    
    if not CLAUDE_AVAILABLE:
        print("❌ Cannot test Claude - package not installed")
        return False
    
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("❌ Cannot test Claude - ANTHROPIC_API_KEY not set")
        return False
    
    try:
        client = anthropic.Anthropic(api_key=api_key)
        
        # Simple test
        response = client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=100,
            temperature=0.1,
            messages=[{
                "role": "user", 
                "content": "Respond with just the JSON: {\"test\": \"success\"}"
            }]
        )
        
        response_text = response.content[0].text.strip()
        print(f"Claude response: {response_text}")
        
        # Try to parse as JSON
        try:
            result = json.loads(response_text)
            print("✅ Claude integration working")
            return True
        except json.JSONDecodeError:
            print("❌ Claude didn't return valid JSON")
            return False
            
    except Exception as e:
        print(f"❌ Claude API error: {e}")
        return False

def create_fallback_analysis():
    """Create UniversalContractV3 compliant fallback analysis"""
    
    return {
        "meta": {
            "generator": "ContractSummarizer",
            "version": "3.0",
            "language": "fr",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "locale_guess": "France",
            "source_doc_info": {
                "title": "test_document.pdf",
                "doc_type": "PDF",
                "signing_method": None,
                "signatures_present": False,
                "version_label": None,
                "effective_date": None
            }
        },
        "parties": {
            "list": [
                {"name": None, "role": None, "legal_form": None, "siren_siret": None, 
                 "address": None, "representative": None, "contact_masked": None}
            ],
            "third_parties": []
        },
        "contract": {
            "object": "Test contract analysis",
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
        "summary_plain": "Test analysis - backend integration working",
        "risks_red_flags": ["Test mode - no real analysis performed"],
        "missing_info": ["Real contract content", "Detailed analysis"],
        "operational_actions": {
            "jira_summary": None,
            "key_dates": [],
            "renewal_window_days": None
        }
    }

if __name__ == '__main__':
    print("🧪 Testing Claude Backend Integration")
    print("=" * 50)
    
    # Test Claude availability
    claude_works = test_claude_analysis()
    
    # Test fallback analysis structure
    print("\n📋 Testing fallback analysis structure...")
    fallback = create_fallback_analysis()
    
    try:
        json_str = json.dumps(fallback, ensure_ascii=False, indent=2)
        print("✅ Fallback analysis JSON is valid")
        print(f"📊 Analysis size: {len(json_str)} characters")
    except Exception as e:
        print(f"❌ Fallback analysis JSON error: {e}")
    
    print("\n🎯 Integration Status:")
    print(f"Claude Available: {'✅' if CLAUDE_AVAILABLE else '❌'}")
    print(f"Claude API Key: {'✅' if os.getenv('ANTHROPIC_API_KEY') else '❌'}")
    print(f"Claude Working: {'✅' if claude_works else '❌'}")
    print(f"Fallback Ready: ✅")
