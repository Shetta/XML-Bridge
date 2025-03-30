"""
Music Encoding Initiative (MEI) Parser Module.

This module provides functionality for parsing and validating MEI format music notation.
It handles complex musical structures including notes, measures, articulations, and metadata.

Classes:
    MEIParser: Main parser class for MEI format handling
"""

from lxml import etree
import traceback
import re
from typing import Dict, List, Optional, Union, Any
from .base import BaseTransformer
import logging


class MEIParser(BaseTransformer):
    """
    Parser for Music Encoding Initiative (MEI) format.
    
    This class handles parsing, validation, and transformation of MEI format
    music notation files. It supports extended musical elements and attributes.
    
    Attributes:
        NAMESPACE (str): MEI XML namespace
        DURATION_MAP (dict): Mapping between duration representations
        ARTICULATION_MAP (dict): Mapping between articulation types
        supported_elements (set): Set of supported MEI elements
        logger (logging.Logger): Logger for this class
    """
    
    NAMESPACE = "http://www.music-encoding.org/ns/mei"
    
    DURATION_MAP = {
        'maxima': 'maxima',
        'long': 'long',
        'breve': 'breve',
        '1': 'whole',
        '2': 'half',
        '4': 'quarter',
        '8': 'eighth',
        '16': 'sixteenth',
        '32': '32nd',
        '64': '64th'
    }
    
    ARTICULATION_MAP = {
        'stacc': 'staccato',
        'accent': 'accent',
        'ten': 'tenuto',
        'marc': 'marcato'
    }

    def __init__(self, schema_path: Optional[str] = None):
        """
        Initialize MEI Parser.

        Args:
            schema_path (Optional[str]): Path to MEI XML schema file
        """
        super().__init__(schema_path)
        self.supported_elements = {
            'note', 'rest', 'chord', 'measure', 'staff', 'clef', 
            'keySig', 'meterSig', 'barLine', 'slur', 'tie', 'beam',
            'dynam', 'ornament', 'artic', 'verse'
        }
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def parse(self, xml_string: str) -> List[etree._Element]:
        """
        Parse MEI XML into list of note elements.

        Args:
            xml_string (str): MEI XML content to parse

        Returns:
            List[etree._Element]: List of parsed note elements

        Raises:
            ValueError: If parsing fails or XML is invalid
        """
        try:
            root = etree.fromstring(xml_string)
            # Look for notes with or without namespace
            notes = root.findall('.//mei:note', namespaces={'mei': self.NAMESPACE})
            if not notes:
                notes = root.findall('.//note')
            if not notes:
                raise ValueError("No note elements found")
            return notes
        except etree.ParseError as e:
            self.logger.error(f"Parse error: {str(e)}")
            raise ValueError(f"Parse error: {str(e)}")

    def validate(self, xml_string: str) -> None:
        """Validate MEI XML content."""
        try:
            # Remove any existing XML declaration
            if xml_string.startswith('<?xml'):
                xml_string = xml_string[xml_string.find('?>')+2:].lstrip()
                
            # Remove any existing namespace declarations
            xml_string = re.sub(r'\sxmlns="[^"]*"', '', xml_string)
            
            # Add single namespace declaration if it's MEI
            if xml_string.startswith('<mei'):
                xml_string = xml_string.replace('<mei', '<mei xmlns="http://www.music-encoding.org/ns/mei"', 1)
            
            root = etree.fromstring(xml_string.encode('utf-8'))
            
            # Check root element (with or without namespace)
            if not (root.tag == 'mei' or root.tag.endswith('}mei')):
                raise ValueError("Root element must be <mei>")
                
            # Validate required sections
            required_sections = {'music', 'body', 'mdiv', 'score'}
            found_sections = set()
            
            for elem in root.iter():
                tag = elem.tag.split('}')[-1]  # Remove namespace
                found_sections.add(tag)
            
            missing_sections = required_sections - found_sections
            if missing_sections:
                raise ValueError(f"Missing required sections: {', '.join(missing_sections)}")
                
            if self.schema:
                self.schema.assertValid(root)
                
        except etree.ParseError as e:
            raise ValueError(f"Invalid MEI XML: {str(e)}")

    def _validate_structure(self, root: etree._Element) -> None:
        """
        Validate the structural integrity of MEI document.

        Args:
            root (etree._Element): Root element of MEI document

        Raises:
            ValueError: If structural validation fails
        """
        required_sections = {'music', 'body', 'mdiv', 'score'}
        found_sections = set()
        
        for elem in root.iter():
            tag = elem.tag.replace(f'{{{self.NAMESPACE}}}', '')
            found_sections.add(tag)
            
        missing_sections = required_sections - found_sections
        if missing_sections:
            self.logger.error(f"Missing required sections: {missing_sections}")
            raise ValueError(f"Missing required sections: {', '.join(missing_sections)}")

    def _validate_metadata(self, root: etree._Element) -> None:
        """
        Validate metadata section of MEI document.

        Args:
            root (etree._Element): Root element of MEI document

        Raises:
            ValueError: If metadata validation fails
        """
        meiHead = root.find(f'.//{{{self.NAMESPACE}}}meiHead')
        if meiHead is None:
            self.logger.error("Missing required <meiHead> element")
            raise ValueError("Missing required <meiHead> element")
            
        required_elements = {'fileDesc', 'titleStmt'}
        found_elements = set()
        
        for elem in meiHead.iter():
            tag = elem.tag.replace(f'{{{self.NAMESPACE}}}', '')
            found_elements.add(tag)
            
        missing_elements = required_elements - found_elements
        if missing_elements:
            self.logger.error(f"Missing required metadata elements: {missing_elements}")
            raise ValueError(f"Missing required metadata elements: {', '.join(missing_elements)}")

    def _validate_musical_content(self, root: etree._Element) -> None:
        """
        Validate musical content of MEI document.

        Args:
            root (etree._Element): Root element of MEI document

        Raises:
            ValueError: If musical content validation fails
        """
        notes = root.findall(f'.//{{{self.NAMESPACE}}}note')
        if not notes:
            notes = root.findall('.//note')
        
        if not notes:
            self.logger.error("No note elements found")
            raise ValueError("No note elements found")
        
        for i, note in enumerate(notes):
            self._validate_note(note, i)

    def _validate_note(self, note: etree._Element, index: int) -> None:
        """
        Validate a single note element.

        Args:
            note (etree._Element): Note element to validate
            index (int): Index of the note for error reporting

        Raises:
            ValueError: If note validation fails
        """
        required_attrs = ['pname', 'dur']
        for attr in required_attrs:
            if attr not in note.attrib:
                self.logger.error(f"Note {index}: Missing required attribute '{attr}'")
                raise ValueError(f"Note {index}: Missing required attribute '{attr}'")
        
        pname = note.get('pname')
        if not re.match(r'^[A-G]$', pname):
            self.logger.error(f"Note {index}: Invalid pitch name: {pname}")
            raise ValueError(f"Note {index}: Invalid pitch name: {pname}")
        
        dur = note.get('dur')
        if dur not in self.DURATION_MAP:
            self.logger.error(f"Note {index}: Invalid duration: {dur}")
            raise ValueError(f"Note {index}: Invalid duration: {dur}")

    def extract_metadata(self, root: etree._Element) -> Dict[str, Any]:
        """
        Extract metadata from MEI document.

        Args:
            root (etree._Element): Root element of MEI document

        Returns:
            Dict[str, Any]: Extracted metadata
        """
        metadata = {}
        meiHead = root.find(f'.//{{{self.NAMESPACE}}}meiHead')
        
        if meiHead is not None:
            # Extract title
            title = meiHead.find(f'.//{{{self.NAMESPACE}}}title')
            if title is not None:
                metadata['title'] = title.text
                
            # Extract composer
            composer = meiHead.find(f'.//{{{self.NAMESPACE}}}composer')
            if composer is not None:
                metadata['composer'] = composer.text
                
            # Extract additional metadata
            for elem in meiHead.iter():
                tag = elem.tag.replace(f'{{{self.NAMESPACE}}}', '')
                if tag not in ['meiHead', 'title', 'composer'] and elem.text:
                    metadata[tag] = elem.text
                    
        return metadata

    def create_note(self, pitch: str, duration: str) -> etree._Element:
        """
        Creates a validated MEI note element.

        Args:
            pitch (str): The pitch name (e.g., "C", "D", "E")
            duration (str): The duration value

        Returns:
            etree._Element: Created MEI note element

        Raises:
            ValueError: If pitch or duration is invalid
        """
        if not re.match(r'^[A-G]$', pitch):
            raise ValueError(f"Invalid pitch name: {pitch}")
            
        if duration not in self.DURATION_MAP:
            raise ValueError(f"Invalid duration: {duration}")
            
        note = etree.Element(f'{{{self.NAMESPACE}}}note')
        note.set('pname', pitch)
        note.set('dur', duration)
        return note

    def parse_measure(self, measure: etree._Element) -> Dict[str, Any]:
        """
        Parse a complete MEI measure with all its contents.

        Args:
            measure (etree._Element): Measure element to parse

        Returns:
            Dict[str, Any]: Dictionary containing parsed measure data
        """
        measure_data = {
            'n': measure.get('n', ''),
            'left': measure.get('left', ''),
            'right': measure.get('right', ''),
            'contents': []
        }
        
        for elem in measure:
            tag = elem.tag.replace(f'{{{self.NAMESPACE}}}', '')
            
            if tag == 'note':
                measure_data['contents'].append({
                    'type': 'note',
                    'attributes': self._parse_note_attributes(elem)
                })
            elif tag == 'rest':
                measure_data['contents'].append({
                    'type': 'rest',
                    'attributes': self._parse_rest_attributes(elem)
                })
            elif tag == 'chord':
                chord_notes = []
                for note in elem.findall(f'.//{{{self.NAMESPACE}}}note'):
                    chord_notes.append(self._parse_note_attributes(note))
                measure_data['contents'].append({
                    'type': 'chord',
                    'notes': chord_notes
                })
            elif tag in ['clef', 'keySig', 'meterSig']:
                measure_data['contents'].append({
                    'type': tag,
                    'attributes': dict(elem.attrib)
                })
                
        return measure_data

    def _parse_note_attributes(self, note: etree._Element) -> Dict[str, Any]:
        """
        Parse all attributes from an MEI note element.

        Args:
            note (etree._Element): MEI note element

        Returns:
            Dict[str, Any]: Dictionary of parsed attributes
        """
        attrs = {}
        
        # Core musical attributes
        for attr in ['pname', 'dur', 'oct', 'accid']:
            if attr in note.attrib:
                attrs[attr] = note.get(attr)
        
        # Extended attributes
        if 'stem.dir' in note.attrib:
            attrs['stem_direction'] = note.get('stem.dir')
        if 'artic' in note.attrib:
            attrs['articulations'] = note.get('artic').split()
        
        # Editorial and performance attributes
        if 'resp' in note.attrib:
            attrs['editorial'] = note.get('resp')
        if 'vel' in note.attrib:
            attrs['velocity'] = note.get('vel')
        
        return attrs

    def _parse_rest_attributes(self, rest: etree._Element) -> Dict[str, Any]:
        """
        Parse attributes from an MEI rest element.

        Args:
            rest (etree._Element): MEI rest element

        Returns:
            Dict[str, Any]: Dictionary of parsed attributes
        """
        attrs = {}
        
        if 'dur' in rest.attrib:
            attrs['duration'] = rest.get('dur')
        
        return attrs