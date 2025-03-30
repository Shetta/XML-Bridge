# XML-Bridge

XML Bridge is a specialized tool for converting between different music notation formats, with a focus on preserving early music notation features. It provides seamless transformation between CMME (Computerized Mensural Music Editing), MEI (Music Encoding Initiative), and JSON formats.

## Overview

Early music notation (pre-1600) contains unique features that are challenging to convert between different formats. XML Bridge addresses these challenges by providing both standard and interactive conversion options, ensuring accurate preservation of musical content across format boundaries.

The application offers format conversion between CMME, MEI, and JSON; interactive conversion for complex musical structures; quality evaluation of conversions; dataset management for storing and organizing music files; sample datasets for testing and learning; and support for early music notation features including mensural notation, ligatures, and coloration.

## Features

### Standard Conversion

Standard conversion provides a quick, one-click transformation between formats. This works well for modern notation without complex early music features. The supported conversion paths include CMME to MEI, MEI to CMME, CMME to JSON, MEI to JSON, JSON to CMME, and JSON to MEI.

### Interactive Conversion

For files with early music notation or ambiguous features, the interactive conversion mode guides you through the process with decision points for manual intervention. This helps preserve specialized notation features that might be lost in automatic conversion.

### Conversion Evaluation

The evaluation component analyzes conversion quality by examining accuracy score, element preservation rates, data loss detection, structural integrity measurement, and format-specific feature analysis.

### Dataset Management

The dataset manager provides tools for organizing, storing, and validating music notation files. You can create collections of related files across different formats and add metadata for better organization.

## Getting Started

### Installation

First, clone the repository by running `git clone https://github.com/yourusername/xml-bridge.git`, then enter the directory with `cd xml-bridge`. Next, set up a virtual environment with `python -m venv venv` and activate it using `source venv/bin/activate` (on Windows, use `venv\Scripts\activate`). After that, install dependencies by running `pip install -r requirements.txt`. Finally, initialize the application with `python app.py`. The server will start at http://localhost:8000 by default.

### Usage Examples

#### Basic Conversion

To convert a CMME file to MEI format through the web interface, open http://localhost:8000 in your browser, select "CMME" as source format and "MEI" as target format, upload or drag-and-drop your CMME file, and click "Convert".

#### Command Line Usage

For batch processing, you can use the API directly. To convert CMME to MEI, use `curl -X POST -F "file=@path/to/your/file.xml" http://localhost:8000/transform?type=cmme-to-mei -o output.xml`. To extract metadata from a file, use `curl -X POST -F "file=@path/to/your/file.xml" http://localhost:8000/metadata?type=cmme`.

#### Working with Early Music Notation

Consider this example of CMME notation with mensural features:

```xml
<cmme>
  <metadata>
    <title>Early Music Example</title>
    <composer>Anonymous</composer>
    <date>1500</date>
  </metadata>
  <score>
    <staff name="Tenor">
      <clef shape="C" line="4"/>
      <measure number="1">
        <note pitch="G3" duration="brevis">
          <ligature position="start"/>
        </note>
        <note pitch="A3" duration="semibrevis">
          <ligature position="end"/>
        </note>
      </measure>
    </staff>
  </score>
</cmme>
```

For this file, you would use interactive conversion to ensure the ligature notation is properly handled in the target format.

## Understanding Early Music Notation

XML Bridge handles several specialized early music notation features. Mensural Notation includes note values like maxima, longa, brevis not found in modern notation. Ligatures represent groups of notes written as a single unit. Coloration refers to note coloring indicating rhythmic alterations. Mensuration Signs are early time signatures (e.g., C, O, C.). Musica Ficta consists of editorial accidentals indicated with special notation.

## Project Structure

The backend directory contains core conversion logic and processing modules such as base.py which provides the base transformer class with common functionality; cmme_parser.py which is the parser for CMME format; mei_parser.py which handles the parser for MEI format; json_converter.py which manages the converter for JSON format; transformer.py which orchestrates main transformation operations; dataset.py which contains the dataset management functionality; evaluation.py which provides conversion quality evaluation; interactive.py which handles interactive conversion processing; and serializer.py which contains data serialization utilities. The static directory contains frontend assets including CSS and JavaScript. The templates directory stores HTML templates for the web interface. The app.py file serves as the main application entry point and API routes.

## Contributing

We welcome contributions to XML Bridge. If you're interested in early music notation or music encoding standards, your expertise would be particularly valuable. Some areas where you can contribute include adding support for additional early music notation features, improving conversion accuracy between formats, enhancing the interactive conversion interface, adding support for additional music notation formats, and expanding the sample datasets.

## Citation

If you use XML Bridge in your research, please cite it as: "XML Bridge: A Tool for Converting Early Music Notation Between Formats. https://github.com/Shetta/XML-Bridge".

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

This project builds upon the work of the music encoding community, particularly the Music Encoding Initiative (MEI) community, the Computerized Mensural Music Editing (CMME) project, and researchers and practitioners in the field of early music notation.
