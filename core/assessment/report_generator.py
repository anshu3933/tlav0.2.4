# core/assessment/report_generator.py

from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

from config.logging_config import get_module_logger
from core.assessment.interfaces import ReportGeneratorInterface

# Create a logger for this module
logger = get_module_logger("report_generator")

class ReportGenerator(ReportGeneratorInterface):
    """Generate assessment reports based on student performance."""
    
    def __init__(self, grading_scale: Optional[Dict[str, float]] = None):
        """Initialize the report generator.
        
        Args:
            grading_scale: Optional custom grading scale
        """
        self.grading_scale = grading_scale or self._default_grading_scale()
        self.mastery_threshold = 0.8  # Default mastery threshold
        logger.debug("Initialized Report Generator")
    
    def _default_grading_scale(self) -> Dict[str, float]:
        """Get default grading scale.
        
        Returns:
            Grading scale dictionary mapping grades to minimum score thresholds
        """
        return {
            "A": 0.9,  # 90% and above
            "B": 0.8,  # 80% to 89%
            "C": 0.7,  # 70% to 79%
            "D": 0.6,  # 60% to 69%
            "F": 0.0   # Below 60%
        }
    
    def generate_report(self, student_id: str, assessment: Dict[str, Any], 
                       interactions: List[Dict[str, Any]], 
                       knowledge_state: Dict[str, float]) -> Dict[str, Any]:
        """Generate an assessment report.
        
        Args:
            student_id: Student identifier
            assessment: Assessment dictionary
            interactions: List of student interactions
            knowledge_state: Student knowledge state
            
        Returns:
            Assessment report dictionary
        """
        try:
            # Create report structure
            report = {
                "report_id": str(uuid.uuid4()),
                "student_id": student_id,
                "assessment_id": assessment.get("assessment_id"),
                "assessment_title": assessment.get("title", "Untitled Assessment"),
                "generated_at": datetime.now().isoformat(),
                "overall_performance": {},
                "question_performance": [],
                "knowledge_components": [],
                "recommendations": []
            }
            
            # Calculate overall performance
            correct_count = sum(1 for interaction in interactions if interaction.get("is_correct", False))
            total_questions = len(interactions)
            
            if total_questions > 0:
                score = correct_count / total_questions
                report["overall_performance"] = {
                    "correct_count": correct_count,
                    "total_questions": total_questions,
                    "percentage": score * 100,
                    "grade": self._calculate_grade(score)
                }
            
            # Analyze per-question performance
            report["question_performance"] = self._analyze_question_performance(assessment, interactions)
            
            # Analyze knowledge components
            report["knowledge_components"] = self._analyze_knowledge_components(assessment, knowledge_state)
            
            # Generate recommendations
            report["recommendations"] = self._generate_recommendations(report["knowledge_components"])
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating assessment report: {str(e)}", exc_info=True)
            return {
                "report_id": str(uuid.uuid4()),
                "student_id": student_id,
                "assessment_id": assessment.get("assessment_id", "unknown"),
                "generated_at": datetime.now().isoformat(),
                "error": str(e)
            }
    
    def _calculate_grade(self, score: float) -> str:
        """Calculate letter grade based on score.
        
        Args:
            score: Score as decimal (0 to 1)
            
        Returns:
            Letter grade
        """
        # Ensure score is between 0 and 1
        score = max(0.0, min(1.0, score))
        
        # Find the highest grade threshold that the score exceeds
        for grade, threshold in sorted(self.grading_scale.items(), key=lambda x: x[1], reverse=True):
            if score >= threshold:
                return grade
        
        # Default to F if no threshold matched (shouldn't happen with proper scale)
        return "F"

    def _analyze_question_performance(self, assessment: Dict[str, Any], 
                                     interactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze per-question performance.
        
        Args:
            assessment: Assessment dictionary
            interactions: List of student interactions
            
        Returns:
            List of question performance analyses
        """
        question_performance = []
        
        # Create a mapping of question IDs to questions
        questions = {q.get("question_id"): q for q in assessment.get("questions", [])}
        
        # Process each interaction
        for interaction in interactions:
            question_id = interaction.get("question_id")
            question = questions.get(question_id)
            
            if not question:
                continue
            
            # Create performance record
            performance = {
                "question_id": question_id,
                "text": question.get("text", ""),
                "is_correct": interaction.get("is_correct", False),
                "cognitive_skills": question.get("cognitive_skills", []),
                "knowledge_components": [
                    {
                        "id": kc.get("id"),
                        "name": kc.get("name", "")
                    } for kc in question.get("knowledge_components", [])
                ]
            }
            
            question_performance.append(performance)
        
        return question_performance
    
    def _analyze_knowledge_components(self, assessment: Dict[str, Any], 
                                    knowledge_state: Dict[str, float]) -> List[Dict[str, Any]]:
        """Analyze knowledge components.
        
        Args:
            assessment: Assessment dictionary
            knowledge_state: Student knowledge state
            
        Returns:
            List of knowledge component analyses
        """
        components = []
        component_map = {}
        
        # Create a mapping of component IDs to component details
        for question in assessment.get("questions", []):
            for kc in question.get("knowledge_components", []):
                component_id = kc.get("id")
                if component_id and component_id not in component_map:
                    component_map[component_id] = kc
        
        # Process each component in the knowledge state
        for component_id, mastery in knowledge_state.items():
            # Skip if not relevant to the assessment
            if component_id not in component_map:
                continue
            
            # Get component details
            kc = component_map.get(component_id, {})
            
            # Create component analysis
            component = {
                "component_id": component_id,
                "name": kc.get("name", component_id.replace("kc_", "").replace("_", " ").title()),
                "category": kc.get("category", ""),
                "subject": kc.get("subject", ""),
                "mastery": mastery,
                "mastery_level": self._get_mastery_level(mastery)
            }
            
            components.append(component)
        
        # Sort by mastery (ascending)
        components.sort(key=lambda c: c["mastery"])
        
        return components
    
    def _get_mastery_level(self, mastery: float) -> str:
        """Get mastery level descriptor.
        
        Args:
            mastery: Mastery value (0 to 1)
            
        Returns:
            Mastery level descriptor
        """
        if mastery >= 0.9:
            return "Expert"
        elif mastery >= 0.8:
            return "Proficient"
        elif mastery >= 0.7:
            return "Developing"
        elif mastery >= 0.5:
            return "Basic"
        else:
            return "Novice"
    
    def _generate_recommendations(self, knowledge_components: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate learning recommendations based on knowledge components.
        
        Args:
            knowledge_components: List of knowledge component analyses
            
        Returns:
            List of recommendation dictionaries
        """
        recommendations = []
        
        # Focus on components below mastery threshold
        focus_components = [c for c in knowledge_components if c["mastery"] < self.mastery_threshold]
        
        for component in focus_components[:3]:  # Limit to top 3 priorities
            component_name = component.get("name", "")
            mastery = component.get("mastery", 0)
            
            # Create recommendation
            recommendation = {
                "component_id": component.get("component_id", ""),
                "component_name": component_name,
                "current_mastery": mastery,
                "target_mastery": self.mastery_threshold,
                "recommendation": f"Focus on {component_name} skills to improve mastery"
            }
            
            recommendations.append(recommendation)
        
        return recommendations