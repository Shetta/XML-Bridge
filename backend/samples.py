"""
Sample Datasets Module.

This module provides sample data for testing and demonstration purposes,
including edge cases and complex musical structures.
"""

from typing import Dict, List, Optional, Union, Any
import os
import json
import shutil
from pathlib import Path
from datetime import datetime
import logging
from lxml import etree

class SampleDatasets:
    """
    Manages sample datasets for testing and demonstration.
    """

    def __init__(self, base_path: str):
        """
        Initialize the sample datasets manager.

        Args:
            base_path: Base directory for sample storage
        """
        self.base_path = Path(base_path)
        self.samples_path = self.base_path / 'samples'
        self.logger = logging.getLogger(__name__)
        
        # Initialize directory structure
        self._initialize_directories()
        
        # Sample categories and their descriptions
        self.categories = {
            'basic': {
                'description': 'Basic examples for common use cases',
                'path': self.samples_path / 'basic'
            },
            'complex': {
                'description': 'Complex musical structures and advanced features',
                'path': self.samples_path / 'complex'
            },
            'edge_cases': {
                'description': 'Edge cases and unusual scenarios',
                'path': self.samples_path / 'edge_cases'
            },
            'real_world': {
                'description': 'Real-world examples from actual scores',
                'path': self.samples_path / 'real_world'
            }
        }

        # Initialize sample data
        self._initialize_samples()

    def _initialize_directories(self):
        """Create necessary directory structure."""
        self.samples_path.mkdir(parents=True, exist_ok=True)
        
        # Create category directories
        for category in ['basic', 'complex', 'edge_cases', 'real_world']:
            (self.samples_path / category).mkdir(exist_ok=True)
            
        # Create format-specific subdirectories in each category
        for category in self.samples_path.iterdir():
            if category.is_dir():
                (category / 'cmme').mkdir(exist_ok=True)
                (category / 'mei').mkdir(exist_ok=True)
                (category / 'json').mkdir(exist_ok=True)

    def _initialize_samples(self):
        """Initialize sample datasets."""
        try:
            self._create_basic_samples()
            self._create_complex_samples()
            self._create_edge_cases()
            self._create_real_world_samples()
            self.logger.info("Sample datasets initialized successfully")
        except Exception as e:
            self.logger.error(f"Error initializing samples: {str(e)}")
            raise

    def _create_basic_samples(self):
        """Create basic sample files."""
        # Basic CMME example
        basic_cmme = """
        <cmme>
            <metadata>
                <title>Basic Example</title>
                <composer>Test Composer</composer>
                <date>2023</date>
            </metadata>
            <score>
                <staff name="Voice">
                    <clef shape="G" line="2"/>
                    <measure number="1">
                        <note pitch="C4" duration="quarter"/>
                        <note pitch="D4" duration="half"/>
                        <note pitch="E4" duration="quarter"/>
                    </measure>
                </staff>
            </score>
        </cmme>
        """

        # Basic MEI example
        basic_mei = """
        <mei xmlns="http://www.music-encoding.org/ns/mei">
            <meiHead>
                <fileDesc>
                    <titleStmt>
                        <title>Basic Example</title>
                        <composer>Test Composer</composer>
                    </titleStmt>
                    <pubStmt>
                        <date>2023</date>
                    </pubStmt>
                </fileDesc>
            </meiHead>
            <music>
                <body>
                    <mdiv>
                        <score>
                            <scoreDef>
                                <staffGrp>
                                    <staffDef n="1" lines="5" clef.shape="G" clef.line="2"/>
                                </staffGrp>
                            </scoreDef>
                            <section>
                                <measure n="1">
                                    <staff n="1">
                                        <layer n="1">
                                            <note pname="c" oct="4" dur="4"/>
                                            <note pname="d" oct="4" dur="2"/>
                                            <note pname="e" oct="4" dur="4"/>
                                        </layer>
                                    </staff>
                                </measure>
                            </section>
                        </score>
                    </mdiv>
                </body>
            </music>
        </mei>
        """

        # Basic JSON example
        basic_json = {
            "metadata": {
                "title": "Basic Example",
                "composer": "Test Composer",
                "date": "2023"
            },
            "score": {
                "staves": [{
                    "name": "Voice",
                    "clef": {
                        "shape": "G",
                        "line": 2
                    },
                    "measures": [{
                        "number": 1,
                        "notes": [
                            {"pitch": "C4", "duration": "quarter"},
                            {"pitch": "D4", "duration": "half"},
                            {"pitch": "E4", "duration": "quarter"}
                        ]
                    }]
                }]
            }
        }

        self._save_sample('basic', 'basic_example.cmme', basic_cmme)
        self._save_sample('basic', 'basic_example.mei', basic_mei)
        self._save_sample('basic', 'basic_example.json', json.dumps(basic_json, indent=2))

    def _create_complex_samples(self):
        """Create complex sample files with advanced musical features."""
        # Complex CMME example with multiple voices, articulations, and ornaments
        complex_cmme = """
        <cmme>
            <metadata>
                <title>Complex Example</title>
                <composer>Test Composer</composer>
                <date>1500</date>
                <source>Manuscript XYZ</source>
            </metadata>
            <score>
                <staff name="Superius">
                    <clef shape="G" line="2"/>
                    <key signature="1s"/>
                    <time signature="3/4"/>
                    <measure number="1">
                        <note pitch="C4" duration="eighth" stem-direction="up">
                            <articulation type="staccato"/>
                        </note>
                        <note pitch="D4" duration="sixteenth" stem-direction="up">
                            <articulation type="accent"/>
                        </note>
                        <chord>
                            <note pitch="E4" duration="quarter"/>
                            <note pitch="G4" duration="quarter"/>
                        </chord>
                    </measure>
                </staff>
            </score>
        </cmme>
        """

        # Complex MEI example
        complex_mei = """
        <mei xmlns="http://www.music-encoding.org/ns/mei">
            <meiHead>
                <fileDesc>
                    <titleStmt>
                        <title>Complex Example</title>
                        <composer>Test Composer</composer>
                    </titleStmt>
                    <sourceDesc>
                        <source>
                            <titleStmt>
                                <title>Manuscript XYZ</title>
                            </titleStmt>
                            <dating>
                                <date>1500</date>
                            </dating>
                        </source>
                    </sourceDesc>
                </fileDesc>
            </meiHead>
            <music>
                <body>
                    <mdiv>
                        <score>
                            <scoreDef key.sig="1s" meter.count="3" meter.unit="4">
                                <staffGrp>
                                    <staffDef n="1" lines="5" clef.shape="G" clef.line="2"/>
                                </staffGrp>
                            </scoreDef>
                            <section>
                                <measure n="1">
                                    <staff n="1">
                                        <layer n="1">
                                            <note pname="c" oct="4" dur="8" stem.dir="up">
                                                <artic artic="stacc"/>
                                            </note>
                                            <note pname="d" oct="4" dur="16" stem.dir="up">
                                                <artic artic="acc"/>
                                            </note>
                                            <chord dur="4">
                                                <note pname="e" oct="4"/>
                                                <note pname="g" oct="4"/>
                                            </chord>
                                        </layer>
                                    </staff>
                                </measure>
                            </section>
                        </score>
                    </mdiv>
                </body>
            </music>
        </mei>
        """

        self._save_sample('complex', 'complex_example.cmme', complex_cmme)
        self._save_sample('complex', 'complex_example.mei', complex_mei)

    def _create_edge_cases(self):
        """Create edge case samples."""
        edge_cases = {
            'empty_measures.cmme': """
                <cmme>
                    <metadata><title>Empty Measures</title></metadata>
                    <score>
                        <measure number="1"/>
                        <measure number="2"/>
                    </score>
                </cmme>
            """,
            'nested_elements.mei': """
                <mei xmlns="http://www.music-encoding.org/ns/mei">
                    <music>
                        <body>
                            <mdiv>
                                <score>
                                    <section>
                                        <measure>
                                            <staff>
                                                <layer>
                                                    <beam>
                                                        <chord>
                                                            <note pname="c" oct="4" dur="8"/>
                                                            <note pname="e" oct="4" dur="8"/>
                                                        </chord>
                                                    </beam>
                                                </layer>
                                            </staff>
                                        </measure>
                                    </section>
                                </score>
                            </mdiv>
                        </body>
                    </music>
                </mei>
            """,
            'special_characters.cmme': """
                <cmme>
                    <metadata>
                        <title>Special Characters: áéíóú &amp; ñ</title>
                    </metadata>
                    <score>
                        <note pitch="C4" duration="quarter"/>
                    </score>
                </cmme>
            """
        }

        for filename, content in edge_cases.items():
            self._save_sample('edge_cases', filename, content)

    def _create_real_world_samples(self):
        """Create real-world example samples."""
        # Implementation for real-world samples would go here
        # These would typically be loaded from actual musical scores
        pass

    def _save_sample(self, category: str, filename: str, content: str):
        """
        Save a sample file.

        Args:
            category: Sample category
            filename: File name
            content: File content
        """
        format_type = filename.split('.')[-1]
        path = self.categories[category]['path'] / format_type / filename
        
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            self.logger.error(f"Error saving sample {filename}: {str(e)}")
            raise

    def get_sample(self, category: str, filename: str) -> str:
        """
        Retrieve a sample file.

        Args:
            category: Sample category
            filename: File name

        Returns:
            str: File content

        Raises:
            ValueError: If sample not found
        """
        format_type = filename.split('.')[-1]
        path = self.categories[category]['path'] / format_type / filename
        
        if not path.exists():
            raise ValueError(f"Sample not found: {filename}")
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            self.logger.error(f"Error reading sample {filename}: {str(e)}")
            raise

    def list_samples(self) -> Dict[str, Dict[str, Any]]:
        """
        List all available samples by category.

        Returns:
            Dict[str, Dict[str, Any]]: Dictionary of categories and their samples
        """
        samples = {}
        for category, info in self.categories.items():
            samples[category] = {
                'description': info['description'],
                'samples': {}
            }
            
            for format_dir in ['cmme', 'mei', 'json']:
                format_path = info['path'] / format_dir
                if format_path.exists():
                    samples[category]['samples'][format_dir] = [
                        f.name for f in format_path.glob('*')
                    ]
                    
        return samples

    def get_sample_metadata(self, category: str, filename: str) -> Dict[str, Any]:
        """
        Get metadata for a specific sample.

        Args:
            category: Sample category
            filename: File name

        Returns:
            Dict[str, Any]: Sample metadata
        """
        content = self.get_sample(category, filename)
        format_type = filename.split('.')[-1]
        
        try:
            if format_type == 'json':
                data = json.loads(content)
                return data.get('metadata', {})
            else:
                root = etree.fromstring(content.encode('utf-8'))
                if format_type == 'cmme':
                    metadata = root.find('metadata')
                    if metadata is not None:
                        return {child.tag: child.text for child in metadata}
                else:  # mei
                    metadata = {}
                    title = root.find('.//*title')
                    composer = root.find('.//*composer')
                    if title is not None:
                        metadata['title'] = title.text
                    if composer is not None:
                        metadata['composer'] = composer.text
                    return metadata
        except Exception as e:
            self.logger.error(f"Error extracting metadata from {filename}: {str(e)}")
            return {}

    def validate_sample(self, category: str, filename: str) -> bool:
        """
        Validate a sample file.

        Args:
            category: Sample category
            filename: File name

        Returns:
            bool: True if valid, False otherwise
        """
        try:
            content = self.get_sample(category, filename)
            format_type = filename.split('.')[-1]
            
            if format_type == 'json':
                json.loads(content)
            else:
                etree.fromstring(content.encode('utf-8'))
            return True
        except Exception as e:
            self.logger.error(f"Validation failed for {filename}: {str(e)}")
            return False

    def create_test_suite(self) -> List[Dict[str, Any]]:
        """
        Create a test suite from samples.

        Returns:
            List[Dict[str, Any]]: List of test cases
        """
        test_suite = []
        for category, info in self.categories.items():
            for format_dir in ['cmme', 'mei', 'json']:
                format_path = info['path'] / format_dir
                if format_path.exists():
                    for file_path in format_path.glob('*'):
                        test_suite.append({
                            'category': category,
                            'format': format_dir,
                            'filename': file_path.name,
                            'content': self.get_sample(category, file_path.name),
                            'metadata': self.get_sample_metadata(category, file_path.name)
                        })
        return test_suite