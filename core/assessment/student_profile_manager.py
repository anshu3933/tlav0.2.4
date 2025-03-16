# core/assessment/student_profile_manager.py

from typing import Dict, Any, List, Optional
from datetime import datetime

from config.logging_config import get_module_logger
from core.assessment.interfaces import StudentProfileManagerInterface
from ui.state_manager import state_manager

# Create a logger for this module
logger = get_module_logger("student_profile_manager")

class StudentProfileManager(StudentProfileManagerInterface):
    """Manage student profiles and knowledge states."""
    
    def __init__(self):
        """Initialize the student profile manager."""
        self.state_manager = state_manager
        logger.debug("Initialized Student Profile Manager")
    
    def get_student_profile(self, student_id: str) -> Dict[str, Any]:
        """Get a student profile by ID, creating it if it doesn't exist.
        
        Args:
            student_id: Student identifier
            
        Returns:
            Student profile dictionary
        """
        # Create a profile key for storage
        profile_key = f"student_profile_{student_id}"
        
        # Try to get existing profile
        profile = self.state_manager.get(profile_key)
        
        # If no profile exists, create a new one
        if not profile:
            profile = {
                "student_id": student_id,
                "creation_date": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
                "name": f"Student {student_id}",  # Default name
                "grade_level": "Unknown",
                "interaction_history": [],
                "knowledge_state": {},
                "metrics": {
                    "overall_mastery": 0.0,
                    "strengths": [],
                    "areas_for_improvement": []
                }
            }
            # Save the new profile
            self.state_manager.set(profile_key, profile)
        
        return profile
    
    def update_profile_with_trace(self, student_id: str, trace: Dict[str, Any]) -> Dict[str, Any]:
        """Update student profile with performance trace data.
        
        Args:
            student_id: Student identifier
            trace: Performance trace with interaction and knowledge updates
            
        Returns:
            Updated student profile
        """
        try:
            # Get current profile
            profile = self.get_student_profile(student_id)
            
            # Check if trace contains error
            if "error" in trace:
                logger.warning(f"Trace contains error: {trace['error']}")
                return profile
            
            # Extract interaction data
            interaction = trace.get("interaction", {})
            knowledge_updates = trace.get("knowledge_updates", {})
            
            # Skip if interaction is empty
            if not interaction:
                logger.warning("Trace contains no interaction data")
                return profile
            
            # Add interaction to history
            if "interaction_history" not in profile:
                profile["interaction_history"] = []
            profile["interaction_history"].append(interaction)
            
            # Update knowledge state
            if "knowledge_state" not in profile:
                profile["knowledge_state"] = {}
            
            # Process each knowledge component update
            for component_id, update in knowledge_updates.items():
                # Get current state or create new one
                if component_id not in profile["knowledge_state"]:
                    profile["knowledge_state"][component_id] = {
                        "initial_value": update.get("new_value", 0.5),
                        "current_value": update.get("new_value", 0.5),
                        "confidence": update.get("confidence", 0.5),
                        "last_updated": interaction.get("timestamp", datetime.now().isoformat()),
                        "history": []
                    }
                else:
                    # Update current values
                    profile["knowledge_state"][component_id]["current_value"] = update.get("new_value", 0.5)
                    profile["knowledge_state"][component_id]["confidence"] = update.get("confidence", 0.5)
                    profile["knowledge_state"][component_id]["last_updated"] = interaction.get("timestamp", datetime.now().isoformat())
                
                # Add to history
                history_entry = {
                    "timestamp": interaction.get("timestamp", datetime.now().isoformat()),
                    "value": update.get("new_value", 0.5),
                    "confidence": update.get("confidence", 0.5),
                    "is_correct": interaction.get("is_correct", False)
                }
                profile["knowledge_state"][component_id]["history"].append(history_entry)
            
            # Update metrics
            profile["metrics"] = self._calculate_metrics(profile)
            
            # Update last updated timestamp
            profile["last_updated"] = datetime.now().isoformat()
            
            # Save updated profile
            profile_key = f"student_profile_{student_id}"
            self.state_manager.set(profile_key, profile)
            
            return profile
            
        except Exception as e:
            logger.error(f"Error updating student profile: {str(e)}", exc_info=True)
            return self.get_student_profile(student_id)
    
    def get_student_knowledge_state(self, student_id: str, subject: Optional[str] = None) -> Dict[str, float]:
        """Get a student's current knowledge state.
        
        Args:
            student_id: Student identifier
            subject: Optional subject filter
            
        Returns:
            Dictionary mapping knowledge component IDs to mastery values
        """
        # Get student profile
        profile = self.get_student_profile(student_id)
        
        # Extract knowledge state
        knowledge_state = profile.get("knowledge_state", {})
        result = {}
        
        # Process each component
        for component_id, state in knowledge_state.items():
            # Apply subject filter if specified
            if subject and subject.lower() not in component_id.lower():
                continue
            
            # Extract current value
            result[component_id] = state.get("current_value", 0.5)
        
        return result
    
    def get_learning_recommendations(self, student_id: str, subject: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get learning recommendations for a student.
        
        Args:
            student_id: Student identifier
            subject: Optional subject filter
            
        Returns:
            List of recommendation dictionaries
        """
        # Get knowledge state
        knowledge_state = self.get_student_knowledge_state(student_id, subject)
        
        # Generate recommendations for components below mastery threshold
        recommendations = []
        for component_id, mastery in knowledge_state.items():
            # Skip if mastery is already high
            if mastery >= 0.8:
                continue
            
            # Determine priority based on mastery level
            if mastery < 0.4:
                priority = "high"
            elif mastery < 0.6:
                priority = "medium"
            else:
                priority = "low"
            
            # Format component name for display
            component_name = component_id.replace("kc_", "").replace("_", " ").title()
            
            # Create recommendation
            recommendation = {
                "component_id": component_id,
                "component_name": component_name,
                "mastery": mastery,
                "priority": priority,
                "recommendation": f"Focus on {component_name} to improve mastery"
            }
            
            recommendations.append(recommendation)
        
        # Sort by priority (high > medium > low)
        priority_order = {"high": 0, "medium": 1, "low": 2}
        recommendations.sort(key=lambda r: priority_order.get(r["priority"], 3))
        
        return recommendations
    
    def _calculate_metrics(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate overall metrics for a student profile.
        
        Args:
            profile: Student profile
            
        Returns:
            Updated metrics
        """
        metrics = {
            "overall_mastery": 0.0,
            "strengths": [],
            "areas_for_improvement": []
        }
        
        # Extract knowledge state
        knowledge_state = profile.get("knowledge_state", {})
        
        # Skip if no knowledge state exists
        if not knowledge_state:
            return metrics
        
        # Calculate overall mastery (average of all components)
        values = [state.get("current_value", 0.5) for state in knowledge_state.values()]
        if values:
            metrics["overall_mastery"] = sum(values) / len(values)
        
        # Identify strengths (mastery >= 0.8)
        for component_id, state in knowledge_state.items():
            mastery = state.get("current_value", 0.5)
            component_name = component_id.replace("kc_", "").replace("_", " ").title()
            
            if mastery >= 0.8:
                metrics["strengths"].append({
                    "component_id": component_id,
                    "component_name": component_name,
                    "mastery": mastery
                })
            elif mastery < 0.6:
                metrics["areas_for_improvement"].append({
                    "component_id": component_id,
                    "component_name": component_name,
                    "mastery": mastery
                })
        
        # Sort strengths by mastery (highest first)
        metrics["strengths"].sort(key=lambda s: s["mastery"], reverse=True)
        
        # Sort areas for improvement by mastery (lowest first)
        metrics["areas_for_improvement"].sort(key=lambda a: a["mastery"])
        
        return metrics