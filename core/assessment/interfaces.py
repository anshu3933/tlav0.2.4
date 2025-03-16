# core/assessment/interfaces.py

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class AssessmentProcessorInterface(ABC):
    """Interface for assessment processing components."""
    
    @abstractmethod
    def process_assessment(self, assessment: Dict[str, Any]) -> Dict[str, Any]:
        """Process an assessment to identify knowledge components."""
        pass
    
    @abstractmethod
    def process_student_response(self, student_id: str, question: Dict[str, Any], 
                                response: Any) -> Dict[str, Any]:
        """Process a student's response to update knowledge state."""
        pass

class StudentProfileManagerInterface(ABC):
    """Interface for student profile management."""
    
    @abstractmethod
    def get_student_profile(self, student_id: str) -> Dict[str, Any]:
        """Get a student profile by ID."""
        pass
    
    @abstractmethod
    def update_profile_with_trace(self, student_id: str, trace: Dict[str, Any]) -> Dict[str, Any]:
        """Update student profile with performance trace data."""
        pass
    
    @abstractmethod
    def get_student_knowledge_state(self, student_id: str, subject: Optional[str] = None) -> Dict[str, float]:
        """Get a student's current knowledge state."""
        pass

class ReportGeneratorInterface(ABC):
    """Interface for assessment report generation."""
    
    @abstractmethod
    def generate_report(self, student_id: str, assessment: Dict[str, Any], 
                       interactions: List[Dict[str, Any]], 
                       knowledge_state: Dict[str, float]) -> Dict[str, Any]:
        """Generate an assessment report."""
        pass