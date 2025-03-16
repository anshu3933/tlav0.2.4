# core/assessment/assessment_processor.py

import uuid
import re
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

from config.logging_config import get_module_logger
from core.assessment.interfaces import AssessmentProcessorInterface
from core.assessment.knowledge_tracing import BayesianKnowledgeTracer

# Create a logger for this module
logger = get_module_logger("assessment_processor")

class AssessmentProcessor(AssessmentProcessorInterface):
    """Process and decompose assessments into knowledge components."""
    
    def __init__(self, curriculum_data: Optional[Dict[str, Any]] = None):
        """Initialize the assessment processor.
        
        Args:
            curriculum_data: Optional curriculum data dictionary
        """
        self.knowledge_tracer = BayesianKnowledgeTracer()
        self.curriculum_data = curriculum_data or self._default_curriculum_data()
        logger.debug("Initialized Assessment Processor")
    
    def _default_curriculum_data(self) -> Dict[str, Any]:
        """Provide default curriculum data structure."""
        return {
            "subjects": {
                "mathematics": {
                    "categories": {
                        "number_sense": ["counting", "place_value", "number_recognition"],
                        "operations": ["addition", "subtraction", "multiplication", "division"],
                        "fractions": ["fraction_concepts", "fraction_operations", "decimals"],
                        "geometry": ["shapes", "measurement", "spatial_reasoning"]
                    }
                },
                "reading": {
                    "categories": {
                        "phonics": ["letter_recognition", "phonemic_awareness", "decoding"],
                        "fluency": ["reading_rate", "accuracy", "expression"],
                        "comprehension": ["main_idea", "details", "inference", "prediction"],
                        "vocabulary": ["word_meaning", "context_clues", "word_relationships"]
                    }
                }
            },
            "cognitive_skills": {
                "remember": ["identify", "recall", "recognize", "list"],
                "understand": ["explain", "summarize", "describe", "compare"],
                "apply": ["use", "solve", "demonstrate", "calculate"],
                "analyze": ["analyze", "examine", "categorize", "differentiate"],
                "evaluate": ["evaluate", "judge", "critique", "assess"],
                "create": ["create", "design", "develop", "compose"]
            }
        }
    
    def process_assessment(self, assessment: Dict[str, Any]) -> Dict[str, Any]:
        """Process an assessment to identify knowledge components.
        
        Args:
            assessment: Assessment data dictionary
            
        Returns:
            Processed assessment with knowledge components
        """
        try:
            # Create a copy to avoid modifying the original
            processed = assessment.copy()
            
            # Ensure assessment has a unique ID
            if "assessment_id" not in processed:
                processed["assessment_id"] = str(uuid.uuid4())
            
            # Process questions if they exist
            if "questions" in processed:
                processed_questions = []
                for question in processed["questions"]:
                    processed_question = self._process_question(
                        question,
                        processed.get("subject", ""),
                        processed.get("grade_level", "")
                    )
                    processed_questions.append(processed_question)
                processed["questions"] = processed_questions
            
            # Add processing metadata
            processed["processed_at"] = datetime.now().isoformat()
            
            return processed
            
        except Exception as e:
            logger.error(f"Error processing assessment: {str(e)}", exc_info=True)
            # Return original assessment if processing fails
            assessment["processing_error"] = str(e)
            return assessment
    
    def _process_question(self, question: Dict[str, Any], subject: str, grade_level: str) -> Dict[str, Any]:
        """Process a question to identify cognitive skills and knowledge components.
        
        Args:
            question: Question data
            subject: Subject area
            grade_level: Grade level
            
        Returns:
            Processed question with identified skills and components
        """
        # Create a copy to avoid modifying the original
        processed = question.copy()
        
        # Ensure question has an ID
        if "question_id" not in processed:
            processed["question_id"] = str(uuid.uuid4())
        
        # Skip if already processed
        if "cognitive_skills" in processed and "knowledge_components" in processed:
            return processed
        
        # Extract text and ensure it exists
        text = processed.get("text", "")
        if not text:
            processed["cognitive_skills"] = []
            processed["knowledge_components"] = []
            return processed
        
        # Identify cognitive skills
        processed["cognitive_skills"] = self._identify_cognitive_skills(text)
        
        # Identify knowledge components
        processed["knowledge_components"] = self._identify_knowledge_components(text, subject)
        
        # Estimate difficulty if not provided
        if "difficulty" not in processed:
            processed["difficulty"] = self._estimate_difficulty(
                processed["cognitive_skills"],
                processed["knowledge_components"]
            )
        
        return processed
    
    def _identify_cognitive_skills(self, text: str) -> List[str]:
        """Identify cognitive skills from question text.
        
        Args:
            text: Question text
            
        Returns:
            List of identified cognitive skills
        """
        text = text.lower()
        identified_skills = []
        
        for skill, indicators in self.curriculum_data["cognitive_skills"].items():
            for indicator in indicators:
                if indicator in text:
                    identified_skills.append(skill)
                    break
        
        # Default to "remember" if no skills identified
        if not identified_skills:
            identified_skills.append("remember")
        
        return identified_skills
    
    def _identify_knowledge_components(self, text: str, subject: str) -> List[Dict[str, Any]]:
        """Identify knowledge components from question text.
        
        Args:
            text: Question text
            subject: Subject area
            
        Returns:
            List of knowledge component dictionaries
        """
        text = text.lower()
        components = []
        subject_data = self.curriculum_data["subjects"].get(subject.lower(), {})
        
        # If subject not found, return empty list
        if not subject_data:
            return components
        
        # Search for knowledge components
        for category, skills in subject_data.get("categories", {}).items():
            for skill in skills:
                # Check if skill keywords are in the text
                if skill.replace("_", " ") in text:
                    # Create a unique ID for the component
                    component_id = f"kc_{subject.lower()}_{category}_{skill}"
                    
                    # Create component structure
                    component = {
                        "id": component_id,
                        "name": skill.replace("_", " ").title(),
                        "category": category,
                        "subject": subject.lower()
                    }
                    
                    # Add to list if not already present
                    if not any(c["id"] == component_id for c in components):
                        components.append(component)
        
        return components
    
    def _estimate_difficulty(self, cognitive_skills: List[str], knowledge_components: List[Dict[str, Any]]) -> float:
        """Estimate question difficulty based on cognitive skills and knowledge components.
        
        Args:
            cognitive_skills: Identified cognitive skills
            knowledge_components: Identified knowledge components
            
        Returns:
            Difficulty value (0 to 1)
        """
        # Base difficulty on cognitive skills level
        skill_difficulty = {
            "remember": 0.2,
            "understand": 0.4,
            "apply": 0.6,
            "analyze": 0.7,
            "evaluate": 0.8,
            "create": 0.9
        }
        
        # Calculate average difficulty from skills
        skill_values = [skill_difficulty.get(skill, 0.5) for skill in cognitive_skills]
        avg_difficulty = sum(skill_values) / max(len(skill_values), 1)
        
        # Complexity factor based on number of knowledge components
        complexity_factor = min(1.0, 0.1 * len(knowledge_components))
        
        # Combined difficulty (weighted average)
        difficulty = (0.7 * avg_difficulty) + (0.3 * complexity_factor)
        
        # Ensure difficulty is between 0 and 1
        return max(0.1, min(0.9, difficulty))
    
    def process_student_response(self, student_id: str, question: Dict[str, Any], response: Any) -> Dict[str, Any]:
        """Process a student's response to update knowledge state.
        
        Args:
            student_id: Student identifier
            question: Processed question dictionary
            response: Student's response
            
        Returns:
            Trace with interaction data and knowledge updates
        """
        try:
            # Validate inputs
            if not student_id or not question or "question_id" not in question:
                logger.warning("Invalid inputs for processing student response")
                return {"error": "Invalid inputs"}
            
            # Evaluate correctness
            is_correct = self._evaluate_correctness(question, response)
            
            # Create interaction record
            interaction = {
                "timestamp": datetime.now().isoformat(),
                "student_id": student_id,
                "question_id": question["question_id"],
                "is_correct": is_correct,
                "response": response
            }
            
            # Initialize knowledge updates dictionary
            knowledge_updates = {}
            
            # Update knowledge state for each component
            for component in question.get("knowledge_components", []):
                component_id = component.get("id")
                if not component_id:
                    continue
                
                # Use default prior if not provided
                prior = 0.5
                
                # Update knowledge using Bayesian knowledge tracing
                knowledge_update = self.knowledge_tracer.update_knowledge(
                    prior=prior,
                    is_correct=is_correct,
                    difficulty=question.get("difficulty", 0.5)
                )
                
                # Store updates
                knowledge_updates[component_id] = {
                    "prior": prior,
                    "new_value": knowledge_update["value"],
                    "confidence": knowledge_update["confidence"]
                }
            
            # Create and return the trace
            return {
                "interaction": interaction,
                "knowledge_updates": knowledge_updates
            }
            
        except Exception as e:
            logger.error(f"Error processing student response: {str(e)}", exc_info=True)
            return {"error": str(e)}
    
    def _evaluate_correctness(self, question: Dict[str, Any], response: Any) -> bool:
        """Evaluate if a response is correct.
        
        Args:
            question: Question dictionary
            response: Student's response
            
        Returns:
            True if response is correct, False otherwise
        """
        # Get question data
        question_type = question.get("question_type", "")
        correct_answer = question.get("correct_answer")
        
        # If no correct answer specified, return False
        if correct_answer is None:
            return False
        
        try:
            # Evaluate based on question type
            if question_type == "multiple_choice":
                return response == correct_answer
                
            elif question_type == "true_false":
                # Handle both string and boolean representations
                if isinstance(response, str):
                    return response.lower() == str(correct_answer).lower()
                return bool(response) == bool(correct_answer)
                
            elif question_type == "fill_in":
                # Normalize text for comparison
                response_text = str(response).strip().lower()
                correct_text = str(correct_answer).strip().lower()
                return response_text == correct_text
                
            elif question_type == "numeric":
                # Convert to numbers and compare with tolerance
                tolerance = question.get("tolerance", 0.001)
                return abs(float(response) - float(correct_answer)) <= tolerance
            
            # Default case
            return False
            
        except Exception as e:
            logger.error(f"Error evaluating correctness: {str(e)}")
            return False