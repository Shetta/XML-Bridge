"""
Interactive Component Module.

This module provides interactive tools for handling ambiguous conversions
and cases requiring user input during the conversion process.
"""

from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass
from enum import Enum
import json
import logging
from datetime import datetime
import os
from pathlib import Path
import threading
from queue import Queue
import uuid

class DecisionType(Enum):
    """Types of decisions that might be needed during conversion."""
    ATTRIBUTE_MAPPING = "attribute_mapping"
    STRUCTURE_CHOICE = "structure_choice"
    METADATA_RESOLUTION = "metadata_resolution"
    FORMAT_SPECIFIC = "format_specific"
    AMBIGUOUS_NOTATION = "ambiguous_notation"
    MISSING_INFORMATION = "missing_information"

@dataclass
class ConversionDecision:
    """Represents a decision point in the conversion process."""
    id: str
    type: DecisionType
    context: str
    options: List[Any]
    description: str
    default_option: Optional[Any] = None
    impact: str = ""
    timestamp: str = ""
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
        if self.metadata is None:
            self.metadata = {}

@dataclass
class DecisionResult:
    """Result of a conversion decision."""
    decision_id: str
    choice: Any
    timestamp: str
    user_id: Optional[str] = None
    notes: Optional[str] = None

class ConversionSession:
    """Represents an interactive conversion session."""
    def __init__(self, session_id: str, source_format: str, target_format: str):
        self.session_id = session_id
        self.source_format = source_format
        self.target_format = target_format
        self.decisions: List[ConversionDecision] = []
        self.results: List[DecisionResult] = []
        self.status = "pending"
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at
        self.metadata: Dict[str, Any] = {}

class InteractiveHandler:
    """
    Handles interactive decisions during conversion process.
    """

    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize the interactive handler.

        Args:
            storage_path: Optional path for storing decision history
        """
        self.logger = logging.getLogger(__name__)
        self.storage_path = Path(storage_path) if storage_path else None
        self.decision_handlers: Dict[DecisionType, Callable] = {}
        self.user_preferences: Dict[str, Any] = {}
        self.active_sessions: Dict[str, ConversionSession] = {}
        self.decision_queue: Queue = Queue()
        self.results_queue: Queue = Queue()
        
        # Initialize storage
        if self.storage_path:
            self.storage_path.mkdir(parents=True, exist_ok=True)
            self._load_preferences()
            
        # Start background worker
        self._start_background_worker()

    def register_decision_handler(self, decision_type: DecisionType, 
                                handler: Callable):
        """Register a handler for a specific type of decision."""
        self.decision_handlers[decision_type] = handler
        self.logger.info(f"Registered handler for {decision_type.value}")

    def create_session(self, source_format: str, target_format: str) -> str:
        """Create a new conversion session."""
        session_id = str(uuid.uuid4())
        session = ConversionSession(session_id, source_format, target_format)
        self.active_sessions[session_id] = session
        return session_id

    def add_decision(self, session_id: str, decision: ConversionDecision):
        """Add a decision to a session."""
        if session_id not in self.active_sessions:
            raise ValueError(f"Invalid session ID: {session_id}")
            
        session = self.active_sessions[session_id]
        session.decisions.append(decision)
        session.updated_at = datetime.now().isoformat()
        
        # Check for stored preferences
        if self._has_stored_preference(decision):
            self._apply_stored_preference(session_id, decision)
        else:
            self.decision_queue.put((session_id, decision))

    def resolve_decision(self, session_id: str, decision_id: str, 
                        choice: Any, user_id: Optional[str] = None,
                        notes: Optional[str] = None) -> Any:
        """
        Resolve a decision with user's choice.

        Args:
            session_id: Session identifier
            decision_id: Decision identifier
            choice: User's chosen option
            user_id: Optional user identifier
            notes: Optional notes about the decision

        Returns:
            Any: Result of the decision resolution
        """
        try:
            session = self.active_sessions[session_id]
            decision = next(d for d in session.decisions if d.id == decision_id)
            
            result = DecisionResult(
                decision_id=decision_id,
                choice=choice,
                timestamp=datetime.now().isoformat(),
                user_id=user_id,
                notes=notes
            )
            
            session.results.append(result)
            session.updated_at = datetime.now().isoformat()
            
            # Store preference if appropriate
            self._store_preference(decision, choice)
            
            # Process the decision
            handler = self.decision_handlers.get(decision.type)
            if handler:
                processed_result = handler(decision, choice)
                self.results_queue.put((session_id, decision_id, processed_result))
                return processed_result
            else:
                raise ValueError(f"No handler for decision type: {decision.type}")
                
        except Exception as e:
            self.logger.error(f"Error resolving decision: {str(e)}")
            raise

    def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """Get current status of a conversion session."""
        if session_id not in self.active_sessions:
            raise ValueError(f"Invalid session ID: {session_id}")
            
        session = self.active_sessions[session_id]
        pending_decisions = [d for d in session.decisions 
                           if not any(r.decision_id == d.id for r in session.results)]
        
        return {
            "session_id": session_id,
            "status": session.status,
            "source_format": session.source_format,
            "target_format": session.target_format,
            "total_decisions": len(session.decisions),
            "resolved_decisions": len(session.results),
            "pending_decisions": len(pending_decisions),
            "created_at": session.created_at,
            "updated_at": session.updated_at
        }

    def _start_background_worker(self):
        """Start background worker for processing decisions."""
        def worker():
            while True:
                try:
                    session_id, decision = self.decision_queue.get()
                    if self._has_stored_preference(decision):
                        self._apply_stored_preference(session_id, decision)
                    self.decision_queue.task_done()
                except Exception as e:
                    self.logger.error(f"Error in background worker: {str(e)}")
                    
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def _store_preference(self, decision: ConversionDecision, choice: Any):
        """Store user's preference for similar future decisions."""
        if not self._should_store_preference(decision):
            return
            
        key = self._get_preference_key(decision)
        self.user_preferences[key] = {
            "choice": choice,
            "timestamp": datetime.now().isoformat(),
            "context": decision.context
        }
        
        if self.storage_path:
            self._save_preferences()

    def _has_stored_preference(self, decision: ConversionDecision) -> bool:
        """Check if there's a stored preference for this decision."""
        return self._get_preference_key(decision) in self.user_preferences

    def _apply_stored_preference(self, session_id: str, 
                               decision: ConversionDecision):
        """Apply stored preference to a decision."""
        key = self._get_preference_key(decision)
        if key in self.user_preferences:
            stored = self.user_preferences[key]
            self.resolve_decision(
                session_id,
                decision.id,
                stored["choice"],
                user_id="system",
                notes="Applied stored preference"
            )

    def _get_preference_key(self, decision: ConversionDecision) -> str:
        """Generate a key for storing preferences."""
        return f"{decision.type.value}:{decision.context}"

    def _should_store_preference(self, decision: ConversionDecision) -> bool:
        """Determine if a preference should be stored."""
        # Add logic for determining which decisions should have preferences stored
        return True

    def _save_preferences(self):
        """Save user preferences to file."""
        if not self.storage_path:
            return
            
        try:
            prefs_file = self.storage_path / "preferences.json"
            with open(prefs_file, 'w') as f:
                json.dump(self.user_preferences, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving preferences: {str(e)}")

    def _load_preferences(self):
        """Load user preferences from file."""
        if not self.storage_path:
            return
            
        try:
            prefs_file = self.storage_path / "preferences.json"
            if prefs_file.exists():
                with open(prefs_file, 'r') as f:
                    self.user_preferences = json.load(f)
        except Exception as e:
            self.logger.error(f"Error loading preferences: {str(e)}")

class InteractiveConverter:
    """
    Handles interactive conversion process.
    """

    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize the interactive converter.

        Args:
            storage_path: Optional path for storing conversion history
        """
        self.handler = InteractiveHandler(storage_path)
        self.logger = logging.getLogger(__name__)
        self._register_default_handlers()

    def start_conversion(self, source_content: str, source_format: str,
                        target_format: str) -> Dict[str, Any]:
        """
        Start an interactive conversion process.

        Args:
            source_content: Content to convert
            source_format: Source format
            target_format: Target format

        Returns:
            Dict[str, Any]: Session information
        """
        try:
            # Create new session
            session_id = self.handler.create_session(source_format, target_format)
            
            # Analyze conversion requirements
            decisions = self._analyze_conversion_needs(
                source_content, source_format, target_format
            )
            
            # Add decisions to session
            for decision in decisions:
                self.handler.add_decision(session_id, decision)
            
            return {
                "session_id": session_id,
                "status": "initialized",
                "pending_decisions": len(decisions)
            }
            
        except Exception as e:
            self.logger.error(f"Error starting conversion: {str(e)}")
            raise

    def get_next_decision(self, session_id: str) -> Optional[ConversionDecision]:
        """Get next pending decision for a session."""
        status = self.handler.get_session_status(session_id)
        if status["pending_decisions"] > 0:
            session = self.handler.active_sessions[session_id]
            pending = [d for d in session.decisions 
                      if not any(r.decision_id == d.id for r in session.results)]
            return pending[0] if pending else None
        return None

    def resolve_decision(self, session_id: str, decision_id: str,
                        choice: Any) -> Dict[str, Any]:
        """
        Resolve a conversion decision.

        Args:
            session_id: Session identifier
            decision_id: Decision identifier
            choice: Chosen option

        Returns:
            Dict[str, Any]: Updated session status
        """
        try:
            result = self.handler.resolve_decision(session_id, decision_id, choice)
            status = self.handler.get_session_status(session_id)
            
            return {
                "status": status,
                "result": result,
                "next_decision": self.get_next_decision(session_id)
            }
            
        except Exception as e:
            self.logger.error(f"Error resolving decision: {str(e)}")
            raise

    def _register_default_handlers(self):
        """Register default decision handlers."""
        self.handler.register_decision_handler(
            DecisionType.ATTRIBUTE_MAPPING,
            self._handle_attribute_mapping
        )
        self.handler.register_decision_handler(
            DecisionType.STRUCTURE_CHOICE,
            self._handle_structure_choice
        )
        self.handler.register_decision_handler(
            DecisionType.METADATA_RESOLUTION,
            self._handle_metadata_resolution
        )
        self.handler.register_decision_handler(
            DecisionType.FORMAT_SPECIFIC,
            self._handle_format_specific
        )
        self.handler.register_decision_handler(
            DecisionType.AMBIGUOUS_NOTATION,
            self._handle_ambiguous_notation
        )
        self.handler.register_decision_handler(
            DecisionType.MISSING_INFORMATION,
            self._handle_missing_information
        )

    def _analyze_conversion_needs(self, content: str, source_format: str,
                                target_format: str) -> List[ConversionDecision]:
        """
        Analyze content and identify needed decisions.

        Args:
            content: Source content
            source_format: Source format
            target_format: Target format

        Returns:
            List[ConversionDecision]: List of required decisions
        """
        decisions = []
        
        # Analyze structure
        structural_issues = self._analyze_structural_issues(
            content, source_format, target_format
        )
        for issue in structural_issues:
            decisions.append(ConversionDecision(
                id=str(uuid.uuid4()),
                type=DecisionType.STRUCTURE_CHOICE,
                context=issue["context"],
                options=issue["options"],
                description=issue["description"],
                impact=issue.get("impact", ""),
                metadata={"issue_type": "structural"}
            ))
        
        # Analyze attributes
        attribute_issues = self._analyze_attribute_issues(
            content, source_format, target_format
        )
        for issue in attribute_issues:
            decisions.append(ConversionDecision(
                id=str(uuid.uuid4()),
                type=DecisionType.ATTRIBUTE_MAPPING,
                context=issue["context"],
                options=issue["options"],
                description=issue["description"],
                impact=issue.get("impact", ""),
                metadata={"issue_type": "attribute"}
            ))
        
        return decisions

    def _analyze_structural_issues(self, content: str, source_format: str,
                                 target_format: str) -> List[Dict[str, Any]]:
        """Analyze structural conversion issues."""
        # Implementation for structural analysis
        return []

    def _analyze_attribute_issues(self, content: str, source_format: str,
                                target_format: str) -> List[Dict[str, Any]]:
        """Analyze attribute conversion issues."""
        # Implementation for attribute analysis
        return []

    def _handle_attribute_mapping(self, decision: ConversionDecision,
                                choice: Any) -> Any:
        """Handle attribute mapping decisions."""
        # Implementation for attribute mapping
        return choice

    def _handle_structure_choice(self, decision: ConversionDecision,
                               choice: Any) -> Any:
        """Handle structural choice decisions."""
        # Implementation for structure choices
        return choice

    def _handle_metadata_resolution(self, decision: ConversionDecision,
                                  choice: Any) -> Any:
        """Handle metadata resolution decisions."""
        # Implementation for metadata resolution
        return choice

    def _handle_format_specific(self, decision: ConversionDecision,
                              choice: Any) -> Any:
        """Handle format-specific decisions."""
        # Implementation for format-specific handling
        return choice

    def _handle_ambiguous_notation(self, decision: ConversionDecision,
                                 choice: Any) -> Any:
        """Handle ambiguous notation decisions."""
        # Implementation for ambiguous notation handling
        return choice

    def _handle_missing_information(self, decision: ConversionDecision,
                                  choice: Any) -> Any:
        """Handle missing information decisions."""
        # Implementation for missing information handling
        return choice