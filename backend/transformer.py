"""
Transformer Module.

This module provides the main transformation functionality between different music notation formats.
It handles conversions between CMME, MEI, and JSON formats while preserving metadata and structure.
"""

from lxml import etree
from typing import Dict, List, Optional, Union, Any, Tuple
import re
import json
import logging
import traceback
import os
import uuid
from .cmme_parser import CMMEParser
from .mei_parser import MEIParser
from .json_converter import JSONConverter
from .serializer import Serializer


class Transformer:
    """
    Main transformer for converting between music notation formats.
    
    This class handles all transformations between CMME, MEI, and JSON formats,
    including validation, metadata preservation, and format-specific features.
    
    Attributes:
        cmme_parser (CMMEParser): Parser for CMME format
        mei_parser (MEIParser): Parser for MEI format
        json_converter (JSONConverter): Converter for JSON format
        serializer (Serializer): Data serialization handler
        supported_formats (dict): Dictionary of supported formats and their properties
        logger (logging.Logger): Logger instance for the transformer
    """
    
    # MEI namespace constant
    MEI_NS = "http://www.music-encoding.org/ns/mei"
    MEI_NS_MAP = {"mei": MEI_NS}
    
    def __init__(self, cmme_schema: Optional[str] = None, mei_schema: Optional[str] = None):
        """
        Initialize the transformer with optional schema files.

        Args:
            cmme_schema (Optional[str]): Path to CMME schema file
            mei_schema (Optional[str]): Path to MEI schema file
        """
        self.cmme_parser = CMMEParser(cmme_schema)
        self.mei_parser = MEIParser(mei_schema)
        self.json_converter = JSONConverter()
        self.serializer = Serializer()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Define supported formats and their properties with expanded extensions
        self.supported_formats = {
            'cmme': {
                'extensions': ['.xml', '.cmme'],
                'mime': 'text/xml',
                'parser': self.cmme_parser
            },
            'mei': {
                'extensions': ['.xml', '.mei'],
                'mime': 'text/xml',
                'parser': self.mei_parser
            },
            'json': {
                'extensions': ['.json'],
                'mime': 'application/json',
                'converter': self.json_converter
            }
        }
        
        self.element_mappings = {
            'cmme_to_mei': {
                # Basic music elements
                'note': 'note',
                'rest': 'rest',
                'chord': 'chord',
                'measure': 'measure',
                'staff': 'staff',
                
                # Structural elements
                'clef': 'clef',
                'key': 'keySig',
                'time': 'meterSig',
                'barline': 'barLine',
                'score': 'score',
                'part': 'part',
                
                # Performance markings
                'articulation': 'artic',
                'dynamics': 'dynam',
                'slur': 'slur',
                'tie': 'tie',
                'beam': 'beam',
                'tuplet': 'tuplet',
                'fermata': 'fermata',
                
                # Text elements
                'lyrics': 'verse',
                'text': 'text',
                'direction': 'dir',
                
                # Early music specific
                'ligature': 'ligature',
                'mensuration': 'mensur',
                'coloration': 'note', # MEI uses @colored attribute instead
                'proportion': 'proport',
                'custos': 'custos',
                'accidental': 'accid',
                
                # Editorial elements
                'editorial': 'supplied',
                'variant': 'app',
                'critical': 'annot',
                'metadata': 'meiHead'
            },
            'mei_to_cmme': {
                # Basic music elements
                'note': 'note',
                'rest': 'rest',
                'chord': 'chord',
                'measure': 'measure',
                'staff': 'staff',
                
                # Structural elements
                'clef': 'clef',
                'keySig': 'key',
                'meterSig': 'time',
                'barLine': 'barline',
                'score': 'score',
                'part': 'part',
                
                # Performance markings
                'artic': 'articulation',
                'dynam': 'dynamics',
                'slur': 'slur',
                'tie': 'tie',
                'beam': 'beam',
                'tuplet': 'tuplet',
                'fermata': 'fermata',
                
                # Text elements
                'verse': 'lyrics',
                'text': 'text',
                'dir': 'direction',
                
                # Early music specific
                'ligature': 'ligature',
                'mensur': 'mensuration',
                'proport': 'proportion',
                'custos': 'custos',
                'accid': 'accidental',
                
                # Editorial elements
                'supplied': 'editorial',
                'app': 'variant',
                'annot': 'critical',
                'meiHead': 'metadata'
            }
        }

        # Also update the attribute mappings for more comprehensive coverage
        self.attribute_mappings = {
            'cmme_to_mei': {
                # Pitch and duration attributes
                'pitch': {'pname': lambda v: self._extract_pname(v), 
                        'oct': lambda v: self._extract_octave(v),
                       'accid': lambda v: self._extract_accidental(v)},
                'duration': {'dur': lambda v: self._convert_duration_to_mei(v),
                            'dots': lambda v: self._extract_dots(v)},
                
                # Other common attributes
                'octave': 'oct',
                'accidental': 'accid',
                'stem-direction': 'stem.dir',
                'beam': 'beam',
                'slur': 'slur',
                'tie': 'tie',
                'fermata': 'fermata',
                'id': 'xml:id',
                
                # Early music attributes
                'mensuration': {'mensur.sign': lambda v: self._extract_mensur_sign(v),
                                'mensur.dot': lambda v: self._extract_mensur_dot(v)},
                'coloration': 'colored',
                'ligature-position': 'ligature.form'
            },
            'mei_to_cmme': {
                # Pitch and duration attributes
                'pname': {'pitch': lambda v, oct, accid: self._create_cmme_pitch(v, oct, accid)},
                'oct': 'octave', # Used in _create_cmme_pitch
                'accid': 'accidental', # Used in _create_cmme_pitch
                'dur': {'duration': lambda v: self._convert_duration_to_cmme(v)},
                'dots': 'dot-count',
                
                # Other common attributes
                'stem.dir': 'stem-direction',
                'beam': 'beam',
                'slur': 'slur',
                'tie': 'tie',
                'fermata': 'fermata',
                'xml:id': 'id',
                
                # Early music attributes
                'mensur.sign': {'mensuration': lambda v, dot: self._create_mensuration(v, dot)},
                'mensur.dot': None, # Used in _create_mensuration
                'colored': 'coloration',
                'ligature.form': 'ligature-position'
            }
        }

        # Add special mapping for duration values
        self.duration_mappings = {
            'cmme_to_mei': {
                'maxima': 'maxima',
                'longa': 'long',
                'brevis': 'breve',
                'semibrevis': 'breve',
                'minima': 'long',
                'semiminima': 'breve',
                'whole': '1',
                'half': '2',
                'quarter': '4',
                'eighth': '8',
                'sixteenth': '16',
                '32nd': '32',
                '64th': '64',
                '128th': '128'
            },
            'mei_to_cmme': {
                'maxima': 'maxima',
                'long': 'longa',
                'breve': 'brevis',
                '1': 'whole',
                '2': 'half',
                '4': 'quarter',
                '8': 'eighth',
                '16': 'sixteenth',
                '32': '32nd',
                '64': '64th',
                '128': '128th'
            }
        }

        # Add mapping for articulation values
        self.articulation_mappings = {
            'cmme_to_mei': {
                'staccato': 'stacc',
                'accent': 'acc',
                'tenuto': 'ten',
                'marcato': 'marc',
                'staccatissimo': 'stacciss',
                'spiccato': 'spicc',
                'portato': 'port',
                'legato': 'leg',
                'mordent': 'mord',
                'turn': 'turn',
                'trill': 'trill'
            },
            'mei_to_cmme': {
                'stacc': 'staccato',
                'acc': 'accent',
                'ten': 'tenuto',
                'marc': 'marcato',
                'stacciss': 'staccatissimo',
                'spicc': 'spiccato',
                'port': 'portato',
                'leg': 'legato',
                'mord': 'mordent',
                'turn': 'turn',
                'trill': 'trill'
            }
        }

        # Add mapping for mensuration signs
        self.mensuration_mappings = {
            'C': 'tempus_imperfectum',         # Imperfect time (duple)
            'O': 'tempus_perfectum',           # Perfect time (triple)
            'C.': 'tempus_imperfectum_prolatio_perfecta', # Imperfect time, perfect prolation
            'O.': 'tempus_perfectum_prolatio_perfecta',   # Perfect time, perfect prolation
            'C/': 'tempus_imperfectum_diminutum',        # Diminished imperfect time
            'O/': 'tempus_perfectum_diminutum'           # Diminished perfect time
        }

    def transform(self, data: str, conversion_type: str) -> str:
        """
        Transform data between supported formats with improved structure preservation and error logging.

        Args:
            data (str): Input data to transform
            conversion_type (str): Type of conversion (e.g., 'cmme-to-mei')

        Returns:
            str: Transformed data

        Raises:
            ValueError: If conversion type is invalid or transformation fails
        """
        try:
            source_format, target_format = conversion_type.split('-to-')
            
            if source_format not in self.supported_formats or \
               target_format not in self.supported_formats:
                raise ValueError(f"Unsupported conversion: {conversion_type}")
            
            # Track transformation process for debugging
            self.logger.info(f"Starting transformation from {source_format} to {target_format}")
            
            # Deserialize input data
            deserialized = self.serializer.deserialize(data)
            
            # Initialize tracking structures for data loss analysis
            element_counts_before = {}
            attribute_counts_before = {}
            lost_attributes = {}
            lost_elements = {}
            
            # Count elements in source before conversion for logging purposes
            if source_format in ['cmme', 'mei']:
                try:
                    if isinstance(deserialized, str) and deserialized.strip():
                        # Handle various string preprocessing issues
                        source_content = self._preprocess_xml_content(deserialized)
                        source_root = etree.fromstring(source_content)
                        
                        # Count elements and attributes by type
                        element_counts_before, attribute_counts_before = self._count_elements_and_attributes(source_root)
                        self.logger.info(f"Source element counts: {element_counts_before}")
                        self.logger.info(f"Source attribute counts: {attribute_counts_before}")
                except Exception as e:
                    self.logger.warning(f"Could not count elements in source: {str(e)}")
            
            # Extract metadata before transformation
            metadata = self._extract_metadata_from_content(deserialized, source_format)
            
            # Perform the actual transformation with structure preservation
            result = self._perform_transformation(deserialized, source_format, target_format, metadata)
            
            # Format and normalize the result
            result = self._format_result(result, target_format, metadata)
            
            # After conversion, analyze result for data loss
            if target_format in ['cmme', 'mei'] and isinstance(result, str) and result.strip():
                try:
                    # Preprocess result for analysis
                    result_content = self._preprocess_xml_content(result)
                    result_root = etree.fromstring(result_content)
                    
                    # Count elements and attributes in result
                    element_counts_after, attribute_counts_after = self._count_elements_and_attributes(result_root)
                    self.logger.info(f"Target element counts: {element_counts_after}")
                    
                    # Compare counts to identify lost elements
                    for element_type, count in element_counts_before.items():
                        target_count = element_counts_after.get(element_type, 0)
                        if target_count < count:
                            lost_elements[element_type] = count - target_count
                            self.logger.warning(f"Data loss detected: Lost {count - target_count} {element_type} elements")
                    
                    # Log detailed data loss information
                    if lost_elements:
                        self.logger.warning(f"Conversion from {source_format} to {target_format} lost elements: {lost_elements}")
                    
                    # Compare attribute counts to identify lost attributes
                    for attr_name, count in attribute_counts_before.items():
                        target_count = attribute_counts_after.get(attr_name, 0)
                        if target_count < count:
                            lost_attributes[attr_name] = count - target_count
                            self.logger.warning(f"Data loss detected: Lost {count - target_count} '{attr_name}' attributes")
                    
                    if lost_attributes:
                        self.logger.warning(f"Conversion from {source_format} to {target_format} lost attributes: {lost_attributes}")
                        
                except Exception as e:
                    self.logger.warning(f"Error analyzing conversion results: {str(e)}")

            # Validate the final result if possible
            if target_format in ['cmme', 'mei']:
                try:
                    if target_format == 'cmme':
                        self.cmme_parser.validate(result)
                    else:  # mei
                        self.mei_parser.validate(result)
                except Exception as e:
                    self.logger.warning(f"Generated {target_format} content validation failed: {str(e)}")
                    # Don't raise an exception here, allow potentially useful but invalid content to pass through
            
            return self.serializer.serialize(result)

        except json.JSONDecodeError as e:
            self.logger.error(f"JSON parsing error: {str(e)}")
            self.logger.error(traceback.format_exc())
            raise ValueError(f"Invalid JSON format: {str(e)}")
        except etree.ParseError as e:
            self.logger.error(f"XML parsing error: {str(e)}")
            self.logger.error(traceback.format_exc())
            raise ValueError(f"Invalid XML format: {str(e)}")
        except Exception as e:
            self.logger.error(f"Transformation error: {str(e)}")
            self.logger.error(traceback.format_exc())
            raise ValueError(f"Transformation error: {str(e)}")

    def _preprocess_xml_content(self, content: str) -> str:
        """
        Preprocess XML content to handle common issues.
        
        Args:
            content (str): XML content string
            
        Returns:
            str: Preprocessed XML content
        """
        if not content or not isinstance(content, str):
            return content
            
        # Remove XML declaration if present
        if content.startswith('<?xml'):
            content = content[content.find('?>')+2:].lstrip()
        
        # Handle potential BOM (Byte Order Mark)
        if content.startswith('\ufeff'):
            content = content[1:]
        
        # Normalize line endings
        content = content.replace('\r\n', '\n').replace('\r', '\n')
        
        # Remove extra whitespace
        content = content.strip()
        
        return content

    def _count_elements_and_attributes(self, root: etree._Element) -> Tuple[Dict[str, int], Dict[str, int]]:
        """
        Count elements and attributes by type in an XML tree.
        
        Args:
            root (etree._Element): XML root element
            
        Returns:
            Tuple[Dict[str, int], Dict[str, int]]: Element counts and attribute counts
        """
        element_counts = {}
        attribute_counts = {}
        
        # Handle namespace-prefixed elements
        for element in root.iter():
            # Get tag name without namespace
            tag = element.tag
            if '}' in tag:
                tag = tag.split('}', 1)[1]
                
            element_counts[tag] = element_counts.get(tag, 0) + 1
            
            # Count attributes
            for attr_name in element.attrib:
                # Remove namespace from attribute name if present
                if '}' in attr_name:
                    attr_name = attr_name.split('}', 1)[1]
                
                attribute_counts[attr_name] = attribute_counts.get(attr_name, 0) + 1
        
        return element_counts, attribute_counts

    def _extract_metadata_from_content(self, content: Any, format_type: str) -> Dict:
        """
        Extract metadata from content in specified format.
        
        Args:
            content (Any): Content to extract metadata from
            format_type (str): Format type ('cmme', 'mei', or 'json')
            
        Returns:
            Dict: Extracted metadata or empty dict if extraction fails
        """
        try:
            if format_type == 'json':
                if isinstance(content, str):
                    json_data = json.loads(content)
                else:
                    json_data = content
                return json_data.get('metadata', {})
            
            # Handle XML formats
            if isinstance(content, str):
                # Preprocess XML content
                content = self._preprocess_xml_content(content)
                root = etree.fromstring(content.encode('utf-8'))
            else:
                root = content

            if format_type == 'cmme':
                metadata_elem = root.find('metadata')
                if metadata_elem is not None:
                    return {elem.tag: elem.text for elem in metadata_elem}
            elif format_type == 'mei':
                metadata = {}
                # Try both with and without namespace
                meiHead = root.find('.//{http://www.music-encoding.org/ns/mei}meiHead')
                if meiHead is None:
                    meiHead = root.find('.//meiHead')
                    
                if meiHead is not None:
                    # Extract title and composer
                    title = meiHead.find('.//{http://www.music-encoding.org/ns/mei}title') or meiHead.find('.//title')
                    composer = meiHead.find('.//{http://www.music-encoding.org/ns/mei}composer') or meiHead.find('.//composer')
                    
                    if title is not None and title.text:
                        metadata['title'] = title.text
                    if composer is not None and composer.text:
                        metadata['composer'] = composer.text
                    
                    # Extract other metadata
                    for elem in meiHead.iter():
                        tag = elem.tag
                        if '}' in tag:
                            tag = tag.split('}', 1)[1]
                            
                        if tag not in ['meiHead', 'fileDesc', 'titleStmt', 'pubStmt'] and elem.text and elem.text.strip():
                            metadata[tag] = elem.text.strip()
                return metadata
            
            return {}  # Return empty dict if no metadata found or unsupported format
        except Exception as e:
            self.logger.warning(f"Metadata extraction failed: {str(e)}")
            return {}

    def _perform_transformation(self, data: Any, source_format: str, target_format: str, metadata: Dict) -> Any:
        """
        Perform actual transformation between formats.
        
        Args:
            data (Any): Data to transform
            source_format (str): Source format ('cmme', 'mei', or 'json')
            target_format (str): Target format ('cmme', 'mei', or 'json')
            metadata (Dict): Extracted metadata
            
        Returns:
            Any: Transformed data
        """
        if source_format == 'cmme' and target_format == 'mei':
            # Parse CMME document to structure
            if isinstance(data, str):
                data = self._preprocess_xml_content(data)
                root = etree.fromstring(data.encode('utf-8'))
            else:
                root = data
                
            parsed_structure = self._parse_cmme_document_structure(root)
            return self._create_mei_document_from_structure(parsed_structure, metadata)
            
        elif source_format == 'mei' and target_format == 'cmme':
            # Parse MEI document to structure
            if isinstance(data, str):
                data = self._preprocess_xml_content(data)
                root = etree.fromstring(data.encode('utf-8'))
            else:
                root = data
                
            parsed_structure = self._parse_mei_document_structure(root)
            return self._create_cmme_document_from_structure(parsed_structure, metadata)
            
        elif source_format == 'json':
            if target_format == 'cmme':
                return self.json_converter.json_to_cmme(data)
            else:  # mei
                return self.json_converter.json_to_mei(data)
        else:  # XML source to JSON
            if isinstance(data, str):
                data = self._preprocess_xml_content(data)
                root = etree.fromstring(data.encode('utf-8'))
            else:
                root = data
                
            if source_format == 'cmme':
                return self.json_converter.cmme_to_json(root)
            else:  # mei to json
                return self.json_converter.mei_to_json(root)

    def _format_result(self, result: Any, target_format: str, metadata: Dict) -> Any:
        """
        Format and normalize the transformation result.
        
        Args:
            result (Any): Transformation result
            target_format (str): Target format ('cmme', 'mei', or 'json')
            metadata (Dict): Metadata to include if applicable
            
        Returns:
            Any: Formatted result
        """
        if not result:
            return result
            
        if target_format == 'json' and (isinstance(result, dict) or 
                                        (isinstance(result, str) and result.strip().startswith('{'))):
            # Ensure JSON result has metadata
            if isinstance(result, str):
                json_obj = json.loads(result)
            else:
                json_obj = result
                
            if metadata and ('metadata' not in json_obj or not json_obj['metadata']):
                json_obj['metadata'] = metadata
                
            return json.dumps(json_obj, indent=2)
        elif target_format in ['cmme', 'mei'] and isinstance(result, str):
            # Format XML result
            result = result.strip()
            
            # Remove any existing XML declaration
            if result.startswith('<?xml'):
                result = result[result.find('?>')+2:].lstrip()
                
            # Add XML declaration
            result = f'<?xml version="1.0" encoding="UTF-8"?>\n{result}'
            
            # Add MEI namespace if needed
            if target_format == 'mei' and '<mei' in result and not 'xmlns=' in result:
                result = result.replace(
                    '<mei>',
                    f'<mei xmlns="{self.MEI_NS}">'
                )
                
            return result
        
        return result

    def _parse_cmme_document_structure(self, root: etree._Element) -> Dict:
        """
        Parse CMME document structure including hierarchy of parts, measures, etc.
        """
        structure = {
            'metadata': {},
            'parts': []
        }
        
        # Extract metadata
        metadata_elem = root.find('metadata')
        if metadata_elem is not None:
            structure['metadata'] = {elem.tag: elem.text for elem in metadata_elem if elem.text}
        
        # Extract score structure
        score = root.find('score')
        if score is None:
            # Try without explicit score element
            score = root
            
        if score is not None:
            # Handle globally defined elements
            global_clefs = {}
            global_keys = {}
            global_times = {}
            
            # Check for global elements
            for global_elem in score:
                if global_elem.tag == 'clef' and 'staff' in global_elem.attrib:
                    staff_id = global_elem.get('staff')
                    global_clefs[staff_id] = global_elem
                elif global_elem.tag == 'key' and 'staff' in global_elem.attrib:
                    staff_id = global_elem.get('staff')
                    global_keys[staff_id] = global_elem
                elif global_elem.tag == 'time' and 'staff' in global_elem.attrib:
                    staff_id = global_elem.get('staff')
                    global_times[staff_id] = global_elem
            
            # Extract staves/parts
            staves = score.findall('staff')
            if not staves:
                # Check if there's a parts element
                parts_elem = score.find('parts')
                if parts_elem is not None:
                    staves = parts_elem.findall('staff')
            
            for staff in staves:
                part = {
                    'name': staff.get('name', ''),
                    'id': staff.get('id', str(len(structure['parts']) + 1)),
                    'measures': []
                }
                
                # Apply global settings if they exist for this staff
                staff_id = staff.get('id', '')
                
                # Extract clef information
                clef = staff.find('clef')
                if clef is None and staff_id in global_clefs:
                    clef = global_clefs[staff_id]
                    
                if clef is not None:
                    part['clef'] = {
                        'shape': clef.get('shape', 'G'),
                        'line': clef.get('line', '2')
                    }
                
                # Extract key signature
                key = staff.find('key')
                if key is None and staff_id in global_keys:
                    key = global_keys[staff_id]
                    
                if key is not None:
                    part['key'] = {
                        'signature': key.get('signature', '0')
                    }
                
                # Extract time signature
                time = staff.find('time')
                if time is None and staff_id in global_times:
                    time = global_times[staff_id]
                    
                if time is not None:
                    part['time'] = {
                        'signature': time.get('signature', '4/4')
                    }
                
                # Extract measures
                measures = staff.findall('measure')
                
                # Handle case where there are no explicit measure elements
                if not measures:
                    # Treat the staff as a single measure
                    single_measure = {
                        'number': '1',
                        'contents': []
                    }
                    
                    # Extract all content elements directly under staff
                    for elem in staff:
                        if elem.tag not in ['clef', 'key', 'time']:
                            if elem.tag == 'note':
                                single_measure['contents'].append({
                                    'type': 'note',
                                    'element': elem
                                })
                            elif elem.tag == 'rest':
                                single_measure['contents'].append({
                                    'type': 'rest',
                                    'element': elem
                                })
                            elif elem.tag == 'chord':
                                notes = []
                                for note in elem.findall('note'):
                                    notes.append(note)
                                
                                single_measure['contents'].append({
                                    'type': 'chord',
                                    'notes': notes
                                })
                            else:
                                # Handle other element types
                                single_measure['contents'].append({
                                    'type': elem.tag,
                                    'element': elem
                                })
                    
                    if single_measure['contents']:
                        part['measures'].append(single_measure)
                else:
                    # Process measures normally
                    for measure in measures:
                        measure_data = {
                            'number': measure.get('number', str(len(part['measures']) + 1)),
                            'contents': []
                        }
                        
                        # Extract all content elements in order
                        for elem in measure:
                            if elem.tag == 'note':
                                measure_data['contents'].append({
                                    'type': 'note',
                                    'element': elem
                                })
                            elif elem.tag == 'rest':
                                measure_data['contents'].append({
                                    'type': 'rest',
                                    'element': elem
                                })
                            elif elem.tag == 'chord':
                                notes = []
                                for note in elem.findall('note'):
                                    notes.append(note)
                                
                                measure_data['contents'].append({
                                    'type': 'chord',
                                    'notes': notes
                                })
                            else:
                                # Handle other element types
                                measure_data['contents'].append({
                                    'type': elem.tag,
                                    'element': elem
                                })
                        
                        part['measures'].append(measure_data)
                
                structure['parts'].append(part)
        
        return structure

    def _parse_mei_document_structure(self, root: etree._Element) -> Dict:
        """
        Parse MEI document structure including hierarchy of parts, measures, etc.
        """
        structure = {
            'metadata': {},
            'parts': []
        }
        
        # Define namespace handling for XPath queries
        nsmap = {'mei': self.MEI_NS}
        
        # Helper function to find elements with or without namespace
        def find_with_ns(element, xpath):
            # Try with namespace
            result = element.xpath(xpath, namespaces=nsmap)
            if result:
                return result
            
            # Try without namespace by removing mei: prefix
            xpath_no_ns = xpath.replace('mei:', '')
            return element.xpath(xpath_no_ns)
        
        # Extract metadata
        meiHead_elements = find_with_ns(root, './/mei:meiHead')
        if meiHead_elements:
            meiHead = meiHead_elements[0]
            
            # Extract metadata from meiHead
            title_elements = find_with_ns(meiHead, './/mei:title')
            if title_elements and title_elements[0].text:
                structure['metadata']['title'] = title_elements[0].text.strip()
                
            composer_elements = find_with_ns(meiHead, './/mei:composer')
            if composer_elements and composer_elements[0].text:
                structure['metadata']['composer'] = composer_elements[0].text.strip()
                
            # Extract other metadata elements
            for elem in meiHead.iter():
                tag = elem.tag
                if '}' in tag:
                    tag = tag.split('}', 1)[1]
                    
                if tag not in ['meiHead', 'fileDesc', 'titleStmt', 'pubStmt'] and elem.text and elem.text.strip():
                    structure['metadata'][tag] = elem.text.strip()
        
        # Find score element
        score_elements = find_with_ns(root, './/mei:score') or find_with_ns(root, './/mei:mdiv')
        if not score_elements:
            # If no score or mdiv, try to find any music content
            body_elements = find_with_ns(root, './/mei:body')
            if body_elements:
                score_elements = [body_elements[0]]
            else:
                # Last resort - use root itself
                score_elements = [root]
                
        if score_elements:
            score = score_elements[0]
            
            # Find staff definitions
            staffDef_elements = find_with_ns(score, './/mei:staffDef')
            
            # Create part entries based on staff definitions
            staff_defs_by_n = {}
            for staffDef in staffDef_elements:
                staff_n = staffDef.get('n', '')
                if not staff_n:
                    continue
                    
                staff_defs_by_n[staff_n] = staffDef
                
                part = {
                    'id': staff_n,
                    'name': '',
                    'measures': []
                }
                
                # Extract staff label if present
                label_elements = find_with_ns(staffDef, './/mei:label')
                if label_elements and label_elements[0].text:
                    part['name'] = label_elements[0].text.strip()
                
                # Extract clef information
                clef_shape = staffDef.get('clef.shape', '')
                clef_line = staffDef.get('clef.line', '')
                if clef_shape or clef_line:
                    part['clef'] = {
                        'shape': clef_shape or 'G',
                        'line': clef_line or '2'
                    }
                
                # Extract key signature
                key_sig = staffDef.get('key.sig', '')
                if key_sig:
                    part['key'] = {
                        'signature': key_sig
                    }
                
                # Extract time signature
                meter_count = staffDef.get('meter.count', '')
                meter_unit = staffDef.get('meter.unit', '')
                if meter_count and meter_unit:
                    part['time'] = {
                        'signature': f"{meter_count}/{meter_unit}"
                    }
                elif staffDef.get('meter.sym', ''):
                    part['time'] = {
                        'signature': staffDef.get('meter.sym')
                    }
                
                structure['parts'].append(part)
            
            # If no staffDef elements found, try to infer from content
            if not structure['parts']:
                # Look for staff elements to determine how many parts
                staff_elements = find_with_ns(score, './/mei:staff')
                staff_numbers = set()
                for staff in staff_elements:
                    staff_n = staff.get('n', '')
                    if staff_n:
                        staff_numbers.add(staff_n)
                
                # Create parts based on staff numbers found
                for staff_n in sorted(staff_numbers):
                    part = {
                        'id': staff_n,
                        'name': f"Staff {staff_n}",
                        'measures': []
                    }
                    structure['parts'].append(part)
            
            # Find section elements
            section_elements = find_with_ns(score, './/mei:section')
            if not section_elements:
                # If no section elements, try to find content directly
                section_elements = [score]
            
            # Process each section
            for section in section_elements:
                # Find measure elements
                measure_elements = find_with_ns(section, './/mei:measure')
                
                # Process each measure
                for measure in measure_elements:
                    measure_n = measure.get('n', str(len(structure['parts'][0]['measures']) + 1) if structure['parts'] else '1')
                    
                    # Process each staff in the measure
                    staff_elements = find_with_ns(measure, './/mei:staff')
                    
                    for staff in staff_elements:
                        staff_n = staff.get('n', '')
                        if not staff_n:
                            continue
                            
                        # Find the part this staff belongs to
                        part_index = -1
                        for i, part in enumerate(structure['parts']):
                            if part['id'] == staff_n:
                                part_index = i
                                break
                                
                        if part_index < 0:
                            # Create a new part if not found
                            part = {
                                'id': staff_n,
                                'name': f"Staff {staff_n}",
                                'measures': []
                            }
                            part_index = len(structure['parts'])
                            structure['parts'].append(part)
                            
                        # Create measure data for this part
                        measure_data = {
                            'number': measure_n,
                            'contents': []
                        }
                        
                        # Process layers
                        layer_elements = find_with_ns(staff, './/mei:layer')
                        
                        if layer_elements:
                            for layer in layer_elements:
                                # Process elements in layer
                                for elem in layer:
                                    tag = elem.tag
                                    if '}' in tag:
                                        tag = tag.split('}', 1)[1]
                                        
                                    if tag == 'note':
                                        measure_data['contents'].append({
                                            'type': 'note',
                                            'element': elem
                                        })
                                    elif tag == 'rest':
                                        measure_data['contents'].append({
                                            'type': 'rest',
                                            'element': elem
                                        })
                                    elif tag == 'chord':
                                        notes = []
                                        note_elements = find_with_ns(elem, './/mei:note')
                                        for note in note_elements:
                                            notes.append(note)
                                            
                                        measure_data['contents'].append({
                                            'type': 'chord',
                                            'notes': notes
                                        })
                                    else:
                                        # Handle other element types
                                        measure_data['contents'].append({
                                            'type': tag,
                                            'element': elem
                                        })
                        else:
                            # No layers found, process staff contents directly
                            for elem in staff:
                                tag = elem.tag
                                if '}' in tag:
                                    tag = tag.split('}', 1)[1]
                                    
                                if tag == 'note':
                                    measure_data['contents'].append({
                                        'type': 'note',
                                        'element': elem
                                    })
                                elif tag == 'rest':
                                    measure_data['contents'].append({
                                        'type': 'rest',
                                        'element': elem
                                    })
                                elif tag == 'chord':
                                    notes = []
                                    note_elements = find_with_ns(elem, './/mei:note')
                                    for note in note_elements:
                                        notes.append(note)
                                        
                                    measure_data['contents'].append({
                                        'type': 'chord',
                                        'notes': notes
                                    })
                                else:
                                    # Handle other element types
                                    measure_data['contents'].append({
                                        'type': tag,
                                        'element': elem
                                    })
                        
                        # Add measure to part if it has contents
                        if measure_data['contents']:
                            structure['parts'][part_index]['measures'].append(measure_data)
        
        return structure

    def _create_mei_document_from_structure(self, structure: Dict, metadata: Optional[Dict] = None) -> str:
        """
        Create a complete MEI document from the parsed structure.
        """
        # Create root element with namespace
        root = etree.Element('{' + self.MEI_NS + '}mei', nsmap={None: self.MEI_NS})
        
        # Add metadata
        if metadata or structure.get('metadata'):
            metadata_to_use = metadata if metadata else structure.get('metadata', {})
            meiHead = etree.SubElement(root, '{' + self.MEI_NS + '}meiHead')
            fileDesc = etree.SubElement(meiHead, '{' + self.MEI_NS + '}fileDesc')
            
            # Add title and composer
            titleStmt = etree.SubElement(fileDesc, '{' + self.MEI_NS + '}titleStmt')
            if 'title' in metadata_to_use:
                title = etree.SubElement(titleStmt, '{' + self.MEI_NS + '}title')
                title.text = metadata_to_use['title']
            
            if 'composer' in metadata_to_use:
                composer = etree.SubElement(titleStmt, '{' + self.MEI_NS + '}composer')
                composer.text = metadata_to_use['composer']
            
            # Add other metadata
            if metadata_to_use:
                pubStmt = etree.SubElement(fileDesc, '{' + self.MEI_NS + '}pubStmt')
                for key, value in metadata_to_use.items():
                    if key not in ['title', 'composer'] and value:
                        elem = etree.SubElement(pubStmt, '{' + self.MEI_NS + '}' + key)
                        elem.text = str(value)
        
        # Create music structure
        music = etree.SubElement(root, '{' + self.MEI_NS + '}music')
        body = etree.SubElement(music, '{' + self.MEI_NS + '}body')
        mdiv = etree.SubElement(body, '{' + self.MEI_NS + '}mdiv')
        score = etree.SubElement(mdiv, '{' + self.MEI_NS + '}score')
        
        # Add staves definition
        scoreDef = etree.SubElement(score, '{' + self.MEI_NS + '}scoreDef')
        staffGrp = etree.SubElement(scoreDef, '{' + self.MEI_NS + '}staffGrp')
        
        # Add parts/staves
        for i, part in enumerate(structure.get('parts', [])):
            # Add staff definition
            staffDef = etree.SubElement(staffGrp, '{' + self.MEI_NS + '}staffDef')
            staffDef.set('n', part.get('id', str(i+1)))
            staffDef.set('lines', '5')  # Default value
            
            if 'clef' in part:
                staffDef.set('clef.shape', part['clef'].get('shape', 'G'))
                staffDef.set('clef.line', part['clef'].get('line', '2'))
            
            if 'name' in part and part['name']:
                label = etree.SubElement(staffDef, '{' + self.MEI_NS + '}label')
                label.text = part['name']
                
            # Handle key signature
            if 'key' in part:
                staffDef.set('key.sig', part['key'].get('signature', '0'))
                
            # Handle time signature
            if 'time' in part:
                time_sig = part['time'].get('signature', '')
                if re.match(r'\d+/\d+', time_sig):
                    parts = time_sig.split('/')
                    staffDef.set('meter.count', parts[0])
                    staffDef.set('meter.unit', parts[1])
                elif time_sig in ['C', 'O', 'C.', 'O.']:
                    # Handle mensuration signs
                    staffDef.set('meter.sym', time_sig)
        
        # Add musical content
        section = etree.SubElement(score, '{' + self.MEI_NS + '}section')
        
        # Process each measure for each part
        max_measures = max((len(part.get('measures', [])) for part in structure.get('parts', [])), default=0)
        
        for measure_idx in range(max_measures):
            measure = etree.SubElement(section, '{' + self.MEI_NS + '}measure')
            measure.set('n', str(measure_idx + 1))
            
            for part_idx, part in enumerate(structure.get('parts', [])):
                if measure_idx < len(part.get('measures', [])):
                    part_measure = part['measures'][measure_idx]
                    staff = etree.SubElement(measure, '{' + self.MEI_NS + '}staff')
                    staff.set('n', part.get('id', str(part_idx + 1)))
                    
                    layer = etree.SubElement(staff, '{' + self.MEI_NS + '}layer')
                    layer.set('n', '1')
                    
                    # Add measure contents
                    for content in part_measure.get('contents', []):
                        if content['type'] == 'note':
                            # Convert note element
                            mei_note = self._convert_note_cmme_to_mei(content['element'])
                            layer.append(mei_note)
                        elif content['type'] == 'rest':
                            # Convert rest element
                            mei_rest = self._convert_rest_cmme_to_mei(content['element'])
                            layer.append(mei_rest)
                        elif content['type'] == 'chord':
                            # Create chord element
                            chord = etree.SubElement(layer, '{' + self.MEI_NS + '}chord')
                            
                            # Convert each note in the chord
                            for note in content.get('notes', []):
                                mei_note = self._convert_note_cmme_to_mei(note)
                                chord.append(mei_note)
                        else:
                            # Handle other elements
                            self._convert_generic_element(content['element'], layer)
        
        # Return the MEI document as a string
        return etree.tostring(root, encoding='unicode', pretty_print=True)
    

    def _create_cmme_document_from_structure(self, structure: Dict, metadata: Optional[Dict] = None) -> str:
        """
        Create a complete CMME document from a parsed MEI structure.
        """
        # Create root element
        root = etree.Element('cmme')
        
        # Add metadata
        if metadata or structure.get('metadata'):
            metadata_to_use = metadata if metadata else structure.get('metadata', {})
            metadata_elem = etree.SubElement(root, 'metadata')
            
            # Add all metadata fields
            for key, value in metadata_to_use.items():
                if value:
                    elem = etree.SubElement(metadata_elem, key)
                    elem.text = str(value)
        
        # Create score element
        score = etree.SubElement(root, 'score')
        
        # Add staves/parts
        for part in structure.get('parts', []):
            staff = etree.SubElement(score, 'staff')
            staff.set('name', part.get('name', ''))
            if 'id' in part:
                staff.set('id', part['id'])
            
            # Add clef if present
            if 'clef' in part:
                clef = etree.SubElement(staff, 'clef')
                clef.set('shape', part['clef'].get('shape', 'G'))
                clef.set('line', part['clef'].get('line', '2'))
            
            # Add key signature if present
            if 'key' in part:
                key = etree.SubElement(staff, 'key')
                key.set('signature', part['key'].get('signature', ''))
            
            # Add time signature if present
            if 'time' in part:
                time = etree.SubElement(staff, 'time')
                time.set('signature', part['time'].get('signature', ''))
            
            # Process measures
            for measure_data in part.get('measures', []):
                measure = etree.SubElement(staff, 'measure')
                measure.set('number', measure_data.get('number', ''))
                
                # Add measure contents
                for content in measure_data.get('contents', []):
                    if content['type'] == 'note':
                        # Convert note element from MEI to CMME
                        cmme_note = self._convert_note_mei_to_cmme(content['element'])
                        measure.append(cmme_note)
                    elif content['type'] == 'rest':
                        # Convert rest element
                        cmme_rest = self._convert_rest_mei_to_cmme(content['element'])
                        measure.append(cmme_rest)
                    elif content['type'] == 'chord':
                        # Create chord element
                        chord = etree.SubElement(measure, 'chord')
                        
                        # Convert each note in the chord
                        for note in content.get('notes', []):
                            cmme_note = self._convert_note_mei_to_cmme(note)
                            chord.append(cmme_note)
                    else:
                        # Handle other elements
                        self._convert_mei_element_to_cmme(content['element'], measure)
        
        # Return the CMME document as a string
        return etree.tostring(root, encoding='unicode', pretty_print=True)

    def _convert_note_cmme_to_mei(self, note: etree._Element) -> etree._Element:
        """
        Convert a CMME note to MEI format with enhanced attribute mapping.

        Args:
            note (etree._Element): CMME note element

        Returns:
            etree._Element: Converted MEI note element
        """
        mei_note = etree.Element('{' + self.MEI_NS + '}note')
        
        # Handle pitch conversion with accidentals
        if 'pitch' in note.attrib:
            pitch_value = note.get('pitch')
            pitch_match = re.match(r'^([A-G])([#b\.]?)(\d+)$', pitch_value)
            
            if pitch_match:
                pname, accid_or_dot, octave = pitch_match.groups()
                
                # Set pname and octave
                mei_note.set('pname', pname.lower())
                mei_note.set('oct', octave)
                
                # Handle accidentals and musica ficta
                if accid_or_dot == '#':
                    mei_note.set('accid', 's')  # sharp
                elif accid_or_dot == 'b':
                    mei_note.set('accid', 'f')  # flat
                elif accid_or_dot == '.':
                    # This is musica ficta (editorial accidental)
                    mei_note.set('accid.ges', 'n')  # editorial natural
                    
                # Check for additional accidental in the pitch
                if len(pitch_value) > len(pname) + len(octave) + len(accid_or_dot):
                    extra_accid = pitch_value[len(pname) + len(accid_or_dot)]
                    if extra_accid == '#':
                        if accid_or_dot == '.':
                            mei_note.set('accid.ges', 's')  # editorial sharp
                        else:
                            mei_note.set('accid', 's')  # sharp
                    elif extra_accid == 'b':
                        if accid_or_dot == '.':
                            mei_note.set('accid.ges', 'f')  # editorial flat
                        else:
                            mei_note.set('accid', 'f')  # flat
        
        # Handle duration with dots
        if 'duration' in note.attrib:
            duration = note.get('duration')
            
            # Check for dot notation in the duration
            if ' dot' in duration:
                parts = duration.split(' ')
                base_dur = parts[0]
                
                # Set base duration
                mei_duration = self._get_mei_duration_value(base_dur)
                mei_note.set('dur', mei_duration)
                
                # Set dots attribute
                if 'double-dot' in duration:
                    mei_note.set('dots', '2')
                elif 'triple-dot' in duration:
                    mei_note.set('dots', '3')
                else:
                    mei_note.set('dots', '1')
            else:
                # Simple duration
                mei_duration = self._get_mei_duration_value(duration)
                mei_note.set('dur', mei_duration)
        
        # Apply other attribute mappings from the comprehensive mapping
        for cmme_attr, mei_attr in self.attribute_mappings['cmme_to_mei'].items():
            if cmme_attr in note.attrib and cmme_attr not in ['pitch', 'duration']:
                if isinstance(mei_attr, dict):
                    # Handle complex mappings that require transformation
                    for target_attr, transform_func in mei_attr.items():
                        if callable(transform_func):
                            try:
                                result = transform_func(note.get(cmme_attr))
                                if result is not None:  # Only set if not None
                                    mei_note.set(target_attr, result)
                            except Exception as e:
                                self.logger.warning(f"Failed to transform attribute {cmme_attr}: {str(e)}")
                else:
                    # Simple attribute mapping
                    mei_note.set(mei_attr, note.get(cmme_attr))
        
        # Copy any other attributes with a prefix to avoid namespace conflicts
        for attr, value in note.attrib.items():
            if attr not in ['pitch', 'duration'] and not any(attr == cmme_attr for cmme_attr in self.attribute_mappings['cmme_to_mei']):
                mei_note.set('cmme:' + attr, value)
        
        # Handle articulations
        for artic in note.findall('articulation'):
            artic_type = artic.get('type')
            if artic_type:
                mei_artic = etree.SubElement(mei_note, '{' + self.MEI_NS + '}artic')
                mei_artic.set('artic', self.mei_parser.ARTICULATION_MAP.get(artic_type, artic_type))
                
                # Also preserve all articulation attributes
                for attr, value in artic.attrib.items():
                    if attr != 'type':
                        mei_artic.set(attr, value)
        
        # Handle ligature notation
        ligature = note.find('ligature')
        if ligature is not None:
            mei_ligature = etree.SubElement(mei_note, '{' + self.MEI_NS + '}ligature')
            
            # Map position to form
            if 'position' in ligature.attrib:
                position = ligature.get('position')
                form_map = {'start': 'initial', 'middle': 'medial', 'end': 'terminal'}
                mei_ligature.set('form', form_map.get(position, position))
            
            # Copy other ligature attributes
            for attr, value in ligature.attrib.items():
                if attr != 'position':
                    mei_ligature.set(attr, value)
        
        # Handle mensuration signs
        mensuration = note.find('mensuration')
        if mensuration is not None:
            mei_mensur = etree.SubElement(mei_note, '{' + self.MEI_NS + '}mensur')
            
            # Handle sign attribute
            if 'sign' in mensuration.attrib:
                sign = mensuration.get('sign')
                
                # Extract base sign and dot
                if len(sign) > 1 and sign[1] == '.':
                    mei_mensur.set('sign', sign[0])
                    mei_mensur.set('dot', 'true')
                else:
                    mei_mensur.set('sign', sign[0] if sign else 'C')
                    
                # Handle strike-through (diminution)
                if '/' in sign:
                    mei_mensur.set('slash', 'true')
            
            # Copy other mensuration attributes
            for attr, value in mensuration.attrib.items():
                if attr != 'sign':
                    mei_mensur.set(attr, value)
        
        # Handle coloration
        coloration = note.find('coloration')
        if coloration is not None:
            mei_note.set('colored', 'true')
            
            # Set type if specified
            if 'type' in coloration.attrib:
                mei_note.set('color', coloration.get('type'))
        
        # Handle other child elements
        for child in note:
            if child.tag not in ['articulation', 'ligature', 'mensuration', 'coloration']:
                # Create corresponding MEI element
                mei_child_name = self._get_mei_element_name(child.tag)
                mei_child = etree.SubElement(mei_note, '{' + self.MEI_NS + '}' + mei_child_name)
                
                # Copy all attributes
                for attr, value in child.attrib.items():
                    mei_child.set(attr, value)
                
                # Copy text content if any
                if child.text and child.text.strip():
                    mei_child.text = child.text.strip()
        
        return mei_note
    
    def _convert_note_mei_to_cmme(self, note: etree._Element) -> etree._Element:
        """
        Convert an MEI note to CMME format with enhanced attribute mapping.

        Args:
            note (etree._Element): MEI note element

        Returns:
            etree._Element: Converted CMME note element
        """
        cmme_note = etree.Element('note')
        
        # Handle namespace in tag if present
        is_mei_ns = note.tag.startswith('{' + self.MEI_NS + '}')
        
        # Combine pname and oct into pitch
        pname = note.get('pname')
        oct = note.get('oct')
        accid = note.get('accid')
        accid_ges = note.get('accid.ges')
        
        if pname and oct:
            # Construct pitch value
            pitch = pname.upper() + oct
            
            # Add accidental if present
            if accid == 's':
                pitch = pitch[0] + '#' + pitch[1:]
            elif accid == 'f':
                pitch = pitch[0] + 'b' + pitch[1:]
            
            # Handle musica ficta (editorial accidentals)
            if accid_ges and not accid:
                # Add dot for musica ficta
                pitch = pitch[0] + '.' + pitch[1:]
                if accid_ges == 's':
                    pitch = pitch.replace('.', '.#')
                elif accid_ges == 'f':
                    pitch = pitch.replace('.', '.b')
                    
            cmme_note.set('pitch', pitch)
        
        # Handle duration and dots
        dur = note.get('dur')
        dots = note.get('dots')
        
        if dur:
            # Convert MEI duration to CMME format
            duration = self._get_cmme_duration_value(dur)
            
            # Add dots if present
            if dots:
                if dots == '1':
                    duration += ' dot'
                elif dots == '2':
                    duration += ' double-dot'
                elif dots == '3':
                    duration += ' triple-dot'
                    
            cmme_note.set('duration', duration)
        
        # Apply attribute mappings from the comprehensive mapping
        for mei_attr, cmme_attr in self.attribute_mappings['mei_to_cmme'].items():
            if mei_attr in note.attrib and mei_attr not in ['pname', 'oct', 'dur', 'dots', 'accid', 'accid.ges']:
                if isinstance(cmme_attr, dict):
                    # Handle complex mappings that require transformation
                    for target_attr, transform_func in cmme_attr.items():
                        if callable(transform_func):
                            try:
                                # For pitch mapping, we need both pname and oct
                                if mei_attr == 'pname' and 'oct' in note.attrib:
                                    result = transform_func(note.get(mei_attr), note.get('oct'))
                                # For duration with dots
                                elif mei_attr == 'dots' and 'dur' in note.attrib:
                                    result = transform_func(note.get('dots'), note.get('dur'))
                                else:
                                    result = transform_func(note.get(mei_attr))
                                    
                                if result is not None and result != '':  # Only set if not None or empty
                                    cmme_note.set(target_attr, result)
                            except Exception as e:
                                self.logger.warning(f"Failed to transform attribute {mei_attr}: {str(e)}")
                else:
                    # Simple attribute mapping
                    cmme_note.set(cmme_attr, note.get(mei_attr))
        
        # Handle MEI-specific attributes with custom prefix
        for attr, value in note.attrib.items():
            if attr not in ['pname', 'oct', 'dur', 'dots', 'accid', 'accid.ges'] and \
            not any(attr == mei_attr for mei_attr in self.attribute_mappings['mei_to_cmme']):
                # Skip attributes with XML namespace or already containing colons
                if '}' in attr or ':' in attr:
                    # For xml:id specifically, convert to a standard 'id' attribute
                    if attr.endswith('}id') and '{http://www.w3.org/XML/1998/namespace}' in attr:
                        cmme_note.set('id', value)
                    # Otherwise skip this attribute
                    continue
                else:
                    # Add mei: prefix only for non-namespaced attributes
                    cmme_note.set('mei:' + attr, value)
        
        # Handle articulations
        artic_tag = '{' + self.MEI_NS + '}artic' if is_mei_ns else 'artic'
        for artic in note.findall(artic_tag):
            artic_value = artic.get('artic') or artic.get('type')
            if artic_value:
                cmme_artic = etree.SubElement(cmme_note, 'articulation')
                
                # Map MEI articulation to CMME
                artic_map = {v: k for k, v in self.mei_parser.ARTICULATION_MAP.items()}
                cmme_artic.set('type', artic_map.get(artic_value, artic_value))
                
                # Copy other attributes
                for attr, value in artic.attrib.items():
                    if attr not in ['artic', 'type']:
                        cmme_artic.set(attr, value)
        
        # Handle ligature
        ligature_tag = '{' + self.MEI_NS + '}ligature' if is_mei_ns else 'ligature'
        ligature = note.find(ligature_tag)
        if ligature is not None:
            cmme_ligature = etree.SubElement(cmme_note, 'ligature')
            
            # Map form to position
            if 'form' in ligature.attrib:
                form = ligature.get('form')
                position_map = {'initial': 'start', 'terminal': 'end', 'medial': 'middle'}
                cmme_ligature.set('position', position_map.get(form, form))
            
            # Copy other attributes
            for attr, value in ligature.attrib.items():
                if attr != 'form':
                    cmme_ligature.set(attr, value)
        
        # Handle mensuration
        mensur_tag = '{' + self.MEI_NS + '}mensur' if is_mei_ns else 'mensur'
        mensur = note.find(mensur_tag)
        if mensur is not None:
            cmme_mensuration = etree.SubElement(cmme_note, 'mensuration')
            
            # Combine sign and dot
            if 'sign' in mensur.attrib:
                sign = mensur.get('sign')
                if mensur.get('dot') == 'true':
                    sign += '.'
                if mensur.get('slash') == 'true':
                    sign += '/'
                cmme_mensuration.set('sign', sign)
            
            # Copy other attributes
            for attr, value in mensur.attrib.items():
                if attr not in ['sign', 'dot', 'slash']:
                    cmme_mensuration.set(attr, value)
        
        # Handle coloration (MEI uses @colored attribute)
        if note.get('colored') == 'true':
            cmme_coloration = etree.SubElement(cmme_note, 'coloration')
            if 'color' in note.attrib:
                cmme_coloration.set('type', note.get('color'))
            else:
                cmme_coloration.set('type', 'blackened')
        
        # Handle other child elements
        for child in note:
            child_tag = child.tag
            if '}' in child_tag:
                child_tag = child_tag.split('}')[-1]
                
            if child_tag not in ['artic', 'ligature', 'mensur']:
                # Map MEI element to CMME
                cmme_child_name = self._get_cmme_element_name(child_tag)
                cmme_child = etree.SubElement(cmme_note, cmme_child_name)
                
                # Copy all attributes
                for attr, value in child.attrib.items():
                    cmme_child.set(attr, value)
                
                # Copy text content if any
                if child.text and child.text.strip():
                    cmme_child.text = child.text.strip()
        
        return cmme_note

    def _convert_rest_cmme_to_mei(self, rest: etree._Element) -> etree._Element:
        """Convert CMME rest to MEI rest."""
        mei_rest = etree.Element('{' + self.MEI_NS + '}rest')
        
        # Convert duration
        if 'duration' in rest.attrib:
            duration = rest.get('duration')
            mei_duration = self._get_mei_duration(duration)
            for dur_attr, dur_value in mei_duration.items():
                mei_rest.set(dur_attr, dur_value)
        
        # Copy other attributes
        for attr, value in rest.attrib.items():
            if attr != 'duration':
                mei_rest.set(attr, value)
        
        return mei_rest

    def _convert_rest_mei_to_cmme(self, rest: etree._Element) -> etree._Element:
        """Convert MEI rest to CMME rest."""
        cmme_rest = etree.Element('rest')
        
        # Map duration from MEI to CMME
        dur = rest.get('dur')
        dots = rest.get('dots')
        
        if dur:
            # Convert MEI duration to CMME format
            duration = self._get_cmme_duration(dur, dots)
            cmme_rest.set('duration', duration)
        
        # Copy other attributes, removing namespace if present
        for attr, value in rest.attrib.items():
            if attr not in ['dur', 'dots']:
                if '}' in attr:
                    attr = attr.split('}', 1)[1]
                cmme_rest.set(attr, value)
        
        return cmme_rest

    def _convert_generic_element(self, element: etree._Element, parent: etree._Element) -> None:
        """Convert a generic CMME element to MEI and add it to the parent."""
        # Map element name to MEI equivalent
        mei_element_name = self._get_mei_element_name(element.tag)
        mei_element = etree.SubElement(parent, '{' + self.MEI_NS + '}' + mei_element_name)
        
        # Copy attributes
        for attr, value in element.attrib.items():
            mei_element.set(attr, value)
        
        # Copy text content
        if element.text and element.text.strip():
            mei_element.text = element.text.strip()
        
        # Convert children recursively
        for child in element:
            self._convert_generic_element(child, mei_element)

    def _convert_mei_element_to_cmme(self, element: etree._Element, parent: etree._Element) -> None:
        """Convert a generic MEI element to CMME and add it to the parent."""
        # Get element tag without namespace
        tag = element.tag
        if '}' in tag:
            tag = tag.split('}', 1)[1]
            
        # Map element name to CMME equivalent
        cmme_element_name = self._get_cmme_element_name(tag)
        cmme_element = etree.SubElement(parent, cmme_element_name)
        
        # Copy attributes, removing namespace if present
        for attr, value in element.attrib.items():
            if '}' in attr:
                attr = attr.split('}', 1)[1]
            cmme_element.set(attr, value)
        
        # Copy text content
        if element.text and element.text.strip():
            cmme_element.text = element.text.strip()
        
        # Convert children recursively
        for child in element:
            child_tag = child.tag
            if '}' in child_tag:
                child_tag = child_tag.split('}', 1)[1]
                
            # Recursively convert child elements
            self._convert_mei_element_to_cmme(child, cmme_element)

    def _get_mei_duration(self, cmme_duration: str) -> Dict[str, str]:
        """
        Convert CMME duration to MEI duration attributes.
        
        Args:
            cmme_duration (str): CMME duration specification
            
        Returns:
            Dict[str, str]: MEI duration attributes
        """
        result = {}
        
        # Get duration mapping
        dur_map = self.duration_mappings['cmme_to_mei']
        
        # Check for compound duration (e.g., "quarter dot")
        parts = cmme_duration.split() if ' ' in cmme_duration else [cmme_duration]
        base_dur = parts[0]
        
        # Set the base duration
        if base_dur in dur_map:
            result['dur'] = dur_map[base_dur]
        else:
            # Try to match numeric representation
            if re.match(r'^\d+$', base_dur):
                result['dur'] = base_dur
            else:
                # Default to quarter note if unknown
                result['dur'] = '4'
                self.logger.warning(f"Unknown duration format: {cmme_duration}, defaulting to quarter note")
        
        # Handle dots
        if 'dot' in cmme_duration:
            if 'double-dot' in cmme_duration:
                result['dots'] = '2'
            elif 'triple-dot' in cmme_duration:
                result['dots'] = '3'
            else:
                result['dots'] = '1'
        
        return result

    def _get_cmme_duration(self, mei_duration: str, dots: Optional[str] = None) -> str:
        """
        Convert MEI duration to CMME duration.
        
        Args:
            mei_duration (str): MEI duration value
            dots (Optional[str]): Number of dots
            
        Returns:
            str: CMME duration string
        """
        # Get duration mapping
        dur_map = self.duration_mappings['mei_to_cmme']
        
        # Get base duration
        cmme_dur = dur_map.get(mei_duration, mei_duration)
        
        # Handle dots
        if dots:
            if dots == '1':
                cmme_dur += ' dot'
            elif dots == '2':
                cmme_dur += ' double-dot'
            elif dots == '3':
                cmme_dur += ' triple-dot'
        
        return cmme_dur

    def _get_mei_element_name(self, cmme_element_name: str) -> str:
        """
        Map CMME element names to MEI element names.
        
        Args:
            cmme_element_name (str): CMME element name
            
        Returns:
            str: Corresponding MEI element name
        """
        return self.element_mappings['cmme_to_mei'].get(cmme_element_name, cmme_element_name)

    def _get_cmme_element_name(self, mei_element_name: str) -> str:
        """
        Map MEI element names to CMME element names.
        
        Args:
            mei_element_name (str): MEI element name
            
        Returns:
            str: Corresponding CMME element name
        """
        return self.element_mappings['mei_to_cmme'].get(mei_element_name, mei_element_name)

    def _handle_format_specific_features(self, source_format: str, target_format: str, 
                                         element: etree._Element, converted_element: etree._Element) -> etree._Element:
        """
        Handle format-specific features that need special treatment during conversion.
        
        Args:
            source_format: The source format ('cmme', 'mei', 'json')
            target_format: The target format ('cmme', 'mei', 'json') 
            element: The source element
            converted_element: The already converted element that needs enhancement
            
        Returns:
            The enhanced converted element
        """
        # Handle CMME-specific early music notation when converting to MEI
        if source_format == 'cmme' and target_format == 'mei':
            # Handle mensural notation
            if 'mensural' in element.attrib and element.get('mensural') == 'true':
                converted_element.set('mensural', 'true')
                
            # Handle ligatures
            ligature = element.find('ligature')
            if ligature is not None:
                mei_ligature = etree.SubElement(converted_element, '{' + self.MEI_NS + '}ligature')
                if 'position' in ligature.attrib:
                    # Map CMME positions to MEI forms
                    position_map = {'start': 'initial', 'end': 'terminal', 'middle': 'medial'}
                    mei_ligature.set('form', position_map.get(ligature.get('position'), ligature.get('position')))
                    
            # Handle coloration
            if 'coloration' in element.attrib:
                converted_element.set('colored', element.get('coloration'))
                
            # Handle musica ficta
            if element.tag == 'note' and 'pitch' in element.attrib:
                pitch = element.get('pitch', '')
                if '.' in pitch:  # Indicates musica ficta in CMME
                    if '#' in pitch:
                        converted_element.set('accid.ges', 's')
                    elif 'b' in pitch:
                        converted_element.set('accid.ges', 'f')
                    else:
                        converted_element.set('accid.ges', 'n')
                    
            # Handle mensuration signs
            if element.tag == 'time' and 'signature' in element.attrib:
                sign = element.get('signature')
                if sign in ['C', 'O', 'C.', 'O.']:
                    # Convert to MEI mensuration element
                    converted_element.tag = '{' + self.MEI_NS + '}mensur'
                    converted_element.set('sign', sign[0])  # C or O
                    if '.' in sign:
                        converted_element.set('dot', 'true')
                        
        # Handle MEI-specific features when converting to CMME
        elif source_format == 'mei' and target_format == 'cmme':
            # Handle mansuration elements
            if element.tag.endswith('mensur'):
                sign = element.get('sign', '')
                dot = element.get('dot', 'false')
                
                if sign in ['C', 'O']:
                    converted_element.tag = 'time'
                    sign_value = sign
                    if dot == 'true':
                        sign_value += '.'
                    converted_element.set('signature', sign_value)
                    
            # Handle ligatures
            ligature_tag = '{' + self.MEI_NS + '}ligature' if element.tag.startswith('{') else 'ligature'
            ligature = element.find(ligature_tag)
            if ligature is not None:
                cmme_ligature = etree.SubElement(converted_element, 'ligature')
                if 'form' in ligature.attrib:
                    form = ligature.get('form')
                    # Map MEI forms to CMME positions
                    position_map = {'initial': 'start', 'terminal': 'end', 'medial': 'middle'}
                    cmme_ligature.set('position', position_map.get(form, form))
                    
            # Handle accidentals with musica ficta
            if (element.tag.endswith('note') or element.tag == 'note') and 'accid.ges' in element.attrib:
                # Add dot notation to pitch for musica ficta in CMME
                if 'pitch' in converted_element.attrib:
                    pitch = converted_element.get('pitch')
                    if not '.' in pitch:
                        accid_ges = element.get('accid.ges')
                        if accid_ges == 's':
                            modified_pitch = pitch[0] + '.#' + pitch[-1]
                        elif accid_ges == 'f':
                            modified_pitch = pitch[0] + '.b' + pitch[-1]
                        else:
                            modified_pitch = pitch[0] + '.' + pitch[-1]
                        converted_element.set('pitch', modified_pitch)
        
        return converted_element
    
    def _get_mei_duration_value(self, cmme_duration: str) -> str:
        """Convert CMME duration value to MEI dur value."""
        # Parse duration, handling dot notation
        if ' dot' in cmme_duration:
            base_dur = cmme_duration.split(' ')[0]
        else:
            base_dur = cmme_duration
            
        # Map CMME duration names to MEI values
        duration_map = {
            'maxima': 'maxima',
            'longa': 'long',
            'brevis': 'breve',
            'whole': '1',
            'half': '2',
            'quarter': '4',
            'eighth': '8',
            'sixteenth': '16',
            '32nd': '32',
            '64th': '64',
            '128th': '128'
        }
        
        return duration_map.get(base_dur, base_dur)

    def _get_cmme_duration_value(self, mei_duration: str) -> str:
        """Convert MEI dur value to CMME duration value."""
        # Map MEI duration values to CMME names
        duration_map = {
            'maxima': 'maxima',
            'long': 'longa',
            'breve': 'brevis',
            '1': 'whole',
            '2': 'half',
            '4': 'quarter',
            '8': 'eighth',
            '16': 'sixteenth',
            '32': '32nd',
            '64': '64th',
            '128': '128th'
        }
        
        return duration_map.get(mei_duration, mei_duration)

    def _get_cmme_duration_with_dots(self, duration: str, dots: str) -> str:
        """Combine MEI duration and dots into CMME duration value."""
        base_duration = self._get_cmme_duration_value(duration)
        
        # Add dot suffix based on dots count
        if dots == '1':
            return f"{base_duration} dot"
        elif dots == '2':
            return f"{base_duration} double-dot"
        elif dots == '3':
            return f"{base_duration} triple-dot"
        else:
            return base_duration

    def validate_format(self, filename: str, format_type: str) -> bool:
        """
        Validate if file format matches expected type.

        Args:
            filename (str): Name of the file
            format_type (str): Expected format type

        Returns:
            bool: True if format is valid, False otherwise
        """
        try:
            if format_type not in self.supported_formats:
                return False

            # Check file extension - support for multiple extensions per format
            extension = os.path.splitext(filename)[1].lower()
            valid_extensions = self.supported_formats[format_type]['extensions']
            if extension not in valid_extensions:
                return False

            return True
        except Exception as e:
            self.logger.error(f"Format validation error: {str(e)}")
            return False

    def detect_xml_format(self, xml_content: str) -> Optional[str]:
        """
        Detect whether the XML content is MEI or CMME format.
        
        Args:
            xml_content (str): XML content to analyze
            
        Returns:
            Optional[str]: 'mei' or 'cmme' based on content analysis, or None if format cannot be determined
        """
        try:
            # Preprocess XML content
            xml_content = self._preprocess_xml_content(xml_content)
            
            # Check for MEI namespace or root element
            if (f'xmlns="{self.MEI_NS}"' in xml_content or 
                '<mei' in xml_content or 
                f'{{{self.MEI_NS}}}mei' in xml_content):
                return 'mei'
                
            # Check for CMME root element
            if '<cmme' in xml_content:
                return 'cmme'
                
            # If unclear, parse and check root element
            try:
                root = etree.fromstring(xml_content.encode('utf-8'))
                root_tag = root.tag
                if '}' in root_tag:
                    root_tag = root_tag.split('}', 1)[1]
                    
                if root_tag == 'mei':
                    return 'mei'
                elif root_tag == 'cmme':
                    return 'cmme'
                
                # Check for characteristic elements
                if root.find('.//*[@clef.shape]') is not None or root.find('.//*staffDef') is not None:
                    return 'mei'
                elif root.find('.//clef') is not None:
                    return 'cmme'
            except:
                # Parsing failed, try simpler checks
                pass
                
            # If still unclear, attempt heuristic detection
            mei_indicators = ['<mei:', '<staffDef', '<meiHead', '<measure n=', '<layer n=']
            cmme_indicators = ['<staff name=', '<measure number=', '<metadata>', '<clef shape=']
            
            mei_count = sum(1 for indicator in mei_indicators if indicator in xml_content)
            cmme_count = sum(1 for indicator in cmme_indicators if indicator in xml_content)
            
            if mei_count > cmme_count:
                return 'mei'
            elif cmme_count > mei_count:
                return 'cmme'
                
            # If still unclear, return None
            return None
        except Exception as e:
            self.logger.error(f"Format detection error: {str(e)}")
            return None

    def get_mime_type(self, format_type: str) -> str:
        """
        Get MIME type for format.

        Args:
            format_type (str): Format type

        Returns:
            str: MIME type for the format
        """
        return self.supported_formats.get(format_type, {}).get('mime', 'text/plain')
    
    def extract_metadata(self, data: str, format_type: str) -> Dict:
        """
        Extract metadata from CMME, MEI, or JSON data.

        Args:
            data (str): Input data
            format_type (str): Format type ('cmme', 'mei', or 'json')

        Returns:
            Dict: Extracted metadata

        Raises:
            ValueError: If metadata extraction fails
        """
        try:
            return self._extract_metadata_from_content(data, format_type)
        except Exception as e:
            self.logger.error(f"Metadata extraction error: {str(e)}")
            self.logger.error(traceback.format_exc())
            raise ValueError(f"Metadata extraction error: {str(e)}")

    def validate_and_transform(self, data: str, conversion_type: str) -> str:
        """
        Validates and transforms data based on the specified conversion type.

        Args:
            data (str): Input data
            conversion_type (str): Conversion type (e.g., 'cmme-to-mei')

        Returns:
            str: Transformed data

        Raises:
            ValueError: If validation or transformation fails
        """
        try:
            source_format, target_format = conversion_type.split('-to-')
            
            # Check if the formats are supported
            if source_format not in self.supported_formats or target_format not in self.supported_formats:
                raise ValueError(f"Unsupported conversion: {conversion_type}")
                
            # For XML formats, try to detect format if not matching expected type
            if source_format in ['cmme', 'mei'] and isinstance(data, str):
                detected_format = self.detect_xml_format(data)
                if detected_format and detected_format != source_format:
                    self.logger.warning(f"Format mismatch: Specified '{source_format}' but detected '{detected_format}'")
                    # Auto-correct the conversion type
                    conversion_type = f"{detected_format}-to-{target_format}"
                    source_format = detected_format
            
            # Validate input format
            if source_format == 'json':
                try:
                    self.json_converter.validate_json(self.serializer.deserialize(data))
                except Exception as e:
                    self.logger.warning(f"JSON validation failed: {str(e)}")
            elif source_format == 'cmme':
                try:
                    self.cmme_parser.validate(self.serializer.deserialize(data))
                except Exception as e:
                    self.logger.warning(f"CMME validation failed: {str(e)}")
            elif source_format == 'mei':
                try:
                    self.mei_parser.validate(self.serializer.deserialize(data))
                except Exception as e:
                    self.logger.warning(f"MEI validation failed: {str(e)}")
            
            # Even if validation fails, attempt transformation (might be partial conversion)
            return self.transform(data, conversion_type)
        except Exception as e:
            self.logger.error(f"Validation and transformation error: {str(e)}")
            self.logger.error(traceback.format_exc())
            raise ValueError(f"Validation and transformation error: {str(e)}")

    def get_supported_formats(self) -> Dict[str, Dict]:
        """
        Get information about supported formats.

        Returns:
            Dict[str, Dict]: Dictionary of supported formats and their properties
        """
        return self.supported_formats

    def get_format_extensions(self, format_type: str) -> List[str]:
        """
        Get supported file extensions for a format.

        Args:
            format_type (str): Format type

        Returns:
            List[str]: List of supported extensions
        """
        return self.supported_formats.get(format_type, {}).get('extensions', [])

    def validate_metadata(self, metadata: Dict) -> bool:
        """
        Validate metadata structure.

        Args:
            metadata (Dict): Metadata to validate

        Returns:
            bool: True if valid, False otherwise
        """
        try:
            if not isinstance(metadata, dict):
                return False
            
            # Check for required fields
            required_fields = {'title', 'composer'}
            if not all(field in metadata for field in required_fields):
                return False
            
            # Validate field types
            for key, value in metadata.items():
                if not isinstance(value, (str, int, float, bool, type(None))):
                    return False
            
            return True
        except Exception as e:
            self.logger.error(f"Metadata validation error: {str(e)}")
            return False

    def merge_metadata(self, source_metadata: Dict, target_metadata: Dict) -> Dict:
        """
        Merge two metadata dictionaries.

        Args:
            source_metadata (Dict): Source metadata
            target_metadata (Dict): Target metadata

        Returns:
            Dict: Merged metadata
        """
        merged = target_metadata.copy()
        for key, value in source_metadata.items():
            if key not in merged or not merged[key]:
                merged[key] = value
        return merged

    def clean_metadata(self, metadata: Dict) -> Dict:
        """
        Clean and normalize metadata.

        Args:
            metadata (Dict): Metadata to clean

        Returns:
            Dict: Cleaned metadata
        """
        cleaned = {}
        for key, value in metadata.items():
            # Normalize key
            clean_key = key.lower().strip().replace(' ', '_')
            # Clean value
            if isinstance(value, str):
                clean_value = value.strip()
                if clean_value:
                    cleaned[clean_key] = clean_value
            else:
                cleaned[clean_key] = value
        return cleaned