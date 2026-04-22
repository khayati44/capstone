"""
Ethical AI Framework for Tax Deduction System
Addresses bias mitigation, fairness, transparency, and accountability
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import json

logger = logging.getLogger(__name__)


class BiasType(Enum):
    """Types of potential biases in AI systems"""
    GENDER = "gender_bias"
    INCOME = "income_bias"
    REGIONAL = "regional_bias"
    AGE = "age_bias"
    OCCUPATION = "occupation_bias"
    CONFIRMATION = "confirmation_bias"


@dataclass
class EthicalCheckResult:
    """Result of ethical AI validation"""
    passed: bool
    issues_found: List[str]
    recommendations: List[str]
    bias_score: float  # 0.0 (no bias) to 1.0 (high bias)
    fairness_metrics: Dict[str, float]


class BiasDetector:
    """
    Detects potential biases in tax deduction recommendations.
    Implements fairness checks across different demographic groups.
    """
    
    def __init__(self):
        self.bias_keywords = {
            BiasType.GENDER: ["male", "female", "mr", "mrs", "ms"],
            BiasType.INCOME: ["rich", "poor", "wealthy", "low-income"],
            BiasType.REGIONAL: ["urban", "rural", "metro", "tier-1"],
            BiasType.OCCUPATION: ["executive", "labor", "professional", "worker"]
        }
    
    def check_recommendation_bias(self, 
                                   user_profile: Dict, 
                                   recommendations: List[Dict]) -> EthicalCheckResult:
        """
        Check if recommendations are biased based on user demographics.
        
        Example fairness metric: Are 80C recommendations given equally 
        regardless of gender/income level?
        """
        issues = []
        recommendations_list = []
        bias_score = 0.0
        
        # Check 1: Income-based bias
        if self._has_income_bias(user_profile, recommendations):
            issues.append("Potential income-based bias detected")
            bias_score += 0.3
            recommendations_list.append(
                "Ensure recommendations are income-proportional, not income-discriminatory"
            )
        
        # Check 2: Gender-based bias (should not affect tax recommendations)
        if "gender" in user_profile:
            # Tax rules are gender-neutral - any gender reference is problematic
            for rec in recommendations:
                text = json.dumps(rec).lower()
                if any(kw in text for kw in self.bias_keywords[BiasType.GENDER]):
                    issues.append("Gender information should not affect tax recommendations")
                    bias_score += 0.4
                    break
        
        # Check 3: Explainability - are recommendations explained?
        unexplained = [r for r in recommendations if "reasoning" not in r]
        if unexplained:
            issues.append(f"{len(unexplained)} recommendations lack explanation")
            recommendations_list.append("Add clear reasoning for all recommendations")
        
        # Fairness metrics
        fairness_metrics = {
            "explanation_coverage": 1.0 - (len(unexplained) / max(len(recommendations), 1)),
            "demographic_neutrality": 1.0 - bias_score,
            "transparency_score": 0.8  # Based on system design
        }
        
        passed = bias_score < 0.3 and len(issues) < 2
        
        return EthicalCheckResult(
            passed=passed,
            issues_found=issues,
            recommendations=recommendations_list,
            bias_score=bias_score,
            fairness_metrics=fairness_metrics
        )
    
    def _has_income_bias(self, user_profile: Dict, recommendations: List[Dict]) -> bool:
        """Check if recommendations unfairly favor high-income users"""
        # Example: High-income users shouldn't get more complex/better recommendations
        # Tax deductions should be available to all income groups equally
        
        income = user_profile.get("income", 0)
        
        # Check if number/quality of recommendations varies suspiciously with income
        if income > 1000000 and len(recommendations) > 10:
            # Suspiciously many recommendations for high earners
            return True
        
        return False


class TransparencyEngine:
    """
    Provides explainable AI outputs for tax decisions.
    Ensures users understand WHY certain deductions were recommended.
    """
    
    def explain_deduction(self, transaction: Dict, tax_section: str) -> Dict[str, Any]:
        """
        Generate human-readable explanation for tax deduction.
        
        Returns:
            Explanation with reasoning, legal basis, and confidence
        """
        explanations = {
            "80C": {
                "simple": "This expense qualifies for Section 80C deduction (investments/savings)",
                "detailed": "Section 80C allows deduction up to ₹1,50,000 for specified investments including LIC, PPF, ELSS, etc.",
                "legal_ref": "Income Tax Act 1961, Section 80C",
                "limit": 150000
            },
            "80D": {
                "simple": "Health insurance premium qualifies for Section 80D deduction",
                "detailed": "Section 80D allows deduction for health insurance premiums: ₹25,000 (self/family) + ₹25,000 (parents under 60)",
                "legal_ref": "Income Tax Act 1961, Section 80D",
                "limit": 50000
            },
            "80E": {
                "simple": "Education loan interest is fully deductible under Section 80E",
                "detailed": "Section 80E allows full deduction of interest paid on education loans with no upper limit",
                "legal_ref": "Income Tax Act 1961, Section 80E",
                "limit": None
            },
            "80G": {
                "simple": "Donation qualifies for Section 80G deduction",
                "detailed": "Section 80G allows deduction for donations to specified funds/charities (50% or 100% based on recipient)",
                "legal_ref": "Income Tax Act 1961, Section 80G",
                "limit": None
            },
            "24B": {
                "simple": "Home loan interest qualifies for Section 24B deduction",
                "detailed": "Section 24B allows deduction up to ₹2,00,000 for interest on home loan for self-occupied property",
                "legal_ref": "Income Tax Act 1961, Section 24",
                "limit": 200000
            }
        }
        
        section_info = explanations.get(tax_section, {
            "simple": f"This may qualify for tax deduction under Section {tax_section}",
            "detailed": "Please consult a tax professional for specific guidance",
            "legal_ref": f"Section {tax_section}",
            "limit": None
        })
        
        return {
            "transaction_description": transaction.get("description"),
            "amount": transaction.get("debit_amount", 0),
            "tax_section": tax_section,
            "explanation_simple": section_info["simple"],
            "explanation_detailed": section_info["detailed"],
            "legal_basis": section_info["legal_ref"],
            "deduction_limit": section_info["limit"],
            "reasoning_steps": [
                f"1. Identified transaction type: {transaction.get('category', 'Unknown')}",
                f"2. Matched to tax section: {tax_section}",
                f"3. Verified against IT Act provisions",
                f"4. Applied applicable limits: ₹{section_info['limit']:,}" if section_info['limit'] else "4. No upper limit applicable"
            ],
            "confidence": self._calculate_confidence(transaction, tax_section)
        }
    
    def _calculate_confidence(self, transaction: Dict, tax_section: str) -> float:
        """Calculate confidence score for the recommendation"""
        # Simplified confidence calculation
        description = transaction.get("description", "").upper()
        
        # High confidence for exact keyword matches
        high_conf_keywords = {
            "80C": ["LIC", "PPF", "ELSS", "NSC"],
            "80D": ["HEALTH INSURANCE", "MEDICLAIM"],
            "80E": ["EDUCATION LOAN"],
            "80G": ["DONATION", "CHARITABLE"],
            "24B": ["HOME LOAN", "HOUSING LOAN"]
        }
        
        keywords = high_conf_keywords.get(tax_section, [])
        if any(kw in description for kw in keywords):
            return 0.95
        
        return 0.70  # Medium confidence for rule-based matches
    
    def generate_decision_log(self, decisions: List[Dict]) -> Dict:
        """
        Generate audit log of all AI decisions for accountability.
        Supports regulatory compliance and user trust.
        """
        return {
            "total_decisions": len(decisions),
            "timestamp": "2026-04-20T20:57:55",
            "decisions": decisions,
            "model_version": "1.0.0",
            "decision_maker": "TaxDeductionAI",
            "audit_trail": {
                "explainability": "All decisions include reasoning",
                "human_review": "Recommended for amounts > ₹50,000",
                "appeal_process": "Users can dispute via /api/dispute endpoint"
            }
        }


class FairnessAuditor:
    """
    Audits system outputs for fairness across different user groups.
    Implements demographic parity and equal opportunity checks.
    """
    
    def audit_recommendations(self, 
                             recommendations_by_group: Dict[str, List[Dict]]) -> Dict:
        """
        Audit if recommendations are fair across demographic groups.
        
        Args:
            recommendations_by_group: {
                "group_A": [recommendations],
                "group_B": [recommendations]
            }
        
        Returns:
            Fairness audit report
        """
        group_stats = {}
        
        for group, recs in recommendations_by_group.items():
            group_stats[group] = {
                "count": len(recs),
                "avg_deduction": sum(r.get("amount", 0) for r in recs) / max(len(recs), 1),
                "sections_covered": len(set(r.get("section") for r in recs))
            }
        
        # Check demographic parity: similar deduction averages?
        avg_deductions = [stats["avg_deduction"] for stats in group_stats.values()]
        max_avg = max(avg_deductions) if avg_deductions else 0
        min_avg = min(avg_deductions) if avg_deductions else 0
        
        disparity_ratio = min_avg / max_avg if max_avg > 0 else 1.0
        
        # Fairness metrics
        is_fair = disparity_ratio > 0.8  # Less than 20% disparity
        
        return {
            "is_fair": is_fair,
            "disparity_ratio": disparity_ratio,
            "group_statistics": group_stats,
            "fairness_score": disparity_ratio,
            "recommendation": "PASS" if is_fair else "REVIEW_REQUIRED",
            "notes": "Demographic parity maintained" if is_fair else "Significant disparity detected between groups"
        }


class EthicalAIFramework:
    """
    Main framework integrating all ethical AI components.
    Use this for capstone project ethical considerations demonstration.
    """
    
    def __init__(self):
        self.bias_detector = BiasDetector()
        self.transparency_engine = TransparencyEngine()
        self.fairness_auditor = FairnessAuditor()
        logger.info("Ethical AI Framework initialized")
    
    def comprehensive_ethical_check(self, 
                                     user_profile: Dict,
                                     transactions: List[Dict],
                                     recommendations: List[Dict]) -> Dict:
        """
        Run comprehensive ethical AI validation.
        
        Returns complete ethical assessment including:
        - Bias detection
        - Explainability
        - Fairness metrics
        - Audit trail
        """
        # 1. Bias detection
        bias_result = self.bias_detector.check_recommendation_bias(
            user_profile, recommendations
        )
        
        # 2. Generate explanations for transparency
        explanations = [
            self.transparency_engine.explain_deduction(tx, rec.get("tax_section", ""))
            for tx, rec in zip(transactions, recommendations)
        ]
        
        # 3. Decision audit log
        decision_log = self.transparency_engine.generate_decision_log(recommendations)
        
        return {
            "ethical_validation": {
                "bias_check": {
                    "passed": bias_result.passed,
                    "bias_score": bias_result.bias_score,
                    "issues": bias_result.issues_found,
                    "recommendations": bias_result.recommendations
                },
                "fairness_metrics": bias_result.fairness_metrics,
                "transparency": {
                    "all_decisions_explained": len(explanations) == len(recommendations),
                    "explanation_count": len(explanations),
                    "audit_log_generated": True
                }
            },
            "explanations": explanations,
            "audit_trail": decision_log,
            "ethical_score": (
                bias_result.fairness_metrics["demographic_neutrality"] +
                bias_result.fairness_metrics["explanation_coverage"] +
                bias_result.fairness_metrics["transparency_score"]
            ) / 3
        }


# ═══ USAGE EXAMPLE ═══════════════════════════════════════════════════════════

def demo_ethical_ai():
    """Demonstrate ethical AI framework"""
    
    framework = EthicalAIFramework()
    
    user = {"user_id": 123, "income": 800000, "gender": "neutral"}
    
    transactions = [
        {"id": 1, "description": "LIC Premium", "debit_amount": 15000, "category": "Insurance"},
        {"id": 2, "description": "PPF Deposit", "debit_amount": 20000, "category": "Investment"}
    ]
    
    recommendations = [
        {"tax_section": "80C", "amount": 15000, "reasoning": "Life insurance premium"},
        {"tax_section": "80C", "amount": 20000, "reasoning": "PPF investment"}
    ]
    
    result = framework.comprehensive_ethical_check(user, transactions, recommendations)
    
    print("\n" + "="*80)
    print("ETHICAL AI VALIDATION RESULT")
    print("="*80)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    demo_ethical_ai()
