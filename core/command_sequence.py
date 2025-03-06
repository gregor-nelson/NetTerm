"""
Command Sequence module for the Serial Monitor application.
Provides functionality to record, save, and play back sequences of commands.
"""
import json
from typing import List, Dict, Any, Optional

class CommandSequence:
    """Represents a sequence of commands that can be sent to a serial device."""
    
    def __init__(self, name: str, commands: List[Dict[str, Any]]):
        """
        Initialize a command sequence.
        
        Args:
            name: Name of the sequence
            commands: List of command dictionaries, each containing:
                      - 'command': The command string
                      - 'delay': Delay in ms before next command
                      - 'wait_for_prompt': Whether to wait for a prompt before next command
                      - 'use_termination': (optional) Override auto-termination setting
        """
        self.name = name
        self.commands = commands
        self.current_index = 0
        
    def reset(self):
        """Reset the sequence to the beginning."""
        self.current_index = 0
        
    def get_next_command(self) -> Optional[Dict[str, Any]]:
        """
        Get the next command in the sequence.
        
        Returns:
            Command dictionary or None if at the end of the sequence
        """
        if self.current_index >= len(self.commands):
            return None
            
        command = self.commands[self.current_index]
        self.current_index += 1
        return command
        
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the sequence to a dictionary for serialization.
        
        Returns:
            Dictionary representation of the sequence
        """
        return {
            'name': self.name,
            'commands': self.commands
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CommandSequence':
        """
        Create a sequence from a dictionary.
        
        Args:
            data: Dictionary representation of the sequence
            
        Returns:
            CommandSequence instance
        """
        return cls(
            name=data['name'],
            commands=data['commands']
        )