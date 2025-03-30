"""
JSON Converter Module.

This module provides conversion functionality between JSON and music notation XML formats.
"""

from lxml import etree
from typing import Dict, Any, Union, List, Optional
import json
import logging
import re


class JSONConverter:
    """
    Converter for transforming between JSON and music notation XML formats.
    
    This class handles conversions between JSON and structured XML formats
    like CMME and MEI, with support for preserving metadata and structure.
    
    Attributes:
        logger (logging.Logger): Logger instance for the converter
        MEI_NS (str): MEI XML namespace
    """
    
    # MEI namespace
    MEI_NS = "http://www.music-encoding.org/ns/mei"
    
    def __init__(self):
        """Initialize the JSON converter."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def validate_json(self, data: Union[str, Dict]) -> bool:
        """
        Validate JSON data structure.

        Args:
            data (Union[str, Dict]): JSON data as string or dict

        Returns:
            bool: True if valid, False otherwise

        Raises:
            ValueError: If validation fails with specific error
        """
        try:
            # Convert string to dict if needed
            if isinstance(data, str):
                json_obj = json.loads(data)
            else:
                json_obj = data
            
            # Check if it's a dictionary
            if not isinstance(json_obj, dict):
                raise ValueError("JSON root must be an object")
            
            # Check for required fields
            if 'metadata' not in json_obj:
                raise ValueError("Missing required 'metadata' field")
            
            if 'parts' not in json_obj:
                raise ValueError("Missing required 'parts' field")
            
            if not isinstance(json_obj['parts'], list):
                raise ValueError("'parts' field must be an array")
            
            # Validate parts
            for part_idx, part in enumerate(json_obj['parts']):
                if not isinstance(part, dict):
                    raise ValueError(f"Part at index {part_idx} must be an object")
                
                if 'id' not in part and 'name' not in part:
                    raise ValueError(f"Part at index {part_idx} must have 'id' or 'name'")
                
                if 'measures' not in part or not isinstance(part['measures'], list):
                    raise ValueError(f"Part at index {part_idx} must have 'measures' array")
                
                # Validate measures
                for measure_idx, measure in enumerate(part['measures']):
                    if not isinstance(measure, dict):
                        raise ValueError(f"Measure at index {measure_idx} in part {part_idx} must be an object")
                    
                    if 'events' not in measure and 'notes' not in measure and 'contents' not in measure:
                        raise ValueError(f"Measure at index {measure_idx} in part {part_idx} must have 'events', 'notes', or 'contents' field")
            
            return True
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON syntax: {str(e)}")
        except Exception as e:
            self.logger.error(f"JSON validation error: {str(e)}")
            raise ValueError(f"Invalid JSON structure: {str(e)}")
    
    def json_to_cmme(self, data: Union[str, Dict]) -> str:
        """
        Convert JSON to CMME XML.

        Args:
            data (Union[str, Dict]): JSON data as string or dict

        Returns:
            str: CMME XML string

        Raises:
            ValueError: If conversion fails
        """
        try:
            # Convert string to dict if needed
            if isinstance(data, str):
                json_obj = json.loads(data)
            else:
                json_obj = data
            
            # Create root element
            root = etree.Element('cmme')
            
            # Add metadata
            if 'metadata' in json_obj and json_obj['metadata']:
                metadata_elem = etree.SubElement(root, 'metadata')
                for key, value in json_obj['metadata'].items():
                    if value is not None:
                        meta_field = etree.SubElement(metadata_elem, key)
                        meta_field.text = str(value)
            
            # Create score element
            score = etree.SubElement(root, 'score')
            
            # Add parts/staves
            for part in json_obj.get('parts', []):
                staff = etree.SubElement(score, 'staff')
                
                # Set staff attributes
                if 'name' in part:
                    staff.set('name', str(part['name']))
                if 'id' in part:
                    staff.set('id', str(part['id']))
                
                # Add clef if present
                if 'clef' in part and part['clef']:
                    clef = etree.SubElement(staff, 'clef')
                    if isinstance(part['clef'], dict):
                        if 'shape' in part['clef']:
                            clef.set('shape', str(part['clef']['shape']))
                        if 'line' in part['clef']:
                            clef.set('line', str(part['clef']['line']))
                    elif isinstance(part['clef'], str):
                        # Handle string representation like "G2"
                        if part['clef'][0] in ['G', 'F', 'C'] and part['clef'][1:].isdigit():
                            clef.set('shape', part['clef'][0])
                            clef.set('line', part['clef'][1:])
                
                # Add key signature if present
                if 'key' in part and part['key']:
                    key = etree.SubElement(staff, 'key')
                    if isinstance(part['key'], dict) and 'signature' in part['key']:
                        key.set('signature', str(part['key']['signature']))
                    elif isinstance(part['key'], dict) and 'sig' in part['key']:
                        key.set('signature', str(part['key']['sig']))
                    elif isinstance(part['key'], str) or isinstance(part['key'], int):
                        key.set('signature', str(part['key']))
                
                # Add time signature if present
                if 'time' in part and part['time']:
                    time = etree.SubElement(staff, 'time')
                    if isinstance(part['time'], dict) and 'signature' in part['time']:
                        time.set('signature', str(part['time']['signature']))
                    elif isinstance(part['time'], dict) and 'count' in part['time'] and 'unit' in part['time']:
                        time.set('signature', f"{part['time']['count']}/{part['time']['unit']}")
                    elif isinstance(part['time'], str):
                        time.set('signature', part['time'])
                elif 'meter' in part and part['meter']:
                    time = etree.SubElement(staff, 'time')
                    if isinstance(part['meter'], dict):
                        if 'count' in part['meter'] and 'unit' in part['meter']:
                            time.set('signature', f"{part['meter']['count']}/{part['meter']['unit']}")
                        elif 'sym' in part['meter']:
                            time.set('signature', str(part['meter']['sym']))
                
                # Process measures
                for measure in part.get('measures', []):
                    measure_elem = etree.SubElement(staff, 'measure')
                    
                    # Set measure number
                    if 'number' in measure:
                        measure_elem.set('number', str(measure['number']))
                    elif 'n' in measure:
                        measure_elem.set('number', str(measure['n']))
                    
                    # Process measure contents
                    events = measure.get('events', [])
                    if not events:
                        events = measure.get('notes', [])
                    if not events:
                        events = measure.get('contents', [])
                    
                    for event in events:
                        if isinstance(event, dict):
                            event_type = event.get('type', '').lower()
                            
                            if event_type == 'note' or 'pitch' in event:
                                # Create note element
                                note = etree.SubElement(measure_elem, 'note')
                                
                                # Set pitch
                                if 'pitch' in event:
                                    note.set('pitch', str(event['pitch']))
                                elif 'pname' in event and 'oct' in event:
                                    # Convert from MEI pname+oct to CMME pitch
                                    pname = event['pname'].upper()
                                    oct = str(event['oct'])
                                    pitch = pname + oct
                                    
                                    # Handle accidentals
                                    if 'accid' in event:
                                        accid = event['accid']
                                        if accid == 's':
                                            pitch = pname + '#' + oct
                                        elif accid == 'f':
                                            pitch = pname + 'b' + oct
                                    
                                    note.set('pitch', pitch)
                                
                                # Set duration
                                if 'duration' in event:
                                    note.set('duration', str(event['duration']))
                                elif 'dur' in event:
                                    dur = event['dur']
                                    # Convert MEI duration to CMME
                                    dur_map = {
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
                                    
                                    duration = dur_map.get(str(dur), str(dur))
                                    
                                    # Add dots if present
                                    if 'dots' in event:
                                        dots = int(event['dots'])
                                        if dots == 1:
                                            duration += ' dot'
                                        elif dots == 2:
                                            duration += ' double-dot'
                                        elif dots == 3:
                                            duration += ' triple-dot'
                                    
                                    note.set('duration', duration)
                                
                                # Copy other attributes
                                for key, value in event.items():
                                    if key not in ['type', 'pitch', 'duration', 'pname', 'oct', 'accid', 'dur', 'dots', 'artic']:
                                        note.set(key, str(value))
                                
                                # Handle articulations
                                if 'artic' in event:
                                    artics = event['artic']
                                    if isinstance(artics, list):
                                        for artic_value in artics:
                                            artic = etree.SubElement(note, 'articulation')
                                            artic.set('type', str(artic_value))
                                    else:
                                        artic = etree.SubElement(note, 'articulation')
                                        artic.set('type', str(artics))
                            
                            elif event_type == 'rest':
                                # Create rest element
                                rest = etree.SubElement(measure_elem, 'rest')
                                
                                # Set duration
                                if 'duration' in event:
                                    rest.set('duration', str(event['duration']))
                                elif 'dur' in event:
                                    dur = event['dur']
                                    # Convert MEI duration to CMME
                                    dur_map = {
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
                                    
                                    duration = dur_map.get(str(dur), str(dur))
                                    
                                    # Add dots if present
                                    if 'dots' in event:
                                        dots = int(event['dots'])
                                        if dots == 1:
                                            duration += ' dot'
                                        elif dots == 2:
                                            duration += ' double-dot'
                                        elif dots == 3:
                                            duration += ' triple-dot'
                                    
                                    rest.set('duration', duration)
                                
                                # Copy other attributes
                                for key, value in event.items():
                                    if key not in ['type', 'duration', 'dur', 'dots']:
                                        rest.set(key, str(value))
                            
                            elif event_type == 'chord':
                                # Create chord element
                                chord = etree.SubElement(measure_elem, 'chord')
                                
                                # Set chord attributes
                                for key, value in event.items():
                                    if key not in ['type', 'notes', 'dur', 'dots']:
                                        chord.set(key, str(value))
                                
                                # Add chord notes
                                for note_data in event.get('notes', []):
                                    note = etree.SubElement(chord, 'note')
                                    
                                    # Set pitch
                                    if 'pitch' in note_data:
                                        note.set('pitch', str(note_data['pitch']))
                                    elif 'pname' in note_data and 'oct' in note_data:
                                        # Convert from MEI pname+oct to CMME pitch
                                        pname = note_data['pname'].upper()
                                        oct = str(note_data['oct'])
                                        pitch = pname + oct
                                        
                                        # Handle accidentals
                                        if 'accid' in note_data:
                                            accid = note_data['accid']
                                            if accid == 's':
                                                pitch = pname + '#' + oct
                                            elif accid == 'f':
                                                pitch = pname + 'b' + oct
                                        
                                        note.set('pitch', pitch)
                                    
                                    # Inherit duration from chord if not specified on note
                                    if 'duration' not in note_data and 'dur' not in note_data:
                                        if 'duration' in event:
                                            note.set('duration', str(event['duration']))
                                        elif 'dur' in event:
                                            dur = event['dur']
                                            # Convert MEI duration to CMME
                                            dur_map = {
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
                                            
                                            duration = dur_map.get(str(dur), str(dur))
                                            
                                            # Add dots if present
                                            if 'dots' in event:
                                                dots = int(event['dots'])
                                                if dots == 1:
                                                    duration += ' dot'
                                                elif dots == 2:
                                                    duration += ' double-dot'
                                                elif dots == 3:
                                                    duration += ' triple-dot'
                                            
                                            note.set('duration', duration)
                                    
                                    # Copy other attributes
                                    for key, value in note_data.items():
                                        if key not in ['pitch', 'duration', 'pname', 'oct', 'accid', 'dur', 'dots']:
                                            note.set(key, str(value))
                            
                            else:
                                # Handle other event types (e.g., barline, clef change)
                                event_elem = etree.SubElement(measure_elem, event_type)
                                
                                # Copy attributes
                                for key, value in event.items():
                                    if key != 'type' and value is not None:
                                        event_elem.set(key, str(value))
            
            # Return as XML string
            return etree.tostring(root, encoding='unicode', pretty_print=True)
        except Exception as e:
            self.logger.error(f"Failed to convert JSON to CMME: {str(e)}")
            raise ValueError(f"JSON to CMME conversion failed: {str(e)}")
    
    def json_to_mei(self, data: Union[str, Dict]) -> str:
        """
        Convert JSON to MEI XML.

        Args:
            data (Union[str, Dict]): JSON data as string or dict

        Returns:
            str: MEI XML string

        Raises:
            ValueError: If conversion fails
        """
        try:
            # Convert string to dict if needed
            if isinstance(data, str):
                json_obj = json.loads(data)
            else:
                json_obj = data
            
            # Create root element with namespace
            root = etree.Element('{' + self.MEI_NS + '}mei')
            
            # Add metadata
            if 'metadata' in json_obj and json_obj['metadata']:
                meiHead = etree.SubElement(root, '{' + self.MEI_NS + '}meiHead')
                fileDesc = etree.SubElement(meiHead, '{' + self.MEI_NS + '}fileDesc')
                titleStmt = etree.SubElement(fileDesc, '{' + self.MEI_NS + '}titleStmt')
                
                # Add title and composer
                if 'title' in json_obj['metadata']:
                    title = etree.SubElement(titleStmt, '{' + self.MEI_NS + '}title')
                    title.text = str(json_obj['metadata']['title'])
                
                if 'composer' in json_obj['metadata']:
                    composer = etree.SubElement(titleStmt, '{' + self.MEI_NS + '}composer')
                    composer.text = str(json_obj['metadata']['composer'])
                
                # Add other metadata
                pubStmt = etree.SubElement(fileDesc, '{' + self.MEI_NS + '}pubStmt')
                for key, value in json_obj['metadata'].items():
                    if key not in ['title', 'composer'] and value is not None:
                        elem = etree.SubElement(pubStmt, '{' + self.MEI_NS + '}' + key)
                        elem.text = str(value)
            
            # Create music structure
            music = etree.SubElement(root, '{' + self.MEI_NS + '}music')
            body = etree.SubElement(music, '{' + self.MEI_NS + '}body')
            mdiv = etree.SubElement(body, '{' + self.MEI_NS + '}mdiv')
            score = etree.SubElement(mdiv, '{' + self.MEI_NS + '}score')
            
            # Add staff definitions
            scoreDef = etree.SubElement(score, '{' + self.MEI_NS + '}scoreDef')
            staffGrp = etree.SubElement(scoreDef, '{' + self.MEI_NS + '}staffGrp')
            
            # Add parts
            for part_idx, part in enumerate(json_obj.get('parts', [])):
                staff_n = part.get('id', str(part_idx + 1))
                
                # Add staff definition
                staffDef = etree.SubElement(staffGrp, '{' + self.MEI_NS + '}staffDef')
                staffDef.set('n', staff_n)
                staffDef.set('lines', part.get('lines', '5'))
                
                # Add staff label
                if 'name' in part and part['name']:
                    label = etree.SubElement(staffDef, '{' + self.MEI_NS + '}label')
                    label.text = str(part['name'])
                
                # Add clef information
                if 'clef' in part and part['clef']:
                    if isinstance(part['clef'], dict):
                        if 'shape' in part['clef']:
                            staffDef.set('clef.shape', str(part['clef']['shape']))
                        if 'line' in part['clef']:
                            staffDef.set('clef.line', str(part['clef']['line']))
                    elif isinstance(part['clef'], str):
                        # Handle string representation like "G2"
                        if part['clef'][0] in ['G', 'F', 'C'] and part['clef'][1:].isdigit():
                            staffDef.set('clef.shape', part['clef'][0])
                            staffDef.set('clef.line', part['clef'][1:])
                
                # Add key signature
                if 'key' in part and part['key']:
                    if isinstance(part['key'], dict) and 'signature' in part['key']:
                        staffDef.set('key.sig', str(part['key']['signature']))
                    elif isinstance(part['key'], dict) and 'sig' in part['key']:
                        staffDef.set('key.sig', str(part['key']['sig']))
                    elif isinstance(part['key'], str) or isinstance(part['key'], int):
                        staffDef.set('key.sig', str(part['key']))
                
                # Add time/meter signature
                if 'time' in part and part['time']:
                    if isinstance(part['time'], dict) and 'signature' in part['time']:
                        sig = part['time']['signature']
                        if re.match(r'\d+/\d+', sig):
                            parts = sig.split('/')
                            staffDef.set('meter.count', parts[0])
                            staffDef.set('meter.unit', parts[1])
                        elif sig in ['C', 'O', 'C.', 'O.']:
                            staffDef.set('meter.sym', sig)
                    elif isinstance(part['time'], dict) and 'count' in part['time'] and 'unit' in part['time']:
                        staffDef.set('meter.count', str(part['time']['count']))
                        staffDef.set('meter.unit', str(part['time']['unit']))
                    elif isinstance(part['time'], str):
                        if re.match(r'\d+/\d+', part['time']):
                            parts = part['time'].split('/')
                            staffDef.set('meter.count', parts[0])
                            staffDef.set('meter.unit', parts[1])
                        elif part['time'] in ['C', 'O', 'C.', 'O.']:
                            staffDef.set('meter.sym', part['time'])
                elif 'meter' in part and part['meter']:
                    if isinstance(part['meter'], dict):
                        if 'count' in part['meter'] and 'unit' in part['meter']:
                            staffDef.set('meter.count', str(part['meter']['count']))
                            staffDef.set('meter.unit', str(part['meter']['unit']))
                        elif 'sym' in part['meter']:
                            staffDef.set('meter.sym', str(part['meter']['sym']))
            
            # Add section for musical content
            section = etree.SubElement(score, '{' + self.MEI_NS + '}section')
            
            # Get max number of measures across parts
            max_measures = 0
            for part in json_obj.get('parts', []):
                max_measures = max(max_measures, len(part.get('measures', [])))
            
            # Process measures
            for measure_idx in range(max_measures):
                measure = etree.SubElement(section, '{' + self.MEI_NS + '}measure')
                measure.set('n', str(measure_idx + 1))
                
                # Process each part's measure
                for part_idx, part in enumerate(json_obj.get('parts', [])):
                    if measure_idx < len(part.get('measures', [])):
                        measure_data = part['measures'][measure_idx]
                        
                        # Set measure number if specified
                        if 'number' in measure_data:
                            measure.set('n', str(measure_data['number']))
                        elif 'n' in measure_data:
                            measure.set('n', str(measure_data['n']))
                        
                        staff_n = part.get('id', str(part_idx + 1))
                        staff = etree.SubElement(measure, '{' + self.MEI_NS + '}staff')
                        staff.set('n', staff_n)
                        
                        # Create a default layer
                        layer = etree.SubElement(staff, '{' + self.MEI_NS + '}layer')
                        layer.set('n', '1')
                        
                        # Process events
                        events = measure_data.get('events', [])
                        if not events:
                            events = measure_data.get('notes', [])
                        if not events:
                            events = measure_data.get('contents', [])
                        
                        for event in events:
                            if isinstance(event, dict):
                                event_type = event.get('type', '').lower()
                                
                                # Determine which layer this event belongs to
                                layer_n = event.get('layer', '1')
                                current_layer = layer
                                
                                # Find or create the appropriate layer
                                if layer_n != '1':
                                    existing_layer = None
                                    for l in staff.findall('{' + self.MEI_NS + '}layer'):
                                        if l.get('n') == layer_n:
                                            existing_layer = l
                                            break
                                    
                                    if existing_layer is None:
                                        # Create a new layer
                                        new_layer = etree.SubElement(staff, '{' + self.MEI_NS + '}layer')
                                        new_layer.set('n', layer_n)
                                        current_layer = new_layer
                                    else:
                                        current_layer = existing_layer
                                
                                if event_type == 'note' or 'pname' in event or 'pitch' in event:
                                    # Create note element
                                    note = etree.SubElement(current_layer, '{' + self.MEI_NS + '}note')
                                    
                                    # Set pitch information
                                    if 'pname' in event and 'oct' in event:
                                        note.set('pname', str(event['pname']).lower())
                                        note.set('oct', str(event['oct']))
                                        
                                        # Set accidental if present
                                        if 'accid' in event:
                                            note.set('accid', str(event['accid']))
                                    elif 'pitch' in event:
                                        # Convert CMME pitch to MEI pname+oct
                                        pitch = event['pitch']
                                        match = re.match(r'^([A-G])(\.)?([#b])?(\d+)$', pitch)
                                        if match:
                                            pname, dot, accid, oct = match.groups()
                                            note.set('pname', pname.lower())
                                            note.set('oct', oct)
                                            
                                            if accid:
                                                note.set('accid', 's' if accid == '#' else 'f')
                                            
                                            if dot:
                                                # Handle musica ficta
                                                note.set('accid.ges', 's' if accid == '#' else ('f' if accid == 'b' else 'n'))
                                    
                                    # Set duration
                                    if 'dur' in event:
                                        note.set('dur', str(event['dur']))
                                        if 'dots' in event:
                                            note.set('dots', str(event['dots']))
                                    elif 'duration' in event:
                                        # Convert CMME duration to MEI
                                        duration = event['duration']
                                        dur_map = {
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
                                        
                                        # Handle dots in duration string
                                        dots = 0
                                        if ' dot' in duration:
                                            base_dur = duration.split(' dot')[0].strip()
                                            if 'double-dot' in duration:
                                                dots = 2
                                            elif 'triple-dot' in duration:
                                                dots = 3
                                            else:
                                                dots = 1
                                        else:
                                            base_dur = duration
                                        
                                        note.set('dur', dur_map.get(base_dur, base_dur))
                                        if dots > 0:
                                            note.set('dots', str(dots))
                                    
                                    # Copy other attributes
                                    for key, value in event.items():
                                        if key not in ['type', 'pitch', 'duration', 'pname', 'oct', 'accid', 'dur', 'dots', 'layer', 'artic', 'articulations']:
                                            note.set(key, str(value))
                                    
                                    # Handle articulations
                                    if 'artic' in event:
                                        artics = event['artic']
                                        if isinstance(artics, list):
                                            for artic_value in artics:
                                                artic = etree.SubElement(note, '{' + self.MEI_NS + '}artic')
                                                artic.set('artic', str(artic_value))
                                        else:
                                            artic = etree.SubElement(note, '{' + self.MEI_NS + '}artic')
                                            artic.set('artic', str(artics))
                                    elif 'articulations' in event:
                                        for artic_data in event['articulations']:
                                            artic = etree.SubElement(note, '{' + self.MEI_NS + '}artic')
                                            if isinstance(artic_data, dict) and 'type' in artic_data:
                                                artic.set('artic', str(artic_data['type']))
                                                
                                                # Copy other articulation attributes
                                                for key, value in artic_data.items():
                                                    if key != 'type':
                                                        artic.set(key, str(value))
                                            else:
                                                artic.set('artic', str(artic_data))
                                
                                elif event_type == 'rest':
                                    # Create rest element
                                    rest = etree.SubElement(current_layer, '{' + self.MEI_NS + '}rest')
                                    
                                    # Set duration
                                    if 'dur' in event:
                                        rest.set('dur', str(event['dur']))
                                        if 'dots' in event:
                                            rest.set('dots', str(event['dots']))
                                    elif 'duration' in event:
                                        # Convert CMME duration to MEI
                                        duration = event['duration']
                                        dur_map = {
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
                                        
                                        # Handle dots in duration string
                                        dots = 0
                                        if ' dot' in duration:
                                            base_dur = duration.split(' dot')[0].strip()
                                            if 'double-dot' in duration:
                                                dots = 2
                                            elif 'triple-dot' in duration:
                                                dots = 3
                                            else:
                                                dots = 1
                                        else:
                                            base_dur = duration
                                        
                                        rest.set('dur', dur_map.get(base_dur, base_dur))
                                        if dots > 0:
                                            rest.set('dots', str(dots))
                                    
                                    # Copy other attributes
                                    for key, value in event.items():
                                        if key not in ['type', 'duration', 'dur', 'dots', 'layer']:
                                            rest.set(key, str(value))
                                
                                elif event_type == 'chord':
                                    # Create chord element
                                    chord = etree.SubElement(current_layer, '{' + self.MEI_NS + '}chord')
                                    
                                    # Set duration for the chord
                                    if 'dur' in event:
                                        chord.set('dur', str(event['dur']))
                                        if 'dots' in event:
                                            chord.set('dots', str(event['dots']))
                                    elif 'duration' in event:
                                        # Convert CMME duration to MEI
                                        duration = event['duration']
                                        dur_map = {
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
                                        
                                        # Handle dots in duration string
                                        dots = 0
                                        if ' dot' in duration:
                                            base_dur = duration.split(' dot')[0].strip()
                                            if 'double-dot' in duration:
                                                dots = 2
                                            elif 'triple-dot' in duration:
                                                dots = 3
                                            else:
                                                dots = 1
                                        else:
                                            base_dur = duration
                                        
                                        chord.set('dur', dur_map.get(base_dur, base_dur))
                                        if dots > 0:
                                            chord.set('dots', str(dots))
                                    
                                    # Copy chord attributes
                                    for key, value in event.items():
                                        if key not in ['type', 'notes', 'duration', 'dur', 'dots', 'layer']:
                                            chord.set(key, str(value))
                                    
                                    # Add notes to chord
                                    for note_data in event.get('notes', []):
                                        note = etree.SubElement(chord, '{' + self.MEI_NS + '}note')
                                        
                                        # Set pitch information
                                        if 'pname' in note_data and 'oct' in note_data:
                                            note.set('pname', str(note_data['pname']).lower())
                                            note.set('oct', str(note_data['oct']))
                                            
                                            # Set accidental if present
                                            if 'accid' in note_data:
                                                note.set('accid', str(note_data['accid']))
                                        elif 'pitch' in note_data:
                                            # Convert CMME pitch to MEI pname+oct
                                            pitch = note_data['pitch']
                                            match = re.match(r'^([A-G])(\.)?([#b])?(\d+)$', pitch)
                                            if match:
                                                pname, dot, accid, oct = match.groups()
                                                note.set('pname', pname.lower())
                                                note.set('oct', oct)
                                                
                                                if accid:
                                                    note.set('accid', 's' if accid == '#' else 'f')
                                                
                                                if dot:
                                                    # Handle musica ficta
                                                    note.set('accid.ges', 's' if accid == '#' else ('f' if accid == 'b' else 'n'))
                                        
                                        # Copy other note attributes
                                        for key, value in note_data.items():
                                            if key not in ['pname', 'oct', 'accid', 'pitch']:
                                                note.set(key, str(value))
                                
                                elif event_type in ['mrest', 'mspace']:
                                    # Create multi-measure rest/space element
                                    elem = etree.SubElement(current_layer, '{' + self.MEI_NS + '}' + event_type)
                                    
                                    # Copy attributes
                                    for key, value in event.items():
                                        if key not in ['type', 'layer']:
                                            elem.set(key, str(value))
                                
                                elif event_type in ['clef', 'keysig', 'meter', 'keysig', 'metersig', 'dir', 'dynam', 'tempo', 'barline', 'fermata', 'breath']:
                                    # Handle other musical elements
                                    # Map some common element names
                                    mei_element_map = {
                                        'keysig': 'keySig',
                                        'meter': 'meterSig',
                                        'metersig': 'meterSig',
                                        'time': 'meterSig',
                                        'barline': 'barLine',
                                        'dynamic': 'dynam'
                                    }
                                    
                                    mei_type = mei_element_map.get(event_type, event_type)
                                    elem = etree.SubElement(current_layer, '{' + self.MEI_NS + '}' + mei_type)
                                    
                                    # Copy attributes
                                    for key, value in event.items():
                                        if key not in ['type', 'layer']:
                                            elem.set(key, str(value))
                                
                                elif event_type:
                                    # Handle any other element types
                                    elem = etree.SubElement(current_layer, '{' + self.MEI_NS + '}' + event_type)
                                    
                                    # Copy attributes
                                    for key, value in event.items():
                                        if key not in ['type', 'layer']:
                                            elem.set(key, str(value))
            
            # Return as XML string
            return etree.tostring(root, encoding='unicode', pretty_print=True)
        except Exception as e:
            self.logger.error(f"Failed to convert JSON to MEI: {str(e)}")
            raise ValueError(f"JSON to MEI conversion failed: {str(e)}")
    
    def cmme_to_json(self, data: Union[str, etree._Element]) -> str:
        """
        Convert CMME XML to JSON.

        Args:
            data (Union[str, etree._Element]): CMME XML data as string or element

        Returns:
            str: JSON string

        Raises:
            ValueError: If conversion fails
        """
        try:
            # Parse string to element if needed
            if isinstance(data, str):
                try:
                    # Remove XML declaration if present
                    if data.startswith('<?xml'):
                        data = data[data.find('?>')+2:].lstrip()
                    root = etree.fromstring(data.encode('utf-8'))
                except etree.ParseError as e:
                    raise ValueError(f"Invalid XML: {str(e)}")
            else:
                root = data
            
            # Check if root is cmme
            if root.tag != 'cmme':
                raise ValueError(f"Root element must be 'cmme', got '{root.tag}'")
            
            # Create result structure
            result = {
                'format': 'cmme',
                'metadata': {},
                'parts': []
            }
            
            # Extract metadata
            metadata_elem = root.find('metadata')
            if metadata_elem is not None:
                for child in metadata_elem:
                    result['metadata'][child.tag] = child.text
            
            # Extract score content
            score = root.find('score')
            if score is not None:
                # Process staff elements (parts)
                staffs = score.findall('staff')
                
                # If no staffs found, check if there's a parts element
                if not staffs:
                    parts_elem = score.find('parts')
                    if parts_elem is not None:
                        staffs = parts_elem.findall('staff')
                
                for staff_idx, staff in enumerate(staffs):
                    part = {
                        'id': staff.get('id', str(staff_idx + 1)),
                        'name': staff.get('name', f"Staff {staff_idx + 1}"),
                        'measures': []
                    }
                    
                    # Extract clef
                    clef = staff.find('clef')
                    if clef is not None:
                        part['clef'] = {
                            'shape': clef.get('shape', 'G'),
                            'line': clef.get('line', '2')
                        }
                    
                    # Extract key
                    key = staff.find('key')
                    if key is not None:
                        part['key'] = {
                            'signature': key.get('signature', '0')
                        }
                    
                    # Extract time
                    time = staff.find('time')
                    if time is not None:
                        part['time'] = {
                            'signature': time.get('signature', '4/4')
                        }
                    
                    # Process measures
                    measures = staff.findall('measure')
                    for measure in measures:
                        m = {
                            'number': measure.get('number', ''),
                            'events': []
                        }
                        
                        # Process musical events
                        for child in measure:
                            if child.tag == 'note':
                                note = {
                                    'type': 'note',
                                    'pitch': child.get('pitch', ''),
                                    'duration': child.get('duration', '')
                                }
                                
                                # Copy other attributes
                                for attr, value in child.attrib.items():
                                    if attr not in ['pitch', 'duration']:
                                        note[attr] = value
                                
                                # Extract articulations
                                articulations = child.findall('articulation')
                                if articulations:
                                    note['articulations'] = []
                                    for artic in articulations:
                                        artic_data = {
                                            'type': artic.get('type', '')
                                        }
                                        # Copy other attributes
                                        for attr, value in artic.attrib.items():
                                            if attr != 'type':
                                                artic_data[attr] = value
                                        
                                        note['articulations'].append(artic_data)
                                
                                m['events'].append(note)
                            
                            elif child.tag == 'rest':
                                rest = {
                                    'type': 'rest',
                                    'duration': child.get('duration', '')
                                }
                                
                                # Copy other attributes
                                for attr, value in child.attrib.items():
                                    if attr != 'duration':
                                        rest[attr] = value
                                
                                m['events'].append(rest)
                            
                            elif child.tag == 'chord':
                                chord = {
                                    'type': 'chord',
                                    'notes': []
                                }
                                
                                # Get chord duration from first note if available
                                first_note = child.find('note')
                                if first_note is not None and 'duration' in first_note.attrib:
                                    chord['duration'] = first_note.get('duration')
                                
                                # Extract notes
                                for note in child.findall('note'):
                                    note_data = {
                                        'pitch': note.get('pitch', '')
                                    }
                                    # Don't duplicate duration in notes if chord has it
                                    if 'duration' not in chord:
                                        note_data['duration'] = note.get('duration', '')
                                    
                                    # Copy other attributes
                                    for attr, value in note.attrib.items():
                                        if attr not in ['pitch', 'duration'] or 'duration' not in chord:
                                            note_data[attr] = value
                                    
                                    chord['notes'].append(note_data)
                                
                                # Copy chord attributes
                                for attr, value in child.attrib.items():
                                    chord[attr] = value
                                
                                m['events'].append(chord)
                            
                            else:
                                # Handle other elements
                                event = {
                                    'type': child.tag
                                }
                                
                                # Copy attributes
                                for attr, value in child.attrib.items():
                                    event[attr] = value
                                
                                # Copy text content if any
                                if child.text and child.text.strip():
                                    event['text'] = child.text.strip()
                                
                                m['events'].append(event)
                        
                        part['measures'].append(m)
                    
                    result['parts'].append(part)
            
            # Return as JSON string
            return json.dumps(result, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to convert CMME to JSON: {str(e)}")
            raise ValueError(f"CMME to JSON conversion failed: {str(e)}")
    
    def mei_to_json(self, data: Union[str, etree._Element]) -> str:
        """
        Convert MEI XML to JSON.

        Args:
            data (Union[str, etree._Element]): MEI XML data as string or element

        Returns:
            str: JSON string

        Raises:
            ValueError: If conversion fails
        """
        try:
            # Parse string to element if needed
            if isinstance(data, str):
                try:
                    # Remove XML declaration if present
                    if data.startswith('<?xml'):
                        data = data[data.find('?>')+2:].lstrip()
                    root = etree.fromstring(data.encode('utf-8'))
                except etree.ParseError as e:
                    raise ValueError(f"Invalid XML: {str(e)}")
            else:
                root = data
            
            # Check if root is mei (with or without namespace)
            root_tag = root.tag
            if '}' in root_tag:
                root_tag = root_tag.split('}', 1)[1]
            
            if root_tag != 'mei':
                raise ValueError(f"Root element must be 'mei', got '{root_tag}'")
            
            # Helper function to handle namespaces
            def get_tag(elem):
                tag = elem.tag
                if '}' in tag:
                    return tag.split('}', 1)[1]
                return tag
            
            # Helper for finding elements with or without namespace
            def find_with_ns(elem, xpath):
                try:
                    # Try with namespace
                    result = elem.xpath(xpath, namespaces={"mei": self.MEI_NS})
                    if result:
                        return result
                    
                    # Try without namespace
                    xpath_no_ns = xpath.replace('mei:', '')
                    return elem.xpath(xpath_no_ns)
                except:
                    # Fallback for basic xpath
                    if xpath.startswith('.//mei:'):
                        tag = xpath[6:]
                        with_ns = elem.findall(f'.//{{{self.MEI_NS}}}{tag}')
                        if with_ns:
                            return with_ns
                        return elem.findall(f'.//{tag}')
                    return []
            
            # Create result structure
            result = {
                'format': 'mei',
                'metadata': {},
                'parts': []
            }
            
            # Extract metadata from meiHead
            meiHead_elements = find_with_ns(root, './/mei:meiHead')
            if meiHead_elements:
                meiHead = meiHead_elements[0]
                
                # Get title
                title_elements = find_with_ns(meiHead, './/mei:title')
                if title_elements and title_elements[0].text:
                    result['metadata']['title'] = title_elements[0].text.strip()
                
                # Get composer
                composer_elements = find_with_ns(meiHead, './/mei:composer')
                if composer_elements and composer_elements[0].text:
                    result['metadata']['composer'] = composer_elements[0].text.strip()
                
                # Get other metadata
                for elem in meiHead.iter():
                    tag = get_tag(elem)
                    if tag not in ['meiHead', 'fileDesc', 'titleStmt', 'pubStmt', 'encodingDesc', 'title', 'composer'] and elem.text:
                        text = elem.text.strip()
                        if text:
                            result['metadata'][tag] = text
            
            # Find score element
            score_elements = find_with_ns(root, './/mei:score')
            if score_elements:
                score = score_elements[0]
                
                # Extract staff definitions
                staff_defs = {}
                staffDef_elements = find_with_ns(score, './/mei:staffDef')
                for staffDef in staffDef_elements:
                    n = staffDef.get('n')
                    if not n:
                        continue
                    
                    staff_def = {
                        'n': n,
                        'lines': staffDef.get('lines', '5')
                    }
                    
                    # Get staff label
                    label_elements = find_with_ns(staffDef, './/mei:label')
                    if label_elements and label_elements[0].text:
                        staff_def['name'] = label_elements[0].text.strip()
                    
                    # Get clef information
                    clef_shape = staffDef.get('clef.shape')
                    clef_line = staffDef.get('clef.line')
                    if clef_shape or clef_line:
                        staff_def['clef'] = {
                            'shape': clef_shape or 'G',
                            'line': clef_line or '2'
                        }
                    
                    # Get key signature
                    key_sig = staffDef.get('key.sig')
                    if key_sig:
                        staff_def['key'] = {
                            'sig': key_sig
                        }
                    
                    # Get meter information
                    meter_count = staffDef.get('meter.count')
                    meter_unit = staffDef.get('meter.unit')
                    meter_sym = staffDef.get('meter.sym')
                    
                    if meter_count and meter_unit:
                        staff_def['meter'] = {
                            'count': meter_count,
                            'unit': meter_unit
                        }
                    elif meter_sym:
                        staff_def['meter'] = {
                            'sym': meter_sym
                        }
                    
                    staff_defs[n] = staff_def
                
                # Create parts for each staff definition
                for n, staff_def in staff_defs.items():
                    part = {
                        'id': n,
                        'name': staff_def.get('name', f"Staff {n}"),
                        'lines': staff_def.get('lines', '5'),
                        'clef': staff_def.get('clef'),
                        'key': staff_def.get('key'),
                        'meter': staff_def.get('meter'),
                        'measures': []
                    }
                    result['parts'].append(part)
                
                # If no staff definitions were found, try to infer from content
                if not result['parts']:
                    staff_elements = find_with_ns(score, './/mei:staff')
                    staff_numbers = set()
                    for staff in staff_elements:
                        n = staff.get('n')
                        if n:
                            staff_numbers.add(n)
                    
                    for n in sorted(staff_numbers):
                        part = {
                            'id': n,
                            'name': f"Staff {n}",
                            'measures': []
                        }
                        result['parts'].append(part)
                
                # Find section and measures
                section_elements = find_with_ns(score, './/mei:section')
                if section_elements:
                    section = section_elements[0]
                    measure_elements = find_with_ns(section, './/mei:measure')
                    
                    # Process each measure
                    for measure in measure_elements:
                        measure_n = measure.get('n', '')
                        
                        # Find all staff elements in this measure
                        staff_elements = find_with_ns(measure, './/mei:staff')
                        for staff in staff_elements:
                            staff_n = staff.get('n', '')
                            if not staff_n:
                                continue
                            
                            # Find which part this belongs to
                            part_idx = None
                            for i, part in enumerate(result['parts']):
                                if part['id'] == staff_n:
                                    part_idx = i
                                    break
                            
                            if part_idx is None:
                                # Create new part if not found
                                part = {
                                    'id': staff_n,
                                    'name': f"Staff {staff_n}",
                                    'measures': []
                                }
                                part_idx = len(result['parts'])
                                result['parts'].append(part)
                            
                            # Create or find the appropriate measure
                            measure_idx = None
                            for i, m in enumerate(result['parts'][part_idx]['measures']):
                                if m.get('n') == measure_n:
                                    measure_idx = i
                                    break
                            
                            if measure_idx is None:
                                # Create new measure
                                m = {
                                    'n': measure_n,
                                    'events': []
                                }
                                measure_idx = len(result['parts'][part_idx]['measures'])
                                result['parts'][part_idx]['measures'].append(m)
                            
                            # Get current measure
                            current_measure = result['parts'][part_idx]['measures'][measure_idx]
                            
                            # Process layers
                            layer_elements = find_with_ns(staff, './/mei:layer')
                            for layer in layer_elements:
                                layer_n = layer.get('n', '1')
                                
                                # Process all elements in the layer
                                for elem in layer:
                                    tag = get_tag(elem)
                                    
                                    if tag == 'note':
                                        # Extract note data
                                        note = {
                                            'type': 'note',
                                            'layer': layer_n
                                        }
                                        
                                        # Get pitch
                                        if 'pname' in elem.attrib and 'oct' in elem.attrib:
                                            note['pname'] = elem.get('pname')
                                            note['oct'] = elem.get('oct')
                                        
                                        # Get duration
                                        if 'dur' in elem.attrib:
                                            note['dur'] = elem.get('dur')
                                            if 'dots' in elem.attrib:
                                                note['dots'] = elem.get('dots')
                                        
                                        # Get accidental
                                        if 'accid' in elem.attrib:
                                            note['accid'] = elem.get('accid')
                                        
                                        # Copy other attributes
                                        for attr, value in elem.attrib.items():
                                            if attr not in ['pname', 'oct', 'dur', 'dots', 'accid']:
                                                note[attr] = value
                                        
                                        # Get articulations
                                        artic_elements = find_with_ns(elem, './/mei:artic')
                                        if artic_elements:
                                            note['artic'] = []
                                            for artic in artic_elements:
                                                artic_type = artic.get('artic')
                                                if artic_type:
                                                    note['artic'].append(artic_type)
                                        
                                        current_measure['events'].append(note)
                                    
                                    elif tag == 'rest':
                                        # Extract rest data
                                        rest = {
                                            'type': 'rest',
                                            'layer': layer_n
                                        }
                                        
                                        # Get duration
                                        if 'dur' in elem.attrib:
                                            rest['dur'] = elem.get('dur')
                                            if 'dots' in elem.attrib:
                                                rest['dots'] = elem.get('dots')
                                        
                                        # Copy other attributes
                                        for attr, value in elem.attrib.items():
                                            if attr not in ['dur', 'dots']:
                                                rest[attr] = value
                                        
                                        current_measure['events'].append(rest)
                                    
                                    elif tag == 'chord':
                                        # Extract chord data
                                        chord = {
                                            'type': 'chord',
                                            'layer': layer_n,
                                            'notes': []
                                        }
                                        
                                        # Get duration
                                        if 'dur' in elem.attrib:
                                            chord['dur'] = elem.get('dur')
                                            if 'dots' in elem.attrib:
                                                chord['dots'] = elem.get('dots')
                                        
                                        # Get notes
                                        note_elements = find_with_ns(elem, './/mei:note')
                                        for note_elem in note_elements:
                                            note = {}
                                            
                                            # Get pitch
                                            if 'pname' in note_elem.attrib and 'oct' in note_elem.attrib:
                                                note['pname'] = note_elem.get('pname')
                                                note['oct'] = note_elem.get('oct')
                                            
                                            # Get accidental
                                            if 'accid' in note_elem.attrib:
                                                note['accid'] = note_elem.get('accid')
                                            
                                            # Copy other attributes
                                            for attr, value in note_elem.attrib.items():
                                                if attr not in ['pname', 'oct', 'accid']:
                                                    note[attr] = value
                                            
                                            chord['notes'].append(note)
                                        
                                        # Copy chord attributes
                                        for attr, value in elem.attrib.items():
                                            if attr not in ['dur', 'dots']:
                                                chord[attr] = value
                                        
                                        current_measure['events'].append(chord)
                                    
                                    elif tag in ['mRest', 'mSpace']:
                                        # Handle measure rest or space
                                        event = {
                                            'type': tag,
                                            'layer': layer_n
                                        }
                                        
                                        # Copy attributes
                                        for attr, value in elem.attrib.items():
                                            event[attr] = value
                                        
                                        current_measure['events'].append(event)
                                    
                                    else:
                                        # Handle other elements
                                        event = {
                                            'type': tag,
                                            'layer': layer_n
                                        }
                                        
                                        # Copy attributes
                                        for attr, value in elem.attrib.items():
                                            event[attr] = value
                                        
                                        # Copy text content if any
                                        if elem.text and elem.text.strip():
                                            event['text'] = elem.text.strip()
                                        
                                        current_measure['events'].append(event)
            
            # Return as JSON string
            return json.dumps(result, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to convert MEI to JSON: {str(e)}")
            raise ValueError(f"MEI to JSON conversion failed: {str(e)}")