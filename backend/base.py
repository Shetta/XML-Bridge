"""
Base Transformer Module.

This module provides the base class for music notation format transformers.
It defines the common interface and functionality that all format-specific
transformers must implement.

Classes:
    BaseTransformer: Abstract base class for music notation transformers
"""

from abc import ABC, abstractmethod
from lxml import etree
from typing import Dict, List, Optional, Union, Any
import logging
import os


class BaseTransformer(ABC):
    """
    Abstract base class for music notation format transformers.
    
    This class defines the interface that all format-specific transformers
    must implement. It provides basic functionality for XML validation
    and parsing.
    
    Attributes:
        schema (Optional[etree.XMLSchema]): XML Schema for validation
        logger (logging.Logger): Logger instance for the transformer
        schema_path (Optional[str]): Path to the XML schema file
    """
    
    def __init__(self, schema_path: Optional[str] = None):
        """
        Initialize the base transformer.

        Args:
            schema_path (Optional[str]): Path to XML schema file for validation

        Raises:
            ValueError: If schema file cannot be loaded
        """
        self.schema = None
        self.schema_path = schema_path
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        if schema_path:
            try:
                if not os.path.exists(schema_path):
                    raise ValueError(f"Schema file not found: {schema_path}")
                    
                schema_doc = etree.parse(schema_path)
                self.schema = etree.XMLSchema(schema_doc)
                self.logger.info(f"Loaded schema from {schema_path}")
            except (etree.ParseError, IOError) as e:
                self.logger.error(f"Failed to load schema: {str(e)}")
                raise ValueError(f"Failed to load schema: {str(e)}")

    @abstractmethod
    def validate(self, xml_string: str) -> None:
        """
        Validate XML structure against schema and rules.

        Args:
            xml_string (str): XML content to validate

        Raises:
            ValueError: If validation fails
            NotImplementedError: If not implemented by subclass
        """
        pass
    
    @abstractmethod
    def parse(self, xml_string: str) -> Union[List[etree._Element], Dict[str, Any]]:
        """
        Parse XML into structured data.

        Args:
            xml_string (str): XML content to parse

        Returns:
            Union[List[etree._Element], Dict[str, Any]]: Parsed musical data

        Raises:
            ValueError: If parsing fails
            NotImplementedError: If not implemented by subclass
        """
        pass
    
    @abstractmethod
    def extract_metadata(self, root: etree._Element) -> Dict[str, Any]:
        """
        Extract metadata from XML document.

        Args:
            root (etree._Element): Root element of XML document

        Returns:
            Dict[str, Any]: Extracted metadata

        Raises:
            NotImplementedError: If not implemented by subclass
        """
        pass

    def _validate_xml_syntax(self, xml_string: str) -> etree._Element:
        """
        Validate basic XML syntax and return parsed root element.

        Args:
            xml_string (str): XML content to validate

        Returns:
            etree._Element: Parsed XML root element

        Raises:
            ValueError: If XML syntax is invalid
        """
        try:
            return etree.fromstring(xml_string)
        except etree.ParseError as e:
            self.logger.error(f"XML syntax error: {str(e)}")
            raise ValueError(f"Invalid XML syntax: {str(e)}")

    def _validate_schema(self, root: etree._Element) -> None:
        """
        Validate XML against schema if available.

        Args:
            root (etree._Element): Root element to validate

        Raises:
            ValueError: If validation against schema fails
        """
        if self.schema is not None:
            try:
                self.schema.assertValid(root)
            except etree.DocumentInvalid as e:
                self.logger.error(f"Schema validation failed: {str(e)}")
                raise ValueError(f"Document does not match schema: {str(e)}")

    def _get_element_path(self, element: etree._Element) -> str:
        """
        Get XPath-like string representation of element's location.

        Args:
            element (etree._Element): Element to get path for

        Returns:
            str: XPath-like location string
        """
        path_parts = []
        current = element
        while current is not None:
            if current.getparent() is not None:
                siblings = current.getparent().findall(current.tag)
                if len(siblings) > 1:
                    index = siblings.index(current) + 1
                    path_parts.append(f"{current.tag}[{index}]")
                else:
                    path_parts.append(current.tag)
            else:
                path_parts.append(current.tag)
            current = current.getparent()
        return '/' + '/'.join(reversed(path_parts))

    def _check_required_attributes(
        self,
        element: etree._Element,
        required_attrs: List[str],
        context: str = ""
    ) -> None:
        """
        Check if element has all required attributes.

        Args:
            element (etree._Element): Element to check
            required_attrs (List[str]): List of required attribute names
            context (str): Additional context for error messages

        Raises:
            ValueError: If any required attributes are missing
        """
        missing_attrs = [
            attr for attr in required_attrs if attr not in element.attrib
        ]
        if missing_attrs:
            path = self._get_element_path(element)
            error_msg = f"Missing required attributes {missing_attrs} at {path}"
            if context:
                error_msg += f" ({context})"
            self.logger.error(error_msg)
            raise ValueError(error_msg)

    def _validate_attribute_values(
        self,
        element: etree._Element,
        validations: Dict[str, List[str]],
        context: str = ""
    ) -> None:
        """
        Validate attribute values against allowed values.

        Args:
            element (etree._Element): Element to validate
            validations (Dict[str, List[str]]): Dictionary of attribute names
                and their allowed values
            context (str): Additional context for error messages

        Raises:
            ValueError: If any attribute values are invalid
        """
        for attr, allowed_values in validations.items():
            if attr in element.attrib and element.get(attr) not in allowed_values:
                path = self._get_element_path(element)
                error_msg = (
                    f"Invalid value '{element.get(attr)}' for attribute '{attr}' "
                    f"at {path}. Allowed values: {allowed_values}"
                )
                if context:
                    error_msg += f" ({context})"
                self.logger.error(error_msg)
                raise ValueError(error_msg)

    def _validate_child_elements(
        self,
        element: etree._Element,
        required_children: List[str],
        context: str = ""
    ) -> None:
        """
        Validate presence of required child elements.

        Args:
            element (etree._Element): Parent element to check
            required_children (List[str]): List of required child element names
            context (str): Additional context for error messages

        Raises:
            ValueError: If any required child elements are missing
        """
        for child_name in required_children:
            if element.find(child_name) is None:
                path = self._get_element_path(element)
                error_msg = f"Missing required child element '{child_name}' at {path}"
                if context:
                    error_msg += f" ({context})"
                self.logger.error(error_msg)
                raise ValueError(error_msg)

    def get_schema_path(self) -> Optional[str]:
        """
        Get the path to the currently loaded schema file.

        Returns:
            Optional[str]: Path to the schema file or None if no schema is loaded
        """
        return self.schema_path

    def has_schema(self) -> bool:
        """
        Check if a schema is loaded.

        Returns:
            bool: True if a schema is loaded, False otherwise
        """
        return self.schema is not None