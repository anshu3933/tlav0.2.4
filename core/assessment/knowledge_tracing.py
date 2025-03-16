# core/assessment/knowledge_tracing.py

import math
from typing import Dict, Any, Optional

class BayesianKnowledgeTracer:
    """Bayesian Knowledge Tracing for estimating student knowledge state."""
    
    def __init__(self, slip_prob: float = 0.1, guess_prob: float = 0.2):
        """Initialize the knowledge tracer.
        
        Args:
            slip_prob: Probability of slipping (answering incorrectly despite knowing)
            guess_prob: Probability of guessing (answering correctly despite not knowing)
        """
        self.slip_prob = max(0.01, min(0.5, slip_prob))  # Constrain between 0.01 and 0.5
        self.guess_prob = max(0.01, min(0.5, guess_prob))  # Constrain between 0.01 and 0.5
    
    def update_knowledge(self, prior: float, is_correct: bool, 
                         difficulty: Optional[float] = None) -> Dict[str, float]:
        """Update knowledge state using Bayesian update.
        
        Args:
            prior: Prior probability of knowing (0 to 1)
            is_correct: Whether the response was correct
            difficulty: Optional question difficulty to adjust slip/guess probabilities
            
        Returns:
            Updated knowledge state with value and confidence
        """
        # Validate inputs
        prior = max(0.01, min(0.99, prior))  # Ensure prior is between 0.01 and 0.99
        
        # Adjust slip and guess probabilities based on difficulty if provided
        slip = self.slip_prob
        guess = self.guess_prob
        
        if difficulty is not None:
            difficulty = max(0.0, min(1.0, difficulty))  # Ensure difficulty is between 0 and 1
            slip = self.slip_prob * (0.5 + 0.5 * difficulty)  # Higher difficulty = higher slip probability
            guess = self.guess_prob * (1.0 - 0.5 * difficulty)  # Higher difficulty = lower guess probability
        
        # Calculate the posterior probability using Bayes' rule
        if is_correct:
            # P(known | correct) = P(correct | known) * P(known) / P(correct)
            numerator = (1 - slip) * prior
            denominator = (1 - slip) * prior + guess * (1 - prior)
        else:
            # P(known | incorrect) = P(incorrect | known) * P(known) / P(incorrect)
            numerator = slip * prior
            denominator = slip * prior + (1 - guess) * (1 - prior)
        
        # Avoid division by zero
        posterior = numerator / max(denominator, 0.001)
        
        # Ensure posterior is between 0.01 and 0.99
        posterior = max(0.01, min(0.99, posterior))
        
        # Calculate confidence based on consistency of evidence
        # Confidence increases when predictions match outcomes
        evidence_strength = 0.1  # Base evidence strength
        if (prior > 0.5 and is_correct) or (prior < 0.5 and not is_correct):
            # Outcome matches prediction, increase confidence
            confidence = min(1.0, prior + evidence_strength * (1 - prior))
        else:
            # Outcome contradicts prediction, decrease confidence
            confidence = max(0.5, prior - evidence_strength)
        
        return {
            "value": posterior,
            "confidence": confidence
        }