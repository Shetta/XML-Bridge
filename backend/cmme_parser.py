"""
CMME (Computerized Mensural Music Editing) Parser Module.

This module provides functionality for parsing and validating CMME format music notation.
It maintains compatibility with basic CMME parsing while offering enhanced features.
CMME specializes in early music (pre-1600) notation with support for mensural notation features.

Classes:
    CMMEParser: Main parser class for CMME format handling
"""

from lxml import etree
import traceback
import re
from typing import Dict, List, Optional, Union, Any
from .base import BaseTransformer
import logging


class CMMEParser(BaseTransformer):
    """
    CMME format specific transformer.
    
    Provides both basic CMME parsing functionality and enhanced features
    for complex musical structures in early music notation (pre-1600).
    CMME (Computerized Mensural Music Editing) is specifically designed
    for rendering and encoding mensural notation with features not found 
    in common modern notation.
    """
    
    # Original basic duration mappings
    VALID_DURATIONS_TEXT = {'whole', 'half', 'quarter', 'eighth', 'sixteenth', '32nd', '64th',
                          'maxima', 'longa', 'brevis', 'semibrevis', 'minima', 'semiminima'}
    
    DURATION_MAP = {
        'maxima': 'maxima',      # Early music specific durations
        'longa': 'long',         # Early music specific durations
        'brevis': 'breve',       # Early music specific durations
        'semibrevis': 'whole',   # Early music equivalent to whole note
        'minima': 'half',        # Early music equivalent to half note
        'semiminima': 'quarter', # Early music equivalent to quarter note
        'fusa': 'eighth',        # Early music equivalent to eighth note
        'semifusa': 'sixteenth', # Early music equivalent to sixteenth note
        'whole': '1',
        'half': '2',
        'quarter': '4',
        'eighth': '8',
        'sixteenth': '16',
        '32nd': '32',
        '64th': '64',
        # Reverse mappings
        '1': 'whole',
        '2': 'half',
        '4': 'quarter',
        '8': 'eighth',
        '16': 'sixteenth',
        '32': '32nd',
        '64': '64th',
        'maxima': 'maxima',
        'long': 'longa',
        'breve': 'brevis'
    }
    
    # Enhanced mappings for extended functionality in early music notation
    EXTENDED_DURATION_MAP = {
        'maxima': 'maxima',
        'longa': 'long',
        'brevis': 'breve',
        'semibrevis': 'whole',
        'minima': 'half',
        'semiminima': 'quarter',
        'fusa': 'eighth',
        'semifusa': 'sixteenth',
        'whole': '1',
        'half': '2',
        'quarter': '4',
        'eighth': '8',
        'sixteenth': '16',
        '32nd': '32',
        '64th': '64',
        'dot': '.',
        'double-dot': '..',
        'proportion': 'proportion', # Early music specific - proportional notation
        'mensuration': 'mensuration' # Early music specific - mensuration signs
    }
    
    # Articulation mappings including early music specific notations
    ARTICULATION_MAP = {
        'staccato': 'stacc',
        'accent': 'accent',
        'tenuto': 'ten',
        'marcato': 'marc',
        'ligature': 'lig',     # Early music specific - ligature notation
        'coloration': 'color', # Early music specific - coloration
        'fermata': 'fermata',
        'mordent': 'mord'
    }
    
    # Mensuration signs used in early music notation
    MENSURATION_SIGNS = {
        'C': 'tempus_imperfectum',         # Imperfect time (duple)
        'O': 'tempus_perfectum',           # Perfect time (triple)
        'C.': 'tempus_imperfectum_prolatio_perfecta', # Imperfect time, perfect prolation
        'O.': 'tempus_perfectum_prolatio_perfecta',   # Perfect time, perfect prolation
        'C/': 'tempus_imperfectum_diminutum',        # Diminished imperfect time
        'O/': 'tempus_perfectum_diminutum'           # Diminished perfect time
    }

    def __init__(self, schema_path: Optional[str] = None):
        """
        Initialize CMME Parser.

        Args:
            schema_path (Optional[str]): Path to CMME XML schema file
        """
        super().__init__(schema_path)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.supported_elements = {
            'note', 'rest', 'chord', 'measure', 'staff', 'clef', 
            'key', 'time', 'barline', 'slur', 'tie', 'beam',
            'dynamics', 'ornament', 'articulation', 'lyrics',
            # Early music specific elements
            'ligature', 'mensuration', 'proportion', 'coloration',
            'accidental', 'custos', 'directionSign', 'fermata',
            'editorial', 'critical', 'variant'
        }

    # Original core methods
    def parse(self, xml_string: str) -> List[etree._Element]:
        """
        Parse CMME XML into list of note elements (original method).

        Args:
            xml_string (str): CMME XML content

        Returns:
            List[etree._Element]: List of note elements

        Raises:
            ValueError: If parsing fails or no notes found
        """
        try:
            root = etree.fromstring(xml_string)
            notes = root.findall('.//note')
            if not notes:
                raise ValueError("No <note> elements found")
            return notes
        except etree.ParseError as e:
            raise ValueError(f"Parse error: {str(e)}")

    def validate(self, xml_string: str) -> None:
        """Validate CMME XML content."""
        try:
            # Remove any existing XML declaration
            if xml_string.startswith('<?xml'):
                xml_string = xml_string[xml_string.find('?>')+2:].lstrip()
                
            root = etree.fromstring(xml_string.encode('utf-8'))
            
            if root.tag != 'cmme':
                raise ValueError("Root element must be <cmme>")
                
            self._validate_notes(root)
            self._validate_metadata(root)
            
        except etree.ParseError as e:
            raise ValueError(f"Invalid CMME XML: {str(e)}")

    def _validate_metadata(self, root: etree._Element) -> None:
        """
        Validates metadata section if present (original method).

        Args:
            root (etree._Element): Root element to validate

        Raises:
            ValueError: If required metadata is missing
        """
        metadata = root.find('metadata')
        if metadata is not None:
            required_fields = {'title', 'composer'}
            found_fields = {child.tag for child in metadata}
            missing_fields = required_fields - found_fields
            if missing_fields:
                raise ValueError(
                    f"Missing required metadata fields: {', '.join(missing_fields)}"
                )

    def _validate_notes(self, root: etree._Element) -> None:
        """
        Validates note elements, including early music specific features.

        Args:
            root (etree._Element): Root element containing notes

        Raises:
            ValueError: If note validation fails
        """
        notes = root.findall('.//note')
        if not notes:
            raise ValueError("No <note> elements found")
        
        for i, note in enumerate(notes):
            pitch = note.get('pitch')
            duration = note.get('duration')
            
            if not pitch or not duration:
                raise ValueError(f"Note {i}: Missing required attributes (pitch, duration)")
            
            # Validate pitch format with special handling for early music notation
            # Standard format (e.g., "C4", "D#3") or Early music format (e.g., "C.4" for musica ficta)
            if not (re.match(r'^[A-G][#b\.]?[0-9]$', pitch) or
                    # Handle pitched mensural notation (letter-based pitch with no octave)
                    re.match(r'^[A-G][#b\.]?$', pitch)):
                raise ValueError(f"Note {i}: Invalid pitch format: {pitch}")
            
            # Validate duration with expanded options for early music notation
            if duration not in self.VALID_DURATIONS_TEXT:
                raise ValueError(f"Note {i}: Invalid duration: {duration}")
            
            # Check for ligature notation (specific to early music)
            if note.find('ligature') is not None:
                # Validate ligature attributes
                ligature = note.find('ligature')
                position = ligature.get('position')
                if position and position not in ('start', 'middle', 'end'):
                    raise ValueError(f"Note {i}: Invalid ligature position: {position}")
            
            # Check for mensuration (specific to early music)
            if note.find('mensuration') is not None:
                mensuration = note.find('mensuration')
                sign = mensuration.get('sign')
                if sign and sign not in self.MENSURATION_SIGNS:
                    raise ValueError(f"Note {i}: Invalid mensuration sign: {sign}")

    def extract_metadata(self, root: etree._Element) -> Dict:
        """
        Extracts metadata from CMME XML (original method).

        Args:
            root (etree._Element): Root element containing metadata

        Returns:
            Dict: Extracted metadata
        """
        metadata = {}
        metadata_elem = root.find('metadata')
        if metadata_elem is not None:
            for elem in metadata_elem:
                metadata[elem.tag] = elem.text
        return metadata

    def create_note(self, pitch: str, duration: str) -> etree._Element:
        """
        Creates a validated CMME note element with support for early music notation.

        Args:
            pitch (str): The pitch value (e.g., "C4", "D#3" or early music specific "C.4")
            duration (str): The duration value (including early music values)

        Returns:
            etree._Element: Created note element

        Raises:
            ValueError: If pitch or duration is invalid
        """
        # Validate pitch with support for early music notation
        if not (re.match(r'^[A-G][#b\.]?[0-9]$', pitch) or re.match(r'^[A-G][#b\.]?$', pitch)):
            raise ValueError(f"Invalid pitch format: {pitch}")
            
        if duration not in self.VALID_DURATIONS_TEXT:
            raise ValueError(f"Invalid duration: {duration}")
            
        note = etree.Element('note')
        note.set('pitch', pitch)
        note.set('duration', duration)
        return note
        
    def create_mensural_note(self, pitch: str, duration: str, 
                           ligature: Optional[str] = None,
                           mensuration: Optional[str] = None,
                           coloration: bool = False) -> etree._Element:
        """
        Creates a mensural notation note element with early music specific features.

        Args:
            pitch (str): The pitch value
            duration (str): The duration value using mensural terminology
            ligature (Optional[str]): Ligature position ('start', 'middle', 'end')
            mensuration (Optional[str]): Mensuration sign key from MENSURATION_SIGNS
            coloration (bool): Whether the note uses coloration

        Returns:
            etree._Element: Created mensural note element

        Raises:
            ValueError: If parameters are invalid
        """
        # Create base note
        note = self.create_note(pitch, duration)
        
        # Add mensural notation specific features
        if ligature:
            if ligature not in ('start', 'middle', 'end'):
                raise ValueError(f"Invalid ligature position: {ligature}")
            lig_elem = etree.SubElement(note, 'ligature')
            lig_elem.set('position', ligature)
        
        if mensuration:
            if mensuration not in self.MENSURATION_SIGNS:
                raise ValueError(f"Invalid mensuration sign: {mensuration}")
            mens_elem = etree.SubElement(note, 'mensuration')
            mens_elem.set('sign', mensuration)
        
        if coloration:
            color_elem = etree.SubElement(note, 'coloration')
            color_elem.set('type', 'blackened')
            
        return note

    # Enhanced methods for extended functionality
    def parse_extended(self, xml_string: str) -> Dict[str, Any]:
        """
        Parse CMME XML with enhanced features.

        Args:
            xml_string (str): CMME XML content

        Returns:
            Dict[str, Any]: Complete musical data structure

        Raises:
            ValueError: If parsing fails
        """
        try:
            root = etree.fromstring(xml_string)
            return {
                'metadata': self.extract_metadata(root),
                'parts': self._parse_parts(root),
                'directives': self._parse_directives(root)
            }
        except Exception as e:
            self.logger.error(f"Enhanced parsing failed: {str(e)}")
            raise ValueError(f"Enhanced parsing failed: {str(e)}")

    def _parse_parts(self, root: etree._Element) -> List[Dict[str, Any]]:
        """
        Parse all parts/staves from the CMME document.

        Args:
            root (etree._Element): Root element

        Returns:
            List[Dict[str, Any]]: List of parsed parts
        """
        parts = []
        for staff in root.findall('.//staff'):
            part_data = {
                'id': staff.get('id', ''),
                'name': staff.get('name', ''),
                'measures': self._parse_measures(staff)
            }
            parts.append(part_data)
        return parts

    def _parse_measures(self, staff: etree._Element) -> List[Dict[str, Any]]:
        """
        Parse measures in a staff.

        Args:
            staff (etree._Element): Staff element

        Returns:
            List[Dict[str, Any]]: List of parsed measures
        """
        measures = []
        for measure in staff.findall('measure'):
            measure_data = {
                'number': measure.get('n', ''),
                'contents': self._parse_measure_contents(measure)
            }
            measures.append(measure_data)
        return measures

    def _parse_measure_contents(self, measure: etree._Element) -> List[Dict[str, Any]]:
        """
        Parse contents of a measure.

        Args:
            measure (etree._Element): Measure element

        Returns:
            List[Dict[str, Any]]: List of parsed musical elements
        """
        contents = []
        for elem in measure:
            if elem.tag == 'note':
                contents.append({
                    'type': 'note',
                    'attributes': self._parse_note_attributes(elem)
                })
            elif elem.tag == 'rest':
                contents.append({
                    'type': 'rest',
                    'duration': elem.get('duration')
                })
            elif elem.tag == 'chord':
                contents.append({
                    'type': 'chord',
                    'notes': [self._parse_note_attributes(note) 
                             for note in elem.findall('note')]
                })
        return contents

    def _parse_note_attributes(self, note: etree._Element) -> Dict[str, Any]:
        """
        Parse attributes of a note element with support for early music notation features.

        Args:
            note (etree._Element): Note element

        Returns:
            Dict[str, Any]: Parsed note attributes
        """
        attrs = {
            'pitch': note.get('pitch'),
            'duration': note.get('duration')
        }
        
        # Optional attributes
        optional_attrs = ['octave', 'accidental', 'stem-direction']
        for attr in optional_attrs:
            if attr in note.attrib:
                attrs[attr] = note.get(attr)
        
        # Articulations
        articulations = note.findall('articulation')
        if articulations:
            attrs['articulations'] = [
                art.get('type') for art in articulations
            ]
        
        # Early music specific features
        
        # Ligatures (connecting multiple notes in early music)
        ligature = note.find('ligature')
        if ligature is not None:
            attrs['ligature'] = {
                'position': ligature.get('position', 'middle'),
                'form': ligature.get('form', 'recta')  # recta or obliqua
            }
        
        # Mensuration signs (time signatures in early music)
        mensuration = note.find('mensuration')
        if mensuration is not None:
            sign = mensuration.get('sign')
            attrs['mensuration'] = {
                'sign': sign,
                'meaning': self.MENSURATION_SIGNS.get(sign, 'unknown')
            }
        
        # Coloration (note coloring indicating rhythmic alterations)
        coloration = note.find('coloration')
        if coloration is not None:
            attrs['coloration'] = coloration.get('type', 'blackened')
        
        # Musica ficta (accidentals above the staff)
        if 'ficta' in note.attrib or note.find('ficta') is not None:
            attrs['ficta'] = note.get('ficta') or note.find('ficta').get('type')
        
        # Editorial markings (scholarly additions)
        editorial = note.find('editorial')
        if editorial is not None:
            attrs['editorial'] = {
                'type': editorial.get('type', 'addition'),
                'source': editorial.get('source'),
                'certainty': editorial.get('certainty')
            }
            
        return attrs

    def _parse_directives(self, root: etree._Element) -> List[Dict[str, str]]:
        """
        Parse musical directives.

        Args:
            root (etree._Element): Root element

        Returns:
            List[Dict[str, str]]: List of parsed directives
        """
        directives = []
        for directive in root.findall('.//directive'):
            directives.append({
                'type': directive.get('type', ''),
                'text': directive.text or '',
                'placement': directive.get('placement', '')
            })
        return directives