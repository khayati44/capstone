"""
Enhanced Multi-Agent System with A2A (Agent-to-Agent) Communication
Demonstrates agent collaboration patterns for capstone requirements
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json

logger = logging.getLogger(__name__)


@dataclass
class AgentMessage:
    """
    Message passed between agents in A2A communication.
    Follows structured communication protocol.
    """
    from_agent: str
    to_agent: str
    message_type: str  # "request", "response", "notification", "error"
    content: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    conversation_id: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "from": self.from_agent,
            "to": self.to_agent,
            "type": self.message_type,
            "content": self.content,
            "timestamp": self.timestamp,
            "conversation_id": self.conversation_id
        }


class AgentCommunicationBus:
    """
    Central communication hub for agent-to-agent messaging.
    Implements pub-sub pattern for agent collaboration.
    """
    
    def __init__(self):
        self.message_history: List[AgentMessage] = []
        self.subscribers: Dict[str, List[callable]] = {}
    
    def send_message(self, message: AgentMessage):
        """Send message from one agent to another"""
        self.message_history.append(message)
        logger.info(f"A2A Message: {message.from_agent} → {message.to_agent} ({message.message_type})")
        
        # Notify subscribers
        if message.to_agent in self.subscribers:
            for callback in self.subscribers[message.to_agent]:
                callback(message)
    
    def subscribe(self, agent_name: str, callback: callable):
        """Subscribe an agent to receive messages"""
        if agent_name not in self.subscribers:
            self.subscribers[agent_name] = []
        self.subscribers[agent_name].append(callback)
    
    def get_conversation(self, conversation_id: str) -> List[AgentMessage]:
        """Get all messages in a conversation"""
        return [msg for msg in self.message_history if msg.conversation_id == conversation_id]


class EnhancedCategorizerAgent:
    """
    Agent 1: Transaction Categorizer with A2A communication
    """
    
    def __init__(self, comm_bus: AgentCommunicationBus):
        self.name = "CategorizerAgent"
        self.comm_bus = comm_bus
        self.comm_bus.subscribe(self.name, self.handle_message)
    
    def handle_message(self, message: AgentMessage):
        """Handle incoming A2A messages"""
        if message.message_type == "request":
            # Another agent is requesting categorization
            transactions = message.content.get("transactions", [])
            results = self.categorize_batch(transactions)
            
            # Send response back
            response = AgentMessage(
                from_agent=self.name,
                to_agent=message.from_agent,
                message_type="response",
                content={"categorized_transactions": results},
                conversation_id=message.conversation_id
            )
            self.comm_bus.send_message(response)
    
    def categorize_batch(self, transactions: List[Dict]) -> List[Dict]:
        """Categorize transactions and notify downstream agents"""
        categorized = []
        
        for tx in transactions:
            # Perform categorization (simplified)
            result = self._categorize_single(tx)
            categorized.append(result)
            
            # If tax-relevant, notify TaxMatcherAgent
            if result.get("is_tax_relevant"):
                notification = AgentMessage(
                    from_agent=self.name,
                    to_agent="TaxMatcherAgent",
                    message_type="notification",
                    content={
                        "event": "tax_relevant_found",
                        "transaction": result
                    }
                )
                self.comm_bus.send_message(notification)
        
        return categorized
    
    def _categorize_single(self, tx: Dict) -> Dict:
        """Single transaction categorization logic"""
        description = tx.get("description", "").upper()
        
        # Heuristic categorization
        is_tax_relevant = any(
            keyword in description 
            for keyword in ["LIC", "PPF", "INSURANCE", "DONATION", "LOAN", "ELSS"]
        )
        
        return {
            **tx,
            "category": "Tax-Deductible" if is_tax_relevant else "Regular",
            "is_tax_relevant": is_tax_relevant,
            "processed_by": self.name
        }


class EnhancedTaxMatcherAgent:
    """
    Agent 2: Tax Rule Matcher with A2A communication and RAG integration
    """
    
    def __init__(self, comm_bus: AgentCommunicationBus):
        self.name = "TaxMatcherAgent"
        self.comm_bus = comm_bus
        self.comm_bus.subscribe(self.name, self.handle_message)
        self.pending_calculations = []
    
    def handle_message(self, message: AgentMessage):
        """Handle incoming A2A messages"""
        if message.message_type == "notification":
            # Categorizer found a tax-relevant transaction
            tx = message.content.get("transaction")
            matched = self._match_to_section(tx)
            self.pending_calculations.append(matched)
            
            # Request calculation from CalculatorAgent
            calc_request = AgentMessage(
                from_agent=self.name,
                to_agent="CalculatorAgent",
                message_type="request",
                content={"matched_transactions": [matched]},
                conversation_id=message.conversation_id
            )
            self.comm_bus.send_message(calc_request)
    
    def _match_to_section(self, tx: Dict) -> Dict:
        """Match transaction to tax section using RAG (if available)"""
        description = tx.get("description", "").upper()
        
        # Simple rule-based matching (could use RAG here)
        section = None
        if "LIC" in description or "INSURANCE" in description:
            section = "80C" if "LIFE" in description else "80D"
        elif "PPF" in description or "ELSS" in description:
            section = "80C"
        elif "DONATION" in description:
            section = "80G"
        elif "EDUCATION" in description and "LOAN" in description:
            section = "80E"
        elif "HOME" in description and "LOAN" in description:
            section = "24B"
        
        return {
            **tx,
            "matched_section": section,
            "confidence": 0.85 if section else 0.0,
            "processed_by": self.name
        }


class EnhancedCalculatorAgent:
    """
    Agent 3: Deduction Calculator with reporting capabilities
    """
    
    def __init__(self, comm_bus: AgentCommunicationBus):
        self.name = "CalculatorAgent"
        self.comm_bus = comm_bus
        self.comm_bus.subscribe(self.name, self.handle_message)
        self.reports_generated = []
    
    def handle_message(self, message: AgentMessage):
        """Handle incoming A2A messages"""
        if message.message_type == "request":
            # TaxMatcher requesting calculation
            transactions = message.content.get("matched_transactions", [])
            report = self._calculate_deductions(transactions)
            self.reports_generated.append(report)
            
            # Send response back
            response = AgentMessage(
                from_agent=self.name,
                to_agent=message.from_agent,
                message_type="response",
                content={"report": report},
                conversation_id=message.conversation_id
            )
            self.comm_bus.send_message(response)
            
            # Notify reporting agent for visualization
            viz_notification = AgentMessage(
                from_agent=self.name,
                to_agent="ReportingAgent",
                message_type="notification",
                content={"event": "report_ready", "report": report}
            )
            self.comm_bus.send_message(viz_notification)
    
    def _calculate_deductions(self, transactions: List[Dict]) -> Dict:
        """Calculate section-wise deductions"""
        section_totals = {}
        
        for tx in transactions:
            section = tx.get("matched_section")
            if section:
                amount = tx.get("debit_amount", 0)
                section_totals[section] = section_totals.get(section, 0) + amount
        
        # Apply limits
        limits = {"80C": 150000, "80D": 25000, "80E": None, "80G": None, "24B": 200000}
        capped_totals = {}
        for section, total in section_totals.items():
            limit = limits.get(section)
            capped = min(total, limit) if limit else total
            capped_totals[section] = capped
        
        total_deduction = sum(capped_totals.values())
        
        return {
            "section_wise": capped_totals,
            "total_deductions": total_deduction,
            "tax_savings_20": total_deduction * 0.20,
            "tax_savings_30": total_deduction * 0.30,
            "generated_by": self.name,
            "timestamp": datetime.now().isoformat()
        }


class ReportingAgent:
    """
    Agent 4: Reporting & Visualization Agent
    Demonstrates A2A collaboration for report generation
    """
    
    def __init__(self, comm_bus: AgentCommunicationBus):
        self.name = "ReportingAgent"
        self.comm_bus = comm_bus
        self.comm_bus.subscribe(self.name, self.handle_message)
    
    def handle_message(self, message: AgentMessage):
        """Handle incoming A2A messages"""
        if message.message_type == "notification":
            if message.content.get("event") == "report_ready":
                report = message.content.get("report")
                visualization = self._generate_visualization(report)
                
                logger.info(f"{self.name}: Generated visualization for report")
                logger.info(f"Visualization: {visualization}")
    
    def _generate_visualization(self, report: Dict) -> Dict:
        """Generate visualization data for frontend"""
        section_wise = report.get("section_wise", {})
        
        return {
            "chart_type": "bar",
            "labels": list(section_wise.keys()),
            "values": list(section_wise.values()),
            "title": "Section-wise Tax Deductions",
            "total": report.get("total_deductions", 0)
        }


# ═══ ORCHESTRATOR ═════════════════════════════════════════════════════════════

class MultiAgentOrchestrator:
    """
    Orchestrator demonstrating A2A collaboration patterns.
    Shows how multiple agents communicate to solve complex tasks.
    """
    
    def __init__(self):
        self.comm_bus = AgentCommunicationBus()
        
        # Initialize agents
        self.categorizer = EnhancedCategorizerAgent(self.comm_bus)
        self.tax_matcher = EnhancedTaxMatcherAgent(self.comm_bus)
        self.calculator = EnhancedCalculatorAgent(self.comm_bus)
        self.reporter = ReportingAgent(self.comm_bus)
        
        logger.info("Multi-Agent System initialized with A2A communication")
    
    def process_transactions(self, transactions: List[Dict], conversation_id: str = None) -> Dict:
        """
        Process transactions through multi-agent pipeline with A2A communication.
        
        Flow:
        1. CategorizerAgent categorizes transactions
        2. TaxMatcherAgent matches tax-relevant ones to sections  
        3. CalculatorAgent computes deductions
        4. ReportingAgent generates visualizations
        
        All communication happens via AgentMessage protocol.
        """
        if not conversation_id:
            conversation_id = f"conv_{datetime.now().timestamp()}"
        
        # Start the pipeline by sending request to Categorizer
        initial_request = AgentMessage(
            from_agent="Orchestrator",
            to_agent="CategorizerAgent",
            message_type="request",
            content={"transactions": transactions},
            conversation_id=conversation_id
        )
        
        self.comm_bus.send_message(initial_request)
        
        # In real async implementation, this would wait for final response
        # For demo, we'll process synchronously
        categorized = self.categorizer.categorize_batch(transactions)
        
        return {
            "conversation_id": conversation_id,
            "message_count": len(self.comm_bus.message_history),
            "agents_involved": [self.categorizer.name, self.tax_matcher.name, 
                              self.calculator.name, self.reporter.name],
            "final_report": self.calculator.reports_generated[-1] if self.calculator.reports_generated else {}
        }
    
    def get_conversation_log(self, conversation_id: str) -> List[Dict]:
        """Get full A2A message log for a conversation"""
        messages = self.comm_bus.get_conversation(conversation_id)
        return [msg.to_dict() for msg in messages]


# ═══ DEMO ═════════════════════════════════════════════════════════════════════

def demo_a2a_communication():
    """Demonstrate agent-to-agent communication"""
    
    # Sample transactions
    transactions = [
        {"id": 1, "description": "LIC Premium Payment", "debit_amount": 15000},
        {"id": 2, "description": "Amazon Shopping", "debit_amount": 2000},
        {"id": 3, "description": "PPF Deposit", "debit_amount": 20000},
    ]
    
    # Initialize multi-agent system
    orchestrator = MultiAgentOrchestrator()
    
    # Process transactions
    result = orchestrator.process_transactions(transactions)
    
    print("\n" + "="*80)
    print("MULTI-AGENT PROCESSING RESULT (A2A Communication)")
    print("="*80)
    print(json.dumps(result, indent=2))
    
    # Show message log
    print("\n" + "="*80)
    print("AGENT-TO-AGENT MESSAGE LOG")
    print("="*80)
    for msg in orchestrator.comm_bus.message_history:
        print(f"{msg.timestamp}: {msg.from_agent} → {msg.to_agent} [{msg.message_type}]")


if __name__ == "__main__":
    demo_a2a_communication()
