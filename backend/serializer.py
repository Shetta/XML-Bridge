"""
Serializer Module.

This module provides functionality for serializing and deserializing data
to ensure security and prevent data loss during transformations.

Classes:
    Serializer: Handles serialization and deserialization of data
"""

import base64
import zlib
import json
from typing import Any, Union
import logging


class Serializer:
    """
    Handles serialization and deserialization of data to ensure security
    and prevent data loss during transformations.
    
    This class provides methods to compress, encode, decode, and decompress
    data, as well as JSON serialization for complex data structures.
    
    Attributes:
        logger (logging.Logger): Logger instance for the serializer
    """

    def __init__(self):
        """Initialize the Serializer."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def serialize(self, data: Union[str, dict, list]) -> str:
        """
        Serializes the input data by compressing and encoding it.

        Args:
            data (Union[str, dict, list]): Input data to be serialized.
                Can be a string, dictionary, or list.

        Returns:
            str: Base64-encoded compressed string.

        Raises:
            ValueError: If serialization fails.
        """
        try:
            if isinstance(data, (dict, list)):
                data = json.dumps(data)
            elif not isinstance(data, str):
                raise ValueError("Input must be a string, dictionary, or list")

            compressed_data = zlib.compress(data.encode('utf-8'))
            encoded_data = base64.b64encode(compressed_data).decode('utf-8')
            return encoded_data
        except Exception as e:
            self.logger.error(f"Serialization Error: {str(e)}")
            raise ValueError(f"Serialization Error: {str(e)}")

    def deserialize(self, data: str) -> Any:
        """
        Deserializes the input data by decoding and decompressing it.

        Args:
            data (str): Base64-encoded compressed string.

        Returns:
            Any: Original uncompressed data. Could be a string, dictionary, or list.

        Raises:
            ValueError: If deserialization fails.
        """
        try:
            decoded_data = base64.b64decode(data.encode('utf-8'))
            decompressed_data = zlib.decompress(decoded_data).decode('utf-8')
            
            # Try to parse as JSON, if it fails, return as string
            try:
                return json.loads(decompressed_data)
            except json.JSONDecodeError:
                return decompressed_data
        except Exception as e:
            self.logger.error(f"Deserialization Error: {str(e)}")
            raise ValueError(f"Deserialization Error: {str(e)}")

    def serialize_xml(self, xml_string: str) -> str:
        """
        Serializes XML string data.

        Args:
            xml_string (str): XML string to serialize.

        Returns:
            str: Serialized XML string.

        Raises:
            ValueError: If XML serialization fails.
        """
        return self.serialize(xml_string)

    def deserialize_xml(self, serialized_data: str) -> str:
        """
        Deserializes data back into XML string.

        Args:
            serialized_data (str): Serialized data to deserialize.

        Returns:
            str: Deserialized XML string.

        Raises:
            ValueError: If XML deserialization fails.
        """
        result = self.deserialize(serialized_data)
        if not isinstance(result, str):
            raise ValueError("Deserialized data is not a valid XML string")
        return result

    def serialize_json(self, json_data: Union[dict, list]) -> str:
        """
        Serializes JSON data.

        Args:
            json_data (Union[dict, list]): JSON data to serialize.

        Returns:
            str: Serialized JSON data.

        Raises:
            ValueError: If JSON serialization fails.
        """
        return self.serialize(json_data)

    def deserialize_json(self, serialized_data: str) -> Union[dict, list]:
        """
        Deserializes data back into JSON.

        Args:
            serialized_data (str): Serialized data to deserialize.

        Returns:
            Union[dict, list]: Deserialized JSON data.

        Raises:
            ValueError: If JSON deserialization fails.
        """
        result = self.deserialize(serialized_data)
        if not isinstance(result, (dict, list)):
            raise ValueError("Deserialized data is not valid JSON")
        return result

    def validate_serialized_data(self, data: str) -> bool:
        """
        Validates if the given data is properly serialized.

        Args:
            data (str): Data to validate.

        Returns:
            bool: True if data is valid serialized data, False otherwise.
        """
        try:
            self.deserialize(data)
            return True
        except ValueError:
            return False

    def get_serialized_type(self, serialized_data: str) -> str:
        """
        Attempts to determine the type of the serialized data.

        Args:
            serialized_data (str): Serialized data to check.

        Returns:
            str: 'xml', 'json', or 'unknown'.

        Raises:
            ValueError: If deserialization fails.
        """
        try:
            deserialized = self.deserialize(serialized_data)
            if isinstance(deserialized, str):
                if deserialized.strip().startswith('<'):
                    return 'xml'
                else:
                    return 'unknown'
            elif isinstance(deserialized, (dict, list)):
                return 'json'
            else:
                return 'unknown'
        except ValueError as e:
            self.logger.error(f"Error determining serialized type: {str(e)}")
            raise