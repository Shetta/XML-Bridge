"""
Dataset Management Module.

This module provides functionality for managing music notation datasets,
including creation, updating, and validation of datasets.
"""

import os
import json
import shutil
from typing import Dict, List, Optional, Union
import logging
from datetime import datetime
from pathlib import Path
from lxml import etree

class Dataset:
    """
    Handles dataset operations for music notation files.
    
    This class provides methods for creating, updating, and managing datasets
    of music notation files in various formats.
    
    Attributes:
        base_path (Path): Base path for dataset storage
        logger (logging.Logger): Logger instance
    """
    
    def __init__(self, base_path: Union[str, Path]):
        """
        Initialize Dataset manager.

        Args:
            base_path (Union[str, Path]): Base path for dataset storage
        """
        self.base_path = Path(base_path)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Create base directory if it doesn't exist
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories for different formats
        for format_dir in ['cmme', 'mei', 'json']:
            (self.base_path / format_dir).mkdir(exist_ok=True)

    def validate_mei_content(self, root: etree._Element) -> Dict[str, any]:
        """
        Validate MEI-specific content rules.

        Args:
            root (etree._Element): Root element of MEI document

        Returns:
            Dict[str, Any]: Validation results
        """
        results = {
            "valid": True,
            "errors": [],
            "warnings": []
        }

        try:
            # Check MEI namespace
            if not root.nsmap.get(None) == 'http://www.music-encoding.org/ns/mei':
                results["warnings"].append("Missing or incorrect MEI namespace")

            # Validate required sections
            required_sections = ['music', 'body', 'mdiv', 'score']
            for section in required_sections:
                if not root.find(f'.//{section}'):
                    results["errors"].append(f"Missing required section: {section}")
                    results["valid"] = False

            # Validate notes
            notes = root.findall('.//note')
            for i, note in enumerate(notes):
                # Check required attributes
                required_attrs = ['pname', 'dur']
                for attr in required_attrs:
                    if attr not in note.attrib:
                        results["errors"].append(f"Note {i+1}: Missing required attribute '{attr}'")
                        results["valid"] = False

                # Validate pitch name
                pname = note.get('pname')
                if pname and not pname in 'A B C D E F G':
                    results["errors"].append(f"Note {i+1}: Invalid pitch name '{pname}'")
                    results["valid"] = False

                # Validate duration
                dur = note.get('dur')
                if dur and not dur in ['1', '2', '4', '8', '16', '32', '64', 'breve', 'long']:
                    results["errors"].append(f"Note {i+1}: Invalid duration '{dur}'")
                    results["valid"] = False

            return results

        except Exception as e:
            results["valid"] = False
            results["errors"].append(f"Validation error: {str(e)}")
            return results

    def validate_cmme_content(self, root: etree._Element) -> Dict[str, any]:
        """
        Validate CMME-specific content rules.

        Args:
            root (etree._Element): Root element of CMME document

        Returns:
            Dict[str, Any]: Validation results
        """
        results = {
            "valid": True,
            "errors": [],
            "warnings": []
        }

        try:
            # Check root element
            if root.tag != 'cmme':
                results["errors"].append("Root element must be <cmme>")
                results["valid"] = False

            # Validate metadata
            metadata = root.find('metadata')
            if metadata is None:
                results["warnings"].append("Missing metadata section")
            else:
                required_metadata = ['title', 'composer']
                for field in required_metadata:
                    if metadata.find(field) is None:
                        results["warnings"].append(f"Missing metadata field: {field}")

            # Validate notes
            notes = root.findall('.//note')
            for i, note in enumerate(notes):
                # Check required attributes
                required_attrs = ['pitch', 'duration']
                for attr in required_attrs:
                    if attr not in note.attrib:
                        results["errors"].append(f"Note {i+1}: Missing required attribute '{attr}'")
                        results["valid"] = False

                # Validate pitch format
                pitch = note.get('pitch')
                if pitch and not self._is_valid_cmme_pitch(pitch):
                    results["errors"].append(f"Note {i+1}: Invalid pitch format '{pitch}'")
                    results["valid"] = False

            return results

        except Exception as e:
            results["valid"] = False
            results["errors"].append(f"Validation error: {str(e)}")
            return results

    def validate_json_content(self, data: Dict) -> Dict[str, any]:
        """
        Validate JSON content structure.

        Args:
            data (Dict): JSON data to validate

        Returns:
            Dict[str, Any]: Validation results
        """
        results = {
            "valid": True,
            "errors": [],
            "warnings": []
        }

        try:
            # Check basic structure
            if not isinstance(data, dict):
                results["errors"].append("JSON root must be an object")
                results["valid"] = False
                return results

            # Check required sections
            if 'notes' not in data:
                results["errors"].append("Missing required 'notes' array")
                results["valid"] = False
            elif not isinstance(data['notes'], list):
                results["errors"].append("'notes' must be an array")
                results["valid"] = False
            else:
                # Validate each note
                for i, note in enumerate(data['notes']):
                    if not isinstance(note, dict):
                        results["errors"].append(f"Note {i+1} must be an object")
                        results["valid"] = False
                        continue

                    # Check required fields
                    required_fields = ['pitch', 'duration']
                    for field in required_fields:
                        if field not in note:
                            results["errors"].append(f"Note {i+1}: Missing required field '{field}'")
                            results["valid"] = False

            # Check metadata if present
            if 'metadata' in data:
                if not isinstance(data['metadata'], dict):
                    results["errors"].append("'metadata' must be an object")
                    results["valid"] = False

            return results

        except Exception as e:
            results["valid"] = False
            results["errors"].append(f"Validation error: {str(e)}")
            return results

    def _is_valid_cmme_pitch(self, pitch: str) -> bool:
        """
        Validate CMME pitch format.

        Args:
            pitch (str): Pitch to validate

        Returns:
            bool: True if valid, False otherwise
        """
        import re
        # CMME pitch format: letter(A-G), optional accidental(#/b), octave number
        return bool(re.match(r'^[A-G][#b]?[0-9]$', pitch))

    def _validate_file_format(self, content: str, format_type: str) -> bool:
        """
        Validate file content matches expected format.

        Args:
            content (str): File content
            format_type (str): Expected format type

        Returns:
            bool: True if valid, False otherwise
        """
        try:
            if format_type == 'json':
                json.loads(content)
                return True
            elif format_type in ['cmme', 'mei']:
                # Remove any existing XML declaration
                if content.startswith('<?xml'):
                    content = content[content.find('?>')+2:].lstrip()
                
                root = etree.fromstring(content.encode('utf-8'))
                
                if format_type == 'mei':
                    return root.tag == 'mei' or root.tag.endswith('}mei')
                else:  # cmme
                    return root.tag == 'cmme'
                    
            return False
        except Exception:
            return False

    def create_dataset(self, name: str, description: str = "", files: List[Dict] = None, metadata: Optional[Dict] = None) -> Dict:
        """
        Create a new dataset with optional initial files and metadata.

        Args:
            name (str): Dataset name
            description (str): Dataset description
            files (List[Dict]): Optional list of initial files
            metadata (Optional[Dict]): Optional additional metadata

        Returns:
            Dict: Dataset metadata
        """
        dataset_path = self.base_path / name
        if dataset_path.exists():
            raise ValueError(f"Dataset '{name}' already exists")
            
        # Create dataset directory and format subdirectories
        dataset_path.mkdir(parents=True)
        for format_type in ['cmme', 'mei', 'json']:
            (dataset_path / format_type).mkdir(exist_ok=True)
        
        metadata_dict = {
            'name': name,
            'description': description,
            'created': datetime.now().isoformat(),
            'updated': datetime.now().isoformat(),
            'file_count': 0,
            'formats': {
                'cmme': 0,
                'mei': 0,
                'json': 0
            }
        }
        
        # Add additional metadata if provided
        if metadata:
            for key, value in metadata.items():
                if key not in metadata_dict:  # Don't overwrite core metadata
                    metadata_dict[key] = value
        
        # Save initial metadata
        self._save_metadata(dataset_path, metadata_dict)
        
        # Add initial files if provided
        if files:
            self.update_dataset(name, files)
            metadata_dict = self._load_metadata(dataset_path)  # Reload updated metadata
        
        return metadata_dict

    def update_dataset(self, name: str, files: List[Dict], description: Optional[str] = None) -> Dict:
        """Update existing dataset with new files."""
        dataset_path = self.base_path / name
        if not dataset_path.exists():
            raise ValueError(f"Dataset '{name}' does not exist")
            
        metadata = self._load_metadata(dataset_path)
        
        if description is not None:
            metadata['description'] = description
            
        for file_info in files:
            try:
                format_type = file_info['format'].lower()
                if format_type not in ['cmme', 'mei', 'json']:
                    raise ValueError(f"Unsupported format: {format_type}")
                
                content = file_info['content']
                filename = file_info['filename']
                
                # Validate content format
                if not self._validate_file_format(content, format_type):
                    raise ValueError(f"Invalid {format_type.upper()} format")
                
                # Save file
                format_dir = dataset_path / format_type
                format_dir.mkdir(exist_ok=True)
                
                file_path = format_dir / filename
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                    
                metadata['formats'][format_type] += 1
                metadata['file_count'] += 1
                
            except Exception as e:
                self.logger.error(f"Error processing file {file_info.get('filename')}: {str(e)}")
                raise ValueError(f"Error processing file: {str(e)}")
        
        metadata['updated'] = datetime.now().isoformat()
        self._save_metadata(dataset_path, metadata)
        return metadata

    def get_dataset(self, name: str) -> Dict:
        """
        Get dataset information.

        Args:
            name (str): Dataset name

        Returns:
            Dict: Dataset metadata and files

        Raises:
            ValueError: If dataset doesn't exist
        """
        dataset_path = self.base_path / name
        if not dataset_path.exists():
            raise ValueError(f"Dataset '{name}' does not exist")
            
        metadata = self._load_metadata(dataset_path)
        
        # Add file listings
        files = {}
        for format_type in ['cmme', 'mei', 'json']:
            format_dir = dataset_path / format_type
            if format_dir.exists():
                files[format_type] = [f.name for f in format_dir.glob('*')]
                
        metadata['files'] = files
        return metadata

    def list_datasets(self) -> List[Dict]:
        """
        List all available datasets.

        Returns:
            List[Dict]: List of dataset metadata
        """
        datasets = []
        for path in self.base_path.glob('*'):
            if path.is_dir():
                try:
                    metadata = self._load_metadata(path)
                    datasets.append(metadata)
                except Exception as e:
                    self.logger.error(f"Error loading dataset {path.name}: {str(e)}")
                    
        return datasets

    def delete_dataset(self, name: str) -> bool:
        """
        Delete a dataset.

        Args:
            name (str): Dataset name

        Returns:
            bool: True if deleted successfully

        Raises:
            ValueError: If dataset doesn't exist
        """
        dataset_path = self.base_path / name
        if not dataset_path.exists():
            raise ValueError(f"Dataset '{name}' does not exist")
            
        try:
            shutil.rmtree(dataset_path)
            return True
        except Exception as e:
            self.logger.error(f"Error deleting dataset {name}: {str(e)}")
            return False

    def _save_metadata(self, dataset_path: Union[str, Path], metadata: Dict) -> None:
        """Save dataset metadata."""
        if isinstance(dataset_path, str):
            dataset_path = Path(dataset_path)
        with open(dataset_path / 'metadata.json', 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)

    def _load_metadata(self, dataset_path: Union[str, Path]) -> Dict:
        """Load dataset metadata."""
        try:
            if isinstance(dataset_path, str):
                dataset_path = Path(dataset_path)
            with open(dataset_path / 'metadata.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            raise ValueError(f"Error loading dataset metadata: {str(e)}")

    def validate_dataset(self, name: str) -> Dict:
        """
        Validate all files in a dataset.

        Args:
            name (str): Dataset name

        Returns:
            Dict: Validation results

        Raises:
            ValueError: If dataset doesn't exist
        """
        dataset_path = self.base_path / name
        if not dataset_path.exists():
            raise ValueError(f"Dataset '{name}' does not exist")
            
        results = {
            'valid': 0,
            'invalid': 0,
            'errors': []
        }
        
        for format_type in ['cmme', 'mei', 'json']:
            format_dir = dataset_path / format_type
            if format_dir.exists():
                for file_path in format_dir.glob('*'):
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            
                        # Validate based on format
                        if format_type == 'json':
                            json.loads(content)
                        elif format_type in ['cmme', 'mei']:
                            # Use existing validation logic
                            pass
                            
                        results['valid'] += 1
                    except Exception as e:
                        results['invalid'] += 1
                        results['errors'].append({
                            'file': str(file_path),
                            'error': str(e)
                        })
                        
        return results
    
    def _validate_file_format(self, content: str, format_type: str) -> bool:
        """
        Validate file content matches expected format.

        Args:
            content (str): File content
            format_type (str): Expected format type

        Returns:
            bool: True if valid, False otherwise
        """
        try:
            if format_type == 'json':
                json.loads(content)
                return True
            elif format_type in ['cmme', 'mei']:
                # Basic XML validation
                etree.fromstring(content.encode('utf-8'))
                return True
            return False
        except Exception:
            return False
