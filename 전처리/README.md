# Azure AI HTML Table to Text Converter

This tool converts HTML tables within a document into natural, readable text format using Azure OpenAI Service. It preserves the non-table content and transforms tables into a structured, easily readable format.

## Features

- Detects HTML tables (`<table>` tags) in input files
- Converts tables to natural language text with proper formatting
- Preserves non-table content without modification
- Handles nested tables and merged cells (`rowspan`, `colspan`)
- Outputs results to a file of your choice

## Prerequisites

- Python 3.6+
- Azure OpenAI Service API access
- Required Python packages: `openai`, `python-dotenv`

## Setup

1. Clone or download this repository
2. Install required packages:
   ```
   pip install openai python-dotenv
   ```
3. Create a `.env` file in the same directory as the script with your Azure OpenAI credentials:
   ```
   ENDPOINT_URL=your_azure_endpoint_here
   DEPLOYMENT_NAME=your_deployment_name_here
   AZURE_OPENAI_KEY=your_api_key_here
   ```

## Usage

### Command Line Interface

Run the script with the input file path:

```bash
python azure_table_to_text.py -i input_file.html -o output_file.txt
```

If you don't specify an output file, the result will be saved to `[input_filename]_processed.txt`.

### As a Module

You can also import and use the script as a module in your own code:

```python
from azure_table_to_text import process_file

# Process a file and get the result
processed_text = process_file('input_file.html', 'output_file.txt')
print(processed_text)
```

## How It Works

1. The script reads the input file containing HTML tables
2. It sends the content to Azure OpenAI Service with a specific prompt
3. The AI transforms tables into natural language text while preserving non-table content
4. The result is saved to the specified output file

## Example

### Input:

```html
<table>
  <tr>
    <th>항목</th>
    <th>내용</th>
  </tr>
  <tr>
    <td>임대기간</td>
    <td>2년 (최대 10년 연장 가능)</td>
  </tr>
  <tr>
    <td>보증금</td>
    <td>100만원</td>
  </tr>
  <tr>
    <td>월세</td>
    <td>30만원</td>
  </tr>
</table>
```

### Output:

```
■ 항목별 조건
- 임대기간: 2년 (최대 10년까지 연장 가능)
- 보증금: 100만원
- 월세: 30만원
```

## Notes

- The Azure AI system prompt is configured in Korean, designed to handle Korean language tables
- If you need to process tables in other languages, you may need to modify the system prompt
- Maximum output token limit is set to 800, adjust as needed for larger documents
