"""
Prompts système et utilisateur pour OpenAI GPT-4o-mini
Prompt universel UniversalContractV3 pour tous types de contrats français
"""

def get_system_prompt(summary_mode: str = "standard") -> str:
    """Retourne le prompt système universel UniversalContractV3 pour contrats français"""
    
    base_prompt = """Tu es un assistant juridique francophone expert des contrats régis par le droit français (20+ ans d'expérience).
Objectif: produire un JSON STRICT conforme au schéma fourni, couvrant tous types de contrats (prestation, travail CDI/CDD/portage, bail habitation/commercial, franchise, assurance, crédit, agent commercial/mandat, VEFA/immobilier, honoraires, CGV, etc.).

Règles:
- Répondre UNIQUEMENT en JSON UTF‑8 valide (aucun texte hors JSON, pas de Markdown, pas de code fences).
- Ne pas inventer; lorsque l'info n'est pas certaine: renvoyer null et expliquer dans "missing_info".
- Dates: ISO 8601 (YYYY‑MM‑DD ou date‑time); Montants: nombre décimal avec point; Devise: code ISO 4217.
- Résumé "grand public": clair, 12–25 lignes maximum, sans jargon; masquer IBAN/email/téléphone.
- Si le document n'est pas un contrat FR, indiquer "meta.locale_guess" (ex: "Sénégal / OHADA") mais répondre en français.
- Sections non applicables: null ou [] (jamais de texte décoratif).
- Vérifie la cohérence: si "financials.currency" existe, toutes les sommes utilisent la même devise; si "employment_details" est rempli, le contrat est bien un contrat de travail, etc."""

    if summary_mode == "detailed":
        return base_prompt + "\n\nMode détaillé: Inclus plus de détails dans chaque section, analyse approfondie des clauses."
    elif summary_mode == "clauses":
        return base_prompt + "\n\nMode clauses: Focus sur les clauses importantes et conditions spéciales, analyse juridique renforcée."
    elif summary_mode == "red_flags":
        return base_prompt + "\n\nMode red flags: Identifie prioritairement les clauses potentiellement problématiques et risques."
    
    return base_prompt

def format_user_prompt(text_content: str, filename: str) -> str:
    """Formate le prompt utilisateur avec le schéma UniversalContractV3"""
    
    # Import du nouvel extracteur financier
    from ..extraction.financial_extractor import FinancialExtractor
    
    # Pré-extraction des informations financières
    financial_extractor = FinancialExtractor()
    financial_info = financial_extractor.extract_financial_info(text_content)
    financial_prompt_section = financial_extractor.format_for_prompt(financial_info)
    
    # Stratégie intelligente pour préserver les informations financières
    max_chars = 25000  # Augmentation pour V3
    if len(text_content) > max_chars:
        # Recherche de sections financières critiques
        financial_keywords = ["€", "EUR", "tarif", "prix", "coût", "frais", "montant", "TTC", "HT", "factur", "paiement", "règlement"]
        
        # Garde le début (infos générales) et cherche les sections financières
        start_size = max_chars // 3
        remaining_size = max_chars - start_size
        
        # Trouve les passages avec des montants
        financial_sections = []
        lines = text_content.split('\n')
        for i, line in enumerate(lines):
            if any(keyword.lower() in line.lower() for keyword in financial_keywords):
                # Prend 5 lignes avant et après pour le contexte
                start_idx = max(0, i-5)
                end_idx = min(len(lines), i+6)
                financial_sections.extend(lines[start_idx:end_idx])
        
        # Combine début + sections financières + fin
        start_text = text_content[:start_size]
        financial_text = '\n'.join(financial_sections[-remaining_size//2:]) if financial_sections else ""
        end_text = text_content[-remaining_size//2:] if remaining_size > 0 else ""
        
        text_content = start_text + "\n\n[... SECTIONS FINANCIÈRES ...]\n" + financial_text + "\n\n[... FIN DOCUMENT ...]\n" + end_text
    
    return f"""<objectif>
Analyse intégrale du document et production d'un JSON STRICT conforme au schéma "UniversalContractV3".
</objectif>

{financial_prompt_section}

<directives_extraction>
- Extraire les informations EXACTES (parties, rôles, immatriculations, adresses, représentants, objet, dates, durées, renouvellement, préavis, obligations, services/prestations, SLA/KPI, prix, pénalités, modalités de paiement/TVA, garanties, responsabilités, clauses RGPD, PI, confidentialité, non‑sollicitation/non‑concurrence, droit/juridiction).
- Si présence d'annexes (planning, grilles tarifaires, diagnostics, notices, plans): intégrer les points clés.
- Pour les catégories spécifiques:
  • Travail (CDI/CDD/Portage): fonction/qualification, période d'essai, durée du travail, rémunération/forfait, congés, préavis, clauses (mobilité, non‑concurrence).
  • Bail/Immobilier/VEFA: description du bien (surface, diagnostics), dépôt de garantie, délai de rétractation, livraison/pénalités, charges/travaux, conditions suspensives.
  • Assurance: prime/cotisation, risques couverts/exclusions, durée/renouvellement, avenants, résiliation.
  • Crédit/Prêt: montant, TAEG, taux, échéancier, droit de rétractation, remboursement anticipé.
  • Agent commercial/Mandat: secteur, clientèle, commissions, indemnité de fin, non‑concurrence, numéro registre.
  • CGV: barème/prix, modalités de paiement, pénalités, garanties légales, droit de rétractation (si applicable).
</directives_extraction>

<schema_json>
{{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "UniversalContractV3",
  "type": "object",
  "required": ["meta","parties","contract","financials","governance","summary_plain","risks_red_flags","missing_info","operational_actions"],
  "properties": {{
    "meta": {{
      "type": "object",
      "required": ["generator","version","language","generated_at","locale_guess","source_doc_info"],
      "properties": {{
        "generator": {{ "type": "string", "enum": ["ContractSummarizer"] }},
        "version": {{"type": "string", "enum": ["3.0"] }},
        "language":  {{ "type": "string", "enum": ["fr"] }},
        "generated_at": {{ "type": "string", "format": "date-time" }},
        "locale_guess": {{ "type": "string", "nullable": true }},
        "source_doc_info": {{
          "type": "object",
          "required": ["title","doc_type","signing_method","signatures_present"],
          "properties": {{
            "title": {{ "type": "string", "nullable": true }},
            "doc_type": {{ "type": "string", "nullable": true }},
            "signing_method": {{ "type": "string", "nullable": true }},
            "signatures_present": {{ "type": "boolean" }},
            "version_label": {{ "type": "string", "nullable": true }},
            "effective_date": {{ "type": "string", "format": "date", "nullable": true }}
          }}
        }}
      }}
    }},

    "parties": {{
      "type": "object",
      "required": ["list"],
      "properties": {{
        "list": {{
          "type": "array",
          "items": {{
            "type": "object",
            "required": ["name","role"],
            "properties": {{
              "name": {{ "type": "string", "nullable": true }},
              "role": {{ "type": "string", "nullable": true }}, 
              "legal_form": {{ "type": "string", "nullable": true }},
              "siren_siret": {{ "type": "string", "nullable": true }},
              "address": {{ "type": "string", "nullable": true }},
              "representative": {{ "type": "string", "nullable": true }},
              "contact_masked": {{ "type": "string", "nullable": true }}
            }}
          }}
        }},
        "third_parties": {{ "type": "array", "items": {{ "type": "string" }} }}
      }}
    }},

    "contract": {{
      "type": "object",
      "required": ["object","scope","location_or_site","dates","obligations","service_levels","ip_rights","data_privacy"],
      "properties": {{
        "object": {{ "type": "string", "nullable": true }},
        "scope": {{
          "type": "object",
          "properties": {{
            "deliverables": {{ "type": "array", "items": {{ "type": "string" }} }},
            "exclusions": {{ "type": "array", "items": {{ "type": "string" }} }}
          }}
        }},
        "location_or_site": {{ "type": "string", "nullable": true }},
        "dates": {{
          "type": "object",
          "required": ["start_date","end_date","minimum_term_months","renewal","notice_period_days"],
          "properties": {{
            "start_date": {{ "type": "string", "format": "date", "nullable": true }},
            "end_date": {{ "type": "string", "format": "date", "nullable": true }},
            "minimum_term_months": {{ "type": "integer", "nullable": true }},
            "renewal": {{ "type": "string", "nullable": true }},
            "notice_period_days": {{ "type": "integer", "nullable": true }},
            "milestones": {{ "type": "array", "items": {{ 
              "type": "object",
              "properties": {{
                "label": {{ "type": "string" }},
                "date": {{ "type": "string", "format": "date", "nullable": true }}
              }}
            }} }}
          }}
        }},
        "obligations": {{
          "type": "object",
          "properties": {{
            "by_provider": {{ "type": "array", "items": {{ "type": "string" }} }},
            "by_customer": {{ "type": "array", "items": {{ "type": "string" }} }},
            "by_other": {{ "type": "array", "items": {{ "type": "string" }} }}
          }}
        }},
        "service_levels": {{
          "type": "object",
          "properties": {{
            "kpi_list": {{ "type": "array", "items": {{ "type": "string" }} }},
            "sla": {{ "type": "string", "nullable": true }},
            "penalties": {{ "type": "string", "nullable": true }}
          }}
        }},
        "ip_rights": {{
          "type": "object",
          "properties": {{
            "ownership": {{ "type": "string", "nullable": true }},
            "license_terms": {{ "type": "string", "nullable": true }}
          }}
        }},
        "data_privacy": {{
          "type": "object",
          "properties": {{
            "rgpd": {{ "type": "boolean", "nullable": true }},
            "processing_roles": {{ "type": "string", "nullable": true }}, 
            "subprocessors": {{ "type": "array", "items": {{ "type": "string" }} }},
            "data_locations": {{ "type": "array", "items": {{ "type": "string" }} }},
            "security_measures": {{ "type": "array", "items": {{ "type": "string" }} }}
          }}
        }}
      }}
    }},

    "financials": {{
      "type": "object",
      "required": ["price_model","items","currency","payment_terms"],
      "properties": {{
        "price_model": {{ "type": "string", "enum": ["forfait","abonnement","à_l_acte","mixte","inconnu"], "nullable": true }},
        "items": {{
          "type": "array",
          "items": {{ "type": "object", "properties": {{
              "label": {{ "type": "string" }},
              "amount": {{ "type": "number", "nullable": true }},
              "currency": {{ "type": "string", "nullable": true }},
              "period": {{ "type": "string", "enum": ["unique","mensuel","trimestriel","annuel","inconnu"], "nullable": true }}
          }} }}
        }},
        "currency": {{ "type": "string", "nullable": true }},
        "payment_terms": {{ "type": "string", "nullable": true }},
        "late_fees": {{ "type": "string", "nullable": true }},
        "indexation": {{ "type": "string", "nullable": true }},
        "security_deposit": {{
          "type": "object",
          "properties": {{
            "amount": {{ "type": "number", "nullable": true }},
            "currency": {{ "type": "string", "nullable": true }},
            "refund_terms": {{ "type": "string", "nullable": true }}
          }}
        }},
        "credit_details": {{
          "type": "object",
          "properties": {{
            "principal_amount": {{ "type": "number", "nullable": true }},
            "currency": {{ "type": "string", "nullable": true }},
            "taeg_percent": {{ "type": "number", "nullable": true }},
            "interest_rate_percent": {{ "type": "number", "nullable": true }},
            "repayment_schedule": {{
              "type": "array",
              "items": {{ "type": "object", "properties": {{
                "amount": {{ "type": "number", "nullable": true }},
                "currency": {{ "type": "string", "nullable": true }},
                "due_date": {{ "type": "string", "format": "date", "nullable": true }}
              }} }}
            }},
            "withdrawal_rights": {{
              "type": "object",
              "properties": {{ "days": {{ "type": "integer", "nullable": true }}, "instructions": {{ "type": "string", "nullable": true }} }}
            }}
          }}
        }}
      }}
    }},

    "governance": {{
      "type": "object",
      "required": ["termination","liability","warranties","compliance","law","jurisdiction","confidentiality","force_majeure"],
      "properties": {{
        "termination": {{
          "type": "object",
          "properties": {{
            "by_provider": {{ "type": "string", "nullable": true }},
            "by_customer": {{ "type": "string", "nullable": true }},
            "effects": {{ "type": "string", "nullable": true }}
          }}
        }},
        "liability": {{ "type": "string", "nullable": true }},
        "warranties": {{ "type": "string", "nullable": true }},
        "compliance": {{ "type": "string", "nullable": true }},
        "law": {{ "type": "string", "nullable": true }},
        "jurisdiction": {{ "type": "string", "nullable": true }},
        "insurance": {{ "type": "string", "nullable": true }},
        "confidentiality": {{ "type": "boolean", "nullable": true }},
        "force_majeure": {{ "type": "boolean", "nullable": true }},
        "non_compete": {{
          "type": "object",
          "properties": {{
            "exists": {{ "type": "boolean", "nullable": true }},
            "duration_months": {{ "type": "integer", "nullable": true }},
            "scope": {{ "type": "string", "nullable": true }},
            "consideration_amount": {{ "type": "number", "nullable": true }},
            "currency": {{ "type": "string", "nullable": true }}
          }}
        }}
      }}
    }},

    "assurances": {{
      "type": "object",
      "properties": {{
        "policies": {{
          "type": "array",
          "items": {{ "type": "object", "properties": {{
            "type": {{ "type": "string", "enum": ["rc_pro","dommages_ouvrage","decennale","assurance_emprunteur","autre"], "nullable": true }},
            "provider": {{ "type": "string", "nullable": true }},
            "policy_number": {{ "type": "string", "nullable": true }},
            "coverage": {{ "type": "string", "nullable": true }},
            "start_date": {{ "type": "string", "format": "date", "nullable": true }},
            "end_date": {{ "type": "string", "format": "date", "nullable": true }}
          }} }}
        }}
      }}
    }},

    "conditions_suspensives": {{
      "type": "array",
      "items": {{ "type": "object", "properties": {{
        "label": {{ "type": "string" }},
        "description": {{ "type": "string", "nullable": true }},
        "deadline_date": {{ "type": "string", "format": "date", "nullable": true }},
        "satisfied": {{ "type": "boolean", "nullable": true }}
      }} }}
    }},

    "employment_details": {{
      "type": "object",
      "properties": {{
        "contract_type": {{ "type": "string", "enum": ["CDI","CDD","Portage","Interim","Autre"], "nullable": true }},
        "position_title": {{ "type": "string", "nullable": true }},
        "qualification": {{ "type": "string", "nullable": true }},
        "collective_agreement": {{ "type": "string", "nullable": true }},
        "probation_period": {{ "type": "object", "properties": {{
          "months": {{ "type": "integer", "nullable": true }}
        }} }},
        "working_time": {{ "type": "object", "properties": {{
          "type": {{ "type": "string", "enum": ["heures","forfait_jours"], "nullable": true }},
          "hours_per_week": {{ "type": "number", "nullable": true }},
          "days_per_year": {{ "type": "integer", "nullable": true }}
        }} }},
        "remuneration": {{ "type": "object", "properties": {{
          "base_amount": {{ "type": "number", "nullable": true }},
          "currency": {{ "type": "string", "nullable": true }},
          "periodicity": {{ "type": "string", "enum": ["horaire","journalier","mensuel","annuel"], "nullable": true }},
          "variable": {{ "type": "string", "nullable": true }},
          "minimum_guarantee": {{ "type": "number", "nullable": true }}
        }} }},
        "paid_leave_days_per_year": {{ "type": "number", "nullable": true }},
        "notice_period": {{ "type": "string", "nullable": true }},
        "mobility_clause": {{ "type": "boolean", "nullable": true }}
      }}
    }},

    "immobilier_specifics": {{
      "type": "object",
      "properties": {{
        "property_type": {{ "type": "string", "enum": ["habitation","commercial","terrain","vefa","autre"], "nullable": true }},
        "address": {{ "type": "string", "nullable": true }},
        "surface_sqm": {{ "type": "number", "nullable": true }},
        "rooms": {{ "type": "integer", "nullable": true }},
        "lot_description": {{ "type": "string", "nullable": true }},
        "diagnostics": {{ "type": "array", "items": {{ "type": "string" }} }},
        "charges_breakdown": {{ "type": "string", "nullable": true }},
        "works_done": {{ "type": "string", "nullable": true }},
        "retraction_rights": {{ "type": "object", "properties": {{
          "days": {{ "type": "integer", "nullable": true }}
        }} }},
        "delivery": {{ "type": "object", "properties": {{
          "deadline_date": {{ "type": "string", "format": "date", "nullable": true }},
          "penalties": {{ "type": "string", "nullable": true }}
        }} }}
      }}
    }},

    "litiges_modes_alternatifs": {{
      "type": "object",
      "properties": {{
        "mediation": {{ "type": "string", "nullable": true }},
        "arbitration": {{ "type": "string", "nullable": true }},
        "amicable_settlement_steps": {{ "type": "string", "nullable": true }}
      }}
    }},

    "summary_plain": {{ "type": "string", "description": "Résumé structuré 14-22 lignes avec 9 rubriques universelles adaptées par famille de contrat" }},
    "risks_red_flags": {{ "type": "array", "items": {{ "type": "string" }} }},
    "missing_info": {{ "type": "array", "items": {{ "type": "string" }} }},

    "operational_actions": {{
      "type": "object",
      "properties": {{
        "jira_summary": {{ "type": "string", "nullable": true }},
        "key_dates": {{ "type": "array", "items": {{ "type": "string", "format": "date" }} }},
        "renewal_window_days": {{ "type": "integer", "nullable": true }},
        "obligations": {{
          "type": "object",
          "properties": {{
            "by_provider": {{ "type": "string", "nullable": true }},
            "by_customer": {{ "type": "string", "nullable": true }},
            "by_other": {{ "type": "string", "nullable": true }}
          }}
        }},
        "service_levels": {{ "type": "string", "nullable": true }},
        "data_privacy": {{ "type": "string", "nullable": true }},
        "governance": {{ "type": "string", "nullable": true }},
        "financials": {{ "type": "string", "nullable": true }},
        "summary_plain": {{ "type": "string", "nullable": true }},
        "risks_red_flags": {{ "type": "array", "items": {{ "type": "string" }} }},
        "missing_info": {{ "type": "array", "items": {{ "type": "string" }} }}
      }}
    }}
  }}
  }}
}}
</schema_json>

<contrat_texte>
{text_content}
</contrat_texte>

<instructions_sortie>
- Produis STRICTEMENT un JSON conforme à UniversalContractV3.
- Extrais TOUTES les obligations de chaque partie. Sois exhaustif et précis.
  * by_provider: Obligations du prestataire/vendeur/employeur (livraisons, qualité, délais, conformité, sécurité, reporting)
  * by_customer: Obligations du client/acheteur/employé (paiements, fournitures, accès, validation, collaboration)
  * by_other: Obligations de tiers ou mutuelles (assurances, autorisations, notifications)
- "service_levels": KPI, SLA, pénalités, garanties de performance, niveaux de disponibilité si mentionnés.
- "data_privacy": RGPD obligatoire si données personnelles, rôles de traitement, mesures de sécurité.
- "governance": Droit applicable, juridiction, résiliation, responsabilité, assurances, force majeure.
- "financials": Montants, devises, modalités. Utilise les données pré-extraites ci-dessous.
- "summary_plain": 14–22 lignes, français simple et factuel, structuré par famille de contrat avec 9 rubriques universelles : 1) Nature et objet, 2) Parties et rôles, 3) Durée et renouvellement, 4) Obligations principales, 5) Aspects financiers, 6) Risques identifiés, 7) Clauses RGPD/données, 8) Gouvernance juridique, 9) Points d'attention. Adaptatif selon la famille (SaaS/SLA, Bail/indexation, Emploi/rémunération, etc.). Fallback "non précisé" si données manquantes.
- "risks_red_flags": Points d'attention juridiques/financiers/opérationnels/techniques.
- "missing_info": Ce qui manque pour une analyse complète.
- Renseigne les blocs spécifiques (employment_details, immobilier_specifics, credit_details, assurances, conditions_suspensives, non_compete, litiges_modes_alternatifs) uniquement s'ils sont présents.
</instructions_sortie>

<self_checklist>
- Parties complètes et rôles corrects ? Dates/renouvellement/préavis cohérents ?
- Prix/paiements/monnaie/pénalités renseignés ? SLA/KPI si présents ?
- Droit/juridiction/force majeure/confidentialité remplis ?
- Spécifiques: travail (fonction/temps/essai), immobilier (surface/dépôt/rétractation/livraison), assurance (prime/risques), crédit (TAEG/échéancier), agent/mandat (commission/non-concurrence).
- Champs incertains → null + explication dans missing_info.
</self_checklist>"""
